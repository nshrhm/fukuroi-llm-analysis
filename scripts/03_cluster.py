import argparse, os
import numpy as np
import pandas as pd
import yaml
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import hdbscan

def load_cfg(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    X = np.load(cfg["paths"]["embedding_npz"])["embeddings"]
    umap_csv = cfg["paths"]["umap_csv"]
    out_csv = cfg["paths"]["cluster_csv"]

    df = pd.read_csv(umap_csv)

    method = cfg["cluster"]["method"]
    labels = None
    info = {}

    if method == "hdbscan":
        hcfg = cfg["cluster"]["hdbscan"]
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=int(hcfg["min_cluster_size"]),
            min_samples=int(hcfg["min_samples"]),
            metric=str(hcfg.get("metric", "euclidean")),
        )
        labels = clusterer.fit_predict(X)
        info["n_clusters"] = int(len(set(labels)) - (1 if -1 in labels else 0))
        info["n_noise"] = int((labels == -1).sum())

    elif method == "kmeans":
        kcfg = cfg["cluster"]["kmeans"]
        kmin, kmax = int(kcfg["k_min"]), int(kcfg["k_max"])
        best_k, best_score, best_labels = None, -1.0, None
        for k in range(kmin, kmax + 1):
            km = KMeans(n_clusters=k, random_state=int(kcfg["random_state"]), n_init="auto")
            lab = km.fit_predict(X)
            # silhouette は 2クラスタ以上で計算可能
            s = silhouette_score(X, lab, metric="euclidean")
            if s > best_score:
                best_k, best_score, best_labels = k, s, lab
        labels = best_labels
        info["best_k"] = int(best_k)
        info["silhouette"] = float(best_score)

    else:
        raise ValueError(f"unknown cluster.method: {method}")

    df = df.copy()
    df["cluster"] = labels.astype(int)

    ensure_dir(out_csv)
    df.to_csv(out_csv, index=False)

    print(f"[OK] saved clusters: {out_csv}")
    print(f"[INFO] method={method} info={info}")

if __name__ == "__main__":
    main()
