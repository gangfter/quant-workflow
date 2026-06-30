"""Validation helpers for research scripts."""


def assert_min_bars(panel_or_count, required, context="research"):
    """Raise when a research input has fewer bars than required.

    Args:
        panel_or_count: A DataFrame-like object with ``len()`` or an integer.
        required: Minimum required bar count.
        context: Short label included in the error message.
    """
    actual = (
        int(panel_or_count)
        if isinstance(panel_or_count, int)
        else len(panel_or_count)
    )
    required = int(required)
    if actual < required:
        raise ValueError(
            f"{context}: insufficient bars: actual={actual}, required={required}"
        )
    return None
