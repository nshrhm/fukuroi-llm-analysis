import argparse
import json
import os
from typing import Any

import numpy as np
import pandas as pd

from axis_scoring import (
    dictionary_confidence_from_raw,
    dictionary_raw_signal,
    dictionary_score_from_raw,
    json_dumps_compact,
    load_axis_config,
    normalize_text_for_matching,
)


def _robust_scale_to_pm100(x: np.ndarray, p_lo: float = 5.0, p_hi: float = 95.0) -> np.ndarray:
    lo, hi = np.percentile(x, [p_lo, p_hi])
    if hi == lo:
        return np.zeros_like(x, dtype=np.float32)
    y = 200.0 * (x - lo) / (hi - lo) - 100.0
    return np.clip(y, -100.0, 100.0).astype(np.float32)


def _confidence_from_projection(x: np.ndarray, p_mid: float = 50.0, p_hi: float = 95.0) -> np.ndarray:
    mid = float(np.percentile(x, p_mid))
    hi = float(np.percentile(x, p_hi))
    denom = max(1e-8, abs(hi - mid))
    c = np.abs((x - mid) / denom)
    return np.clip(c, 0.0, 1.0).astype(np.float32)


def _select_anchors_from_dictionary(raw: np.ndarray, k: int = 6) -> tuple[list[int], list[int]]:
    order = np.argsort(raw)
    left = [int(i) for i in order[:k]]
    right = [int(i) for i in order[-k:][::-1]]
    return left, right


def _load_embeddings(path_npz: str) -> np.ndarray:
    z = np.load(path_npz)
    if "embeddings" not in z.files:
        raise SystemExit(f"embeddings not found in npz: {path_npz}")
    X = z["embeddings"].astype(np.float32)
    return X


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--axis-config", default="config/axis_scoring.yaml")
    ap.add_argument("--input-csv", default="outputs/axis_scores/axis_scores.csv", help="CSV to append embedding scores to")
    ap.add_argument("--raw-input-csv", default="data/raw/fukuroi_llm_outputs.csv", help="Used if input-csv does not exist")
    ap.add_argument("--text-col", default="response")
    ap.add_argument("--embedding-npz", default="outputs/embeddings/embeddings.npz")
    ap.add_argument("--output-csv", default="outputs/axis_scores/axis_scores.csv")
    ap.add_argument("--anchors-json", default="outputs/axis_scores/embedding_anchors.json")
    ap.add_argument("--anchors-k", type=int, default=6)
    args = ap.parse_args()

    axes_spec, dict_cfg, weights = load_axis_config(args.axis_config)
    axes_ids = [a.id for a in axes_spec]

    if os.path.exists(args.input_csv):
        df = pd.read_csv(args.input_csv).copy()
    else:
        df = pd.read_csv(args.raw_input_csv).copy()

    if args.text_col not in df.columns:
        raise SystemExit(f"text column not found: {args.text_col}")

    # Align rows with the existing embeddings pipeline:
    # scripts/01_embed.py replaces CR/LF with spaces and drops empty texts.
    cleaned = (
        df[args.text_col]
        .astype(str)
        .str.replace("\r", " ", regex=False)
        .str.replace("\n", " ", regex=False)
        .str.strip()
    )
    keep = cleaned.str.len() > 0
    df = df.loc[keep].reset_index(drop=True)
    cleaned = cleaned.loc[keep].reset_index(drop=True)

    X = _load_embeddings(args.embedding_npz)
    if len(df) != X.shape[0]:
        raise SystemExit(f"row/embedding mismatch: rows={len(df)} embeddings={X.shape[0]}")

    # Ensure dictionary baseline columns exist (used as shared evidence; judge script also writes these)
    for axis_id in axes_ids:
        if f"dict_raw_{axis_id}" in df.columns:
            continue
        axis_dict = dict_cfg.get(axis_id, {}) if isinstance(dict_cfg, dict) else {}
        raws = []
        confs = []
        evids = []
        for t in df[args.text_col].astype(str).tolist():
            raw, meta = dictionary_raw_signal(t, axis_dict, weights)
            raws.append(raw)
            confs.append(dictionary_confidence_from_raw(raw))
            evids.append(meta.get("evidence", []))
        df[f"dict_raw_{axis_id}"] = raws
        df[f"dict_score_{axis_id}"] = [dictionary_score_from_raw(r) for r in raws]
        df[f"dict_confidence_{axis_id}"] = confs
        df[f"dict_evidence_{axis_id}"] = [json_dumps_compact(e) for e in evids]

    anchors_out: dict[str, Any] = {"meta": {"k": args.anchors_k}, "axes": {}}

    for axis_id in axes_ids:
        raw = df[f"dict_raw_{axis_id}"].to_numpy(dtype=np.float32)
        left_idx, right_idx = _select_anchors_from_dictionary(raw, k=args.anchors_k)

        left_center = X[left_idx].mean(axis=0)
        right_center = X[right_idx].mean(axis=0)
        direction = (right_center - left_center).astype(np.float32)
        n = float(np.linalg.norm(direction))
        if n == 0.0:
            proj = np.zeros((len(df),), dtype=np.float32)
        else:
            direction = direction / n
            proj = (X @ direction).astype(np.float32)

            # Orientation sanity: make "right" anchors higher on average.
            if float(proj[right_idx].mean()) < float(proj[left_idx].mean()):
                proj = -proj

        embed_score = _robust_scale_to_pm100(proj, p_lo=5.0, p_hi=95.0)
        embed_conf = _confidence_from_projection(proj, p_mid=50.0, p_hi=95.0)

        df[f"embed_score_{axis_id}"] = embed_score.astype(float)
        df[f"embed_confidence_{axis_id}"] = embed_conf.astype(float)

        # Evidence: keep common dictionary-based evidence for explainability
        if f"embed_evidence_{axis_id}" not in df.columns:
            df[f"embed_evidence_{axis_id}"] = df[f"dict_evidence_{axis_id}"]

        def _preview(i: int) -> dict[str, Any]:
            cols = [c for c in ["session_id", "model_display_name", "persona_name", "travel_type_name"] if c in df.columns]
            meta = {c: df.loc[i, c] for c in cols}
            text = normalize_text_for_matching(str(df.loc[i, args.text_col]))
            return {**meta, "i": int(i), "text_preview": text[:140]}

        anchors_out["axes"][axis_id] = {
            "left_indices": left_idx,
            "right_indices": right_idx,
            "left_preview": [_preview(i) for i in left_idx[:3]],
            "right_preview": [_preview(i) for i in right_idx[:3]],
        }

    os.makedirs(os.path.dirname(args.anchors_json), exist_ok=True)
    with open(args.anchors_json, "w", encoding="utf-8") as f:
        json.dump(anchors_out, f, ensure_ascii=False, indent=2)

    os.makedirs(os.path.dirname(args.output_csv), exist_ok=True)
    df.to_csv(args.output_csv, index=False)
    print(f"[OK] saved: {args.output_csv} rows={len(df)} axes={len(axes_ids)}")
    print(f"[OK] saved anchors: {args.anchors_json}")


if __name__ == "__main__":
    main()

