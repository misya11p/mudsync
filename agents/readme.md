以下のmdの仕様でツールを作ろうと思っている。既に一通りの実装は終わっているが、さらに改良を加えたいと思っている。具体的には、サーバーでプログラムを実行するrunコマンドやjupyterコマンド。そもそもこれらのコマンドはテストしていないのでちゃんと動くかわからない。

更新内容は以下:
buildコマンドを廃止し、runコマンドに統合する
今は単一のDockerfileで環境を作ることになっているがdocker-composeに変更する

```md
# MUDSync

GPUサーバーとの連携をおこなうための自分用コマンドラインツール

## Setup

### 前提条件

- GPUサーバーへのアクセス権限があること
- .ssh/configにGPUサーバーの接続情報が登録されていること

Install:

```
uv tool install mudsync # pypiにupする気はないのでgithub経由で
```

## 機能（global）

サブコマンドの説明。

### `config`

対話型でGPUサーバーの接続情報を設定するコマンド。inquirerPyを使って実装。

1. サーバーの設定。.ssh/configに登録されているサーバーの中から選択する。
2. サーバー上の自分のホームディレクトリのpathを入力。デフォルトは/home。/home/usernameのように指定することを想定

これらの情報は$XDG_CONFIG_HOME/mudsync/config.jsonに保存される。

### `show`

GPUサーバーへのSSH接続情報を表示する

- ip
- サーバーのホスト名
- ユーザー名
- ssh keyのpath
- サーバー上のユーザーホームディレクトリ

## 機能（project）

### `connect`

GPUサーバーにSSH接続し、home/proj_nameディレクトリに移動する。proj_nameは現在のディレクトリ名固定。

### `manage`

同期するファイルやディレクトリの設定。対話シェルで設定。

### `sync`

ローカルのプロジェクトディレクトリとGPUサーバーのproj_homeを同期する。

### `run`

GPUサーバーのdockerコンテナ上で指定したコマンドを実行する。例えば、`run "python train.py"`のように使用する。

サーバー上でdocker compose run --rm [service] python train.pyのようなコマンドが実行される想定。

args:
- command: 実行するコマンド。必須。
- service, s: docker composeのservice名。省略した場合はdocker-compose.jsonの最初のserviceが使用される。
- build, b: コマンド実行前にdockerイメージを再ビルドするかどうか。
- sync, y: コマンド実行前にローカルとサーバーのプロジェクトディレクトリを同期するかどうか。
- file, f: docker-compose.ymlのpath。省略した場合はカレントディレクトリのdocker-compose.ymlが使用される。

### `jupyter`

GPUサーバー上でJupyter Labを起動し、カーネルのurlを出力する。`run jupyter lab`を少し使いやすくしたもの。

args:
- port, p: Jupyter Labを起動する際のポート番号。省略した場合は8888が使用される。
```
