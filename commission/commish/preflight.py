"""First-run checks.

The roast is the frame, never the substitute: whatever the tone, the message has
to leave someone able to fix the problem in the next minute.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from .telemetry import HOME


ENV_FILE = Path.home() / ".commish.env"


def load_env_file() -> None:
    """Read ~/.commish.env if it exists, without overriding a real environment.

    Having to `source` something before every review is the kind of friction
    that quietly kills a tool. The file is the user's own, mode 600 by
    convention, and anything already exported wins.
    """
    if not ENV_FILE.exists():
        return
    try:
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            key, sep, value = line.partition("=")
            if not sep:
                continue
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


def credentials_present(provider: str = "bedrock") -> bool:
    """For OpenRouter, the key. For Bedrock, any credential it will accept: a
    Bedrock API key, static keys, a profile, an assumed role, or instance
    metadata."""
    load_env_file()
    if provider == "openrouter":
        return bool(os.environ.get("OPENROUTER_API_KEY"))
    if os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        return True
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return True
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        return boto3.Session().get_credentials() is not None
    except ImportError:
        return False
    except (BotoCoreError, ClientError):
        return False


def credential_source(provider: str) -> str:
    """Which variable is doing the work -- never its value."""
    if provider == "openrouter":
        return "OPENROUTER_API_KEY"
    if os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        return "AWS_BEARER_TOKEN_BEDROCK"
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        return "AWS_ACCESS_KEY_ID"
    return "profile or instance role"


def is_first_run() -> bool:
    return not HOME.exists()


def _rule(width: int = 74) -> str:
    return "─" * width


NO_CREDENTIALS = """
{rule}

  You come to me and you ask for a review.

  You ask without respect. You offer no credentials. You did not even
  think to make a key. The Commission does not sit for free, and it
  does not sit for strangers.

  Make the key. Then we talk.

{rule}

  1. Generate a Bedrock API key — the short way in, no IAM console,
     no roles to assume:

       https://console.aws.amazon.com/bedrock  →  API keys  →  Generate

     ⚠ When it asks about permissions, grant **AmazonBedrockFullAccess**.
       The narrower default lets the key authenticate and then refuses
       every model call, which looks like a broken tool rather than a
       missing permission. This is the step people get wrong.

  2. Put it where this tool will find it. Either export it:

       export AWS_BEARER_TOKEN_BEDROCK=ABSK...
       export AWS_REGION=us-east-1

     or write those two lines into ~/.commish.env and forget about it —
     that file is read automatically and never overrides a real
     environment variable:

       printf 'export AWS_BEARER_TOKEN_BEDROCK=ABSK...\n'\
              'export AWS_REGION=us-east-1\n' > ~/.commish.env
       chmod 600 ~/.commish.env

     Long-lived credentials work too: AWS_ACCESS_KEY_ID and
     AWS_SECRET_ACCESS_KEY, an AWS_PROFILE, or an instance role.

  3. Enable the models. Access is off by default, granted per account
     and per region, and this is separate from the key's permissions:

       https://console.aws.amazon.com/bedrock  →  Model access
                                              →  Modify model access

     Enable at least two vendors besides the one you write code with.
     Some are region-locked or country-locked; Bedrock will say so.

  4. Confirm the whole chain before trusting it:

       commish doctor

  No AWS account? OpenRouter works too — one key, every vendor, and
  OpenAI and Google come with it:

       https://openrouter.ai/keys  →  Create key
       export OPENROUTER_API_KEY=sk-or-...      # or put it in ~/.commish.env

  With only that key set, the Commission picks OpenRouter by itself.
  With both, it prefers Bedrock; say `provider: openrouter` in
  .commish.yml, COMMISH_PROVIDER=openrouter, or --provider openrouter.

{rule}
"""

NO_OPENROUTER_KEY = """
{rule}

  You asked for OpenRouter and brought no key. The Commission does not
  sit for free.

{rule}

  1. Make a key, and put a few dollars of credit on the account —
     a key on an empty account authenticates and then refuses:

       https://openrouter.ai/keys  →  Create key

  2. Put it where this tool will find it:

       export OPENROUTER_API_KEY=sk-or-...

     or write that line into ~/.commish.env, read automatically:

       printf 'export OPENROUTER_API_KEY=sk-or-...\n' >> ~/.commish.env
       chmod 600 ~/.commish.env

  3. Confirm the whole chain:

       commish --provider openrouter doctor

{rule}
"""

OPENROUTER_REFUSED = """
{rule}

  OpenRouter heard you. It did not serve you.

  1. 401 — the key is wrong, revoked, or not the one you think is set.
       https://openrouter.ai/keys

  2. 402 — the account is out of credit. Every model refuses at once,
     which looks like a broken tool and is a billing page:
       https://openrouter.ai/credits

  3. 403 / 404 — the key is restricted (a model allowlist, a provider
     filter, data-policy settings that exclude every host of a model),
     or the model id is wrong:
       https://openrouter.ai/settings/privacy

  Then:

       commish models      # every id OpenRouter will take
       commish doctor      # whether your configured models answer

{rule}
"""

ACCESS_DENIED = """
{rule}

  The key is good. The door is not open.

  Your credentials authenticated. The models did not answer. There are
  exactly two reasons for that, and they are fixed in different places:

  1. The key lacks permission.
     A Bedrock API key generated with the narrow default can call
     almost nothing. Reissue it with **AmazonBedrockFullAccess**, or
     attach that policy to the IAM identity you are using:

       https://console.aws.amazon.com/bedrock  →  API keys

  2. The models are not enabled in this account and region.
     Bedrock ships with model access switched off. It is granted per
     account, per region, and some models are restricted by country:

       https://console.aws.amazon.com/bedrock  →  Model access
                                              →  Modify model access

  Then:

       commish models      # what this account and region will serve
       commish doctor      # whether your configured models answer

  Put the ids that work into .commish.yml. A Commission drawn from one
  vendor is not a Commission — models that share a vendor share their
  blind spots, and their agreement is not evidence of anything.

{rule}
"""

FIRST_RUN = """
  First sit-down. Reviewers run through {via} — one credential, every
  vendor — and everything is recorded locally in {home} and never leaves
  this machine. Turn it off with COMMISH_NO_TELEMETRY=1.
"""

_VIA = {"bedrock": "AWS Bedrock", "openrouter": "OpenRouter"}


def no_credentials_message(provider: str = "bedrock") -> str:
    template = NO_OPENROUTER_KEY if provider == "openrouter" else NO_CREDENTIALS
    return template.format(rule=_rule())


def access_denied_message(provider: str = "bedrock") -> str:
    template = OPENROUTER_REFUSED if provider == "openrouter" else ACCESS_DENIED
    return template.format(rule=_rule())


def first_run_message(provider: str = "bedrock") -> str:
    return FIRST_RUN.format(home=HOME, via=_VIA.get(provider, provider))


def check(provider: str = "bedrock") -> str | None:
    """Returns a message to print and exit on, or None to proceed."""
    if not credentials_present(provider):
        return no_credentials_message(provider)
    return None
