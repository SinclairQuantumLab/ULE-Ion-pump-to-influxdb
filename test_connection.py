"""
Test connection to the GAMMA VACUUM's spc-1-p-s-1-us110-e-s-n ion pump controller

In the controller menu, set the ethernet settings: DHCP disable, IP address=192.168.1.50, subnet mask=255.255.255.0, and gateway=192.168.1.1
Then, connect the controller directly to a computer (e.g., Raspberry Pi) via Ethernet cable.
Set the computer's IP setting accordingly with IP address=192.168.1.x except x=50
"""

import socket
import time

# --- settings ---
ip = "192.168.1.50"   # change this to your controller IP
port = 23

# --- connect ---
print("Connecting...")
s = socket.create_connection((ip, port), timeout=5)
s.settimeout(1)
print("Connected.\n")

# --- ask for model number ---
cmd = "spc 01\r\n"
print("Sending:", cmd.strip())
s.sendall(cmd.encode("ascii"))
time.sleep(0.5)
reply = s.recv(4096).decode("ascii", errors="replace")
print("Reply:")
print(reply)
print()

# --- ask for firmware version ---
cmd = "spc 02\r\n"
print("Sending:", cmd.strip())
s.sendall(cmd.encode("ascii"))
time.sleep(0.5)
reply = s.recv(4096).decode("ascii", errors="replace")
print("Reply:")
print(reply)
print()

# --- ask for pressure ---
cmd = "spc 0B\r\n"
print("Sending:", cmd.strip())
s.sendall(cmd.encode("ascii"))
time.sleep(0.5)
reply = s.recv(4096).decode("ascii", errors="replace")
print("Reply:")
print(reply)
print()

# --- close connection ---
s.close()
print("Connection closed.")