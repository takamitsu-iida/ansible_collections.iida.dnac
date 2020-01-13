#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

import logging

try:
  # https://pypi.org/project/tabulate/
  HAS_TABULATE = True
  import tabulate
except ImportError:
  HAS_TABULATE = False

try:
  from dnac_rest_client import DnacRestClient
except ImportError:
  from ansible_collections.iida.dnac.plugins.module_utils.dnac_rest_client import DnacRestClient

logger = logging.getLogger(__name__)


class DnacDevices(DnacRestClient):
  """Manage Network Devices"""

  def get_device_list(self):
    """Get device list

    version 1.2
    /dna/intent/api/v1/network-device

    Returns:
        [type] -- [description]
    """
    api_path = '/dna/intent/api/v1/network-device'
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def show_device_list(self, device_list=None):
    """Print devices"""
    if device_list is None:
      device_list = self.get_device_list()
      if not device_list:
        print("no device found.")
        return
    if not HAS_TABULATE:
      print("tabulate module not found.")
      return

    headers = ['hostname', 'mgmt ip', 'serial', 'platform', 'version', 'role', 'uptime']
    table = []

    for device in device_list:
      hostname = device.get('hostname') or '-'
      mgmt = device.get('managementIpAddress') or '-'
      serial_number = device.get('serialNumber') or '-'
      platform_id = device.get('platformId') or '-'
      version = device.get('softwareVersion') or '-'
      role = device.get('role') or '-'
      uptime = device.get('upTime') or '-'

      # in case of switch stacks
      if ',' in serial_number:
        serial_number_parts = serial_number.split(',')
        platform_id_parts = platform_id.split(',')
        serial_platform_list = list(zip(serial_number_parts, platform_id_parts))
      else:
        serial_platform_list = [(serial_number, platform_id)]

      for (serial_number, platform_id) in serial_platform_list:
        table.append([hostname, mgmt, serial_number, platform_id, version, role, uptime])

    print(tabulate.tabulate(table, headers, tablefmt='simple'))


  def get_device_by_id(self, device_id=None):
    """Get device by device_id

    version 1.2
    /dna/intent/api/v1/network-device/{device_id}


    Keyword Arguments:
        device_id {str} -- The identifier of the device (default: {None})

    Returns:
        dict -- Object of the device
    """
    if device_id is None:
      return None
    api_path = '/dna/intent/api/v1/network-device/{}'.format(device_id)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_device_by_ip(self, ip=None):
    """Get device object by ip address

    version 1.2
    /dna/intent/api/v1/network-device?managementIpAddress={ip}

    Keyword Arguments:
        ip {[type]} -- [description] (default: {None})

    Returns:
        dict -- Object of the device
    """
    if ip is None:
      return None
    api_path = '/dna/intent/api/v1/network-device?managementIpAddress={}'.format(ip)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_device_id_by_ip(self, ip=None):
    """Get device_id by ip address

    version 1.2
    /dna/intent/api/v1/network-device?managementIpAddress={ip}

    Keyword Arguments:
        ip {str} -- IP address of the device (default: {None})

    Returns:
        str -- The identifier of the device
    """
    device = self.get_device_by_ip(ip=ip)
    if not device:
      return None
    return device.get('id')


  def get_device_by_serial(self, serial_number=None):
    """Get device object by serial number

    version 1.2
    /dna/intent/api/v1/network-device?serialNumber={}

    Keyword Arguments:
        serial_number {str} -- The serial number of the device (default: {None})

    Returns:
        dict -- Object of the device
    """
    if serial_number is None:
      return None
    api_path = '/dna/intent/api/v1/network-device?serialNumber={}'.format(serial_number)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def show_device(self, device):
    """Show single device information

    Arguments:
        device {dict} -- device object

    Returns:
        None -- print stdout only
    """
    if not device:
      print('no device information found.')
      return

    if not HAS_TABULATE:
      print("tabulate module not found.")
      return

    # print(json.dumps(device, ensure_ascii=False, indent=2))

    def get_row(key):
      return [key, device.get(key) or '-']

    want_keys = [
      'hostname',
      'type',
      'family',
      'series',
      'softwareType',
      'softwareVersion',
      'macAddress',
      'managementIpAddress',
      'serialNumber',  # this might be multiple in case of stack
      'platformId',    # this might be multiple in case of stack
      'role',
      'upTime'
    ]

    table = []
    for key in want_keys:
      table.append(get_row(key))

    print(tabulate.tabulate(table))


  def get_device_licenses(self, device_id=None):
    """Get device licenses by device id

    version 1.2.x
    /api/v1/license-info/network-device/{id}

    Keyword Arguments:
        device_id {str} -- The identifier for the device (default: {None})

    Returns:
        list -- list of licenses
    """
    if device_id is None:
      return None
    api_path = '/api/v1/license-info/network-device/{}'.format(device_id)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def show_device_licenses(self, license_list=None):
    """Show device licenses

    Keyword Arguments:
        license_list {list} -- device license list (default: {None})
    """
    if not license_list:
      print('no license information found.')
      return

    if not HAS_TABULATE:
      print("tabulate module not found.")
      return

    headers = ['name', 'status', 'type', 'maxUsageCount', 'usageCountRemaining']
    table = []
    for lic in license_list:
      license_name = lic.get('name') or '-'
      status = lic.get('status') or '-'
      license_type = lic.get('type') or '-'
      max_usage_count = lic.get('maxUsageCount') or '-'
      usage_count_remaining = lic.get('usageCountRemaining') or '-'
      table.append([license_name, status, license_type, max_usage_count, usage_count_remaining])

    print(tabulate.tabulate(table, headers, tablefmt='simple'))


  def get_device_config(self):
    """Get device config for all devices"""
    api_path = '/dna/intent/api/v1/network-device/config'
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_device_interfaces(self, device_id=None):
    """Get device interfaces by device_id

    version 1.2
    /dna/intent/api/v1/interface/network-device/{device_id}

    Keyword Arguments:
        device_id {str} -- The identifier of the device (default: {None})

    Returns:
        list -- List of interfaces of the device
    """
    if device_id is None:
      return None
    api_path = '/dna/intent/api/v1/interface/network-device/{}'.format(device_id)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_device_interfaces_by_range(self, device_id=None, start_index=1, racords_to_return=1):
    """Get device interfaces by specified range

    version 1.2
    /dna/intent/api/v1/interface/network-device/{device_id}/{start_index}/{records_to_return}

    Keyword Arguments:
        device_id {str} -- The identifier of the device (default: {None})
        start_index {int} -- start index (default: {1})
        racords_to_return {int} -- records to return (default: {1})

    Returns:
        list -- Specified number of list that contains interface object
    """
    if device_id is None:
      return None
    api_path = '/dna/intent/api/v1/interface/network-device/{}/{}/{}'.format(device_id, start_index, racords_to_return)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_device_interfaces_by_name(self, device_id=None, name=None):
    """Get interface details by device_id and interface name

    version 1.2
    /dna/intent/api/v1/interface/network-device/{device_id}/interface-name?name={name}

    Keyword Arguments:
        device_id {str} -- The identifier of the device (default: {None})
        name {str} -- The name of the interface, ex GigabitEthernet0/0/1 (default: {None})

    Returns:
        dict -- Object of the interface
    """
    if device_id is None:
      return None
    api_path = '/dna/intent/api/v1/interface/network-device/{}/interface-name?name={}'.format(device_id, name)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def show_device_interfaces(self, intf_list=None):
    """Print interfaces"""
    if intf_list is None:
      print("no interface found.")
      return

    if not HAS_TABULATE:
      print("tabulate module not found.")
      return

    # sort by portName
    intf_list = sorted(intf_list, key=lambda port: port.get('portName'))

    headers = ['portName', 'speed', 'status', 'interfaceType', 'vlanId', 'Other']
    table = []
    total_ports = total_up = 0
    for intf in intf_list:
      if intf['interfaceType'] == "Physical":
        total_ports += 1
        if intf['status'] == "up":
          total_up += 1

      if intf['ipv4Address'] is not None:
        extra = "{ip}/{mask}".format(ip=intf['ipv4Address'], mask=intf['ipv4Mask'])
      elif intf['portMode'] == "trunk":
        extra = "{trunk}{description}".format(trunk=intf['portMode'], description=intf['description'])
      else:
        extra = ""

      port_name = intf.get('portName') or '-'
      speed = intf.get('speed') or '-'
      status = intf.get('status') or '-'
      interface_type = intf.get('interfaceType') or '-'
      vlan_id = intf.get('vlanId') or '-'

      table.append([port_name, speed, status, interface_type, vlan_id, extra])

    print(tabulate.tabulate(table, headers, tablefmt='simple'))
    print('')
    print("Total ports:{}, up:{}".format(total_ports, total_up))


  def assign_device_to_site(self, site_id, device_list):
    """assign devices to site

    NOT TESTED

    version 1.3
    /dna/system/api/v1/site/{site_id}/device

    Arguments:
        site_id {str} -- The identifier of the site
        device_list {list} -- List of devices
    """
    payload = {
      "device": device_list
    }

    payload = {
      "device": [{
        "serialNumber": "FOC1703V36B",
        "siteName": "Area1-BLD1",
        "ip": ""
      }, {
        "serialNumber": "FTX1842AHM1",
        "siteName": "Area1-BLD1",
        "ip": ""
      }, {
        "serialNumber": "FTX1842AHM2",
        "siteName": "Area1-BLD2",
        "ip": ""
      }, {
        "serialNumber": "FOX1525G5S1",
        "siteName": "Area1-BLD2",
        "ip": ""
      }, {
        "serialNumber": "FOX1524GV2Z",
        "siteName": "Area3-BLD1",
        "ip": ""
      }, {
        "serialNumber": "FXS1825Q1PA",
        "siteName": "Area3-BLD1",
        "ip": ""
      }, {
        "serialNumber": "FCW1630L0JG",
        "siteName": "Area3-BLD2",
        "ip": ""
      }]
    }

    api_path = '/dna/system/api/v1/site/{}/device'.format(site_id)
    api_path = '/dna/intent/api/v1/site/{}/device'.format(site_id)
    response = self.post(api_path=api_path, data=payload)
    print(json.dumps(response, indent=2))


  def execute_module_get_devices(self, check_mode=False):
    """execute ansible module

    Keyword Arguments:
        check_mode {bool} -- Check mode or not (default: {False})

    Returns:
        dict -- Object of the result
    """
    result = {
      'changed': False,
      'failed': False
    }

    if check_mode:
      result['warnings'] = "Get devices operation is not restricted by check_mode"

    device_ip = self.params.get('ip')
    device_id = self.params.get('id')
    device_serial = self.params.get('serial')

    device = None
    device_list = None

    if any([device_ip, device_id, device_serial]):
      if device_ip:
        device = self.get_device_by_ip(device_ip)
      elif device_id:
        device = self.get_device_by_id(device_id)
      elif device_serial:
        device = self.get_device_by_serial(device_serial)
      if device:
        result['device_list'] = [device]
      else:
        result['failed'] = True
    else:
      device_list = self.get_device_list()
      if device_list:
        result['device_list'] = device_list
      else:
        result['failed'] = True

    return result



if __name__ == '__main__':

  import json
  import sys

  from dnac_sandbox import sandbox_params

  def main():
    """main function for test"""

    logging.basicConfig(level=logging.INFO)

    params = sandbox_params.get('always-on-lab')
    # params = sandbox_params.get('hardware-lab')

    # DnacRestClient class object
    drc = DnacDevices(params)

    # get device list and show it
    device_list = drc.get_device_list()
    drc.show_device_list(device_list=device_list)

    # for example
    # select 1st device
    device_id = device_list[0].get('id')

    # get device and show it
    device = drc.get_device_by_id(device_id=device_id)
    drc.show_device(device)

    # get all interfaces and show it
    intf_list = drc.get_device_interfaces(device_id=device_id)
    drc.show_device_interfaces(intf_list)

    # get first 3 interfaces and show it
    intf_list = drc.get_device_interfaces_by_range(device_id=device_id, start_index=1, racords_to_return=3)
    drc.show_device_interfaces(intf_list)

    # get GigabitEthernet0/0/1 and show it
    intf = drc.get_device_interfaces_by_name(device_id=device_id, name='GigabitEthernet0/0/1')
    drc.show_device_interfaces([intf])

    # get licenses of the device and show it
    license_list = drc.get_device_licenses(device_id=device_id)
    drc.show_device_licenses(license_list)

    return 0


  sys.exit(main())
