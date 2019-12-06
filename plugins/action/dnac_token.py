# -*- coding: utf-8 -*-
# pylint: disable=W0212,C0111,E0611

# (c) Takamitsu IIDA (@takamitsu-iida)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


import os
import time

from ansible.plugins.action.normal import ActionModule as _ActionModule

# import from collection
from ansible_collections.iida.dnac.plugins.module_utils.dnac import DnacRestClient

try:
  # pylint: disable=W0611
  # W0611:Unused display imported from __main__
  from __main__ import display
except ImportError:
  # pylint: disable=C0412
  # C0412:Imports from package ansible are not grouped
  from ansible.utils.display import Display
  display = Display()


class ActionModule(_ActionModule):

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


  def run(self, tmp=None, task_vars=None):
    del tmp  # tmp no longer has any effect

    #
    # pre process
    #

    #
    # hostvarsを取り出す
    #
    inventory_hostname = task_vars.get('inventory_hostname')
    hostvars = task_vars['hostvars'].get(inventory_hostname)

    #
    # インベントリ（hostvars）から情報を取り出す
    #
    remote_addr = hostvars.get('remote_addr') or hostvars.get('ansible_ssh_host') or hostvars.get('ansible_host')
    port = hostvars.get('port') or hostvars.get('ansible_ssh_port') or hostvars.get('ansible_port', 443)
    remote_user = hostvars.get('remote_user') or hostvars.get('ansible_ssh_user') or hostvars.get('ansible_user')
    password = hostvars.get('password') or hostvars.get('ansible_ssh_pass') or hostvars.get('ansible_password') or hostvars.get('ansible_pass') # ansible_pass is wrong setting
    timeout = hostvars.get('timeout')
    http_proxy = hostvars.get('http_proxy')
    log_dir = hostvars.get('log_dir') or self.get_working_path()

    # debug
    # display.vvv(remote_addr)
    # display.vvv(remote_user)
    # display.vvv(password)

    #
    # self._task.argsに不足があれば追加する
    # タスクでパラメータを指定していないなら、インベントリの情報で補完する
    #
    if not self._task.args.get('host') and remote_addr:
      self._task.args['host'] = remote_addr

    if not self._task.args.get('port') and port:
      self._task.args['port'] = port

    if not self._task.args.get('username') and remote_user:
      self._task.args['username'] = remote_user

    if not self._task.args.get('password') and password:
      self._task.args['password'] = password

    if not self._task.args.get('timeout') and timeout:
      self._task.args['timeout'] = timeout

    if not self._task.args.get('http_proxy') and http_proxy:
      self._task.args['http_proxy'] = http_proxy

    # log_dir はデフォルトとしてカレントディレクトリを使う
    if not self._task.args.get('log_dir'):
      self._task.args['log_dir'] = log_dir

    #
    # run module
    #

    # do not run the module
    # result = super(ActionModule, self).run(task_vars=task_vars)

    #
    # post process
    #

    result = {
      'changed': False,
      'failed': False
    }

    drc = DnacRestClient(self._task.args)

    token = drc.getToken()

    if token:
      result['token'] = token
    else:
      result['token'] = ''
      result['failed'] = True

    if self._task.args.get('log') and result.get('__log__'):
      log_path = self.write_log(inventory_hostname, result['__log__'])
      result['log_path'] = log_path
      del result['__log__']

    return result
