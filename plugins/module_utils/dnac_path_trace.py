#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

import datetime

import tabulate

try:
  from dnac_rest_client import DnacRestClient
except ImportError:
  from ansible_collections.iida.dnac.plugins.module_utils.dnac_rest_client import DnacRestClient


class DnacPathTrace(DnacRestClient):
  """Manage Path Trace
  """

  def get_path_trace(self):
    """Retrives all previous Pathtraces summary

    version 1.2
    /dna/intent/api/v1/flow-analysis

    Returns:
        list -- List of path trace object
    """
    api_path = '/dna/intent/api/v1/flow-analysis'
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_path_trace_by_id(self, path_id):
    """Get path trace by id

    version 1.2
    /dna/intent/api/v1/flow-analysis/{path_id}

    Arguments:
        path_id {[type]} -- [description]

    Returns:
        dict -- Object of the path trace
    """
    api_path = '/dna/intent/api/v1/flow-analysis/{}'.format(path_id)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def show_path_trace(self, path_trace=None):
    if path_trace is None:
      print("no path_trace found.")
      return

    # print(json.dumps(path_trace, indent=2))
    # networkElementsInfo is the list of trace
    # see data-structure-memo.txt

    headers = ['name', 'ip', 'type', 'ingress', 'egress']
    table = []
    for element in path_trace['networkElementsInfo']:
      element_name = element.get('name')
      element_ip = element.get('ip')
      element_type = element.get('type')
      ingress_name = element.get('ingressInterface', {}).get('physicalInterface', {}).get('name') or '-'
      egress_name = element.get('egressInterface', {}).get('physicalInterface', {}).get('name') or '-'
      table.append([element_name, element_ip, element_type, ingress_name, egress_name])

    print(tabulate.tabulate(table, headers, tablefmt='simple'))


  def show_path_trace_list(self, path_trace_list):
    """Print path trace list

    Arguments:
        path_trace_list {list} -- List of path trace object
    """
    if not path_trace_list:
      print("no path_trace found.")
      return

    # sort by createTime
    path_trace_list = sorted(path_trace_list, key=lambda path: path.get('createTime'))

    headers = ['sourceIP', 'destIP', 'status', 'createTime', 'id', 'inclusions']
    table = []
    for path in path_trace_list:
      source_ip = path.get('sourceIP') or '-'
      dest_ip = path.get('destIP') or '-'
      status = path.get('status')

      create_time = path.get('createTime')  # this is int
      create_time /= 1000  # from msec to sec
      create_time = datetime.datetime.fromtimestamp(create_time)
      create_time = create_time.strftime('%Y-%m-%d %H:%M:%S')

      inclusions = path.get('inclusions') or []
      inclusions = ', '.join(inclusions)

      path_id = path.get('id')

      table.append([source_ip, dest_ip, status, create_time, path_id, inclusions])

    print(tabulate.tabulate(table, headers, tablefmt='simple'))


if __name__ == '__main__':

  import logging
  import sys

  from dnac_sandbox import sandbox_params

  def main():
    """main function for test"""

    logging.basicConfig(level=logging.INFO)

    params = sandbox_params.get('hardware-lab')
    params = sandbox_params.get('always-on-lab')

    # DnacRestClient object
    drc = DnacPathTrace(params)

    # get path_trace list
    path_trace_list = drc.get_path_trace()
    drc.show_path_trace_list(path_trace_list)

    # for example
    # select first path_trace object
    path_trace_id = path_trace_list[0].get('id')
    path_trace_id = '7916708d-be09-40d9-b73f-0b71eb9575b0'
    path_trace = drc.get_path_trace_by_id(path_trace_id)
    drc.show_path_trace(path_trace)



    return 0


  sys.exit(main())
