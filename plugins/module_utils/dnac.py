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

  from dnac_sandbox import sandbox_params

  def main():
    """main function for test"""

    logging.basicConfig(level=logging.INFO)

    params = sandbox_params.get('always-on-lab')

    dnac = Dnac(params)

    device_list = dnac.get_device_list()
    for device in device_list:
      print(json.dumps(device, ensure_ascii=False, indent=2))

    host_list = dnac.get_host_list()
    for host in host_list:
      print(json.dumps(host, ensure_ascii=False, indent=2))

    group_names = dnac.get_group_names()
    for name in group_names:
      print(name)

    return 0

  # 実行
  sys.exit(main())
