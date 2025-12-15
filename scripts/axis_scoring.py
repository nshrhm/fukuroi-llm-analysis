from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
from typing import Any, Iterable

import yaml


@dataclasses.dataclass(frozen=True)
class AxisSpec:
    id: str
    name: str
    left_label: str
    right_label: str
    left_desc: str
    right_desc: str


@dataclasses.dataclass(frozen=True)
class DictionaryWeights:
    keyword_present: float
    regex_present: float


def load_axis_config(path: str) -> tuple[list[AxisSpec], dict[str, Any], DictionaryWeights]:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    axes = [
        AxisSpec(
            id=a["id"],
            name=a["name"],
            left_label=a["left_label"],
            right_label=a["right_label"],
            left_desc=a["left_desc"],
            right_desc=a["right_desc"],
        )
        for a in cfg["axes"]
    ]

    dict_cfg = cfg.get("dictionary", {})
    w = dict_cfg.get("weights", {})
    weights = DictionaryWeights(
        keyword_present=float(w.get("keyword_present", 1.0)),
        regex_present=float(w.get("regex_present", 1.0)),
    )
    return axes, dict_cfg, weights


def stable_text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def normalize_text_for_matching(text: str) -> str:
    return str(text).replace("\r", "\n")


_SENT_SPLIT_RE = re.compile(r"(?<=[。！？!?])\s+|\n+")


def split_sentences(text: str, max_len: int = 140) -> list[str]:
    text = normalize_text_for_matching(text)
    parts = [p.strip() for p in _SENT_SPLIT_RE.split(text) if p and p.strip()]
    out: list[str] = []
    for p in parts:
        if len(p) <= max_len:
            out.append(p)
            continue
        out.append(p[: max_len - 1] + "…")
    return out


def _has_any_keyword(sentence: str, keywords: Iterable[str]) -> bool:
    for kw in keywords:
        if kw and kw in sentence:
            return True
    return False


def _has_any_regex(sentence: str, regexes: Iterable[str]) -> bool:
    for pat in regexes:
        if pat and re.search(pat, sentence):
            return True
    return False


def extract_evidence_sentences(
    text: str,
    left_keywords: list[str],
    right_keywords: list[str],
    left_regex: list[str] | None = None,
    right_regex: list[str] | None = None,
    limit: int = 3,
) -> list[str]:
    left_regex = left_regex or []
    right_regex = right_regex or []
    sents = split_sentences(text)

    picked: list[str] = []
    for s in sents:
        if _has_any_keyword(s, left_keywords) or _has_any_regex(s, left_regex):
            picked.append(s)
        elif _has_any_keyword(s, right_keywords) or _has_any_regex(s, right_regex):
            picked.append(s)
        if len(picked) >= limit:
            break

    dedup: list[str] = []
    seen = set()
    for s in picked:
        if s in seen:
            continue
        seen.add(s)
        dedup.append(s)
    return dedup


def _present_count(text: str, keywords: list[str]) -> int:
    return int(sum(1 for kw in keywords if kw and kw in text))


def _present_regex_count(text: str, regexes: list[str]) -> int:
    return int(sum(1 for pat in regexes if pat and re.search(pat, text)))


def dictionary_raw_signal(
    text: str,
    axis_dict: dict[str, Any],
    weights: DictionaryWeights,
) -> tuple[float, dict[str, Any]]:
    text = normalize_text_for_matching(text)
    left_keywords = list(axis_dict.get("left_keywords", []) or [])
    right_keywords = list(axis_dict.get("right_keywords", []) or [])
    left_regex = list(axis_dict.get("left_regex", []) or [])
    right_regex = list(axis_dict.get("right_regex", []) or [])

    left_kw = _present_count(text, left_keywords)
    right_kw = _present_count(text, right_keywords)
    left_rx = _present_regex_count(text, left_regex)
    right_rx = _present_regex_count(text, right_regex)

    left = weights.keyword_present * left_kw + weights.regex_present * left_rx
    right = weights.keyword_present * right_kw + weights.regex_present * right_rx

    raw = float(right - left)
    evidence = extract_evidence_sentences(
        text=text,
        left_keywords=left_keywords,
        right_keywords=right_keywords,
        left_regex=left_regex,
        right_regex=right_regex,
        limit=3,
    )
    meta = {
        "left_kw_present": left_kw,
        "right_kw_present": right_kw,
        "left_regex_present": left_rx,
        "right_regex_present": right_rx,
        "evidence": evidence,
    }
    return raw, meta


def dictionary_score_from_raw(raw: float, scale: float = 3.0) -> float:
    if scale <= 0:
        return float(max(-100.0, min(100.0, raw)))
    return float(100.0 * math.tanh(raw / scale))


def dictionary_confidence_from_raw(raw: float, max_raw: float = 6.0) -> float:
    if max_raw <= 0:
        return 0.0
    return float(max(0.0, min(1.0, abs(raw) / max_raw)))


def json_dumps_compact(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

