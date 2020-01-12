#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

try:
  from dnac_devices import DnacDevices
  from dnac_host import DnacHost
  from dnac_group import DnacGroup
except ImportError:
  from ansible_collections.iida.dnac.plugins.module_utils.dnac_devices import DnacDevices
  from ansible_collections.iida.dnac.plugins.module_utils.dnac_host import DnacHost
  from ansible_collections.iida.dnac.plugins.module_utils.dnac_group import DnacGroup


class Dnac(DnacDevices, DnacHost, DnacGroup):
  """Manage Dna Center
  """


if __name__ == '__main__':

  import logging
  import sys

  from dnac_sandbox import sandbox_params

  def main():
    """main function for test"""

    logging.basicConfig(level=logging.INFO)

    params = sandbox_params.get('always-on-lab')

    dnac = Dnac(params)

    dnac.ping()

    return 0


  sys.exit(main())
