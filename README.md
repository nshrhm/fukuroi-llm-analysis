# fukuroi-llm-analysis

袋井市の観光案内文（LLM生成テキスト）を対象に、埋め込み・可視化・クラスタリング、および 10軸（形容詞対）によるスコアリング（LLM採点 / 埋め込み投影）を行うための実験用リポジトリです。

## 何ができるか（成果物）

- 文書埋め込みの作成: `outputs/embeddings/embeddings.npz`
- UMAP 2次元可視化: `outputs/umap/umap_2d.csv`, `outputs/figures/umap_2d.pdf`
- クラスタリング結果: `outputs/clusters/clusters.csv`
- 10軸スコア表（比較用に両方式を同一CSVへ）: `outputs/axis_scores/axis_scores.csv`

## まず読むドキュメント

- リポジトリ構成: `docs/REPO_STRUCTURE.md`
- 実験マニュアル（初心者向け補足あり）: `docs/EXPERIMENT_MANUAL.md`
- `axis_scores.csv` の列説明: `docs/AXIS_SCORES_COLUMNS.md`

## クイックスタート

### 1) セットアップ

```bash
make setup
make install
```

### 2) 入力データを配置

- 入力CSVは `data/raw/fukuroi_llm_outputs.csv` を想定しています（`config/config.yaml` の `paths.input_csv`）。
- GitHubには生データを載せない運用を想定し、`data/raw/*.csv` は `.gitignore` で除外されています。

### 3) 埋め込み〜UMAP〜クラスタ

```bash
make all
```

### 4) 10軸スコアリング（LLM採点 / 埋め込み投影）

OpenRouter を利用します。`.env` に `OPENROUTER_API_KEY` を設定してください（`.env` はコミットしません）。

```bash
OPENROUTER_MODEL=openai/gpt-4.1-mini make axis_judge
make axis_embed
```

## 設定ファイル

- パイプライン全体の設定: `config/config.yaml`
- 10軸・辞書ベースラインの設定: `config/axis_scoring.yaml`

