EVPN VXLAN DC DEMO
==================

Summary
-------

This project contains the build and test for building an EVPN VXLAN ERB DC using Juniper QFX devices.

NITA support
------------

This project has been tested on the following versions of NITA:
  * 20.10

The following processes have been provided:
-------------------------------------------

1. Build of all network devices
2. Utility playbook to dump configurations from Junos devices
3. Utility playbook to configure healthbot devices and groups
4. Utility playbook to configure netbox devices
2. Testing of network devices
  * Base testing of each device
  * Connectivity testing using ping
  * BGP neighbour tests

Documentation
-------------

The build process covers the following features of EVPN VXLAN on QFX:

 * eBGP based ipclos underlay 
 * Edge based routing for EVPN VXLAN, leaves act as edge devices
 * Lean spine configuration
 * Border leaf configuration
 * OSPF based firewall connectivity
 * Fabric interconnect from border leaves
 * Support for collapsed spine architecture (its basically ERB + border leaves in one with a few tweaks)
 * Open config telmetry switched on by default
 * Firewall configuration for the SRX (based on OSPF) 

