#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

from dnac_devices import DnacDevices
from dnac_host import DnacHost
from dnac_group import DnacGroup

class Dnac(DnacDevices, DnacHost, DnacGroup):
  """Manage Dna Center
  """



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
    dnac = Dnac()

    host_list = dnac.get_host_list(drc)
    for host in host_list:
      print(json.dumps(host, ensure_ascii=False, indent=2))

    return 0

  # 実行
  sys.exit(main())
