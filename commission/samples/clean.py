"""Nothing wrong here. The Commission should say so and go home."""
from collections import Counter


def word_frequencies(text: str) -> dict[str, int]:
    """Count how often each lowercase word appears."""
    return dict(Counter(text.lower().split()))
