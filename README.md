# Ansible Collection - iida.dnac

(未完成、バックアップ用リポジトリ)

Cisco DNA CenterをREST APIで操作するAnsibleコレクションです。

## Requirements

- Ansible 2.9 or later
- Cisco Intent API 1.2

## Install/Uninstall

このレポジトリをクローンしてください。

```bash
git clone https://github.com/takamitsu-iida/ansible_collections.iida.dnac.git
```

~/.ansible/collections/ansible_collections/ にインストールします。

```bash
make install
```

インターネット上のサンドボックスを使ってテスト実行できます。

```bash
make play
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

```bash
log
├── dnac.lock
└── dnac.pickle
```

dnac.locはロックファイルです。中身は空っぽです。複数のプロセスが同時に走ったときのための保護に使っています。

dnac.pickleはトークンのキャッシュです。一度認証したら、有効期限が切れるまではこのキャッシュを使います。

## 実装について

ターゲットノードに乗り込んで処理を実行するわけではないので、localhost上で実行するactionプラグインを中心に実装します。

## 参考

- Cisco DNA Centerのマニュアル

<https://developer.cisco.com/docs/dna-center/#!cisco-dna-center-v-1-2-6-and-later/authentication>

<https://developer.cisco.com/site/dna-center-rest-api/>

Cisco DNA-Cの使い方自体はユーザガイドを見ること。

- Cisco DevNet Sandbox

常時稼働のものと予約して使うものがある。

<https://developer.cisco.com/docs/dna-center/#!sandboxes/cisco-dna-center-sandboxes>
<https://developer.cisco.com/site/sandbox/>

- Ansible Using Collections

<https://docs.ansible.com/ansible/latest/user_guide/collections_using.html>

- Ansible Developing Collections

<https://docs.ansible.com/ansible/latest/dev_guide/developing_collections.html>

<https://github.com/jandiorio/ansible-dnac-modules>
<https://github.com/CiscoDevNet/DNAC-Top5>
<https://github.com/CiscoDevNet/DNAC-Site>
<https://github.com/CiscoDevNet?language=&page=1&q=dna&type=&utf8=%E2%9C%93>
