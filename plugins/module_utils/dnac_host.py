#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

import logging

import tabulate  # https://pypi.org/project/tabulate/

try:
  from dnac_rest_client import DnacRestClient
except ImportError:
  from ansible_collections.iida.dnac.plugins.module_utils.dnac_rest_client import DnacRestClient

logger = logging.getLogger(__name__)


class DnacHost(DnacRestClient):
  """Manage Network Hosts
  """

  def get_host_list(self):
    """get host object list

    version 1.2
    /api/v1/host

    Returns:
        list -- List of host object
    """
    api_path = '/api/v1/host'
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def show_host_list(self, host_list=None):
    """Print host list

    Keyword Arguments:
        host_list {list} -- List of host object (default: {None})
    """
    if not host_list:
      print("no host is found.")
      return

    headers = ['host ip', 'host mac', 'host type', 'conn device name', 'conn device addr', 'conn intf name', 'vlan']
    table = []
    for host in host_list:
      host_ip = host.get('hostIp') or '-'
      host_mac = host.get('hostMac') or '-'
      host_type = host.get('hostType') or '-'
      connected_device_name = host.get('connectedNetworkDeviceName') or '-'
      connected_device_addr = host.get('connectedNetworkDeviceIpAddress') or '-'
      connected_intf_name = host.get('connectedInterfaceName') or '-'
      vlan_id = host.get('vlanId')
      table.append([host_ip, host_mac, host_type, connected_device_name, connected_device_addr, connected_intf_name, vlan_id])

    print(tabulate.tabulate(table, headers, tablefmt='simple'))


  def get_host_by_id(self, host_id=None):
    """Get host object by id

    Keyword Arguments:
        host_id {str} -- The identifier of the host (default: {None})

    Returns:
        dict -- Object of the host
    """
    if host_id is None:
      return None
    api_path = '/api/v1/host/{}'.format(host_id)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def show_host(self, host=None):
    """Print single host object

    Arguments:
        host {dict} -- Object of the host
    """
    if host is None:
      print("no host found.")
      return

    def get_row(key):
      return [key, host.get(key) or '-']

    want_key = ['hostIp', 'hostMac', 'hostType', 'connectedNetworkDeviceName', 'connectedNetworkDeviceIpAddress', 'vlanId']
    headers = ['key', 'value']
    table = []
    for key in want_key:
      table.append(get_row(key))

    print(tabulate.tabulate(table, headers, tablefmt='simple'))


  def get_host_by_ip(self, ip=None):
    """get host object by ip address"""
    if ip is None:
      return None
    api_path = '/api/v1/host?hostIp={}'.format(ip)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_host_by_mac(self, mac=None):
    """get host object by mac address"""
    if mac is None:
      return None
    api_path = '/api/v1/host?hostMac={}'.format(mac)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


if __name__ == '__main__':

  import sys

  from dnac_sandbox import sandbox_params

  def main():
    """main function for test"""

    logging.basicConfig(level=logging.INFO)

    params = sandbox_params.get('hardware-lab')
    params = sandbox_params.get('always-on-lab')

    # DnacRestClient object
    drc = DnacHost(params)

    # get host list
    host_list = drc.get_host_list()
    drc.show_host_list(host_list=host_list)

    # for example
    # select first host
    host_id = host_list[0].get('id')

    # get host by id
    host = drc.get_host_by_id(host_id)
    drc.show_host(host)

    return 0


  sys.exit(main())
