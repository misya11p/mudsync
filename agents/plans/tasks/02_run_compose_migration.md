## Task 02: run の compose 化

### 目的
- `run` の実行エンジンを `docker compose run` に統一する。

### 作業
- compose コマンド組み立てロジックを実装
- service 自動選択（未指定時）を実装
- `--sync` 指定時の事前同期フローを実装
- SSH 経由実行時のクォート処理を安全化

### 完了条件
- `run` が `docker compose run --rm` ベースで動作
- `--build`, `--file`, `--service`, `--sync` が機能
