#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

class DnacGroup:
  """Manage Groups
  """

  # lookup group_id by group_name
  def get_group_id_by_name(self, drc, group_name):
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
    get_result = drc.get(api_path)
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


  def get_site_names(self, drc):
    """get all site name as dict

    VERSION 1.3
    '/dna/intent/api/v1/site'

    Returns:
        dict -- list of all group name
    """
    _cache = {}

    api_path = '/dna/intent/api/v1/site/count'
    get_result = drc.get(api_path)
    if not get_result or get_result.get('failed'):
      return {}

    data = get_result.get('data')
    count = data.get('response')

    STEP = 10
    for start in range(1, count + 1, STEP):
      api_path = '/dna/intent/api/v1/site?offset={}&limit={}'.format(start, STEP)
      get_result = drc.get(api_path=api_path)
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


  def get_group_names(self, drc):
    """get all group name

    VERSION 1.2
    '/api/v1/group'

    Returns:
        list -- list of all group name
    """

    api_path = '/api/v1/group'
    get_result = drc.get(api_path)
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


  def process_group(self, drc, state='present', group_name='', group_type='area', parent_name='Global', building_info=None):
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

    group_name_list = drc.get_group_names()
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
      group_id = drc.get_group_id_by_name(group_name)
      api_path = api_path + '/' + str(group_id)
      delete_result = self.delete_object(api_path=api_path)
      result.update(delete_result)
    elif state == 'absent' and not has_group_name:
      result['failed'] = False
      result['msg'] = "group_name {} is already absent".format(group_name)

    return result


if __name__ == '__main__':

  import json
  import logging
  import sys

  from dnac_rest_client import DnacRestClient

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
    d = DnacGroup()

    name_list = d.get_group_names(drc)
    for name in name_list:
      print(name)

    print(d.get_group_id_by_name(drc, name_list[0]))

    return 0


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


  # 実行
  sys.exit(main())
