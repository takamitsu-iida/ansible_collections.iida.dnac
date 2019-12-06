#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cisco DNA CenterのREST APIを利用する機能を提供します。

依存外部モジュール
  requests
  pyjwt (optional)
"""

import datetime  # トークンの有効期限時刻を知るために必要
import fcntl  # ファイルロックを使ってプロセス間の排他制御を行う
import functools  # デコレータを作るのに必要
import json
import logging
import os
import pickle
import sys

try:
  import requests
  # HTTPSを使用した場合に、証明書関連の警告を無視する
  # pylint: disable=E1101
  requests.packages.urllib3.disable_warnings()
except ImportError as e:
  logging.exception(e)
  sys.exit(1)

try:
  # pip install pyjwt
  import jwt
  HAS_JWT = True
except ImportError as e:
  import base64  # JWTはbase64でデコードできる
  HAS_JWT = False


class DnacRestClient(object):
  """
  トークンを気にせずにREST APIに接続する機能を提供します。
  """
  # pylint: disable=too-many-instance-attributes

  # DNA Centerの認証エンドポイント
  EP_TOKEN = 'https://{}/dna/system/api/v1/auth/token'

  def __init__(self, params):
    """
    コンストラクタ
    """

    # パラメータの一覧を辞書型で受け取る
    # 期待するキー
    #   host
    #   username
    #   password
    #   timeout
    #   http_proxy

    # 自身の名前から拡張子を除いてプログラム名を得る
    app_name = os.path.splitext(os.path.basename(__file__))[0]

    # トークンを保存するファイル名(形式はjsonではなくpickle形式)
    token_filename = "{}.pickle".format(app_name)

    # トークンを保存するログディレクトリ
    # paramsにlog_dirが無ければ /tmp を利用する
    # 無ければ作る
    self.log_dir = params.get('log_dir', '/tmp')
    os.makedirs(self.log_dir, exist_ok=True)

    # トークンファイルへのパス
    self.token_path = os.path.join(self.log_dir, token_filename)

    # ロックファイルの名前
    lock_filename = "{}.lock".format(app_name)

    # ロックファイルへのパス
    self.lock_path = os.path.join(self.log_dir, lock_filename)

    # ロックファイルが存在しない場合は作っておく
    # 中身は空っぽでよい
    if os.path.isfile(self.lock_path):
      pass
    else:
      with open(self.lock_path, 'w', encoding='UTF-8'):
        pass

    # 接続先のDNS名もしくはIPアドレス
    self._host = params.get('host')

    # トークンを取得するURL
    self.url_token = self.EP_TOKEN.format(self._host)

    # 認証情報
    self._username = params.get('username', '')
    self._password = params.get('password', '')

    # 通信のタイムアウト
    self._timeout = params.get('timeout', 30)

    # プロキシ設定
    http_proxy = params.get('http_proxy')
    if http_proxy:
      self._proxies = {
        'http': http_proxy,
        'https': http_proxy
      }
    else:
      self._proxies = None


  def saveToken(self, token):
    """
    トークンを受け取って辞書型としてpickleでファイルに保存します
    """

    key = self._host + '.' + self._username

    data = self.loadData()

    if data:
      # 上書きする
      data[key] = token
    else:
      # 新規作成
      data = {}
      data[key] = token

    try:
      with open(self.token_path, 'wb') as f:
        pickle.dump(data, f)
    except IOError as e:
      logging.exception(e)


  def loadData(self):
    """
    pickleでファイルに保存されているデータを復元します
    """
    # そもそもファイルがない
    if not os.path.isfile(self.token_path):
      return None

    data = None
    try:
      with open(self.token_path, 'rb') as f:
        data = pickle.load(f)
    except IOError as e:
      logging.exception(e)
    except ValueError as e:
      logging.exception(e)

    return data


  def loadToken(self):
    """
    データをロードして、トークンだけを取り出して返却します。
    """
    data = self.loadData()
    if not data:
      return None

    key = self._host + '.' + self._username
    return data.get(key)


  def isExpired(self, token):
    """
    有効期限が切れていればTrueを返します
    """

    # now = datetime.datetime.utcnow()
    now = datetime.datetime.now(datetime.timezone.utc)

    payload = self.parse_jwt(token)
    if not payload:
      return True

    # 有効期限 'exp' を取り出す
    expires_at_str = payload.get('exp')
    if not expires_at_str:
      return True

    # 時刻に戻す
    expires_at = datetime.datetime.fromtimestamp(expires_at_str, datetime.timezone.utc)
    print(expires_at)

    # dirty hack
    # 誤差と処理遅延を考えて5分を減算する
    expires_at -= datetime.timedelta(minutes=5)

    if now < expires_at:
      return False

    return True


  def getToken(self):
    """
    スレッドセーフなトークン取得
    """
    with open(self.lock_path) as lock_file:
      # ロックを獲得できるまでブロッキング
      fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
      try:
        # ロックを獲得したら、トークンを取得する
        token = self._getToken()
      finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    return token


  def _getToken(self):
    """
    実際にトークンを取得する処理
    """
    # ファイルに有効なキャッシュが残っていればそれを返す
    token = self.getTokenFromCache()
    if token:
      return token

    # 有効なキャッシュはなかった
    logging.info('trying to get new token from api endpoint')

    result = self.getTokenFromNetwork()

    if result.get('failed'):
      message = result.get('message')
      logging.info(message)
      return None

    token = result.get('token')

    # 保存する
    self.saveToken(token)

    return token


  def getTokenFromCache(self):
    """
    ファイルからトークンのキャッシュを取得して返します
    """

    # ファイルから復元
    token = self.loadToken()

    # トークンがディスクに保存されていない
    if not token:
      logging.info("There is no token on disk cache")
      return None

    # トークンの有効期間が切れてないか確認する
    if self.isExpired(token):
      logging.info("Found token on disk cache but expired")
      return None

    logging.info("There is available token on disk cache")
    return token


  def getTokenFromNetwork(self):
    """
    DNA Centerからトークンを取得して返します
    """

    # タイムアウト
    timeout = self._timeout

    # プロキシ
    proxies = self._proxies

    # ヘッダ情報
    headers = {
      'Accept': "application/json",
      'Content-Type': "application/json"
    }

    # 認証情報
    auth = (self._username, self._password)

    # エンドポイント
    url = self.EP_TOKEN.format(self._host)

    # 戻り値
    result = {
      'failed': True,
      'message': '',
      'exception': '',
      'token': ''
    }

    # POSTを発行
    # この処理は最長でself._timeout秒かかる
    r = None
    try:
      r = requests.post(url, timeout=timeout, proxies=proxies, headers=headers, auth=auth, verify=False)
    except requests.exceptions.ProxyError as e:
      result['exception'] = str(e)
      result['message'] = 'requests.exceptions.ProxyError occured'
    except requests.exceptions.SSLError as e:
      result['exception'] = str(e)
      result['message'] = 'requests.exceptions.SSLError occured'
    except requests.exceptions.ConnectionError as e:
      result['exception'] = str(e)
      result['message'] = 'requests.exceptions.ConnectionError occured'
    except requests.exceptions.HTTPError as e:
      result['exception'] = str(e)
      result['message'] = 'requests.exceptions.HTTPError occured'
    except requests.exceptions.ReadTimeout as e:
      result['exception'] = str(e)
      result['message'] = 'requests.exceptions.ReadTimeout occured'
    except requests.exceptions.RequestException as e:
      result['exception'] = str(e)
      result['message'] = 'requests.exceptions.RequestException occured'

    # 応答をチェック
    if not r:
      return result

    if not r.ok:
      result['message'] = 'status code: ' + str(r.status_code)
      return result

    # トークンはレスポンスのデータとして格納されているので、それを取り出す
    data = r.json()
    token = data.get('Token')
    result['token'] = token
    result['failed'] = False

    return result


  def parse_jwt(self, token):
    """
    JWT形式(RFC7519 JSON Web Tokens)のトークンをデコードして返却します

    https://auth0.com/docs/tokens/id-tokens#verify-the-signature
    https://auth0.com/docs/tokens/reference/jwt/jwt-structure
    https://jwt.io

    {
      "sub": "5ce712b08ee66202fa2eb8f8",
      "authSource": "internal",
      "tenantName": "TNT0",
      "roles": [
        "5b6cfdff4309900089f0ff37"
      ],
      "tenantId": "5b6cfdfc4309900089f0ff30",
      "exp": 1575109548,
      "username": "devnetuser"
    }
    """

    if HAS_JWT:
      # PyJWTを使って情報を取り出す
      payload = jwt.decode(token, verify=False)
    else:
      tmp = token.split('.')
      payload = tmp[1]

      # 長さ4の倍数になるように '=' でパディングする
      payload += '=' * (-len(payload) % 4)
      payload = base64.b64decode(payload).decode()
      payload = json.loads(payload)

    return payload


  # デコレータ定義
  def set_token():
    """
    GET/POST/PUT/DELETEの前後処理をするデコレータ
    """
    def _outer_wrapper(wrapped_function):
      @functools.wraps(wrapped_function)
      def _wrapper(self, *args, **kwargs):
        #
        # 前処理
        #

        # 戻り値は必ずオブジェクトを返す
        result = {}

        # トークンを取得
        token = self.getToken()
        if not token:
          logging.error("failed to get token to access rest api")
          result['status_code'] = -100
          result['data'] = None
          return result

        # ヘッダにトークンを挿入
        headers = {
          'Accept': "application/json, text/plain",
          'Content-Type': "application/json",
          'X-Auth-Token': token.get('X-Subject-Token', '')
        }

        # タイムアウト値
        timeout = self.timeout()

        # プロキシ設定
        proxies = self.proxies()

        #
        # 実処理
        #
        r = wrapped_function(self, *args, headers=headers, timeout=timeout, proxies=proxies, verify=False, **kwargs)

        #
        # 後処理
        #

        if r is None:
          result['status_code'] = -1
          result['data'] = None
          return result

        # ログ
        logging.info("%s '%s'", r.status_code, r.url)

        # トークンを保存
        # if r.ok:
        #   restc_tokenmanager.token(token)
        # elif r.status_code == 401:
        #   restc_tokenmanager.token(None)

        # status_codeを保存
        result['status_code'] = r.status_code

        # Content-Typeを保存
        ctype = r.headers.get('Content-Type', '')
        result['Content-Type'] = ctype

        # データを保存
        # JSON形式 or テキスト形式
        if ctype.find("json") >= 0:
          result['data'] = r.json()
        else:
          result['data'] = r.text

        return result
        #
      return _wrapper
    return _outer_wrapper
  #


  # デコレータ版のGET
  # requestsが必要とする引数はデコレータが**kwargsにセットしてくれる
  # この関数の戻り値はデコレータに横取りされ、加工されたものがコール元に返却される
  @set_token()
  def get(self, url='', params='', **kwargs):
    """
    指定したURLにrequests.getで接続して、レスポンスを返します。
    """
    if not url:
      return None

    logging.info("GET '%s'", url)
    try:
      return requests.get(url, params=params, **kwargs)
    except requests.exceptions.ProxyError:
      logging.error("requests.exceptions.ProxyError occured")
    except requests.exceptions.SSLError:
      logging.error("requests.exceptions.SSLError occured")
    except requests.exceptions.ConnectionError:
      logging.error("requests.exceptions.ConnectionError occured")
    except requests.exceptions.HTTPError:
      logging.error("requests.exceptions.HTTPError occured")
    except requests.exceptions.ReadTimeout:
      logging.error("requests.exceptions.ReadTimeout occured")
    except requests.exceptions.RequestException as e:
      logging.exception(e)
    return None


  @set_token()
  def post(self, url='', data='', **kwargs):
    """
    指定したURLにrequests.postで接続して、レスポンスを返します。
    """
    if not url:
      return None

    logging.info("POST '%s'", url)
    try:
      return requests.post(url, json.dumps(data), **kwargs)
    except requests.exceptions.ProxyError:
      logging.error("requests.exceptions.ProxyError occured")
    except requests.exceptions.SSLError:
      logging.error("requests.exceptions.SSLError occured")
    except requests.exceptions.ConnectionError:
      logging.error("requests.exceptions.ConnectionError occured")
    except requests.exceptions.HTTPError:
      logging.error("requests.exceptions.HTTPError occured")
    except requests.exceptions.ReadTimeout:
      logging.error("requests.exceptions.ReadTimeout occured")
    except requests.exceptions.RequestException as e:
      logging.exception(e)
    return None


  @set_token()
  def put(self, url='', data='', **kwargs):
    """
    指定したURLにrequests.putで接続して、レスポンスを返します。
    """
    if not url:
      return None

    logging.info("PUT '%s'", url)
    try:
      return requests.put(url, json.dumps(data), **kwargs)
    except requests.exceptions.ProxyError:
      logging.error("requests.exceptions.ProxyError occured")
    except requests.exceptions.SSLError:
      logging.error("requests.exceptions.SSLError occured")
    except requests.exceptions.ConnectionError:
      logging.error("requests.exceptions.ConnectionError occured")
    except requests.exceptions.HTTPError:
      logging.error("requests.exceptions.HTTPError occured")
    except requests.exceptions.ReadTimeout:
      logging.error("requests.exceptions.ReadTimeout occured")
    except requests.exceptions.RequestException as e:
      logging.exception(e)
    return None


  @set_token()
  def delete(self, url='', **kwargs):
    """
    指定したURLにrequests.deleteで接続して、レスポンスを返します。
    """
    if not url:
      return None

    logging.info("DELETE '%s'", url)
    try:
      return requests.delete(url, **kwargs)
    except requests.exceptions.ProxyError:
      logging.error("requests.exceptions.ProxyError occured")
    except requests.exceptions.SSLError:
      logging.error("requests.exceptions.SSLError occured")
    except requests.exceptions.ConnectionError:
      logging.error("requests.exceptions.ConnectionError occured")
    except requests.exceptions.HTTPError:
      logging.error("requests.exceptions.HTTPError occured")
    except requests.exceptions.ReadTimeout:
      logging.error("requests.exceptions.ReadTimeout occured")
    except requests.exceptions.RequestException as e:
      logging.exception(e)
    return None

  #
  # 以下、getterとsetter
  #

  def host(self, *_):
    """接続先のホスト名を取得、設定します"""
    if not _:
      return self._host
    self._host = _[0]
    return self

  def username(self, *_):
    """接続ユーザ名を取得、設定します"""
    if not _:
      return self._username
    self._username = _[0]
    return self

  def password(self, *_):
    """接続パスワードを取得、設定します"""
    if not _:
      return self._password
    self._password = _[0]
    return self

  def timeout(self, *_):
    """タイムアウト値（秒）を取得、設定します"""
    if not _:
      return self._timeout
    self._timeout = _[0]
    return self

  def proxies(self, *_):
    """プロキシ設定を取得、設定します。"""
    if not _:
      return self._proxies
    self._proxies = _[0]
    return self
  #


#
# ここから単体テスト
#
if __name__ == '__main__':

  def main():
    """
    メイン関数

    Returns:
      int -- 正常終了は0、異常時はそれ以外を返却
    """

    logging.basicConfig(level=logging.INFO)

    # Cisco DevNetのサンドボックス
    # いつまで存在するかわからない
    # https://sandboxdnac2.cisco.com/dna/system/api/v1/auth/token

    params = {
      'host': 'sandboxdnac2.cisco.com',
      'username': 'devnetuser',
      'password': 'Cisco123!',
      'timeout': 30,
      'log_dir': './log',
      'http_proxy': ''  ## http://username:password@proxy-url:8080
    }

    drc = DnacRestClient(params)

    token = drc.getToken()

    if not token:
      print('failed to get token')
      return -1

    payload = drc.parse_jwt(token)

    print(json.dumps(payload, ensure_ascii=False, indent=2))

    return 0


  # 実行
  sys.exit(main())
