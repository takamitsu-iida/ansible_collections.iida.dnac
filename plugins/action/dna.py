# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring

# (c) Takamitsu IIDA (@takamitsu-iida)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


import os
import time

from ansible.plugins.action.normal import ActionModule

try:
  # pylint: disable=unused-import
  from __main__ import display
except ImportError:
  # pylint: disable=ungrouped-imports
  from ansible.utils.display import Display
  display = Display()


class DnaActionModule(ActionModule):

  def get_working_path(self):
    cwd = self._loader.get_basedir()
    # if self._task._role is not None:
    #   cwd = self._task._role._role_path
    return cwd


  def write_log(self, hostname, contents):
    log_path = self.get_working_path() + '/log'
    if not os.path.exists(log_path):
      os.mkdir(log_path)
    # tstamp = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime(time.time()))
    tstamp = time.strftime("%Y-%m-%d@%H-%M-%S", time.localtime(time.time()))
    filename = '{0}/{1}_{2}.log'.format(log_path, hostname, tstamp)
    open(filename, 'w').write(contents)

    return filename


  def complement_task_args_by_hostvars(self, hostvars):
    """complement self._task.args by inventory hostvars

    Arguments:
        hostvars {dict} -- hostvars
    """
    #
    # if task in playbook does not specify parameters, complement it using inventoriy hostvars
    #
    if not self._task.args.get('host'):
      self._task.args['host'] = hostvars.get('remote_addr') or hostvars.get('ansible_ssh_host') or hostvars.get('ansible_host')

    if not self._task.args.get('port'):
      self._task.args['port'] = hostvars.get('port') or hostvars.get('ansible_ssh_port') or hostvars.get('ansible_port', 443)

    if not self._task.args.get('username'):
      self._task.args['username'] = hostvars.get('remote_user') or hostvars.get('ansible_ssh_user') or hostvars.get('ansible_user')

    if not self._task.args.get('password'):
      self._task.args['password'] = hostvars.get('password') or hostvars.get('ansible_ssh_pass') or hostvars.get('ansible_password')

    if not self._task.args.get('timeout'):
      self._task.args['timeout'] = hostvars.get('timeout', 30)

    if not self._task.args.get('http_proxy'):
      self._task.args['http_proxy'] = hostvars.get('http_proxy')

    if not self._task.args.get('log_dir'):
      self._task.args['log_dir'] = hostvars.get('log_dir')
