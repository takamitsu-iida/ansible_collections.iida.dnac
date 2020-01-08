#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

class DnacHost:
  """Manage Network Hosts
  """

  def get_host_list(self, drc):
    """get host object list"""
    api_path = '/api/v1/host'
    get_result = drc.get(api_path=api_path)
    return drc.extract_data_response(get_result)


  def get_host_by_ip(self, drc, ip=None):
    """get host object by ip address"""
    if ip is None:
      return None
    api_path = '/api/v1/host?hostIp={}'.format(ip)
    get_result = drc.get(api_path=api_path)
    return drc.extract_data_response(get_result)


  def get_host_by_mac(self, drc, mac=None):
    """get host object by mac address"""
    if mac is None:
      return None
    api_path = '/api/v1/host?hostMac={}'.format(mac)
    get_result = drc.get(api_path=api_path)
    return drc.extract_data_response(get_result)


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

    dnac = DnacRestClient(params)
    d = DnacHost()

    host_list = d.get_host_list(dnac)
    for host in host_list:
      print(json.dumps(host, ensure_ascii=False, indent=2))

    return 0

  # 実行
  sys.exit(main())
