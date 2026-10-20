"""Strict UTF-8 JSON at the external decision boundary."""
import json
import re


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _constant(value):
    raise ValueError(f"nonfinite JSON value: {value}")


def loads(text, limit=16384):
    if len(text.encode("utf-8")) > limit:
        raise ValueError("PAYLOAD_TOO_LARGE")
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)
    except (RecursionError, OverflowError) as error:
        raise ValueError("JSON nesting or numeric value exceeds parser limits") from error
    # Bound nesting independently of JSON parser's host recursion limit.
    def check(item, depth=0):
        if depth > 5:
            raise ValueError("JSON nesting exceeds limit")
        if isinstance(item, dict):
            for key, v in item.items():
                key.encode("utf-8", errors="strict")
                check(v, depth + 1)
        elif isinstance(item, list):
            if len(item) > 64:
                raise ValueError("JSON array too large")
            for v in item:
                check(v, depth + 1)
        elif isinstance(item, str):
            if len(item.encode("utf-8", errors="strict")) > 4096:
                raise ValueError("string too large")
    check(value)
    return value


def dumps(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def counter(value):
    if type(value) is not str or not re.fullmatch(r"0|[1-9][0-9]{0,19}", value) or int(value) > 2**64-1:
        raise ValueError("expected canonical uint64 decimal string")
    return int(value)
