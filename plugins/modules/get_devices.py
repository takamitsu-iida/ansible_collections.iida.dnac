#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

# (c) 2019, Takamitsu IIDA (@takamitsu-iida)

ANSIBLE_METADATA = {'metadata_version': '0.1', 'status': ['preview'], 'supported_by': 'community'}

DOCUMENTATION = '''
---
module: iida.dnac.get_devices

version_added: 2.9

short_description: Get device information from Cisco DNA Center

description:
  - Get device information from DNA Center

author:
  - Takamitsu IIDA (@takamitsu-iida)

notes:
  - Tested against devnet sandbox
'''

EXAMPLES = '''
'''

RETURN = '''
'''

from ansible.module_utils.basic import AnsibleModule

# import from collection
from ansible_collections.iida.dnac.plugins.module_utils.dnac_devices import DnacDevices as DnacRestClient


def main():
  """main entry point for module execution"""

  argument_spec = dict(DnacRestClient.argument_spec)
  argument_spec.update(
    dict(
      ip=dict(type='str'),
      id=dict(type='str'),
      serial=dict(type='str')
    ))

  # generate module instance
  module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

  # generate DnacRestClient instance
  drc = DnacRestClient(module.params)

  # execute module
  result = drc.execute_module_get_devices(module.check_mode)

  module.exit_json(**result)


if __name__ == '__main__':
  main()
