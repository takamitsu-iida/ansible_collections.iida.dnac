#!/usr/bin/python
# pylint: disable=C0111
# -*- coding: utf-8 -*-

# (c) 2019, Takamitsu IIDA (@takamitsu-iida)

ANSIBLE_METADATA = {'metadata_version': '0.1', 'status': ['preview'], 'supported_by': 'community'}

DOCUMENTATION = '''
---
module: iida.dnac.token

version_added: 2.9

short_description: Get REST API authentication token from DNA Center

description:
  - Get REST API authentication token from DNA Center

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
from ansible_collections.iida.dnac.plugins.module_utils.dnac_rest_client import DnacRestClient


def main():
  """main entry point for module execution"""

  argument_spec = dict(
    host=dict(type='str', required=True),
    port=dict(default=443, type='int'),
    username=dict(default='', type='str'),
    password=dict(default='', type='str'),
    timeout=dict(default=DnacRestClient.DEFAULT_TIMEOUT, type='int'),
    http_proxy=dict(default='', type='str'),
    log=dict(default=False, type='bool'),
    log_dir=dict(default='', type='str'),
    debug=dict(default=False, type='bool')
  )

  # generate module instance
  module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

  drc = DnacRestClient(module.params)

  result = {
    'changed': False,
    'failed': False
  }

  token = drc.get_token()
  if token:
    result['token'] = token
  else:
    result['token'] = ''
    result['failed'] = True

  if result.get('failed'):
    module.fail_json(**result)

  module.exit_json(**result)


if __name__ == '__main__':
  main()
