#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=C0111,E0611

# (c) 2019, Takamitsu IIDA (@takamitsu-iida)

ANSIBLE_METADATA = {'metadata_version': '1.1', 'status': ['preview'], 'supported_by': 'community'}

DOCUMENTATION = '''
---
module: restc

short_description: REST API client

version_added: 2.8

description:
  - REST API client

author:
  - Takamitsu IIDA (@takamitsu-iida)

notes:
  - Tested against CSR1000v 16.03.06
'''

EXAMPLES = '''
'''

RETURN = '''
'''

from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.network.common.utils import remove_default_spec


def main():
  """main entry point for module execution
  """

  element_spec = dict(
    name=dict(),
    state=dict(choices=['present', 'absent']),
    description=dict(type='str'),
    negotiation=dict(type='str'),
    speed=dict(type='str'),
    duplex=dict(choices=['full', 'half', 'auto']),
    mtu=dict(type='int'),
    shutdown=dict(type='bool')
  )

  # list of interfaces
  aggregate_spec = deepcopy(element_spec)
  aggregate_spec['name'] = dict(required=True)

  # remove default in aggregate spec, to handle common arguments
  remove_default_spec(aggregate_spec)

  argument_spec = dict(
    aggregate=dict(type='list', elements='dict', options=aggregate_spec),
    interfaces=dict(type='list'),
    running_config=dict(type='str'),
    running_config_path=dict(type='path'),
    debug=dict(type='bool')
  )

  argument_spec.update(element_spec)

  required_one_of = [
    ('interfaces', 'name', 'aggregate'),
    ('running_config', 'running_config_path')
  ]

  mutually_exclusive = [
    ('name', 'aggregate'),
    ('running_config', 'running_config_path')
  ]

  module = AnsibleModule(
    argument_spec=argument_spec,
    required_one_of=required_one_of,
    mutually_exclusive=mutually_exclusive,
    supports_check_mode=True)

  result = {'changed': False}

  module.exit_json(**result)


if __name__ == '__main__':
  main()
