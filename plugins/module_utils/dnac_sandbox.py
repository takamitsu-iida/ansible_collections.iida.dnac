#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring

sandbox_params = {
  # Cisco DNA Center
  # Always On Lab
  # Version 1.2.10
  'always-on-lab': {
    'host': 'sandboxdnac2.cisco.com',
    'port': 443,
    'username': 'devnetuser',
    'password': 'Cisco123!',
    'timeout': 30,
    'log_dir': './log',
    'http_proxy': ''  ## http://username:password@proxy-url:8080
  },

  # Cisco DNA Center
  # Hardware Lab 2
  # Version 1.2.10
  'hardware-lab-2': {
    'host': '10.10.20.85',
    'port': 443,
    'username': 'admin',
    'password': 'Cisco1234!',
    'timeout': 30,
    'log_dir': './log',
    'http_proxy': ''  ## http://username:password@proxy-url:8080
  }

}
