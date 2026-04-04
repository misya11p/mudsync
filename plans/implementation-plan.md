# MUDSync 実装計画

## アーキテクチャ概要

```
┌─────────────────────────────────────────────────────┐
│                     CLI (Typer)                      │
├─────────┬─────────┬──────────┬──────────────────────┤
│ config  │  show   │ connect  │ manage               │
│  show   │  sync   │  build   │ run                  │
│         │         │          │ jupyter              │
├─────────┴─────────┴──────────┴──────────────────────┤
│                  Core Modules                        │
├──────────────────┬──────────────────────────────────┤
│  Config Manager  │  SSH Config Parser               │
│  (XDG paths)     │  (~/.ssh/config)                 │
├──────────────────┼──────────────────────────────────┤
│  Project Detector│  Sync Rule Manager               │
│  (git root)      │  (exclude rules)                 │
├──────────────────┴──────────────────────────────────┤
│              Subprocess Executor                     │
│         (ssh, rsync, docker commands)               │
└─────────────────────────────────────────────────────┘
```

## 依存ライブラリ

```toml
dependencies = [
    "typer>=0.12",        # CLIフレームワーク
    "inquirerpy>=0.3",    # 対話UI（config, manageコマンド）
    "rich>=13.0",         # 整形出力（Typerに同梱）
]
```

SSH設定のパースには `paramiko` のSSHConfigクラスのみを使用する（SSH接続自体はsubprocess）。paramikoは設定パースのみなので軽量利用。

## 設計方針

### 1. subprocess中心のアーキテクチャ

SSH接続、rsync、Docker操作は全てsubprocessで外部コマンドを実行する。

- **理由**: 既存のSSH/Dockerエコシステムをそのまま利用。認証、鍵管理、ポートフォワーディング等、成熟した実装に任せられる
- **接続方法**: `ssh` コマンドをsubprocessで実行。`-F ~/.ssh/config` で設定ファイルを明示
- **ファイル転送**: `rsync -avz` で差分転送+圧縮
- **Docker**: サーバー上で `docker` コマンドをSSH経由で実行

### 2. 設定管理

| 種別 | 保存先 | 形式 |
|------|--------|------|
| アプリ設定 | `$XDG_CONFIG_HOME/mudsync/config.json` | JSON |
| 同期ルール | `$XDG_STATE_HOME/mudsync/sync_rules/{hash}.json` | JSON |

- XDG環境変数が未設定の場合のデフォルト:
  - `XDG_CONFIG_HOME`: `~/.config`
  - `XDG_STATE_HOME`: `~/.local/state`

### 3. エラーハンドリング

- SSH接続失敗: 明確なエラーメッセージ（接続できない理由の推測を含む）
- プロジェクトルート未検出: `.git` が見つからない旨を表示
- Dockerfile未存在: buildコマンドでエラー
- rsync失敗: 転送エラーの詳細を表示

### 4. 共通処理のモジュール化

```
src/mudsync/
├── config.py          # アプリ設定の読み書き（XDG paths含む）
├── ssh_config.py      # .ssh/configのパース
├── project.py         # プロジェクトルート検出
├── sync_rules.py      # 同期ルールの読み書き
└── commands/          # 各サブコマンドの実装
```

## 実装順序

依存関係を考慮した実装順序:

```
Phase 1: 基盤
  ├─ Task 1: プロジェクトセットアップ
  ├─ Task 2: SSH Configパーサー
  ├─ Task 3: Configコマンド
  └─ Task 4: Showコマンド

Phase 2: プロジェクト機能
  ├─ Task 5: プロジェクト検出
  ├─ Task 6: Connectコマンド
  ├─ Task 7: Manageコマンド
  └─ Task 8: Syncコマンド

Phase 3: Docker機能
  ├─ Task 9: Buildコマンド
  ├─ Task 10: Runコマンド
  └─ Task 11: Jupyterコマンド
```

## テスト方針

- 単体テスト: pytest
- モック: subprocess.callをモックしてSSH/rsync/Dockerコマンドの呼び出しを検証
- 統合テスト: 実際のSSH接続は不要。コマンド呼び出しの組み合わせをテスト

## 完成後の動作フロー例

```bash
# 初期設定
$ mudsync config
? Select SSH host:
  > gpu-server-01
    gpu-server-02
? Remote home directory [/home]: /home/myuser

# 設定確認
$ mudsync show
Host: gpu-server-01
IP: 192.168.1.100
User: myuser
SSH Key: ~/.ssh/id_ed25519
Remote Home: /home/myuser

# プロジェクトディレクトリで
$ cd ~/projects/my-ml-project

# 同期設定
$ mudsync manage
[✓] src/
[✓] train.py
[ ] data/
[✓] Dockerfile
[ ] .git/

# 同期
$ mudsync sync
sending incremental file list
src/model.py
src/utils.py
train.py
Dockerfile

sent 1,234,567 bytes  received 1,234 bytes  2,467,890 bytes/sec

# ビルド
$ mudsync build
Building Docker image...
Successfully tagged myuser_home_my-ml-project

# 実行
$ mudsync run "python train.py --epochs 100"

# Jupyter
$ mudsync jupyter --port 9999
Jupyter Lab URL: http://localhost:9999/?token=abc123...
(Press Ctrl+C to stop port forwarding)

# リモート接続
$ mudsync connect
# SSH接続され、~/my-ml-projectにcdした状態でシェルが起動
myuser@gpu-server:~/my-ml-project$
```
