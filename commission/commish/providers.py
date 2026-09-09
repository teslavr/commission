"""Bedrock access. One credential, many vendors -- that is why we are here."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError


class ModelError(RuntimeError):
    """A single panel member failed. The panel survives; the member is dropped."""


@dataclass
class ModelReply:
    model_id: str
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


def runtime_client(region: str):
    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=BotoConfig(read_timeout=600, connect_timeout=15, retries={"max_attempts": 3}),
    )


def converse(client, model_id: str, system: str, user: str, max_tokens: int = 8000) -> ModelReply:
    """Bedrock's Converse API speaks one shape for every vendor on the panel.

    Note: no temperature. Recent Anthropic models reject sampling parameters,
    and the defaults are what we want anyway.
    """
    try:
        response = client.converse(
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


def list_available_models(region: str) -> list[dict]:
    """What can this account actually call today? Model access is off by default."""
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
