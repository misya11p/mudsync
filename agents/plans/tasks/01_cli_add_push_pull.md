## Task 01: CLI に push/pull を追加

### 目的
- `sync` を維持したまま `push` / `pull` を公開し、用途を明確に分離する。

### 作業
- `src/mudsync/cli.py` に `push` / `pull` サブコマンドを追加
- `push` / `pull` の PATTERN 引数（複数可・必須）を定義
- `manage` のヘルプ文を必要に応じて sync 用であることが分かる文言に調整

### 完了条件
- `mudsync --help` に `sync`, `push`, `pull` が表示される
- `mudsync push --help`, `mudsync pull --help` で引数仕様が確認できる
