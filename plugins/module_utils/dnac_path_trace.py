#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

import logging
import datetime

import tabulate  # https://pypi.org/project/tabulate/

try:
  from dnac_rest_client import DnacRestClient
except ImportError:
  from ansible_collections.iida.dnac.plugins.module_utils.dnac_rest_client import DnacRestClient

logger = logging.getLogger(__name__)

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
    """Print path_trace

    Keyword Arguments:
        path_trace {dict} -- Object of the path_trace (default: {None})
    """
    if path_trace is None:
      logger.error("no path_trace found to show path trace")
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
      logger.error("no path_trace found to show the list of path trace")
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


  def create_path_trace(self, src_ip=None, dst_ip=None, src_port=None, dst_port=None):
    """Initiate a new Pathtrace

    version 1.2
    /dna/intent/api/v1/flow-analysis

    Keyword Arguments:
        src_ip {str} -- [description] (default: {None})
        dst_ip {str} -- [description] (default: {None})
        src_port {str} -- [description] (default: {None})
        dst_port {str} -- [description] (default: {None})

    Returns:
        [type] -- [description]
    """
    if not all((src_ip, dst_ip)):
      logger.error('src_ip and dst_ip are required to create path trace')
      return

    payload = {
      'sourceIP': src_ip,
      'destIP': dst_ip,
      'periodicRefresh': False,
      'inclusions': ['INTERFACE-STATS', 'DEVICE-STATS']
    }

    if src_port is not None:
      payload['sourcePort'] = src_port

    if dst_port is not None:
      payload['destPort'] = dst_port

    api_path = '/dna/intent/api/v1/flow-analysis'

    post_result = self.post(api_path=api_path, data=payload)
    if post_result.get('failed'):
      status_code = post_result.get('status_code')
      if status_code == 403:
        logging.error('The server recognizes the authentication credentials, but the client is not authorized to perform this request.')
      elif status_code == 404:
        logging.error('The client made a request for a resource that does not exist.')
      elif status_code == 409:
        logging.error('The target resource is in a conflicted state. Retrying the request later might succeed.')
      elif status_code == 415:
        logging.error('The client sent a request body in a format that the server does not support')
      return

    data = self.extract_data_response(post_result)
    task_id = data.get('taskId')
    wait_result = self.wait_for_task(task_id)
    if wait_result.get('failed'):
      logger.error('wait failed')
      return

    logger.info(wait_result.get('progress'))


if __name__ == '__main__':

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

    # create a new path trace
    src_ip = '10.10.20.81'
    dst_ip = '10.10.20.82'
    drc.create_path_trace(src_ip=src_ip, dst_ip=dst_ip)

    return 0


  sys.exit(main())
