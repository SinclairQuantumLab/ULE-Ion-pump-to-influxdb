# GAMMA VACUUM SPCe Ion Pump Readings Relay to InfluxDB

Poll the GAMMA VACUUM SPCe ion pump controller and upload readings to InfluxDB.

How to setup

In the controller menu, set the ethernet settings: DHCP disable, IP address=192.168.1.50, subnet mask=255.255.255.0, and gateway=192.168.1.1
Then, connect the controller directly to a computer (e.g., Raspberry Pi) via Ethernet cable.
Set the computer's IP setting accordingly with IP address=192.168.1.x except x=50