## Task 01: CLI 表面の整理

### 目的
- `build` コマンドを CLI から除外し、`run`/`jupyter` のオプションを仕様どおり公開する。

### 作業
- `src/mudsync/cli.py` から `build` import とコマンド定義を削除
- `run` の Typer 引数/オプション定義を更新
- `jupyter` の Typer オプションを拡張

### 完了条件
- `mudsync --help` に `build` が表示されない
- `mudsync run --help` と `mudsync jupyter --help` が仕様を反映
