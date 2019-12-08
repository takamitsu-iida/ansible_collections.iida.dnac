#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Cisco DNA-C REST API Client.

  get authentication token
  process common operation get/post/delete

  Requirements:
    - requests
    - pyjwt (optional)

"""

import datetime  # token expire date
import fcntl  # process exclusion cotrol
import functools  # decorator
import json
import logging
import os
import pickle
import sys

try:
  import requests
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
  import base64  # deode jwt by hand
  HAS_JWT = False


class DnacRestClient(object):
  """process common operation to access cisco dna-c rest api.
  """
  # pylint: disable=too-many-instance-attributes,too-many-public-methods

  API_PATH_TOKEN = '/dna/system/api/v1/auth/token'
  API_PATH_GROUP = '/api/v1/group'

  def __init__(self, params):
    """constructor for DnacRestClient class

    expected key of params
      - check_mode
      - host
      - username
      - password
      - timeout
      - http_proxy

    Arguments:
        params {dict} -- param dictionary
    """

    # use this filename for app name
    app_name = os.path.splitext(os.path.basename(__file__))[0]

    # file name of token cache
    token_filename = "{}.pickle".format(app_name)

    # directory name of token cache
    # /tmp is used if not specified
    self.log_dir = params.get('log_dir', '/tmp')
    os.makedirs(self.log_dir, exist_ok=True)

    # path of token cache
    self.token_path = os.path.join(self.log_dir, token_filename)

    # file name of lock file
    lock_filename = "{}.lock".format(app_name)

    # path of lock file
    self.lock_path = os.path.join(self.log_dir, lock_filename)

    # create lock file with empty content
    if os.path.isfile(self.lock_path):
      pass
    else:
      with open(self.lock_path, 'w', encoding='UTF-8'):
        pass

    # check_mode or not
    self._check_mode = params.get('check_mode', False)

    # target hostname or ip addr
    self._host = params.get('host')

    # username and password
    self._username = params.get('username', '')
    self._password = params.get('password', '')

    # timeout
    self._timeout = params.get('timeout', 30)

    # http proxy
    http_proxy = params.get('http_proxy')
    if http_proxy:
      self._proxies = {
        'http': http_proxy,
        'https': http_proxy
      }
    else:
      self._proxies = None


  def save_token(self, token):
    """Save token string to file as pickle format.

    dict
      key: URL + '.' + username
      value: token string

    Arguments:
        token {string} -- token string
    """

    key = self._host + '.' + self._username

    data = self.load_data()

    if data:
      if not token:
        # remove it
        if key in data:
          data.pop(key)
      else:
        # overwrite the token
        data[key] = token
    else:
      # newly create
      data = {}
      data[key] = token

    try:
      with open(self.token_path, 'wb') as f:
        pickle.dump(data, f)
    except IOError as e:
      logging.exception(e)


  def load_data(self):
    """Restore cache data from pickle file.

    Returns:
        dict or None -- cached data
    """

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


  def load_token(self):
    """Load date from cache file and return token string.

    Returns:
        str or None -- token string
    """
    data = self.load_data()
    if not data:
      return None

    key = self._host + '.' + self._username
    return data.get(key)


  def is_expired(self, token):
    """return True if specified token is expired.
    """

    # now = datetime.datetime.utcnow()
    now = datetime.datetime.now(datetime.timezone.utc)

    payload = self.parse_jwt(token)
    if not payload:
      return True

    # 'exp' is the expiration date
    expires_at_str = payload.get('exp')
    if not expires_at_str:
      return True

    # convert to datetime object
    expires_at = datetime.datetime.fromtimestamp(expires_at_str, datetime.timezone.utc)

    # dirty hack
    # in case of time difference, -5 min
    expires_at -= datetime.timedelta(minutes=5)

    if now < expires_at:
      return False

    return True


  def get_token(self):
    """get token with thread safe
    """
    with open(self.lock_path) as lock_file:
      # block until lock file
      fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
      try:
        token = self._get_token()
      finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    return token


  def _get_token(self):
    """get token
    """
    # return token from cache
    token = self.get_token_from_cache()
    if token:
      return token

    logging.info('trying to get new token from api endpoint')

    result = self.get_token_from_network()

    if result.get('failed'):
      message = result.get('message')
      logging.info(message)
      return None

    token = result.get('token')

    self.save_token(token)

    return token


  def get_token_from_cache(self):
    """get token from cache file.

    Returns:
        str or None -- tonen string if cache is available
    """
    token = self.load_token()

    if not token:
      logging.info("There is no token on disk cache")
      return None

    if self.is_expired(token):
      logging.info("Found token on disk cache but expired")
      return None

    logging.info("There is available token on disk cache")
    return token


  def get_token_from_network(self):
    """get token from dna-c endpoint

    ref
    https://developer.cisco.com/docs/dna-center/#!generating-and-using-an-authorization-token

    Returns:
        str or None -- tonen string if cache is available
    """

    timeout = self._timeout

    proxies = self._proxies

    headers = {
      'Accept': "application/json",
      'Content-Type': "application/json"
    }

    auth = (self._username, self._password)

    api_path = self._normalize_api_path(self.API_PATH_TOKEN)
    url = 'https://{}/{}'.format(self._host, api_path)

    result = {
      'failed': True,
      'msg': '',
      'status_code': -1,
      'token': ''
    }

    try:
      r = requests.post(url, timeout=timeout, proxies=proxies, headers=headers, auth=auth, verify=False)
    except requests.exceptions.ProxyError:
      result['msg'] = 'requests.exceptions.ProxyError occured'
    except requests.exceptions.SSLError:
      result['msg'] = 'requests.exceptions.SSLError occured'
    except requests.exceptions.ConnectionError:
      result['msg'] = 'requests.exceptions.ConnectionError occured'
    except requests.exceptions.HTTPError:
      result['msg'] = 'requests.exceptions.HTTPError occured'
    except requests.exceptions.ReadTimeout:
      result['msg'] = 'requests.exceptions.ReadTimeout occured'
    except requests.exceptions.RequestException:
      result['msg'] = 'requests.exceptions.RequestException occured'

    if r is None:
      return result

    if not r.ok:
      result['msg'] = 'status code: ' + str(r.status_code)
      return result

    # success
    result['failed'] = False

    # get token from response data
    data = r.json()
    result['token'] = data.get('Token')

    return result


  def parse_jwt(self, token):
    """decode JWT format token

    RFC7519 JSON Web Tokens
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

    Arguments:
        token {str} -- JWT format token string

    Returns:
        dict -- token decoded as json format
    """

    if HAS_JWT:
      # if PyJWT is installed
      payload = jwt.decode(token, verify=False)
    else:
      tmp = token.split('.')
      payload = tmp[1]

      # pad '=' until length is multiple of 4
      payload += '=' * (-len(payload) % 4)
      payload = base64.b64decode(payload).decode()
      payload = json.loads(payload)

    return payload


  # define decorator
  def set_token():
    """decorator for GET/POST/PUT/DELETE operation

    keys
      'failed'
      'status_code'
      'data'
      'Content-Type'

    Returns:
        dict -- result of requests GET/POST/PUT/DELETE operation
    """

    def _outer_wrapper(wrapped_function):
      @functools.wraps(wrapped_function)
      def _wrapper(self, *args, **kwargs):

        #
        # PRE PROCESS
        #
        result = {
          'failed': True,
          'msg': '',
          'status_code': -1,
          'data': {}
        }

        token = self.get_token()
        if not token:
          msg = "failed to get token to access rest api"
          logging.error(msg)
          result['msg'] = msg
          return result

        headers = {
          'Accept': "application/json",
          'Content-Type': "application/json",
          'x-auth-token': token
        }

        timeout = self.timeout()
        proxies = self.proxies()

        #
        # PROCESS
        #
        try:
          msg = ''
          r = wrapped_function(self, *args, headers=headers, timeout=timeout, proxies=proxies, verify=False, **kwargs)
        except requests.exceptions.ProxyError as e:
          result['msg'] = "requests.exceptions.ProxyError occured"
          result['original_message'] = str(e)
        except requests.exceptions.SSLError as e:
          result['msg'] = "requests.exceptions.SSLError occured"
          result['original_message'] = str(e)
        except requests.exceptions.ConnectionError as e:
          result['msg'] = "requests.exceptions.ConnectionError occured"
          result['original_message'] = str(e)
        except requests.exceptions.HTTPError as e:
          result['msg'] = "requests.exceptions.HTTPError occured"
          result['original_message'] = str(e)
        except requests.exceptions.ReadTimeout as e:
          result['msg'] = "requests.exceptions.ReadTimeout occured"
          result['original_message'] = str(e)
        except requests.exceptions.RequestException as e:
          result['msg'] = "requests.exceptions.RequestException occured"
          result['original_message'] = str(e)

        #
        # POST PROCESS
        #

        if r is None:
          return result

        result['status_code'] = r.status_code

        # remove token if authentication error
        if r.status_code == 401:
          self.save_token(None)
          result['msg'] = "authentication error?"
          result['original_message'] = r.json()
          return result

        logging.info("%s %s", r.status_code, r.url)

        result['data'] = r.json()

        # success
        if r.ok:
          result['failed'] = False

        return result
        #
      return _wrapper
    return _outer_wrapper
  #


  def _normalize_api_path(self, api_path):
    return api_path.strip('/')

  @set_token()
  def get(self, api_path='', params=None, **kwargs):
    """requests.get() wrapped with set_token() decorator
    """
    if not api_path:
      return None

    api_path = self._normalize_api_path(api_path)
    url = 'https://{}/{}'.format(self._host, api_path)

    logging.info("GET %s", url)
    return requests.get(url, params=params, **kwargs)


  @set_token()
  def post(self, api_path='', data='', **kwargs):
    """requests.post() wrapped with set_token() decorator
    """
    if not api_path:
      return None

    api_path = self._normalize_api_path(api_path)
    url = 'https://{}/{}'.format(self._host, api_path)

    logging.info("POST %s", url)
    return requests.post(url, json.dumps(data), **kwargs)


  @set_token()
  def put(self, api_path='', data='', **kwargs):
    """requests.put() wrapped with set_token() decorator
    """
    if not api_path:
      return None

    api_path = self._normalize_api_path(api_path)
    url = 'https://{}/{}'.format(self._host, api_path)

    logging.info("PUT %s", url)
    return requests.put(url, json.dumps(data), **kwargs)


  @set_token()
  def delete(self, api_path='', **kwargs):
    """requests.delete() wrapped with set_token() decorator
    """
    if not api_path:
      return None

    api_path = self._normalize_api_path(api_path)
    url = 'https://{}/{}'.format(self._host, api_path)

    logging.info("DELETE %s", url)
    return requests.delete(url, **kwargs)


  def create_object(self, api_path='', data=None):
    """create object in dna-c

    Arguments:
        api_path {str} -- target api path
        data {dict} -- data to be created
    """

    result = {
      'changed': False,
      'failed': False,
      'msg': ''
    }

    if self._check_mode:
      result['msg'] = 'did nothing because of check mode'
      result['failed'] = False
      return result

    if not data or not isinstance(data, dict):
      result['msg'] = 'data should be dict object'
      result['failed'] = True
      return result

    r = self.post(api_path=api_path, data=data)

    if not r:
      result['msg'] = 'failed before requests.get()'
      result['failed'] = True
      return result

    if r.status_code in [200, 201]:
      # success

      data = r.get('data')
      if url.find('intent') >= 0:
        task_response = self.intent_task_checker(r['executionId'])
      else:
        task_response = self.task_checker(r['response']['taskId'])


    elif r.status_code == 202:
      # async operation


    else:
      result['changed'] = False
      result['failed'] = True
      result['original_message'] = r.get('original_message')

    return result


  # lookup group_id by group_name
  def get_group_id_by_name(self, group_name):
    """lookup group id

    Arguments:
        group_name {str} -- group name

    Returns:
        str -- group id
    """

    if group_name.lower() == 'global':
      return '-1'

    api_path = self.API_PATH_GROUP
    result = self.get(api_path)
    if not result or result.get('failed'):
      return '-1'

    data = result.get('data')
    #   "data": {
    #     "response": [
    #       {
    #         "parentId": "ba06348e-ee80-4058-bb23-f0c9a5fd728b",
    response = data.get('response')
    if not response:
      return '-1'

    group_ids = [group.get('id') for group in response if group.get('name') == group_name]
    if len(group_ids) == 1:
      return group_ids[0]

    return '-1'

  def get_group_names(self):
    """get all group name

    Returns:
        list -- list of all group name
    """

    api_path = self.API_PATH_GROUP
    result = self.get(api_path)
    if not result or result.get('failed'):
      return []

    data = result.get('data')
    #   "data": {
    #     "response": [
    #       {
    #         "parentId": "ba06348e-ee80-4058-bb23-f0c9a5fd728b",
    response = data.get('response')

    group_names = [group.get('name') for group in response]

    return group_names


  def process_common_settings(self, payload, group_id):
    """[summary]

    Arguments:
        payload {list} -- list of params dict
        group_id {str} -- group_id uuid
    """

    result = {
      'failed': True,
      'changed': False
    }

    if group_id:
      payload[0].update({'groupUuid': group_id})
    else:
      result['original_message'] = group_id
      result['msg'] = "Failed to locate groupUuid"
      return result

    # Define local variables
    state = self.module.params['state']

    # Get current settings
    settings = self.get_obj()
    settings = settings['response']
    setting_count = len(settings)

    # Save the existing and proposed datasets
    self.result['previous'] = settings
    self.result['proprosed'] = payload

    if state == 'present':
      if setting_count == 1:
        # compare previous to proposed
        if settings[0]['value'] != payload[0]['value']:
          self.create_obj(payload)
        else:
          self.result['changed'] = False
          self.result['msg'] = 'Already in desired state.'
          self.module.exit_json(**self.result)
      elif setting_count == 0:
        # create the object
        self.create_obj(payload)

    elif state == 'absent':
      payload[0].update({'value': []})
      self.create_obj(payload)

  #
  # getter/setter
  #
  def check_mode(self, *_):
    """get/set _check_mode"""
    if not _:
      return self._check_mode
    self._check_mode = _[0]
    return self

  def host(self, *_):
    """get/set _host"""
    if not _:
      return self._host
    self._host = _[0]
    return self

  def username(self, *_):
    """get/set _username"""
    if not _:
      return self._username
    self._username = _[0]
    return self

  def password(self, *_):
    """get/set _password"""
    if not _:
      return self._password
    self._password = _[0]
    return self

  def timeout(self, *_):
    """get/set _timeout in second"""
    if not _:
      return self._timeout
    self._timeout = _[0]
    return self

  def proxies(self, *_):
    """get/set _proxies"""
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
    """main function for test

    Returns:
      int -- 0 successfully ended or other
    """

    logging.basicConfig(level=logging.INFO)

    # Cisco DevNet Sandbox
    # https://sandboxdnac2.cisco.com
    params = {
      'host': 'sandboxdnac2.cisco.com',
      'username': 'devnetuser',
      'password': 'Cisco123!',
      'timeout': 30,
      'log_dir': './log',
      'http_proxy': ''  ## http://username:password@proxy-url:8080
    }

    drc = DnacRestClient(params)

    # test authentication
    token = drc.get_token()
    if not token:
      print('failed to get token')
      return -1

    # parse token as JWT format
    payload = drc.parse_jwt(token)
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    # TEST: dump group dictionary
    # _test_group(drc)

    # TEST: get list of group names
    _test_group_names(drc)

    # TEST: get groupUuid
    # _test_group_id(drc, 'test123')

    return 0


  def _test_group(drc):
    api_path = drc.API_PATH_GROUP
    result = drc.get(api_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    # {
    #   "failed": true,
    #   "status_code": 200,
    #   "Content-Type": "application/json",
    #   "data": {
    #     "response": [
    #       {
    #         "parentId": "ba06348e-ee80-4058-bb23-f0c9a5fd728b",
    #         "systemGroup": false,

  def _test_group_names(drc):
    group_names = drc.get_group_names()
    for name in group_names:
      print(name)

  def _test_group_id(drc, group_name):
    result = drc.get_group_id_by_name(group_name)
    print(result)


  # 実行
  sys.exit(main())
