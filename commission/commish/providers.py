"""Model access. One credential, many vendors -- that is why we are here.

Two ways to get that one credential: AWS Bedrock, or OpenRouter. Both speak one
request shape for every vendor, so the rest of the tool never knows which.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


class ModelError(RuntimeError):
    """A single panel member failed. The panel survives; the member is dropped."""


@dataclass
class ModelReply:
    model_id: str
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


class BedrockClient:
    provider = "bedrock"

    def __init__(self, region: str):
        import boto3
        from botocore.config import Config as BotoConfig

        self.region = region
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=BotoConfig(read_timeout=600, connect_timeout=15, retries={"max_attempts": 3}),
        )

    def converse(self, model_id: str, system: str, user: str, max_tokens: int) -> ModelReply:
        """Bedrock's Converse API speaks one shape for every vendor on the panel.

        Note: no temperature. Recent Anthropic models reject sampling parameters,
        and the defaults are what we want anyway.
        """
        from botocore.exceptions import ClientError

        try:
            response = self._client.converse(
                modelId=model_id,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": user}]}],
                inferenceConfig={"maxTokens": max_tokens},
            )
        except ClientError as exc:
            raise ModelError(f"{model_id}: {exc.response['Error']['Message']}") from exc

        blocks = response["output"]["message"]["content"]
        text = "".join(b.get("text", "") for b in blocks)
        usage = response.get("usage", {})
        return ModelReply(
            model_id=model_id,
            text=text,
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
        )


OPENROUTER_URL = "https://openrouter.ai/api/v1"

# Statuses worth a second try: OpenRouter falls over to another upstream on
# retry, so a 502 from one host is often a 200 from the next.
_RETRYABLE = {408, 429, 500, 502, 503, 504}

# Turn HTTP codes into words the rest of the tool (and telemetry) already keys on.
_OPENROUTER_STATUS = {
    400: "ValidationException",
    401: "Unauthorized: bad or missing OPENROUTER_API_KEY credential",
    402: "InsufficientCredits",
    403: "AccessDenied",
    404: "not available for this account",
    408: "timeout",
    429: "throttled",
}


class OpenRouterClient:
    provider = "openrouter"

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = (base_url or os.environ.get("OPENROUTER_BASE_URL") or OPENROUTER_URL).rstrip("/")

    def _request(self, path: str, body: dict | None = None, timeout: float = 600) -> dict:
        headers = {
            "Content-Type": "application/json",
            # Attribution for OpenRouter's app rankings; harmless if ignored.
            "HTTP-Referer": "https://github.com/teslavr/commission",
            "X-Title": "The Commission",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base_url + path, data=data, headers=headers,
                                     method="POST" if data is not None else "GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())

    def converse(self, model_id: str, system: str, user: str, max_tokens: int) -> ModelReply:
        body = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            # The review is the answer; a reasoning model's scratchpad is not.
            "reasoning": {"exclude": True},
        }
        payload = None
        for attempt in range(3):
            try:
                payload = self._request("/chat/completions", body)
                break
            except urllib.error.HTTPError as exc:
                detail = _error_detail(exc)
                label = _OPENROUTER_STATUS.get(exc.code, f"HTTP {exc.code}")
                if exc.code in _RETRYABLE and attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise ModelError(f"{model_id}: {label} — {detail}") from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise ModelError(f"{model_id}: timeout or network error — {exc}") from exc

        # OpenRouter can answer 200 and still carry an upstream error.
        if payload.get("error"):
            err = payload["error"]
            raise ModelError(f"{model_id}: {err.get('message', err)}")
        choices = payload.get("choices") or []
        if not choices:
            raise ModelError(f"{model_id}: empty response")
        choice = choices[0]
        if choice.get("error"):
            raise ModelError(f"{model_id}: {choice['error'].get('message', choice['error'])}")

        content = (choice.get("message") or {}).get("content") or ""
        if isinstance(content, list):  # some upstreams return content parts
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not content.strip() and choice.get("finish_reason") == "length":
            raise ModelError(f"{model_id}: ran out of max_tokens before answering "
                             "(raise max_tokens in .commish.yml)")

        usage = payload.get("usage") or {}
        return ModelReply(
            model_id=model_id,
            text=content,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
        )

    def models(self) -> list[dict]:
        return self._request("/models", timeout=30).get("data", [])


def _error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        body = json.loads(exc.read().decode())
        err = body.get("error", body)
        return str(err.get("message", err) if isinstance(err, dict) else err)[:300]
    except Exception:
        return exc.reason or ""


def runtime_client(cfg):
    """A client for whichever provider the config settled on."""
    if cfg.provider == "openrouter":
        return OpenRouterClient()
    return BedrockClient(cfg.region)


def converse(client, model_id: str, system: str, user: str, max_tokens: int = 8000) -> ModelReply:
    return client.converse(model_id, system, user, max_tokens)


_FENCE = re.compile(r"```(?:[a-zA-Z]*)?\s*(.*?)```", re.DOTALL)
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")

FINDINGS_TAG = "===FINDINGS==="
FIX_TAG = "===FIX==="


def parse_json(text: str) -> dict:
    """JSON only, and only ever small values -- see split_reply for why."""
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1)
    text = text.strip()

    candidates = [text]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])

    last = None
    for candidate in candidates:
        for attempt in (candidate, _TRAILING_COMMA.sub(r"\1", candidate)):
            try:
                return json.loads(attempt)
            except json.JSONDecodeError as exc:
                last = exc
    raise ModelError(f"could not parse JSON from model output: {last}")


def split_reply(text: str) -> tuple[dict, str | None]:
    """Findings as JSON, source code as plain text after a delimiter.

    Asking a model to embed a whole source file inside a JSON string is asking it
    to escape every newline and quote in that file. Strong models manage it;
    weaker ones do not, and we lose a vendor from the committee over punctuation.
    So the code never enters the JSON at all.
    """
    if FIX_TAG in text:
        head, _, tail = text.partition(FIX_TAG)
        code = tail.strip()
        fenced = _FENCE.search(code)
        if fenced:
            code = fenced.group(1)
        code = code.strip() or None
    else:
        head, code = text, None

    head = head.replace(FINDINGS_TAG, "")
    return parse_json(head), code


def list_available_models(cfg) -> list[dict]:
    """What can this account actually call today?"""
    if cfg.provider == "openrouter":
        return _openrouter_models()
    return _bedrock_models(cfg.region)


def _openrouter_models() -> list[dict]:
    """OpenRouter serves every listed model to every key with credits; the
    list is the price list. Text-out models only, the rest cannot review."""
    rows: list[dict] = []
    for model in OpenRouterClient().models():
        outputs = (model.get("architecture") or {}).get("output_modalities") or ["text"]
        if "text" not in outputs or model["id"].endswith(":batch"):
            continue
        pricing = model.get("pricing") or {}
        try:
            price = (f"${float(pricing.get('prompt', 0)) * 1e6:.2f} / "
                     f"${float(pricing.get('completion', 0)) * 1e6:.2f} per 1M")
        except (TypeError, ValueError):
            price = ""
        rows.append({"id": model["id"], "name": model.get("name", ""),
                     "kind": "openrouter", "status": price})
    return rows


def _bedrock_models(region: str) -> list[dict]:
    """Model access is off by default on Bedrock, so this list is the truth."""
    import boto3

    client = boto3.client("bedrock", region_name=region)
    rows: list[dict] = []
    profiles = client.list_inference_profiles(maxResults=100)
    for profile in profiles.get("inferenceProfileSummaries", []):
        rows.append(
            {
                "id": profile["inferenceProfileId"],
                "name": profile.get("inferenceProfileName", ""),
                "kind": "inference-profile",
                "status": profile.get("status", ""),
            }
        )

    foundation = client.list_foundation_models(byOutputModality="TEXT")
    for model in foundation.get("modelSummaries", []):
        rows.append(
            {
                "id": model["modelId"],
                "name": f"{model.get('providerName', '')} {model.get('modelName', '')}".strip(),
                "kind": "foundation-model",
                "status": ",".join(model.get("modelLifecycle", {}).get("status", "") or []),
            }
        )
    return rows
