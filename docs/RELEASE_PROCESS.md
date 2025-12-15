# リリース手順（タグ作成〜GitHub Release）

このプロジェクトはGitタグを基準にバージョンを管理します（例: `v1.0.0`）。

## 0. 前提

- `main` が最新であること
- `.env` や生データがコミット対象に入っていないこと（`docs/GITHUB_UPLOAD_CHECKLIST.md` 参照）

## 1. Changelog を更新

- `CHANGELOG.md` の `Unreleased` に今回の変更点を追記し、リリースする場合は `vX.Y.Z` セクションに移動します。

## 2. コミット

```bash
git add -A
git commit -m "Release vX.Y.Z"
```

## 3. タグ作成（annotated tag）

```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
```

## 4. push（コミット + タグ）

```bash
git push
git push origin vX.Y.Z
```

## 5. GitHub Release 作成

GitHubのUIで:

- リポジトリ → Releases → “Draft a new release”
- Tag に `vX.Y.Z` を選択
- リリース本文は `CHANGELOG.md` から該当セクションを貼る（または要約）

補足:
- 成果物（`outputs/`）は通常コミットしない運用のため、必要ならReleaseのAssetsとして添付します。

