import argparse, os
import numpy as np
import pandas as pd
import yaml
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

def load_cfg(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dir(p: str):
    os.makedirs(os.path.dirname(p), exist_ok=True)

def pick_device(device_cfg: str) -> str:
    if device_cfg in ("cpu", "cuda"):
        return device_cfg
    # auto
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    seed = int(cfg["project"]["seed"])
    np.random.seed(seed)

    input_csv = cfg["paths"]["input_csv"]
    processed_csv = cfg["paths"]["processed_csv"]
    out_npz = cfg["paths"]["embedding_npz"]

    text_col = cfg["text"]["text_column"]
    optional_meta = cfg["text"].get("optional_meta_columns", [])

    emb_cfg = cfg["embedding"]
    model_name = emb_cfg["model_name"]
    batch_size = int(emb_cfg["batch_size"])
    device = pick_device(emb_cfg.get("device", "auto"))
    normalize = bool(emb_cfg.get("normalize", True))
    prefix = emb_cfg.get("e5_prefix", "")

    df = pd.read_csv(input_csv)
    df = df.copy()
    df[text_col] = df[text_col].astype(str).str.replace("\r", " ").str.replace("\n", " ").str.strip()
    df = df[df[text_col].str.len() > 0].reset_index(drop=True)

    keep_cols = [c for c in optional_meta if c in df.columns]
    out_df = df[[text_col] + keep_cols].copy()
    os.makedirs(os.path.dirname(processed_csv), exist_ok=True)
    out_df.to_csv(processed_csv, index=False)

    model = SentenceTransformer(model_name, device=device)

    texts = [prefix + t for t in out_df[text_col].tolist()]
    embs = []
    for i in tqdm(range(0, len(texts), batch_size), desc="embedding"):
        batch = texts[i:i+batch_size]
        vec = model.encode(batch, normalize_embeddings=normalize, show_progress_bar=False)
        embs.append(vec)

    X = np.vstack(embs).astype(np.float32)
    ensure_dir(out_npz)
    np.savez_compressed(out_npz, embeddings=X)

    print(f"[OK] saved embeddings: {out_npz} shape={X.shape} device={device} model={model_name}")

if __name__ == "__main__":
    main()
