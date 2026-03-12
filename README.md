# GAMMA VACUUM SPCe Ion Pump Readings Relay to InfluxDB

A small script that polls a GAMMA VACUUM SPCe ion pump controller over Ethernet and relays its readings to InfluxDB.

## Setup

Configure the controller network settings from the front-panel menu:

- **DHCP**: Disabled  
- **IP address**: `192.168.1.50`  
- **Subnet mask**: `255.255.255.0`  
- **Gateway**: `192.168.1.1`

Then connect the controller directly to a computer, such as a Raspberry Pi, using an Ethernet cable.

Set the computer to a compatible static IP on the same subnet, for example:

- **IP address**: `192.168.1.x` where `x != 50`
- **Subnet mask**: `255.255.255.0`
- **Gateway**: `192.168.1.1`
