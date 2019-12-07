# Ansible Collection - iida.dnac

Cisco DNA CenterをREST APIで操作するAnsibleコレクションです。

## Requirements

- Ansible 2.9 or later
- Cisco Intent API 1.2

## Install/Uninstall

~/.ansible/collections/ansible_collections/ にインストールします。

```bash
make build
make install
```

アンインストールはコレクションを消すだけです。

```bash
make uninstall
```

## プレイブックの流れ

1. トークンを取得するモジュールを実行します
1. 結果をregisterで格納します
1. registerからトークンの文字列を取り出します
1. そのトークンを次のモジュールの引数として利用します

## 認証トークンについて

Cisco DNA CenterのREST APIではJWT形式の認証トークンを返してきます。

認証トークンはプレイブックを実行した場所にlogフォルダを作成して、そこにファイルとしてキャッシュします。

## 実装について

ターゲットノードに乗り込んで処理を実行するわけではないので、localhost上で実行するactionプラグインを中心に実装します。

## 参考

- Cisco DNA Centerのマニュアル

<https://developer.cisco.com/docs/dna-center/#!cisco-dna-center-v-1-2-6-and-later/authentication>

- Using Collections

<https://docs.ansible.com/ansible/latest/user_guide/collections_using.html>

- Developing Collections

<https://docs.ansible.com/ansible/latest/dev_guide/developing_collections.html>
