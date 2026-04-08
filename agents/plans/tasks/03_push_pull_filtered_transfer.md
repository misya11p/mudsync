## Task 03: push/pull の個別転送実装

### 目的
- glob pattern 指定による限定転送を実現し、モデル成果物などを効率的に扱えるようにする。

### 作業
- `src/mudsync/commands/push.py` を新規作成（local -> remote）
- `src/mudsync/commands/pull.py` を新規作成（remote -> local）
- include ルールを固定順序で生成:
  - `--include='*/'`
  - `--include='<pattern>'` (複数)
  - `--exclude='*'`
- `--prune-empty-dirs` を付与
- 実行時に方向・送信元/送信先・pattern 数を表示

### 完了条件
- `mudsync push "PATTERN"` で限定アップロードできる
- `mudsync pull "PATTERN"` で限定ダウンロードできる
- `manage` の除外ルールに依存せず動作する
