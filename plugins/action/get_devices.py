# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

# (c) Takamitsu IIDA (@takamitsu-iida)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os

# import from collection
from ansible_collections.iida.dnac.plugins.action.dna import DnaActionModule
from ansible_collections.iida.dnac.plugins.module_utils.dnac_devices import DnacDevices as DnacRestClient

try:
  # pylint: disable=unused-import
  from __main__ import display
except ImportError:
  # pylint: disable=ungrouped-imports
  from ansible.utils.display import Display
  display = Display()


class ActionModule(DnaActionModule):

  def run(self, tmp=None, task_vars=None):
    del tmp  # tmp no longer has any effect

    # if delegate_to is specified, we must run in module
    run_as_module = bool(hasattr(self._play_context, 'delegate_to'))

    #
    # pre process
    #

    # get hostvars
    inventory_hostname = task_vars.get('inventory_hostname')
    hostvars = task_vars['hostvars'].get(inventory_hostname)

    # complement self._task.args by hostvars
    self.complement_task_args_by_hostvars(hostvars)

    # set log_dir
    if not self._task.args.get('log_dir'):
      cwd = self.get_working_path()
      self._task.args['log_dir'] = os.path.join(cwd, 'log')

    #
    # RUN THE MODULE
    #
    if run_as_module:
      result = super(ActionModule, self).run(task_vars=task_vars)
    else:
      drc = DnacRestClient(self._task.args)
      result = drc.execute_module_get_devices(self._play_context.check_mode)

    #
    # post process
    #

    if self._task.args.get('log') and '__log__' in result:
      log_path = self.write_log(inventory_hostname, result.get('__log__'))
      result['log_path'] = log_path
      del result['__log__']

    return result
