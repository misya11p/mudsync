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
  - `--file`, `-f`: compose ファイルパス（省略時は `compose.yaml` 優先で探索）

#### 2.2 動作
1. app 設定と project コンテキストを解決する。
2. `--sync` が指定された場合、既存 `sync` を実行する。
3. compose ファイルは以下の優先順で決定する。
   - `--file` 指定値
   - `compose.yaml`
   - `compose.yml`
   - `docker-compose.yaml`
   - `docker-compose.yml`
4. service が未指定なら compose サービス一覧の先頭を採用する。
5. SSH 経由でリモートにて以下を実行する。
   - `docker compose [--file <path>] run --rm [--build] <service> <COMMAND>`
6. 終了コードはリモート実行の結果を反映する。

#### 2.3 エラーハンドリング
- compose ファイルが見つからない / サービス解決不能: 明示的なエラーを返す。
- SSH 実行失敗: 終了コード付きで失敗を返す。
- COMMAND 未指定: Typer で入力エラー。

### 3. `jupyter` コマンド

#### 3.1 インターフェース
- 形式: `mudsync jupyter [OPTIONS]`
- オプション:
  - `--port`, `-p`（default: 8888）
  - `--service`, `-s`（省略時は先頭 service）
  - `--build`, `-b`
  - `--sync`, `-y`
  - `--file`, `-f`（run と同じ優先順）

#### 3.2 動作
- `jupyter`:
  1. 必要に応じて `sync` を実行する。
  2. SSH 経由で `docker compose [--file <path>] up [--build] <service>` をフォアグラウンドで実行する。
  3. 起動ログから token 付き URL を抽出する。
  4. URL のホスト部を `ssh_config` の接続先ホスト（HostName/IP）へ差し替え、`--port` を反映して表示する。
  5. `Ctrl+C` 受信時に SSH 経由で `docker compose [--file <path>] down` を実行して終了する。
- 本仕様では SSH port forward は実装対象外（URL 出力のみ）。
- Terminal 強制終了時の完全クリーンアップ保証は今回のスコープ外とする。

### 4. テスト仕様
- 対象: `run.py` / `jupyter.py` のコマンド生成と分岐。
- 観点:
  - `--build` の有無
  - `--file` の有無
  - compose ファイル自動探索順
  - service 指定あり/なし
  - `--sync` 指定時の事前同期呼び出し
  - jupyter の引数構成と URL 置換
  - jupyter 割り込み時の down 実行

### 5. 外部仕様確認（調査結果）
- Docker 公式ドキュメントで `docker compose run --rm SERVICE COMMAND` と `--build` 利用を確認済み。
- Docker 公式ドキュメントで compose 既定ファイルは `compose.yaml`（`compose.yml` などは互換）を確認済み。
- したがって、現在の `docker run` 直接呼び出しから compose へ置換し、`jupyter` をフォアグラウンド `up` + 割り込み時 `down` に整理する方針は妥当。
