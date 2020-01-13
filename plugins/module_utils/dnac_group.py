#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

import logging

# import tabulate  # https://pypi.org/project/tabulate/

try:
  from dnac_rest_client import DnacRestClient
except ImportError:
  from ansible_collections.iida.dnac.plugins.module_utils.dnac_rest_client import DnacRestClient

logger = logging.getLogger(__name__)


class DnacGroup(DnacRestClient):
  """Manage Groups
  """

  def get_group_list(self):
    """get all group

    VERSION 1.2
    '/api/v1/group'

    Returns:
        list -- list of all groups
    """
    api_path = '/api/v1/group'
    get_result = self.get(api_path)
    #   "data": {
    #     "response": [
    #       {
    #         "parentId": "ba06348e-ee80-4058-bb23-f0c9a5fd728b",
    return self.extract_data_response(get_result)


  def get_group_names(self):
    """get all group name

    VERSION 1.2
    '/api/v1/group'

    Returns:
        list -- list of all group name
    """
    group_list = self.get_group_list()
    if not group_list:
      return []
    group_names = [group.get('name') for group in group_list]
    return group_names


  def get_group_by_name(self, group_name):
    """グループの情報を全部取ってから、フィルタリングした結果を返す。

    version1.2

    Arguments:
        group_name {[type]} -- [description]

    Returns:
        [type] -- [description]
    """
    group_list = self.get_group_list()
    if not group_list:
      return None
    matched = [group for group in group_list if group.get('name') == group_name]
    if len(matched) > 0:
      return matched[0]
    return None


  # lookup group_id by group_name
  def get_group_id_by_name(self, group_name):
    """lookup group id

    VERSION 1.2
    '/api/v1/group'

    Arguments:
        group_name {str} -- group name

    Returns:
        str -- group id
    """
    if not group_name:
      return '-1'

    api_path = '/api/v1/group'
    get_result = self.get(api_path)
    #   "data": {
    #     "response": [
    #       {
    #         "parentId": "ba06348e-ee80-4058-bb23-f0c9a5fd728b",
    response = self.extract_data_response(get_result)
    if not response:
      return '0'

    group_ids = [group.get('id') for group in response if group.get('name') == group_name]
    if len(group_ids) == 1:
      return group_ids[0]

    return '0'


  def get_site_names_13(self):
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

    count = self.extract_data_response(get_result)

    STEP = 10
    for start in range(1, count + 1, STEP):
      api_path = '/dna/intent/api/v1/site?offset={}&limit={}'.format(start, STEP)
      get_result = self.get(api_path=api_path)
      if not get_result or get_result.get('failed'):
        return {}
      sites = self.extract_data_response(get_result)
      for site in sites:
        logging.info("Caching %s", site['groupNameHierarchy'])
        _cache[site['groupNameHierarchy']] = site

    # add Global
    _cache['Global'] = {'groupNameHierarchy': 'Global', 'additionalInfo': [{'attributes': {'type': 'area'}}]}

    return _cache


  def process_group(self, state='present', group_name='', group_type='area', parent_name='Global', building_info=None):
    """create/delete group object

    VERSION 1.2
    '/api/v1/group'

    To change group, delete group first and then create group again.

    floor is not supported yet.

    Keyword Arguments:
        state {str} -- 'present' or 'absent' (default: {'present'})
        group_name {str} -- name of the group (default: {''})
        group_type {str} -- 'area' or 'building' or 'floor' (default: {'area'})
        parent_name {str} -- parent name (default: {'Global'})
        building_info {dict} -- buiding info (default: {None})
    """
    result = {
      'failed': True,
      'changed': False
    }

    api_path = '/api/v1/group'

    # check if group_name already exists in dna center
    group_name_list = self.get_group_names()
    has_group_name = group_name in group_name_list

    if state == 'present' and has_group_name:
      result['failed'] = False
      result['msg'] = "group_name {} already exists".format(group_name)

    elif state == 'present' and not has_group_name:
      # newly create group
      payload = {
        'groupTypeList': ["SITE"],
        'name': group_name,
        'additionalInfo': [{
          'nameSpace': "Location",
          'attributes': {
            'type': group_type
          }
        }]
      }

      # check if parent exists and update 'parentId'
      has_parent_name = parent_name in group_name_list
      if not has_parent_name:
        result['msg'] = "there is no parent_name in group_name_list"
        return result
      parent_id = self.get_group_id_by_name(parent_name)
      payload.update({'parentId' : parent_id})

      # check if required parameter is provided
      if group_type == "building":
        if building_info is None:
          result['msg'] = "building_info is required to create group of building"
          return result
        payload['additionalInfo'][0]['attributes'].update(building_info)

      elif group_type == "floor":
        payload['additionalInfo'].append({
          'nameSpace': "mapsSummary",
          'attributes': {
            'rfModel': "37037",
            'floorIndex': "1"
          }
        })
        payload['additionalInfo'].append({
          'nameSpace': "mapGeometry",
          'attributes': {
            'width': "100",
            'length': "100",
            'height': "10"
          }
        })
      create_result = self.create_object(api_path=api_path, data=payload)
      result.update(create_result)

    elif state == 'absent' and has_group_name:
      # delete it
      group_id = self.get_group_id_by_name(group_name)
      api_path = api_path + '/{}'.format(group_id)
      delete_result = self.delete_object(api_path=api_path)
      result.update(delete_result)

    elif state == 'absent' and not has_group_name:
      # already deleted
      result['failed'] = False
      result['msg'] = "group_name {} is already absent".format(group_name)

    return result


if __name__ == '__main__':

  import json
  import sys

  from dnac_sandbox import sandbox_params

  def main():
    """main function for test"""

    logging.basicConfig(level=logging.INFO)

    params = sandbox_params.get('always-on-lab')
    params = sandbox_params.get('hardware-lab')

    # DnacRestClient class object
    drc = DnacGroup(params)

    # test_dump_group(drc)
    # test_group_names(drc)
    # test_group_id(drc)
    test_process_group_present(drc)
    # test_process_group_absent(drc)

    return 0


  def test_dump_group(drc):
    """test dump group"""
    api_path = '/api/v1/group'
    get_result = drc.get(api_path)
    print(json.dumps(get_result, ensure_ascii=False, indent=2))


  def test_group_names(drc):
    """test group names"""
    group_names = drc.get_group_names()
    print(json.dumps(group_names, ensure_ascii=False, indent=2))


  def test_group_id(drc):
    """test group_id"""
    group_name = 'Global'
    result = drc.get_group_id_by_name(group_name)
    print(result)


  def test_process_group_present(drc):
    """test process_group(state='present')"""

    # create area
    process_result = drc.process_group(state='present', group_name='iida', group_type='area', parent_name='Global')
    print(json.dumps(process_result, ensure_ascii=False, indent=2))

    # create building
    building_info = {
      'type': "building",
      'address': "神奈川県川崎市中原区小杉町1-403",
      'country': "日本",
      'latitude': "35.577510",
      'longitude': "139.658149"
    }
    process_result = drc.process_group(state='present', group_name='ksg-tp', group_type='building', parent_name='iida', building_info=building_info)
    print(json.dumps(process_result, ensure_ascii=False, indent=2))

    # create floor
    process_result = drc.process_group(state='present', group_name='ksg-tp-18f', group_type='floor', parent_name='ksg-tp')
    print(json.dumps(process_result, ensure_ascii=False, indent=2))



  def test_process_group_absent(drc):
    """test process_group(state='absent')"""

    # delete floor
    process_result = drc.process_group(state='absent', group_name='ksg-tp-18f')
    print(json.dumps(process_result, ensure_ascii=False, indent=2))

    # delete building
    process_result = drc.process_group(state='absent', group_name='ksg-tp')
    print(json.dumps(process_result, ensure_ascii=False, indent=2))

    # delete area
    process_result = drc.process_group(state='absent', group_name='iida')
    print(json.dumps(process_result, ensure_ascii=False, indent=2))


  sys.exit(main())
