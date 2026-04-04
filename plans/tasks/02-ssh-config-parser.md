# Task 2: SSH Config パーサー

## 概要

`~/.ssh/config` をパースし、登録されているホスト一覧と各ホストの接続情報を取得するモジュールを実装する。

## 実施内容

### 2.1 ファイル: `src/mudsync/ssh_config.py`

### 2.2 実装詳細

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SSHHost:
    """SSH接続情報のデータクラス"""
    host: str           # Host名（設定上のエイリアス）
    hostname: str       # HostName（IPまたはFQDN）
    user: str           # User
    port: int           # Port（デフォルト: 22）
    identity_file: Optional[str] = None  # IdentityFileのパス


def parse_ssh_config() -> dict[str, SSHHost]:
    """
    ~/.ssh/configをパースし、Host名をキーとしたSSHHostの辞書を返す。

    注意:
    - Host * ブロックは全ホストのデフォルトとして適用
    - Includeディレクティブは考慮しない（必要なら拡張）
    - paramiko.config.SSHConfigを使用してパース
    """
    ...


def get_host_config(host: str) -> SSHHost:
    """
    指定されたホスト名の接続情報を返す。

    Args:
        host: .ssh/configのHost名

    Returns:
        SSHHost: 接続情報

    Raises:
        ValueError: ホストが見つからない場合
    """
    ...


def list_hosts() -> list[str]:
    """
    設定されているホスト名の一覧を返す。

    Returns:
        list[str]: ホスト名のリスト（*を除く）
    """
    ...
```

### 2.3 パース方法

`paramiko.config.SSHConfig` を使用する（SSH接続はparamikoを使わない、パースのみ）。

```python
import paramiko.config

ssh_config_path = Path.home() / ".ssh" / "config"
ssh_config = paramiko.config.SSHConfig()
with open(ssh_config_path) as f:
    ssh_config.parse(f)

# 特定ホストの設定を取得
host_config = ssh_config.lookup("server-name")
# host_config["hostname"], host_config["user"], etc.

# ホスト一覧
hosts = [h for h in ssh_config.get_hostnames() if h != "*"]
```

### 2.4 注意点

- `IdentityFile` はチルダ展開が必要: `Path(identity_file).expanduser()`
- `HostName` が未設定の場合、`Host` 名をHostNameとして使用する
- `User` が未設定の場合、現在のOSユーザー名を使用: `os.getlogin()` または `getpass.getuser()`
- `Port` が未設定の場合、22を使用
- `.ssh/config` が存在しない場合は適切なエラーメッセージを表示

## 成果物

- `src/mudsync/ssh_config.py`

## 検証

```python
# 対話Pythonでテスト
from mudsync.ssh_config import list_hosts, get_host_config

print(list_hosts())
# ['gpu-server-01', 'gpu-server-02', ...]

print(get_host_config('gpu-server-01'))
# SSHHost(host='gpu-server-01', hostname='192.168.1.100', user='myuser', port=22, identity_file='/Users/k/.ssh/id_ed25519')
```
