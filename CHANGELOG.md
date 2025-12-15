# Changelog

このプロジェクトの変更履歴です。バージョニングは Semantic Versioning（`MAJOR.MINOR.PATCH`）を想定します。

## Unreleased

- CC BY 4.0 の `LICENSE` を追加し、READMEにライセンスバッジを追加。
- READMEの情報設計を調整（Quick Links、License/Citationの明記）。
- GitHub運用向けドキュメントを追加（`docs/REPO_METADATA.md`, `docs/RELEASE_PROCESS.md`）。
- 引用情報を `CITATION.cff` として追加。

## v1.0.0

初回リリース（再現可能な分析パイプライン一式）。

- 入力検証 → 埋め込み作成 → UMAP可視化 → クラスタリングのパイプラインを提供（`Makefile`, `scripts/00-03_*.py`, `config/config.yaml`）。
- 10軸（形容詞対）スコアリングを追加（`config/axis_scoring.yaml`）。
- 10軸スコアリングの2手法を実装
  - OpenRouter judgeによるLLM採点（`scripts/10_axis_score_judge.py`）
  - 埋め込み射影によるスコアリング（`scripts/11_axis_score_embedding.py`）
- 共同研究向けドキュメントを整備（`docs/*`, `README.md`, `AGENTS.md`）。
