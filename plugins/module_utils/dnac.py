#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines

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
import time
import json
import logging
import os
import pickle
import sys

try:
  import requests
  requests.packages.urllib3.disable_warnings()
except ImportError as e:
  logging.exception(e)
  sys.exit(1)

try:
  import jwt  # pip install pyjwt
  HAS_JWT = True
except ImportError as e:
  import base64  # decode jwt by hand
  HAS_JWT = False


class DnacRestClient(object):
  """process common operation to access cisco dna-c rest api.
  """
  # pylint: disable=too-many-instance-attributes,too-many-public-methods

  # Cisco DNA Center version 1.2.6 and above
  API_PATH_TOKEN = '/dna/system/api/v1/auth/token'

  # DEFAULTS
  DEFAULT_LOGDIR = '/tmp'
  DEFAULT_CHECKMODE = False
  DEFAULT_TIMEOUT = 30  # timeout used in requests module, default is 30 sec


  # parameters for async operation
  RETRY_INTERVAL = 2
  MAX_RETRY_COUNT = 10

  def __init__(self, params):
    """constructor for DnacRestClient class

    expected key of params
      - check_mode
      - host
      - port
      - username
      - password
      - timeout
      - http_proxy
      - runsync

    Arguments:
        params {dict} -- param dictionary
    """

    # use this filename for app name
    app_name = os.path.splitext(os.path.basename(__file__))[0]

    # file name of token cache
    token_filename = "{}.pickle".format(app_name)

    # directory name of token cache, /tmp is used if not specified
    self.log_dir = params.get('log_dir', self.DEFAULT_LOGDIR)
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

    # is check_mode or not, default is False
    self._check_mode = params.get('check_mode', self.DEFAULT_CHECKMODE)

    # target hostname fqdn or ip addr, port
    self._host = params.get('host')
    self._port = params.get('port', 443)

    # username and password
    self._username = params.get('username', '')
    self._password = params.get('password', '')

    # timeout used in requests module
    self._timeout = params.get('timeout', self.DEFAULT_TIMEOUT)

    # http proxy, http://username:password@proxy-server-fqdn:8080
    http_proxy = params.get('http_proxy')
    if http_proxy:
      self._proxies = {
        'http': http_proxy,
        'https': http_proxy
      }
    else:
      self._proxies = None

    # force sync operation, default is False
    self._runsync = params.get('runsync', False)

    # on memory cache for async operation
    # async operation repeats get method until process end
    self._token = ''

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

  def port(self, *_):
    """get/set _port"""
    if not _:
      return self._port
    self._port = _[0]
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

  def runsync(self, *_):
    """get/set _runsync"""
    if not _:
      return self._runsync
    self._runsync = _[0]
    return self


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
        self._token = ''
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

    # in case of time difference, -5 min
    expires_at -= datetime.timedelta(minutes=5)

    if now < expires_at:
      return False

    return True


  def get_token(self):
    """get token thread safe
    """
    # memory cache
    if self._token:
      return self._token

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
    # authentication use https port 443
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

        if self.runsync() is True:
          headers.update({'__runsync': "true"})

        timeout = self.timeout()
        proxies = self.proxies()

        #
        # PROCESS
        #
        r = None
        try:
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
        logging.info("%s %s", r.status_code, r.url)

        # remove token cache if authentication error
        if r.status_code == 401:
          self.save_token(None)
          result['msg'] = "authentication error"
          result['original_message'] = r.json()
          return result

        content_type = r.headers.get('Content-Type', '')
        if content_type.find("json") >= 0:
          result['data'] = r.json()
        else:
          result['data'] = r.text

        # success
        if r.ok:
          result['failed'] = False

        return result
        #
      return _wrapper
    return _outer_wrapper
  #

  @staticmethod
  def _normalize_api_path(api_path):
    return api_path.strip('/')

  @staticmethod
  def _extract_response(get_result):
    if not get_result:
      return None
    data = get_result.get('data', {})
    if isinstance(data, dict):
      return data.get('response')
    return None

  @set_token()
  def get(self, api_path='', params=None, **kwargs):
    """requests.get() wrapped with set_token() decorator
    """
    if not api_path:
      return None

    api_path = self._normalize_api_path(api_path)
    url = 'https://{}:{}/{}'.format(self._host, self._port, api_path)

    logging.info("GET %s", url)
    return requests.get(url, params=params, **kwargs)


  @set_token()
  def post(self, api_path='', data='', **kwargs):
    """requests.post() wrapped with set_token() decorator
    """
    if not api_path:
      return None

    api_path = self._normalize_api_path(api_path)
    url = 'https://{}:{}/{}'.format(self._host, self._port, api_path)

    logging.info("POST %s", url)
    return requests.post(url, json.dumps(data), **kwargs)


  @set_token()
  def put(self, api_path='', data='', **kwargs):
    """requests.put() wrapped with set_token() decorator
    """
    if not api_path:
      return None

    api_path = self._normalize_api_path(api_path)
    url = 'https://{}:{}/{}'.format(self._host, self._port, api_path)

    logging.info("PUT %s", url)
    return requests.put(url, json.dumps(data), **kwargs)


  @set_token()
  def delete(self, api_path='', **kwargs):
    """requests.delete() wrapped with set_token() decorator
    """
    if not api_path:
      return None

    api_path = self._normalize_api_path(api_path)
    url = 'https://{}:{}/{}'.format(self._host, self._port, api_path)

    logging.info("DELETE %s", url)
    return requests.delete(url, **kwargs)


  def wait_for_task(self, task_id):
    """wait for completion of specified task_id
    """
    timeout = self.RETRY_INTERVAL * self.MAX_RETRY_COUNT
    interval = self.RETRY_INTERVAL

    api_path = '/dna/intent/api/v1/task/{}'.format(task_id)

    result = {
      'failed': True,
      'msg': ''
    }

    start_time = time.time()

    while True:
      get_result = self.get(api_path=api_path)
      if not get_result:
        result['msg'] = 'failed before requests.get()'
        break

      data = get_result.get('data', {})
      response = data.get('response')
      # print(json.dumps(response, ensure_ascii=False, indent=2))

      if 'endTime' in response:
        result.update(get_result)
        result['failed'] = False
        break

      if start_time + timeout < time.time():
        result.update(get_result)
        result['failed'] = True
        result['msg'] = "task_id {} did not end within the specified timeout ({} sec)".format(task_id, timeout)
        break

      if response.get('isError') is True:
        result.update(get_result)
        result['failed'] = True
        result['msg'] = "task_id {} is error".format(task_id)
        break

      logging.info("task_id %s has not completed yet. Sleeping %s seconds...", task_id, interval)
      time.sleep(interval)

    return result


  def create_object(self, api_path='', data=None):
    """create object in dna-c

    Arguments:
        api_path {str} -- target api path
        data {dict} -- data to be created
    """

    result = {
      'failed': True,
      'changed': False
    }

    if self._check_mode:
      result['failed'] = False
      result['msg'] = 'did nothing because of check mode'
      return result

    post_result = self.post(api_path=api_path, data=data)

    if not post_result:
      result['msg'] = 'failed before requests.post()'
      return result

    # https://developer.cisco.com/docs/dna-center/#!getting-information-about-asynchronous-operations/getting-information-about-asynchronous-operations
    # When DNA Center Platform returns a 202 (Accepted) HTTP status code,
    # the result body includes a task ID and a URL that you can use to query
    # for more information about the asynchronous task that your original
    # request spawned. For example, you can use this information to
    # determine whether a lengthy task has completed.
    # {
    #     "response": {
    #         "taskId": "85c95140-50fc-4a57-994d-db58d3afe6b3",
    #         "url": "dna/intent/api/v1/task/85c95140-50fc-4a57-994d-db58d3afe6b3"
    #     },
    #     "version": "1.0"
    # }

    if __name__ == '__main__':
      print(json.dumps(post_result, ensure_ascii=False, indent=2))

    data = post_result.get('data')

    if post_result.get('status_code', -1) in [200, 201, 204, 206]:
      # successfuly ended
      result['changed'] = True
      result.update(post_result)
    elif post_result.get('status_code', -1) == 202:
      # successfully ended but async operation is needed
      response = data.get('response')
      task_id = response.get('taskId')
      wait_result = self.wait_for_task(task_id)
      result.update(wait_result)
      result['changed'] = not wait_result.get('failed')
    else:
      result.update(post_result)

    return result


  def delete_object(self, api_path=''):
    """[summary]

    Keyword Arguments:
        api_path {str} -- [description] (default: {''})
        data {dict} -- [description] (default: {None})
    """

    result = {
      'failed': True,
      'changed': False
    }

    if self._check_mode:
      result['failed'] = False
      result['msg'] = 'did nothing because of check mode'
      return result

    delete_result = self.delete(api_path=api_path)

    status_code = delete_result.get('status_code', -1)
    data = delete_result.get('data')

    if status_code in [200, 201, 204, 206]:
      # successfuly ended
      result['changed'] = True
      result.update(delete_result)
    elif status_code == 202:
      # successfully ended but async operation is needed
      response = data.get('response')
      task_id = response.get('taskId')
      wait_result = self.wait_for_task(task_id)
      result.update(wait_result)
      result['changed'] = not wait_result.get('failed')
    else:
      # failed
      result.update(delete_result)

    return result


  # lookup group_id by group_name
  def get_group_id_by_name(self, group_name):
    """lookup group id

    '/api/v1/group'

    Arguments:
        group_name {str} -- group name

    Returns:
        str -- group id
    """

    if not group_name or group_name.lower() == 'global':
      return '-1'

    api_path = '/api/v1/group'
    get_result = self.get(api_path)
    if not get_result or get_result.get('failed', True):
      return '0'

    data = get_result.get('data')
    response = data.get('response')
    #   "data": {
    #     "response": [
    #       {
    #         "parentId": "ba06348e-ee80-4058-bb23-f0c9a5fd728b",
    if not response:
      return '0'

    group_ids = [group.get('id') for group in response if group.get('name') == group_name]
    if len(group_ids) == 1:
      return group_ids[0]

    return '0'


  def get_site_names(self):
    """get all site name as dict

    VERSION 1.3
    '/dna/intent/api/v1/site'

    Returns:
        dict -- list of all group name
    """
    _cache = {}

    api_path = '/dna/intent/api/v1/site/count'
    get_result = self.get(api_path)
    if not get_result or get_result.get('failed'):
      return {}

    data = get_result.get('data')
    count = data.get('response')

    STEP = 10
    for start in range(1, count + 1, STEP):
      api_path = '/dna/intent/api/v1/site?offset={}&limit={}'.format(start, STEP)
      get_result = self.get(api_path=api_path)
      if not get_result or get_result.get('failed'):
        return {}
      data = get_result.get('data')
      sites = data.get('response')
      for site in sites:
        logging.info("Caching %s", site['groupNameHierarchy'])
        _cache[site['groupNameHierarchy']] = site

    # add Global
    _cache['Global'] = {'groupNameHierarchy': 'Global', 'additionalInfo': [{'attributes': {'type': 'area'}}]}

    return _cache


  def get_group_names(self):
    """get all group name

    VERSION 1.2
    '/api/v1/group'

    Returns:
        list -- list of all group name
    """

    api_path = '/api/v1/group'
    get_result = self.get(api_path)
    if not get_result or get_result.get('failed'):
      return []

    data = get_result.get('data')
    #   "data": {
    #     "response": [
    #       {
    #         "parentId": "ba06348e-ee80-4058-bb23-f0c9a5fd728b",
    response = data.get('response')

    group_names = [group.get('name') for group in response]

    return group_names


  def process_common_settings(self, api_path, state, want_settings):
    """[summary]

    Arguments:
        want_settings {list} -- list of desired params dict
        state {str} -- desired state, present or absent
    """

    result = {
      'failed': True,
      'changed': False
    }

    # get current settings
    requests_result = self.get(api_path=api_path)
    data = requests_result.get('data')
    have_settings = data.get('response')
    have_settings_count = len(have_settings)

    # debug
    if __name__ == '__main__':
      print(json.dumps(have_settings, ensure_ascii=False, indent=2))

    # for debug purpose
    result['have'] = have_settings
    result['want'] = want_settings

    if state == 'present' and have_settings_count == 1:
      # have exists
      # compare have and want
      if have_settings[0]['value'] == want_settings[0]['value']:
        result['failed'] = False
        result['msg'] = 'already in desired state'
      else:
        create_result = self.create_object(api_path=api_path, data=want_settings)
        if create_result:
          result.update(create_result)

    elif state == 'present' and have_settings_count == 0:
      # create new object
      create_result = self.create_object(api_path=api_path, data=want_settings)
      if create_result:
        result.update(create_result)

    elif state == 'absent':
      want_settings[0].update({'value': []})
      create_result = self.create_object(api_path=api_path, data=want_settings)
      if create_result:
        result.update(create_result)

    return result


  def process_banner(self, state='present', banner_message='', group_name='Global', retain_banner=True):
    """create banner in dna-c

    data structure
    [
      {
        "instanceType": "banner",
        "instanceUuid": "9f904f59-f2d1-4ab0-b1ba-abcd1eb1e5fd",
        "namespace": "global",
        "type": "banner.setting",
        "key": "device.banner",
        "version": 14,
        "value": [
          {
            "bannerMessage": "Test motd banner",
            "retainExistingBanner": false
          }
        ],
        "groupUuid": "7e0c9368-97a6-41f8-9e2c-d523e007d295",
        "inheritedGroupUuid": "-1",
        "inheritedGroupName": "Global"
      }
    ]

    Keyword Arguments:
        state {str} -- state provides the action to be executed, present or absent (default: {'present'})
        banner_message {str} -- banner message (default: {''})
        group_name {str} -- name of the group in the hierarchy (default: {'Global'})
        retain_banner {bool} -- overwrite existing banner or not (default: {True})
    """

    # convert group name to id
    group_id = self.get_group_id_by_name(group_name)

    payload = [{
      'instanceType': "banner",
      'namespace': "global",
      'type': "banner.setting",
      'key': "device.banner",
      'value': [{
        'bannerMessage': banner_message,
        'retainExistingBanner': retain_banner
      }],
      'groupUuid': group_id
    }]

    api_path = '/api/v1/commonsetting/global/{}?key=device.banner'.format(group_id)
    api_path = self._normalize_api_path(api_path)

    return self.process_common_settings(api_path, state, payload)


  def process_group(self, state='present', group_name='', group_type='area', parent_name='Global', building_info=None):
    """[summary]

    '/api/v1/group'

    group_type is a choice of "area", "building", "floor"

    Keyword Arguments:
        state {str} -- [description] (default: {'present'})
        group_name {str} -- [description] (default: {''})
        group_type {str} -- [description] (default: {'area'})
        parent_name {str} -- [description] (default: {'Global'})
        building_info {dict} -- [description] (default: {None})
    """
    result = {
      'failed': True,
      'changed': False
    }

    payload = {
      'groupTypeList': ["SITE"],
      'name': group_name,
      'additionalInfo': [
        {
          'nameSpace': "Location",
          'attributes': {'type': group_type},
        }]
    }

    if group_type == "building":
      if not building_info:
        building_info = {
          'type': "building",
          'address': "神奈川県川崎市中原区小杉町1-403",
          'country': "Japan",
          'latitude': "35.577510",
          'longitude': "139.658149"
        }

      payload['additionalInfo'][0]['attributes'].update(building_info)

    group_name_list = self.get_group_names()
    has_group_name = group_name in group_name_list
    has_parent_name = parent_name in group_name_list
    if not has_parent_name:
      result['msg'] = "there is no parent_name in group_name_list"
      return result

    api_path = '/api/v1/group'

    if state == 'present' and has_group_name:
      result['failed'] = False
      result['msg'] = "group_name {} already exists".format(group_name)
    elif state == 'present' and not has_group_name:
      create_result = self.create_object(api_path=api_path, data=payload)
      result.update(create_result)
    elif state == 'absent' and has_group_name:
      group_id = self.get_group_id_by_name(group_name)
      api_path = api_path + '/' + str(group_id)
      delete_result = self.delete_object(api_path=api_path)
      result.update(delete_result)
    elif state == 'absent' and not has_group_name:
      result['failed'] = False
      result['msg'] = "group_name {} is already absent".format(group_name)

    return result


  def assign_devices(self, site_id, device_list):
    """assign devices to site

    Arguments:
        site_id {[type]} -- [description]
        device_list {[type]} -- [description]
    """
    payload = {
      "device": device_list
    }

    payload = {
      "device": [{
        "serialNumber": "FOC1703V36B",
        "siteName": "Area1-BLD1",
        "ip": ""
      }, {
        "serialNumber": "FTX1842AHM1",
        "siteName": "Area1-BLD1",
        "ip": ""
      }, {
        "serialNumber": "FTX1842AHM2",
        "siteName": "Area1-BLD2",
        "ip": ""
      }, {
        "serialNumber": "FOX1525G5S1",
        "siteName": "Area1-BLD2",
        "ip": ""
      }, {
        "serialNumber": "FOX1524GV2Z",
        "siteName": "Area3-BLD1",
        "ip": ""
      }, {
        "serialNumber": "FXS1825Q1PA",
        "siteName": "Area3-BLD1",
        "ip": ""
      }, {
        "serialNumber": "FCW1630L0JG",
        "siteName": "Area3-BLD2",
        "ip": ""
      }]
    }

    api_path = '/dna/intent/api/v1/site/{}/device'.format(site_id)
    response = self.post(api_path=api_path, data=payload)
    print(json.dumps(response, indent=2))

  def get_device_list(self):
    """get device object list"""
    api_path = '/dna/intent/api/v1/network-device'
    get_result = self.get(api_path=api_path)
    return self._extract_response(get_result)

  def get_device_by_ip(self, ip=None):
    """get device object by ip address"""
    if ip is None:
      return None
    api_path = '/dna/intent/api/v1/network-device?managementIpAddress={}'.format(ip)
    get_result = self.get(api_path=api_path)
    return self._extract_response(get_result)

  def get_device_by_serial(self, serial_number=None):
    """get device object by serial number"""
    if serial_number is None:
      return None
    api_path = '/dna/intent/api/v1/network-device?serialNumber={}'.format(serial_number)
    get_result = self.get(api_path=api_path)
    return self._extract_response(get_result)

  def get_host_list(self):
    """get host object list"""
    api_path = '/api/v1/host'
    get_result = self.get(api_path=api_path)
    return self._extract_response(get_result)

  def get_host_by_ip(self, ip=None):
    """get host object by ip address"""
    if ip is None:
      return None
    api_path = '/api/v1/host?hostIp={}'.format(ip)
    get_result = self.get(api_path=api_path)
    return self._extract_response(get_result)

  def get_host_by_mac(self, mac=None):
    """get host object by mac address"""
    if mac is None:
      return None
    api_path = '/api/v1/host?hostMac={}'.format(mac)
    get_result = self.get(api_path=api_path)
    return self._extract_response(get_result)

  #

#
# TEST
#
if __name__ == '__main__':

  def main():
    """main function for test"""

    logging.basicConfig(level=logging.INFO)

    # Cisco DevNet Sandbox version 1.2.10 readonly
    _params_readonly = {
      'host': 'sandboxdnac2.cisco.com',
      'port': 443,
      'username': 'devnetuser',
      'password': 'Cisco123!',
      'timeout': 30,
      'log_dir': './log',
      'http_proxy': ''  ## http://username:password@proxy-url:8080
    }

    _params_reserved = {
      'host': '10.10.20.85',
      'port': 443,
      'username': 'admin',
      'password': 'Cisco1234!',
      'timeout': 30,
      'log_dir': './log',
      'http_proxy': ''  ## http://username:password@proxy-url:8080
    }

    HAS_RESERVATION = False
    params = _params_reserved if HAS_RESERVATION else _params_readonly

    drc = DnacRestClient(params)

    # test_token(drc)
    # test_api_path(drc)
    # test_dump_group(drc)
    # test_dump_group_by_name(drc)
    # test_group_names(drc)
    # test_group_id(drc)
    # test_banner(drc)
    # test_process_group(drc)

    r = drc.get_host_by_mac(mac="f0:25:72:2a:d2:41")
    print(json.dumps(r, ensure_ascii=False, indent=2))

    return 0


  def test_token(drc):
    """test token"""
    token = drc.get_token()
    if token:
      # parse token as JWT format
      payload = drc.parse_jwt(token)
      print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
      print('failed to get token')

  def test_api_path(drc):
    """test api_path"""
    api_path_list = [
      # '/dna/intent/api/v1/network-device/count',
      # '/dna/intent/api/v1/network-device',            # all network devices
      # '/dna/intent/api/v1/network-device?managementIpAddress=10.*&hostname=T1-8',
      # '/dna/intent/api/v1/network-device?managementIpAddress=10.10.20.81',
      # '/dna/intent/api/v1/site/count',                # version 1.3 and above
      # '/dna/intent/api/v1/site/?offset=0&limit=1',    # version 1.3 and above
      #
      # '/api/v1/group',
      # '/api/v1/group/count',  # all group include area, building, floor, ...
      # '/api/v1/group/ce4745ec-d99b-4d12-b008-5ad6513b09c3'  # group/{{ id }} returns specific group object
      '/api/v1/host',
      '/api/v1/host?hostIp=10.10.20.83'
    ]
    for api_path in api_path_list:
      get_result = drc.get(api_path=api_path)
      print(json.dumps(get_result, ensure_ascii=False, indent=2))

  def test_dump_group(drc):
    """test dump group"""
    api_path = '/api/v1/group'
    get_result = drc.get(api_path)
    print(json.dumps(get_result, ensure_ascii=False, indent=2))

  def test_dump_group_by_name(drc):
    """test dump group by name"""
    api_path = '/api/v1/group'
    get_result = drc.get(api_path)
    data = get_result.get('data')
    group_list = data.get('response')

    result = []
    names = ['iida', 'ksg-tp', 'Floor 18']
    for group in group_list:
      if group.get('name') in names:
        result.append(group)
    for group in result:
      print(json.dumps(group, ensure_ascii=False, indent=2))

  def test_group_names(drc):
    """test group names"""
    group_names = drc.get_group_names()
    print(json.dumps(group_names, ensure_ascii=False, indent=2))

  def test_group_id(drc):
    """test group_id"""
    group_name = 'Global'
    result = drc.get_group_id_by_name(group_name)
    print(result)

  def test_process_group(drc):
    """test process_group()"""
    process_result = drc.process_group(state='present', group_name='iida', group_type='area', parent_name='Global', building_info=None)
    print(json.dumps(process_result, ensure_ascii=False, indent=2))
    process_result = drc.process_group(state='present', group_name='ksg-tp', group_type='building', parent_name='iida', building_info=None)
    print(json.dumps(process_result, ensure_ascii=False, indent=2))

  def test_process_banner(drc):
    """test process_banner()"""
    group_name = "iida"
    banner_message = "Created by Ansible"
    result = drc.process_banner(state='present', banner_message=banner_message, group_name=group_name, retain_banner=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


  # 実行
  sys.exit(main())
