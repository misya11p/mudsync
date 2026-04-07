## Task 03: jupyter start/stop への再設計

### 目的
- `jupyter` を常駐運用向けに `start/stop` 化し、URL案内を安定提供する。

### 作業
- `jupyter` を Typer のサブコマンド（`start`, `stop`）へ変更
- `start` で `docker compose up -d [--build] <service>` を実行
- `start` でログから token 付き URL を抽出し、HostName/IP へ差し替えて表示
- `stop` で `docker compose down` を実行
- SSH port forward 処理を削除（今回スコープ外）

### 完了条件
- `mudsync jupyter start` が compose 常駐起動と URL 表示を行う
- `mudsync jupyter stop` が compose down を実行する
