# 実験マニュアル

このマニュアルは、`data/raw/fukuroi_llm_outputs.csv`（LLM生成観光案内文）から、埋め込み・可視化・クラスタリング・10軸スコアリングを再現実行するための手順書です。

## 0. 前提

- OS: macOS / Linux を想定（WindowsはWSL推奨）
- Python: 3.10+（環境に合わせて調整）
- インターネット:
  - 埋め込み作成で `sentence-transformers` のモデルを初回ダウンロードする場合に必要
  - LLM採点（judge）は OpenRouter API を呼ぶため必須

## 1. データの準備

### 入力CSVの置き場所

- 既定の入力: `data/raw/fukuroi_llm_outputs.csv`
- `config/config.yaml` の `paths.input_csv` を変えると入力を差し替え可能です。

### 必須列

- `response`: 観光案内文（評価対象テキスト）

補足:
- それ以外の列（例: `model_display_name`, `persona_name`, `travel_type_name`）は、色分けや層別に役立つメタ情報です。

## 2. 環境構築

### 仮想環境の作成と依存関係インストール

```bash
make setup
make install
```

補足:
- 既存の仮想環境を作り直したい場合は `.venv/` を消してから `make setup` をやり直します。

## 3. 埋め込み・可視化・クラスタリング（ネット不要のパート）

### 3.1 入力チェック

```bash
make validate
```

### 3.2 文書埋め込みの作成

```bash
make embed
```

生成物:
- `data/processed/cleaned.csv`: 埋め込み対象として整形したテキスト＋メタ情報
- `outputs/embeddings/embeddings.npz`: 埋め込み配列（例: 64×1024）

### 3.3 UMAPで2次元に落として可視化

```bash
make umap
```

生成物:
- `outputs/umap/umap_2d.csv`
- `outputs/figures/umap_2d.pdf`

### 3.4 クラスタリング

```bash
make cluster
```

生成物:
- `outputs/clusters/clusters.csv`

補足:
- クラスタ手法は `config/config.yaml` の `cluster.method` で切り替えます（既定: `hdbscan`）。

## 4. 10軸スコアリング（2手法）

10軸（形容詞対）は `config/axis_scoring.yaml` で定義されています（a1〜a10）。

スコアはすべて `[-100, 100]` の双極スケールです:
- -100 = 左の特徴が強い
- 0 = 中庸 / 根拠不足で判断できない
- +100 = 右の特徴が強い

### 4.1 共通ベースライン（辞書/ルール）

`dict_*` は、各軸の左右に対応する「手がかり語（キーワード）」や「数値・所要時間の表現（正規表現）」の有無を数える単純な方法です。

- 良い点: ルールが明確で説明しやすい（evidenceも機械的に抽出できる）
- 注意点: 文脈理解はしない（否定、皮肉、比喩、固有名詞の解釈など）

このベースラインは、LLM採点/埋め込み投影の比較基準としてCSVに残します。

### 4.2 LLM採点（judge）

OpenRouterのjudgeモデルが、10軸を `score/evidence/confidence` つきでJSON出力します。

#### 準備: `.env`

`.env` に以下を設定してください（例）:

```
OPENROUTER_API_KEY=YOUR_KEY_HERE
```

#### 実行

```bash
OPENROUTER_MODEL=openai/gpt-4.1-mini make axis_judge
```

生成物:
- `outputs/axis_scores/axis_scores.csv`
- `outputs/axis_scores/judge_cache.jsonl`（途中再開用キャッシュ）

### 4.3 埋め込み投影（embedding projection）

埋め込み（文章→数値ベクトル）を使って、各軸の「方向」を作り、その方向に沿って各文章がどれだけ右寄り/左寄りかを数値化します。

```bash
make axis_embed
```

生成物:
- `outputs/axis_scores/axis_scores.csv`（`embed_*` 列が追加されます）
- `outputs/axis_scores/embedding_anchors.json`（左右アンカーの行インデックスとプレビュー）

補足（初心者向け）:
- 「埋め込み」は文章を意味の近さで比較できる数値ベクトルにしたものです。
- 「射影」は、そのベクトルが“ある方向”にどれだけ寄っているかを1つの数で表す計算です。

## 5. 出力CSVの読み方

`outputs/axis_scores/axis_scores.csv` には大きく3系統の列が入ります。

- `dict_*`: 共通辞書ベースライン
- `judge_*`: LLM採点（OpenRouter）
- `embed_*`: 埋め込み投影

列の詳細は `docs/AXIS_SCORES_COLUMNS.md` を参照してください。

## 6. よくある作業（研究での使い方）

### 6.1 judgeモデルを変えて比較する

```bash
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet make axis_judge
```

補足:
- `judge_cache.jsonl` があるため、同じ入力・同じキャッシュキーだと再利用されます。
- モデルを変える比較を厳密にする場合は、出力先（CSV/キャッシュ）を分ける運用を推奨します。

### 6.2 軸の辞書（ベースライン）を調整する

- `config/axis_scoring.yaml` の `dictionary` を編集します。
- 変更後に再計算したい場合は、`make axis_judge` / `make axis_embed` を再実行します。

## 7. 付録: なぜ「2手法」なのか（短い説明）

- `judge_*` は「意味理解を含む」採点が期待できる一方、モデル依存・コスト/レイテンシがあります。
- `embed_*` は「ネット不要で再現性が高い」一方、軸方向の作り方（アンカー選定）に設計判断があります。
- そこで両方を同じ10軸で数値化し、相関・差分・外れ事例を分析できるようにしています。

