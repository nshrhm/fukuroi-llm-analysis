# Codex / AIエージェント向けメモ（このリポジトリの作業記録）

このファイルは、今後このリポジトリをCodex（CLI）で継続的に更新するための「作業方針・構成・手順」をまとめたものです。

## リポジトリ概要

- 袋井市の観光案内文（LLM生成テキスト）を対象に、埋め込み・可視化・クラスタリング、および 10軸（形容詞対）での数値化を行う。
- 10軸スコアリングは2手法を併用して比較する:
  - `judge_*`: OpenRouter経由のLLM採点（score/evidence/confidence）
  - `embed_*`: 文書埋め込みの軸方向射影（ネット不要で再現性高め）
- 共通のルール/辞書ベースラインを `dict_*` として残し、比較の基準にする。

## 重要な運用ルール（GitHubに載せないもの）

- `.env`（APIキー等の秘密情報）はコミットしない（`.gitignore` で除外済み）。
  - 雛形は `.env.example`。
- `data/raw/*.csv`（生データ）はコミットしない（`.gitignore` で除外済み）。
- `outputs/`（再生成可能な成果物）はコミットしない（`.gitignore` で除外済み）。

## 主要ファイル/フォルダ

- `config/config.yaml`: 埋め込み/UMAP/クラスタ等の設定と入出力パス
- `config/axis_scoring.yaml`: 10軸（a1〜a10）定義 + 共通辞書ベースライン（キーワード/正規表現）
- `scripts/`
  - `00_validate_input.py`: 入力CSV検証（`response`列の存在など）
  - `01_embed.py`: sentence-transformersで埋め込み作成 → `outputs/embeddings/embeddings.npz`
  - `02_umap.py`: UMAP → `outputs/umap/umap_2d.csv` と `outputs/figures/umap_2d.pdf`
  - `03_cluster.py`: クラスタ → `outputs/clusters/clusters.csv`
  - `axis_scoring.py`: 10軸スコアリング共通ユーティリティ（辞書ベースライン/根拠抽出など）
  - `10_axis_score_judge.py`: OpenRouter judgeで採点 → `outputs/axis_scores/axis_scores.csv`
  - `11_axis_score_embedding.py`: 埋め込み射影で `embed_*` 追記 → `outputs/axis_scores/axis_scores.csv`
- `docs/`
  - `REPO_STRUCTURE.md`: 構成説明
  - `EXPERIMENT_MANUAL.md`: 実験手順（初心者向け補足あり）
  - `AXIS_SCORES_COLUMNS.md`: `axis_scores.csv` 列説明（埋め込み/npz/射影/共通ベースライン含む）
  - `GITHUB_UPLOAD_CHECKLIST.md`: アップロード前チェック

## 実行手順（再現用）

### セットアップ

```bash
make setup
make install
```

### 入力チェック → 埋め込み → UMAP → クラスタ

```bash
make validate
make embed
make umap
make cluster
# または
make all
```

### 10軸スコアリング（2手法）

`.env` に `OPENROUTER_API_KEY` を設定する（例は `.env.example`）。

```bash
OPENROUTER_MODEL=openai/gpt-4.1-mini make axis_judge
make axis_embed
```

補足:
- `10_axis_score_judge.py` は `outputs/axis_scores/judge_cache.jsonl` を使って途中再開する。
- judgeモデル比較を厳密にする場合は、CSV/キャッシュの出力先を分ける（運用で対応）。

## 変更時の注意（Codexが守るべきこと）

- 10軸の追加/修正:
  - `config/axis_scoring.yaml` を変更したら、`docs/AXIS_SCORES_COLUMNS.md` も同期して更新する。
  - 既存の軸ID（a1〜a10）は、分析互換性のため基本は変えない（変更するなら破壊的変更として扱う）。
- スクリプト改修:
  - 既存の出力列名（`dict_*`, `judge_*`, `embed_*`）は極力維持し、破壊的変更が必要ならドキュメントに明記する。
- データ/成果物の取り扱い:
  - 生データや成果物をGitHubに載せない前提を崩す場合は、`docs/GITHUB_UPLOAD_CHECKLIST.md` を更新して合意形成する。

