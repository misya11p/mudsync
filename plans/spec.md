# MUDSync 仕様整理書

## 概要

GPUサーバーとの連携を行うためのCLIツール。ローカルのプロジェクトをGPUサーバーと同期し、サーバー上のDockerコンテナでコマンド実行やJupyter Labの起動を行う。

## 基本情報

| 項目 | 値 |
|------|-----|
| ツール名 | `mudsync` |
| 言語 | Python 3.13 |
| CLIフレームワーク | Typer |
| パッケージ管理 | uv |
| 設定保存先 | `$XDG_CONFIG_HOME/mudsync/config.json` |
| 状態保存先 | `$XDG_STATE_HOME/mudsync/sync_rules/{path_hash}.json` |

## 前提条件

- GPUサーバーへのSSHアクセス権限がある
- `.ssh/config` にGPUサーバーの接続情報が登録済み
- rsync がローカル・リモート双方にインストール済み
- Docker がGPUサーバーにインストール済み

## プロジェクトルートの検出

project系コマンドは、カレントディレクトリから上位へ辿り、`.git` ディレクトリが存在する場所をプロジェクトルートとする。`.git` が見つからない場合はエラー。

プロジェクト名（`proj_name`）はプロジェクトルートディレクトリのディレクトリ名。

## サブコマンド一覧

### Global コマンド

#### `mudsync config`

対話的にGPUサーバーの接続情報を設定する。

**入力項目:**
1. サーバー選択（`.ssh/config` に登録されているホスト一覧から選択）
2. サーバー上のユーザーホームディレクトリパス（デフォルト: `/home`、例: `/home/username`）

**保存先:** `$XDG_CONFIG_HOME/mudsync/config.json`

**config.json の構造:**
```json
{
  "ssh_host": "server-name",
  "remote_home": "/home/username"
}
```

SSHの接続詳細（ユーザー名、IdentityFile、IP等）は `.ssh/config` から動的にパースして取得する。

---

#### `mudsync show`

現在の設定に基づくSSH接続情報を表示する。

**表示項目:**
- IPアドレス
- サーバーのホスト名（.ssh/configのHost名）
- ユーザー名
- SSH keyのパス
- サーバー上のユーザーホームディレクトリ

---

### Project コマンド

プロジェクトルート（`.git` が存在するディレクトリ）でのみ実行可能。

#### `mudsync connect`

GPUサーバーにSSH接続し、プロジェクトディレクトリに移動した状態でインタラクティブシェルを提供する。

**動作:**
1. プロジェクトルートを検出
2. `proj_name` をディレクトリ名から取得
3. リモート側のパス: `{remote_home}/proj_name`
4. `ssh -t {host} 'cd {remote_path} && exec $SHELL'` を実行
5. ユーザーが `exit` するとローカルシェルに戻る

---

#### `mudsync manage`

同期対象のファイル・ディレクトリを対話的に管理する。

**UI仕様:**
- プロジェクトルート直下のファイル・ディレクトリ一覧を表示
- 操作方法:
  - `↑`/`↓` or `k`/`j`: ファイル選択移動
  - `→` or `l`: ディレクトリに入る
  - `←` or `h`: 1つ上のディレクトリに戻る
  - `Space`: 同期ON/OFFを切り替え
  - `Enter`: 保存して終了
- 各項目の左側に同期状態を表示（例: `[✓]` / `[ ]`）

**保存先:** `$XDG_STATE_HOME/mudsync/sync_rules/{path_hash}.json`

**path_hash:** プロジェクトルートの絶対パスのSHA-256ハッシュ（16進数、先頭16文字程度）

**sync_rules JSONの構造:**
```json
{
  "project_path": "/absolute/path/to/project",
  "excludes": [
    "data/",
    ".git/",
    "__pycache__/"
  ],
  "includes": [
    "src/",
    "train.py"
  ]
}
```

- デフォルト: 全てのファイル・ディレクトリが同期対象
- `excludes`: 同期から除外するパス（プロジェクトルート相対）
- ディレクトリの場合は末尾に `/` を付与

---

#### `mudsync sync`

ローカルのプロジェクトディレクトリとGPUサーバー上の `{remote_home}/proj_name` をrsyncで同期する。

**動作:**
1. プロジェクトルートを検出
2. manageで設定されたexcludeルールを読み込み
3. 以下のrsyncコマンドを実行:
   ```
   rsync -avz \
     --exclude='data/' \
     --exclude='.git/' \
     --exclude='__pycache__/' \
     -e "ssh -F ~/.ssh/config" \
     /local/project/path/ \
     {user}@{host}:{remote_home}/proj_name/
   ```
4. 転送結果（転送ファイル数、サイズ等）を表示

**注意点:**
- rsyncの `-a` で差分転送（rsyncアルゴリズム）が自動適用される
- `-z` で転送時に圧縮
- `manage` で除外設定されたパスは `--exclude` に渡す
- ソースパス末尾の `/` は重要（ディレクトリの中身を送る）

---

#### `mudsync build`

GPUサーバー上でDockerイメージをビルドする。

**動作:**
1. プロジェクトルートを検出
2. プロジェクト名（`proj_name`）とユーザー名を取得
3. コンテナ名: `{user}_{remote_home_basename}_{proj_name}`
   - `remote_home_basename`: `/home/username` → `username`
   - 例: `john_home_mudsync`
4. サーバー上で以下を実行:
   ```
   cd {remote_home}/proj_name && docker build -t {container_name} .
   ```

**前提:**
- プロジェクトルートに `Dockerfile` が存在すること
- `sync` コマンドで最新のファイルがサーバーに転送済みであること

---

#### `mudsync run [command]`

GPUサーバーのDockerコンテナ上でコマンドを実行する。

**動作:**
1. プロジェクトルートを検出
2. コンテナ名を解決（buildと同じルール）
3. サーバー上で以下を実行:
   ```
   docker run --gpus all -it --rm \
     -v {remote_home}/proj_name:/workspace \
     -w /workspace \
     {container_name} \
     {command}
   ```

**オプション:**
- `command` が指定されない場合は、コンテナのデフォルトCMDを実行
- `--gpus all` でGPUをコンテナに渡す
- `-v` で同期済みディレクトリを `/workspace` にマウント
- `-w /workspace` で作業ディレクトリを `/workspace` に設定
- `--rm` で終了時にコンテナを削除

**使用例:**
```
mudsync run "python train.py"
mudsync run "bash"
mudsync run
```

---

#### `mudsync jupyter [--port PORT]`

GPUサーバー上でJupyter Labを起動し、アクセスURLを出力する。

**動作:**
1. プロジェクトルートを検出
2. コンテナ名を解決
3. サーバー上でJupyter Labをバックグラウンド起動:
   ```
   docker run --gpus all -d --rm \
     -v {remote_home}/proj_name:/workspace \
     -w /workspace \
     -p {port}:8888 \
     {container_name} \
     jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root
   ```
4. SSHポートフォワーディングを設定:
   ```
   ssh -L {port}:localhost:{port} {host} -N
   ```
5. 以下のURLを出力:
   ```
   Jupyter Lab URL: http://localhost:{port}/?token=xxx
   ```
6. フォアグラウンドでSSHを維持（Ctrl+Cで切断）

**ポートフォワーディングについて:**
- `--port` オプションでローカルのポート番号を指定可能（デフォルト: 8888）
- SSH `-L` でローカルポートをサーバーのJupyterポートにフォワード
- フォアグラウンド実行でターミナルを占有
- Ctrl+C でフォワード切断（Jupyterサーバーはサーバー上で動き続ける）

**注意点:**
- Jupyterのtokenはサーバー側で取得してURLに含める
- または `--NotebookApp.token=''` でトークンなしにするオプションも検討

---

## .ssh/config パース仕様

`~/.ssh/config` をパースして以下の情報を取得する:

```
Host server-name
    HostName 192.168.1.100
    User myuser
    IdentityFile ~/.ssh/id_ed25519
    Port 22
```

**取得項目:**
- `Host`: ホスト名（設定選択用）
- `HostName`: IPアドレスまたはFQDN
- `User`: ユーザー名
- `IdentityFile`: SSH秘密鍵のパス
- `Port`: ポート番号（デフォルト: 22）

**実装注意:**
- `Host *` ブロックの設定も考慮
- `Include` ディレクティブがあれば再帰的に読み込む
- パースには `paramiko.config.SSHConfig` の利用を検討（SSH接続はparamikoを使わず、設定パースのみ）

---

## ディレクトリ構造（完成予想）

```
mudsync/
├── pyproject.toml
├── README.md
├── .gitignore
├── .python-version
├── AGENTS.md
├── plans/
│   ├── spec.md          # このファイル
│   ├── implementation-plan.md
│   └── tasks/
│       ├── 01-project-setup.md
│       ├── 02-ssh-config-parser.md
│       ├── 03-config-command.md
│       ├── 04-show-command.md
│       ├── 05-project-detection.md
│       ├── 06-connect-command.md
│       ├── 07-manage-command.md
│       ├── 08-sync-command.md
│       ├── 09-build-command.md
│       ├── 10-run-command.md
│       └── 11-jupyter-command.md
└── src/
    └── mudsync/
        ├── __init__.py
        ├── __main__.py
        ├── cli.py
        ├── config.py
        ├── ssh_config.py
        ├── project.py
        └── commands/
            ├── __init__.py
            ├── config.py
            ├── show.py
            ├── connect.py
            ├── manage.py
            ├── sync.py
            ├── build.py
            ├── run.py
            └── jupyter.py
```
