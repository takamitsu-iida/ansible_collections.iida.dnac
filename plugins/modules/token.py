#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

# (c) 2019, Takamitsu IIDA (@takamitsu-iida)

ANSIBLE_METADATA = {'metadata_version': '0.1', 'status': ['preview'], 'supported_by': 'community'}

DOCUMENTATION = '''
---
module: iida.dnac.token

version_added: 2.9

short_description: Get authentication token from Cisco DNA Center

description:
  - Get REST API authentication token from DNA Center

author:
  - Takamitsu IIDA (@takamitsu-iida)

notes:
  - Tested against devnet sandbox
'''

EXAMPLES = '''
- name: access to cisco dna center rest api
  hosts: sandboxdnac2
  gather_facts: False

  tasks:
    - name: get auth token
      iida.dnac.token:
      register: r

    - debug:
        var: r
'''

RETURN = '''
response:
  description: authentication token string
  returned: when token the returned from dna center
  type: str
  sample: |
    {
      "changed": false,
      "failed": false,
      "token": "eyJ0eXAiOiJKV1QiLCJhb...snipped..."
    }
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
    debug=dict(default=False, type='bool')
  )

  # generate module instance
  module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

  # generate DnacRestClient instance
  drc = DnacRestClient(module.params)

  result = {
    'changed': False
  }

  if module.check_mode:
    module.warn('Get token operation is not restricted by check_mode')

  # get token
  token = drc.get_token()

  # set token to result
  if token:
    result['token'] = token
    module.exit_json(**result)

  result['failed'] = True
  module.fail_json(**result)


if __name__ == '__main__':
  main()
