## 仕様（実装準備版）

### 1. `build` コマンド
- `mudsync build` は削除する。
- CLI ヘルプおよびコマンド一覧からも除外する。

### 2. `run` コマンド

#### 2.1 インターフェース
- 形式: `mudsync run [OPTIONS] COMMAND`
- 引数:
  - `COMMAND`（必須）: コンテナ内で実行するコマンド文字列
- オプション:
  - `--service`, `-s`: compose service 名（省略時はデフォルトサービス）
  - `--build`, `-b`: 実行前にイメージビルドを有効化
  - `--sync`, `-y`: 実行前に `sync` コマンドを実行
  - `--file`, `-f`: compose ファイルパス（省略時 `docker-compose.yml`）

#### 2.2 動作
1. app 設定と project コンテキストを解決する。
2. `--sync` が指定された場合、既存 `sync` を実行する。
3. service が未指定なら compose サービス一覧の先頭を採用する。
4. SSH 経由でリモートにて以下を実行する。
   - `docker compose [--file <path>] run --rm [--build] <service> <COMMAND>`
5. 終了コードはリモート実行の結果を反映する。

#### 2.3 エラーハンドリング
- compose ファイルが見つからない / サービス解決不能: 明示的なエラーを返す。
- SSH 実行失敗: 終了コード付きで失敗を返す。
- COMMAND 未指定: Typer で入力エラー。

### 3. `jupyter` コマンド

#### 3.1 インターフェース
- 形式: `mudsync jupyter [OPTIONS]`
- オプション:
  - `--port`, `-p`（既存維持、default: 8888）
  - `--service`, `-s`（run と同等）
  - `--build`, `-b`（run と同等）
  - `--sync`, `-y`（run と同等）
  - `--file`, `-f`（run と同等）

#### 3.2 動作
- 実質的に `run` の compose 実行基盤を利用し、`jupyter lab --ip=0.0.0.0 --port=<port> --no-browser --allow-root` を実行する。
- 既存の利用者体験を保つため、接続 URL を表示する（token はログから抽出）。

### 4. テスト仕様
- 対象: `run.py` / `jupyter.py` のコマンド生成と分岐。
- 観点:
  - `--build` の有無
  - `--file` の有無
  - service 指定あり/なし
  - `--sync` 指定時の事前同期呼び出し
  - jupyter 実行時の引数構成

### 5. 外部仕様確認（調査結果）
- Docker 公式ドキュメントで `docker compose run --rm SERVICE COMMAND` と `--build` 利用を確認済み。
- したがって、現在の `docker run` 直接呼び出しから compose へ置換する方針は妥当。
