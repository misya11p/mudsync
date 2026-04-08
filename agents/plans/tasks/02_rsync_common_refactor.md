## Task 02: rsync 実装の共通化

### 目的
- 内部実装を再利用可能にし、`sync` / `push` / `pull` の保守コストを下げる。

### 作業
- `src/mudsync/commands/sync.py` で SSH オプション組み立てと rsync 実行処理を共通ヘルパー化
- 既存 `sync` は実質同一挙動を保つ
- `push` / `pull` が共通ヘルパーを利用できる API を整備

### 完了条件
- `sync` の挙動が回帰なく維持される
- push/pull 実装が共通ヘルパー経由で rsync を呼べる
