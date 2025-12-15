import argparse, os
import numpy as np
import pandas as pd
import yaml
import matplotlib.pyplot as plt
import umap

def load_cfg(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def choose_color_column(df: pd.DataFrame, priority: list[str]) -> str | None:
    for c in priority:
        if c in df.columns:
            return c
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    emb_npz = cfg["paths"]["embedding_npz"]
    processed_csv = cfg["paths"]["processed_csv"]
    umap_csv = cfg["paths"]["umap_csv"]
    figdir = cfg["paths"]["figures_dir"]

    ucfg = cfg["umap"]
    reducer = umap.UMAP(
        n_components=int(ucfg["n_components"]),
        n_neighbors=int(ucfg["n_neighbors"]),
        min_dist=float(ucfg["min_dist"]),
        metric=str(ucfg["metric"]),
        random_state=int(ucfg["random_state"]),
    )

    X = np.load(emb_npz)["embeddings"]
    meta = pd.read_csv(processed_csv)

    Z = reducer.fit_transform(X)
    out = meta.copy()
    out["umap_x"] = Z[:, 0]
    out["umap_y"] = Z[:, 1]

    ensure_dir(umap_csv)
    out.to_csv(umap_csv, index=False)

    # Plot (論文向け：pdf)
    os.makedirs(figdir, exist_ok=True)
    try:
        if cfg["plots"].get("japanese_font", False):
            import japanize_matplotlib  # noqa: F401
    except Exception:
        pass

    color_col = choose_color_column(out, cfg["plots"].get("color_by_priority", []))
    plt.figure()
    if color_col is None:
        plt.scatter(out["umap_x"], out["umap_y"], s=8)
        plt.title("UMAP of Tourism Text Embeddings")
    else:
        # カテゴリ色分け（凡例は多すぎる場合があるので後で調整）
        cats = out[color_col].astype(str).fillna("NA")
        for cat in sorted(cats.unique()):
            m = (cats == cat)
            plt.scatter(out.loc[m, "umap_x"], out.loc[m, "umap_y"], s=8, label=cat)
        plt.title(f"UMAP colored by {color_col}")
        if len(cats.unique()) <= 12:
            plt.legend(markerscale=2, fontsize=8)

    plt.xlabel("UMAP-1")
    plt.ylabel("UMAP-2")
    fmt = cfg["plots"].get("format", "pdf")
    dpi = int(cfg["plots"].get("dpi", 300))
    figpath = os.path.join(figdir, f"umap_2d.{fmt}")
    plt.savefig(figpath, dpi=dpi, bbox_inches="tight")
    plt.close()

    print(f"[OK] saved: {umap_csv}")
    print(f"[OK] saved figure: {figpath}")

if __name__ == "__main__":
    main()
