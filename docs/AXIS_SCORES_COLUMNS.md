# `axis_scores.csv` 列見出しの説明

このドキュメントは `outputs/axis_scores/axis_scores.csv` の列（カラム）について説明します。

## 1. データの粒度

- 1行 = 1つのLLM生成観光案内文（ペルソナ×旅行パターン×生成モデルの組み合わせ）
- 軸スコアはすべて **双極（形容詞対）`[-100, 100]`**（-100=左に強い、0=中庸/不明、+100=右に強い）
- 各軸は **根拠フレーズ（evidence）** と **自信度（confidence: 0–1）** を併記

## 2. 軸ID（a1–a10）の定義

軸の詳細定義（左右ラベル・説明・辞書）は `config/axis_scoring.yaml` にあります。`axis_scores.csv` では以下のIDを用います。

- `a1`: 落ち着いた — 活気がある
- `a2`: 伝統的 — 現代的
- `a3`: 自然志向 — 都市/施設志向
- `a4`: ゆったり滞在 — アクティブ回遊
- `a5`: 家族向け — 大人向け
- `a6`: 日本らしい — 国際的/多文化フレンドリー
- `a7`: 宿泊/滞在向き — 日帰り向き
- `a8`: 食の訴求弱 — 食の訴求強
- `a9`: 季節感弱 — 季節感強
- `a10`: 行動の具体性低 — 高

## 3. 生成元（入力）由来の列

以下は主に `data/raw/fukuroi_llm_outputs.csv` から引き継いだ列です（研究での層別・追跡に使用）。

- `session_id`: 生成セッションID
- `experiment_id`: 実験ID
- `timestamp`: 生成時刻（ISO形式）
- `model`: 生成に用いたモデル識別子（例: `openai/...`）
- `model_display_name`: 表示用のモデル名
- `persona_id`, `persona_name`: ペルソナID/名称
- `travel_type_id`, `travel_type_name`: 旅行パターンID/名称
- `prompt`: 入力プロンプト
- `response`: 生成された観光案内文（評価対象テキスト）
- `tokens_used`: トークン数
- `latency_ms`: レイテンシ（ms）
- `response_char_count`, `response_word_count`, `response_line_count`: 生成文の文字/語/行数
- `prompt_char_count`: プロンプト文字数

## 4. 共通ルール/辞書ベースライン（`dict_*`）

全手法共通のベースライン（キーワード/正規表現）で、各軸の「左右の手がかり」の出現を数えて作るスコアです。
辞書の中身は `config/axis_scoring.yaml` の `dictionary` に定義されています。

各軸 `aX` に対して、以下の列が作られます。

- `dict_raw_aX`
  - 右側手がかり（キーワード/正規表現のヒット） − 左側手がかり の差分（生の信号）
  - 0より大：右寄り、0より小：左寄り
- `dict_score_aX`
  - `dict_raw_aX` を `[-100,100]` に写像した値（飽和を避けるため非線形変換）
  - 傾向比較用の連続値（LLM採点・埋め込み投影と同じスケール）
- `dict_confidence_aX`
  - `abs(dict_raw_aX)` をもとにした簡易自信度（0–1）
  - ルール/辞書に基づく「手がかりの強さ」のみを反映（意味理解はしない）
- `dict_evidence_aX`
  - 辞書ヒット（キーワード/正規表現）を含む文を本文から最大3件抽出したもの
  - **JSON配列文字列**（例: `["...","..."]`）

## 5. LLM採点（judge; `judge_*`）

同一のjudgeモデル（OpenRouter経由）に、10軸の **score/evidence/confidence** をJSONで返すよう指示し採点した結果です。

各軸 `aX` に対して、以下の列が作られます。

- `judge_score_aX`
  - LLMが返したスコア（整数、`[-100,100]`）
- `judge_confidence_aX`
  - LLMが返した自信度（0–1）
- `judge_evidence_aX`
  - LLMが返した根拠フレーズ（本文からの短い引用）1〜3個
  - **JSON配列文字列**（例: `["...","..."]`）

補足:
- 採点は途中再開できるよう `outputs/axis_scores/judge_cache.jsonl` にキャッシュされます。

## 6. 埋め込み投影（embedding projection; `embed_*`）

既存の文書埋め込み `outputs/embeddings/embeddings.npz` を使い、各軸ごとに
`direction = mean(right_anchors) - mean(left_anchors)` を作って、各文章を射影した連続スコアです。

各軸 `aX` に対して、以下の列が作られます。

- `embed_score_aX`
  - 射影値をロバストに `[-100,100]` にスケーリングしたスコア
- `embed_confidence_aX`
  - 射影値の「中心からの距離」をもとにした簡易自信度（0–1）
- `embed_evidence_aX`
  - 説明可能性のため、現状は **共通辞書ベースラインの `dict_evidence_aX` と同一**（JSON配列文字列）

補足:
- アンカー（left/right_anchors）は **辞書ベースライン `dict_raw_aX` の極端な例（上位/下位）**から自動選択されます。
- 選ばれたアンカーの行インデックスとプレビューは `outputs/axis_scores/embedding_anchors.json` に保存されます。

### 初心者向け補足（埋め込み・npz・射影）

この節は、テキスト分析に馴染みのない方向けの説明です。

#### 文書埋め込み（embedding）とは

- 文章（テキスト）を、コンピュータが計算しやすい **数字の並び（ベクトル）**に変換したものです。
- 直感的には「文章の意味や雰囲気を要約した座標」のようなもので、**似た文章ほど近い座標**になりやすい性質があります。
- 本プロジェクトでは、64本の観光案内文それぞれを **長さ1024の数値ベクトル**に変換して保存しています（既に作成済み）。

#### `embeddings.npz` とは

- NumPy（Pythonの数値計算ライブラリ）の **圧縮データ形式**で、複数の配列を1ファイルにまとめたものです（拡張子 `.npz`）。
- `outputs/embeddings/embeddings.npz` には `embeddings` という名前の配列が入っており、形状は概ね `(64, 1024)` です。
  - 64行 = 64本の文章
  - 1024列 = 1文章あたり1024次元の埋め込み
- 読み出し例（必要な場合のみ）:

```python
import numpy as np
z = np.load("outputs/embeddings/embeddings.npz")
X = z["embeddings"]   # shape: (64, 1024)
```

#### 射影（projection）とは（なぜスコアになるのか）

- 1024次元の座標空間で、ある軸（方向）を1本決めたとき、各文章がその方向にどれだけ寄っているかを **1つの数**で表す計算が「射影」です。
- 本プロジェクトでは各軸 `aX` について、辞書ベースラインで「左らしい文章」「右らしい文章」を数本ずつ選び、
  - 左の平均ベクトル（left_center）
  - 右の平均ベクトル（right_center）
  の差分を「その軸の方向（direction）」として作っています。
- 各文章の埋め込みベクトルをこの direction に沿って測ると、**左寄り/右寄りの連続値**が得られるため、それを `[-100,100]` にスケーリングしたものが `embed_score_aX` です。

## 7. evidence列の取り扱い（重要）

`*_evidence_*` は「セル内にJSON配列が入っている」形式です（CSVとしては文字列）。
Python/pandasで扱う場合は `json.loads()` で配列に戻せます。

例:

```python
import json, pandas as pd
df = pd.read_csv("outputs/axis_scores/axis_scores.csv")
evidence = json.loads(df.loc[0, "judge_evidence_a10"])
```

## 8. 初心者向け補足（共通ベースラインとは）

`dict_*` は「共通ベースライン（ルール/辞書）」です。これは、文章に含まれる単語や表現の有無を手がかりにして、
各軸の左/右らしさを単純に数える方法です。

- 良い点: 計算が軽い / ルールが明確 / evidence（根拠）を機械的に示せる
- 注意点: 文脈理解はしない（例: 否定・皮肉・比喩、固有名詞の誤解などは扱いにくい）

本研究では、`dict_*` を「比較の基準（ベースライン）」として残しつつ、
LLM採点（`judge_*`）や埋め込み投影（`embed_*`）と並べて分析できるようにしています。

