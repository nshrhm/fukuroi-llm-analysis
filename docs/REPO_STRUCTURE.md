# リポジトリ構成（フォルダ/ファイルの説明）

## 全体像

このリポジトリは、LLMが生成した観光案内文（CSV）を入力として、

1) 入力チェック → 2) 文書埋め込み → 3) 次元削減（UMAP） → 4) クラスタリング → 5) 10軸スコアリング（2手法）

を一通り実行し、結果を `outputs/` に保存します。

## フォルダ一覧

### `config/`

設定ファイルを置きます。

- `config/config.yaml`
  - パイプラインの入出力パス、埋め込みモデル、UMAP、クラスタ、図の出力形式などを設定します。
- `config/axis_scoring.yaml`
  - 10軸（a1〜a10）の定義と、共通ルール/辞書ベースライン（`dict_*`）のキーワード・正規表現を設定します。

### `data/`

入力データと中間生成物（前処理済みCSV）を置きます。

- `data/raw/`
  - 入力CSVを置きます（例: `data/raw/fukuroi_llm_outputs.csv`）。
  - 研究データはGitHubに載せない運用を想定し、`.gitignore` で除外されています。
- `data/processed/`
  - 埋め込み計算の前処理結果（`cleaned.csv`）を保存します。

### `scripts/`

実験で実行するPythonスクリプト群です（基本は `make` 経由で呼び出します）。

- `scripts/00_validate_input.py`
  - 入力CSVの存在確認と、テキスト列（既定: `response`）の存在確認を行います。
- `scripts/01_embed.py`
  - テキスト（`response`）を文書埋め込みに変換し、`outputs/embeddings/embeddings.npz` に保存します。
  - 同時に `data/processed/cleaned.csv` を作り、可視化・クラスタのメタ情報として使います。
- `scripts/02_umap.py`
  - 埋め込みを2次元に次元削減（UMAP）し、`outputs/umap/umap_2d.csv` を出力します。
  - 併せて散布図を `outputs/figures/umap_2d.pdf` に保存します。
- `scripts/03_cluster.py`
  - 埋め込みベクトルをクラスタリングし、`outputs/clusters/clusters.csv` に保存します。
  - 手法は `config/config.yaml` の `cluster.method`（`hdbscan` / `kmeans`）で切り替えます。
- `scripts/axis_scoring.py`
  - 10軸スコアリングで共通利用するユーティリティ（軸設定読み込み、辞書ベースラインの計算、根拠文抽出など）。
- `scripts/10_axis_score_judge.py`
  - OpenRouter経由のjudgeモデルで、10軸（a1〜a10）を `score/evidence/confidence` つきで採点し、`outputs/axis_scores/axis_scores.csv` に保存します。
  - 途中再開用に `outputs/axis_scores/judge_cache.jsonl` にキャッシュします。
- `scripts/11_axis_score_embedding.py`
  - 既存の埋め込み（`outputs/embeddings/embeddings.npz`）から、軸方向に射影して `embed_*` 列を `outputs/axis_scores/axis_scores.csv` に追記します。
  - アンカー（左右の代表文の行インデックス）は `outputs/axis_scores/embedding_anchors.json` に保存します。

### `outputs/`

実行結果を保存するフォルダです。基本的に再生成可能なので、GitHubには載せない運用を想定し `.gitignore` で除外されています。

- `outputs/embeddings/embeddings.npz`: 文書埋め込み（64本×1024次元）
- `outputs/umap/umap_2d.csv`: UMAP 2次元座標
- `outputs/figures/umap_2d.pdf`: UMAPプロット
- `outputs/clusters/clusters.csv`: クラスタ結果
- `outputs/axis_scores/axis_scores.csv`: 10軸スコア表（辞書/LLM採点/埋め込み投影）
- `outputs/axis_scores/judge_cache.jsonl`: judge採点のキャッシュ（再開用）
- `outputs/axis_scores/embedding_anchors.json`: 埋め込み投影のアンカー情報

### `.venv/`

ローカルのPython仮想環境です（GitHubには載せません）。

## ルート直下の主要ファイル

- `Makefile`
  - 代表的な実行コマンドをまとめています（`make all`, `make axis_judge`, `make axis_embed` など）。
- `requirements.txt`
  - Python依存パッケージ一覧です。
- `.env`
  - OpenRouter APIキー等の秘密情報を置きます（GitHubには載せません）。
- `.env.example`
  - `.env` の雛形（サンプル）です。
- `.gitignore`
  - 出力物や生データ、秘密情報などをコミット対象から除外します。

