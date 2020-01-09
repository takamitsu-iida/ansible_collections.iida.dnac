#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

from dnac_rest_client import DnacRestClient

class DnacHost(DnacRestClient):
  """Manage Network Hosts
  """

  def get_host_list(self):
    """get host object list"""
    api_path = '/api/v1/host'
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_host_by_ip(self, ip=None):
    """get host object by ip address"""
    if ip is None:
      return None
    api_path = '/api/v1/host?hostIp={}'.format(ip)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_host_by_mac(self, mac=None):
    """get host object by mac address"""
    if mac is None:
      return None
    api_path = '/api/v1/host?hostMac={}'.format(mac)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


if __name__ == '__main__':

  import json
  import logging
  import sys

  from dnac_sandbox import sandbox_params

  def main():
    """main function for test"""

    logging.basicConfig(level=logging.INFO)

    params = sandbox_params.get('always-on-lab')
    # params = sandbox_params.get('hardware-lab-2')

    # DnacRestClient object
    drc = DnacHost(params)

    host_list = drc.get_host_list()
    for host in host_list:
      print(json.dumps(host, ensure_ascii=False, indent=2))

    return 0

  # 実行
  sys.exit(main())
