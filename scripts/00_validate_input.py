import argparse
import os
import sys
import pandas as pd
import yaml

def load_cfg(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    input_csv = cfg["paths"]["input_csv"]
    text_col = cfg["text"]["text_column"]

    if not os.path.exists(input_csv):
        print(f"[ERROR] input_csv not found: {input_csv}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(input_csv)
    if text_col not in df.columns:
        print(f"[ERROR] required text_column '{text_col}' not found. columns={list(df.columns)}", file=sys.stderr)
        sys.exit(1)

    n_total = len(df)
    n_null = df[text_col].isna().sum()
    print(f"[OK] rows={n_total}, null_text={n_null}")

if __name__ == "__main__":
    main()
