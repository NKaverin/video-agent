import math

INTERCEPT_S = -0.0262
PER_CHAR_S = 0.05152

MIN_MARGIN_S = 0.5
MARGIN_FACTOR = 1.12


def speaking_s(text: str) -> float:
    return INTERCEPT_S + PER_CHAR_S * len(text)


def reserverd_s(text: str) -> float:
    speaking = speaking_s(text)
    return max(speaking + MIN_MARGIN_S, speaking * MARGIN_FACTOR)


def max_chars(seconds: float) -> int:
    by_min_margin = (seconds - MIN_MARGIN_S - INTERCEPT_S) / PER_CHAR_S
    by_factor = (seconds / MARGIN_FACTOR - INTERCEPT_S) / PER_CHAR_S
    return max(0, math.floor(min(by_min_margin, by_factor)))


def budget_table() -> str:
    return "\n".join(
        str(seconds) + " s: " + str(max_chars(seconds)) + " characters"
        for seconds in range(2, 11)
    )
