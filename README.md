# Ansible Collection - iida.dnac

Cisco DNA CenterをREST APIで操作するAnsibleコレクションです。

REST APIクライアントを簡易的にPythonで実装することが多いと思います。
それをansibleで実行するためのコレクションです。

## Requirements

- Ansible 2.9
- Cisco Intent API 1.2

## 作戦

1. トークンを取得するモジュール（アクションプラグイン）を呼び出します
1. 結果をregisterで格納します
1. registerからトークンの文字列を取り出します
1. そのトークンを次のモジュールの引数として利用します

ターゲットノードに乗り込んで処理を実行するわけではないので、localhost上で実行するactionプラグインを中心に実装します。

## 認証トークンについて

REST APIの利用に伴う認証にJWT形式のトークンを返してくる場合を想定します。
