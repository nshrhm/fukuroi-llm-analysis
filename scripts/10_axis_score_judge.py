import argparse
import json
import os
import random
import time
import urllib.error
import urllib.request
from typing import Any

import pandas as pd

from axis_scoring import (
    dictionary_confidence_from_raw,
    dictionary_raw_signal,
    dictionary_score_from_raw,
    json_dumps_compact,
    load_axis_config,
    stable_text_hash,
)

def _load_dotenv(path: str) -> None:
    if not path or not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'").strip('"')
            if not k:
                continue
            os.environ.setdefault(k, v)


def _load_jsonl(path: str) -> list[dict[str, Any]]:
    if not path or not os.path.exists(path):
        return []
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _append_jsonl(path: str, obj: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json_dumps_compact(obj) + "\n")


def _openrouter_request(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.0,
    max_tokens: int = 1800,
    timeout_s: int = 120,
) -> str:
    url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions")
    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read().decode("utf-8")
    j = json.loads(raw)
    return j["choices"][0]["message"]["content"]


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    i = text.find("{")
    j = text.rfind("}")
    if i >= 0 and j > i:
        return json.loads(text[i : j + 1])
    raise ValueError("No JSON object found in response")


def _validate_judge_result(axes_ids: list[str], obj: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError("result is not an object")
    axes = obj.get("axes")
    if not isinstance(axes, dict):
        raise ValueError("missing axes object")

    out_axes: dict[str, Any] = {}
    for axis_id in axes_ids:
        v = axes.get(axis_id)
        if not isinstance(v, dict):
            raise ValueError(f"axis {axis_id} missing")
        score = v.get("score")
        confidence = v.get("confidence")
        evidence = v.get("evidence")
        if not isinstance(score, (int, float)):
            raise ValueError(f"axis {axis_id} score not numeric")
        score = int(round(float(score)))
        if score < -100 or score > 100:
            raise ValueError(f"axis {axis_id} score out of range")
        if not isinstance(confidence, (int, float)):
            raise ValueError(f"axis {axis_id} confidence not numeric")
        confidence = float(confidence)
        if confidence < 0.0 or confidence > 1.0:
            raise ValueError(f"axis {axis_id} confidence out of range")
        if not isinstance(evidence, list) or not all(isinstance(s, str) for s in evidence):
            raise ValueError(f"axis {axis_id} evidence must be string list")

        out_axes[axis_id] = {
            "score": score,
            "confidence": confidence,
            "evidence": evidence[:3],
        }

    notes = obj.get("notes", "")
    if notes is None:
        notes = ""
    if not isinstance(notes, str):
        notes = str(notes)

    return {"axes": out_axes, "notes": notes}


def _build_prompt(axes_spec) -> tuple[str, str]:
    axis_lines = []
    for a in axes_spec:
        axis_lines.append(
            f'- "{a.id}": {a.name}\n'
            f"  -100=「{a.left_label}」({a.left_desc})に強い、0=中庸/不明、+100=「{a.right_label}」({a.right_desc})に強い"
        )
    axes_block = "\n".join(axis_lines)

    system = (
        "あなたは日本語の観光案内文を10個の双極軸で採点する評価者です。"
        "必ずJSONのみを返し、Markdownや説明文は書きません。"
        "本文に根拠が無い場合は score=0 かつ confidenceを低めにします。"
    )

    user = (
        "次の観光案内文について、10軸で採点してください。\n\n"
        "【採点ルール】\n"
        "- 各軸は score∈[-100,100]（-100=左に強い、0=中庸/不明、+100=右に強い）\n"
        "- evidence は本文からの短い引用（原文の一部）を1〜3個。推測で作らない。\n"
        "- confidence は 0〜1。根拠が薄い/判断不能なら低くする。\n\n"
        "【10軸】\n"
        f"{axes_block}\n\n"
        "【出力JSONスキーマ（厳守）】\n"
        "{\n"
        '  "axes": {\n'
        '    "a1": {"score": 0, "confidence": 0.0, "evidence": ["..."]},\n'
        '    "a2": {"score": 0, "confidence": 0.0, "evidence": ["..."]},\n'
        '    "a3": {"score": 0, "confidence": 0.0, "evidence": ["..."]},\n'
        '    "a4": {"score": 0, "confidence": 0.0, "evidence": ["..."]},\n'
        '    "a5": {"score": 0, "confidence": 0.0, "evidence": ["..."]},\n'
        '    "a6": {"score": 0, "confidence": 0.0, "evidence": ["..."]},\n'
        '    "a7": {"score": 0, "confidence": 0.0, "evidence": ["..."]},\n'
        '    "a8": {"score": 0, "confidence": 0.0, "evidence": ["..."]},\n'
        '    "a9": {"score": 0, "confidence": 0.0, "evidence": ["..."]},\n'
        '    "a10": {"score": 0, "confidence": 0.0, "evidence": ["..."]}\n'
        "  },\n"
        '  "notes": ""\n'
        "}\n\n"
        "【観光案内文】\n"
        "{{TEXT}}\n"
    )
    return system, user


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--axis-config", default="config/axis_scoring.yaml")
    ap.add_argument("--input-csv", default="data/raw/fukuroi_llm_outputs.csv")
    ap.add_argument("--text-col", default="response")
    ap.add_argument("--output-csv", default="outputs/axis_scores/axis_scores.csv")
    ap.add_argument("--cache-jsonl", default="outputs/axis_scores/judge_cache.jsonl")
    ap.add_argument("--dotenv", default=".env")
    ap.add_argument("--model", required=True, help="OpenRouter model name (e.g., openai/gpt-4.1-mini)")
    ap.add_argument("--max-rows", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)

    _load_dotenv(args.dotenv)
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is missing (set it in .env and load it into the environment).")

    axes_spec, dict_cfg, weights = load_axis_config(args.axis_config)
    axes_ids = [a.id for a in axes_spec]

    df = pd.read_csv(args.input_csv)
    if args.text_col not in df.columns:
        raise SystemExit(f"text column not found: {args.text_col}")

    if args.max_rows and args.max_rows > 0:
        df = df.head(args.max_rows).copy()
    else:
        df = df.copy()

    text_series = df[args.text_col].astype(str)

    # Common dictionary baseline (for later comparison / evidence helper)
    for axis_id in axes_ids:
        axis_dict = dict_cfg.get(axis_id, {}) if isinstance(dict_cfg, dict) else {}
        raws = []
        confs = []
        evids = []
        for t in text_series.tolist():
            raw, meta = dictionary_raw_signal(t, axis_dict, weights)
            raws.append(raw)
            confs.append(dictionary_confidence_from_raw(raw))
            evids.append(meta.get("evidence", []))
        df[f"dict_raw_{axis_id}"] = raws
        df[f"dict_score_{axis_id}"] = [dictionary_score_from_raw(r) for r in raws]
        df[f"dict_confidence_{axis_id}"] = confs
        df[f"dict_evidence_{axis_id}"] = [json_dumps_compact(e) for e in evids]

    # Load cache to resume
    cache_rows = _load_jsonl(args.cache_jsonl)
    cached: dict[str, dict[str, Any]] = {}
    for r in cache_rows:
        key = r.get("cache_key")
        if isinstance(key, str):
            cached[key] = r

    system, user_tpl = _build_prompt(axes_spec)

    judge_axes: dict[str, dict[str, Any]] = {}
    for i, row in df.iterrows():
        text = str(row[args.text_col])
        cache_key = f"{row.get('session_id', i)}:{stable_text_hash(text)}"
        if cache_key in cached:
            judge_axes[cache_key] = cached[cache_key]["result"]["axes"]
            continue

        user = user_tpl.replace("{{TEXT}}", text)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]

        last_err: str | None = None
        for attempt in range(1, 4):
            try:
                content = _openrouter_request(
                    api_key=api_key,
                    model=args.model,
                    messages=messages,
                    temperature=0.0,
                    max_tokens=1800,
                    timeout_s=180,
                )
                obj = _extract_json(content)
                validated = _validate_judge_result(axes_ids, obj)
                judge_axes[cache_key] = validated["axes"]
                _append_jsonl(
                    args.cache_jsonl,
                    {
                        "cache_key": cache_key,
                        "row_index": int(i),
                        "session_id": row.get("session_id", None),
                        "text_hash": stable_text_hash(text),
                        "model": args.model,
                        "result": validated,
                    },
                )
                last_err = None
                break
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                last_err = f"network error: {e}"
            except Exception as e:
                last_err = f"parse/validate error: {e}"

            if attempt < 3:
                time.sleep(min(5.0, 0.8 * attempt + random.random() * 0.5))

        if last_err:
            raise RuntimeError(f"judge failed at row {i}: {last_err}")

        if args.sleep > 0:
            time.sleep(args.sleep)

    # Materialize judge columns (wide format)
    for axis_id in axes_ids:
        scores = []
        confs = []
        evids = []
        for i, row in df.iterrows():
            text = str(row[args.text_col])
            cache_key = f"{row.get('session_id', i)}:{stable_text_hash(text)}"
            axes_obj = judge_axes[cache_key]
            scores.append(int(axes_obj[axis_id]["score"]))
            confs.append(float(axes_obj[axis_id]["confidence"]))
            evids.append(json_dumps_compact(list(axes_obj[axis_id]["evidence"])))
        df[f"judge_score_{axis_id}"] = scores
        df[f"judge_confidence_{axis_id}"] = confs
        df[f"judge_evidence_{axis_id}"] = evids

    os.makedirs(os.path.dirname(args.output_csv), exist_ok=True)
    df.to_csv(args.output_csv, index=False)
    print(f"[OK] saved: {args.output_csv} rows={len(df)} axes={len(axes_ids)} model={args.model}")


if __name__ == "__main__":
    main()
