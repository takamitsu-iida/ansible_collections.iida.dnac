#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

class DnacDevices:
  """Manage Network Devices
  """

  def assign_devices(self, drc, site_id, device_list):
    """assign devices to site

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

    api_path = '/dna/intent/api/v1/site/{}/device'.format(site_id)
    response = drc.post(api_path=api_path, data=payload)
    print(json.dumps(response, indent=2))


  def get_device_list(self, drc):
    """get device object list"""
    api_path = '/dna/intent/api/v1/network-device'
    get_result = drc.get(api_path=api_path)
    return drc.extract_data_response(get_result)


  def get_device_by_ip(self, drc, ip=None):
    """get device object by ip address"""
    if ip is None:
      return None
    api_path = '/dna/intent/api/v1/network-device?managementIpAddress={}'.format(ip)
    get_result = drc.get(api_path=api_path)
    return drc.extract_data_response(get_result)


  def get_device_by_serial(self, drc, serial_number=None):
    """get device object by serial number"""
    if serial_number is None:
      return None
    api_path = '/dna/intent/api/v1/network-device?serialNumber={}'.format(serial_number)
    get_result = drc.get(api_path=api_path)
    return drc.extract_data_response(get_result)


if __name__ == '__main__':

  import json
  import logging
  import sys

  from dnac_rest_client import DnacRestClient

  def main():
    """main function for test"""

    logging.basicConfig(level=logging.INFO)

    # Cisco DevNet Sandbox version 1.2.10 readonly
    _params_readonly = {
      'host': 'sandboxdnac2.cisco.com',
      'port': 443,
      'username': 'devnetuser',
      'password': 'Cisco123!',
      'timeout': 30,
      'log_dir': './log',
      'http_proxy': ''  ## http://username:password@proxy-url:8080
    }

    _params_reserved = {
      'host': '10.10.20.85',
      'port': 443,
      'username': 'admin',
      'password': 'Cisco1234!',
      'timeout': 30,
      'log_dir': './log',
      'http_proxy': ''  ## http://username:password@proxy-url:8080
    }

    HAS_RESERVATION = False
    params = _params_reserved if HAS_RESERVATION else _params_readonly

    dnac = DnacRestClient(params)
    d = DnacDevices()

    device_list = d.get_device_list(dnac)
    for device in device_list:
      print(json.dumps(device, ensure_ascii=False, indent=2))

    return 0

  # 実行
  sys.exit(main())
