# GitHubアップロード前チェックリスト

対象読者: 研究室の学生・共同研究者（CS基礎はあるが、運用ルールはこれから揃える想定）

このリポジトリは「コードと設定（再現可能性）」をGitHubに置き、「生データ・APIキー・生成物」は原則載せない運用を想定しています。

## 1. 秘密情報の確認（最重要）

- `.env` をコミットしない
  - `.gitignore` で除外されていますが、`git add -f` などで無理に追加しないでください。
  - OpenRouterのキーは `.env` にのみ置きます。
- 既に漏れていないか確認
  - `git status` で `.env` が出ていないこと
  - うっかり貼ったトークンがないこと（`rg -n "OPENROUTER|sk-" -S .` など）

## 2. データの取り扱い

- `data/raw/*.csv` は `.gitignore` で除外（研究データをGitHubへ載せない想定）
- 共同研究者に渡す必要がある場合は、別経路（共有ドライブ等）で配布するか、匿名化・合意済みデータのみを別リポジトリに置く

## 3. 生成物（outputs）の取り扱い

- `outputs/` は `.gitignore` で除外（再生成可能なため）
- 共同研究で「結果ファイルもGitHubに残したい」場合は、次のどちらかを検討
  - A) releases/共有ドライブに成果物（CSV/PDF）を置き、GitHubはリンクのみ
  - B) `outputs/` を除外しつつ、必要な成果物だけ `artifacts/` 等にコピーしてコミットする運用に変更

## 4. 研究再現に必要なファイルが揃っているか

最低限、GitHubに含めたいもの（推奨）:

- `README.md`
- `requirements.txt`
- `Makefile`
- `config/config.yaml`
- `config/axis_scoring.yaml`
- `scripts/` 配下のスクリプト
- `docs/` 配下のドキュメント（構成、実験マニュアル、列説明）
- `.env.example`（キーそのものは入れない）

## 5. 最終確認コマンド（例）

```bash
git status
git diff
```

補足:
- このリポジトリは `.gitignore` で `outputs/` と `data/raw/*.csv` を除外しているため、通常の `git add .` では成果物や生データは入らない想定です。

