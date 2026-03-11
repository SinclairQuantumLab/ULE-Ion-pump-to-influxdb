import socket
import time
import pytest

IP = "192.168.1.50"   # change this
PORT = 23


@pytest.fixture
def spce_socket():
    s = socket.create_connection((IP, PORT), timeout=5)
    s.settimeout(1)
    yield s
    s.close()


def send_command(sock, cmd, wait_time=0.5):
    sock.sendall((cmd + "\r\n").encode("ascii"))
    time.sleep(wait_time)
    return sock.recv(4096).decode("ascii", errors="replace").strip()


def test_connects_to_spce():
    s = socket.create_connection((IP, PORT), timeout=5)
    s.close()


def test_model_query(spce_socket):
    reply = send_command(spce_socket, "spc 01")
    assert reply != ""
    assert "SPC" in reply.upper() or "DIGITEL" in reply.upper()


def test_version_query(spce_socket):
    reply = send_command(spce_socket, "spc 02")
    assert reply != ""
    assert "FIRMWARE" in reply.upper() or "VERSION" in reply.upper()


def test_pressure_query(spce_socket):
    reply = send_command(spce_socket, "spc 0B")
    assert reply != ""
    # keep this loose since exact format may vary slightly
    assert any(unit in reply.upper() for unit in ["TORR", "MBAR", "PA", "MBR", "E-"])