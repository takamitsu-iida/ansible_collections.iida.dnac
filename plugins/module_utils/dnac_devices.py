#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

try:
  from dnac_rest_client import DnacRestClient
except ImportError:
  from ansible_collections.iida.dnac.plugins.module_utils.dnac_rest_client import DnacRestClient


class DnacDevices(DnacRestClient):
  """Manage Network Devices
  """

  def get_device_list(self):
    """Get device object list"""
    api_path = '/dna/intent/api/v1/network-device'
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_device_by_id(self, device_id=None):
    """Get device by id"""
    if device_id is None:
      return None
    api_path = '/dna/intent/api/v1/network-device/{}'.format(device_id)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_device_by_ip(self, ip=None):
    """Get device object by ip address"""
    if ip is None:
      return None
    api_path = '/dna/intent/api/v1/network-device?managementIpAddress={}'.format(ip)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_device_by_serial(self, serial_number=None):
    """Get device object by serial number"""
    if serial_number is None:
      return None
    api_path = '/dna/intent/api/v1/network-device?serialNumber={}'.format(serial_number)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_device_config(self):
    """Get device config for all devices"""
    api_path = '/dna/intent/api/v1/network-device/config'
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_device_interface_by_range(self, device_id=None, start_index=0, racords_to_return=1):
    """Get device interfaces by specified range"""
    if device_id is None:
      return None
    api_path = '/dna/intent/api/v1/interface/network-device/{}/{}/{}'.format(device_id, start_index, racords_to_return)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def get_device_interface_by_name(self, device_id=None, name=None):
    """Get interface details by device_id and interface name"""
    if device_id is None:
      return None
    api_path = '/dna/intent/api/v1/interface/network-device/{}/{}'.format(device_id, name)
    get_result = self.get(api_path=api_path)
    return self.extract_data_response(get_result)


  def assign_device_to_site(self, site_id, device_list):
    """assign devices to site

    Cisco DNA Center Release: 1.3.0.x
    '/dna/system/api/v1/site/{site_id}/device'

    Arguments:
        site_id {[type]} -- [description]
        device_list {[type]} -- [description]
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


if __name__ == '__main__':

  import json
  import logging
  import sys

  from dnac_sandbox import sandbox_params

  def main():
    """main function for test"""

    logging.basicConfig(level=logging.INFO)

    # params = sandbox_params.get('always-on-lab')
    params = sandbox_params.get('hardware-lab')

    # DnacRestClient class object
    drc = DnacDevices(params)

    device_list = drc.get_device_list()
    if device_list:
      for device in device_list:
        print(json.dumps(device, ensure_ascii=False, indent=2))
    else:
      print("no device found")

    return 0

  # 実行
  sys.exit(main())
