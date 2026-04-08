## Task 03: jupyter フォアグラウンド運用への再設計

### 目的
- `jupyter` を単一コマンドで安全運用し、終了時クリーンアップを標準化する。

### 作業
- `jupyter` を単一コマンドのまま compose `up` フォアグラウンド実行へ変更
- `jupyter` でログから token 付き URL を抽出し、HostName/IP へ差し替えて表示
- `KeyboardInterrupt`（Ctrl+C）を捕捉して `docker compose down` を実行
- SSH port forward 処理を削除（今回スコープ外）

### 完了条件
- `mudsync jupyter` が compose フォアグラウンド起動と URL 表示を行う
- `Ctrl+C` で `docker compose down` が実行される
