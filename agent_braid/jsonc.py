# SPDX-License-Identifier: AGPL-3.0-only
"""Side-effect-free JSONC reading: comments, trailing commas and member spans.

Standard library only. ``clean`` blanks ``//`` and ``/* */`` comments and trailing
commas without changing any offset, so spans measured on the cleaned text address
the original text exactly. ``members`` returns the same spans as the strict JSON
scanner in ``tooling_install`` and is used to rewrite only one member.
"""
from __future__ import annotations

from dataclasses import dataclass
import json


class JsoncError(ValueError):
    """The text is not valid JSONC."""


@dataclass(frozen=True)
class Cleaned:
    text: str                      # same length as the input; strict JSON
    trailing: tuple[int, ...]      # offsets of blanked trailing commas


def clean(text: str) -> Cleaned:
    out = list(text)
    trailing = []
    pending = None  # a comma whose next significant character is not yet known
    previous = ""   # last significant character (strings count as '"')
    i = 0
    size = len(text)
    while i < size:
        c = text[i]
        if c == '"':
            pending = None
            previous = '"'
            i += 1
            while i < size and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            if i >= size:
                raise JsoncError("unterminated string")
        elif c == "/" and text[i + 1:i + 2] == "/":
            while i < size and text[i] not in "\r\n":
                out[i] = " "
                i += 1
            continue
        elif c == "/" and text[i + 1:i + 2] == "*":
            end = text.find("*/", i + 2)
            if end < 0:
                raise JsoncError("unterminated block comment")
            for j in range(i, end + 2):
                if text[j] not in "\r\n":
                    out[j] = " "
            i = end + 2
            continue
        elif c == ",":
            # A comma directly after '{', '[', ',' or ':' can never be a trailing comma.
            pending = None if previous in ("{", "[", ",", ":", "") else i
            previous = ","
        elif not c.isspace():
            if c in "}]" and pending is not None:
                out[pending] = " "
                trailing.append(pending)
            pending = None
            previous = c
        i += 1
    return Cleaned("".join(out), tuple(trailing))


def parse(text: str):
    """Parse JSONC; duplicate members and non-finite numbers are errors."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise JsoncError("duplicate JSON member")
            result[key] = value
        return result

    def constant(_value):
        raise JsoncError("nonfinite JSON value")
    try:
        return json.loads(clean(text).text, object_pairs_hook=pairs, parse_constant=constant)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise JsoncError(f"invalid JSONC: {exc}") from exc


def members(cleaned: str, start: int = 0):
    """Return ``(opening, closing, [(key, key_start, value_start, value_end)])``.

    ``cleaned`` is ``clean(text).text``; the object must start at ``start``.
    """
    decoder = json.JSONDecoder()
    try:
        i = start
        while cleaned[i].isspace():
            i += 1
        if cleaned[i] != "{":
            raise JsoncError("member must be an object")
        opening = i
        i += 1
        found = []
        while True:
            while cleaned[i].isspace():
                i += 1
            if cleaned[i] == "}":
                return opening, i, found
            key_start = i
            key, i = decoder.raw_decode(cleaned, i)
            while cleaned[i].isspace():
                i += 1
            if cleaned[i] != ":":
                raise JsoncError("invalid JSON member")
            i += 1
            while cleaned[i].isspace():
                i += 1
            value_start = i
            _, value_end = decoder.raw_decode(cleaned, i)
            found.append((key, key_start, value_start, value_end))
            i = value_end
            while cleaned[i].isspace():
                i += 1
            if cleaned[i] == ",":
                i += 1
            elif cleaned[i] != "}":
                raise JsoncError("invalid JSON object")
            else:
                return opening, i, found
    except (IndexError, json.JSONDecodeError) as exc:
        raise JsoncError("invalid JSON object") from exc
