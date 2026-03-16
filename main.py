"""
Poll the SPCe ion pump controller and upload readings to InfluxDB.

This script runs continuously, polls the SPCe at a fixed interval, uploads the
latest pressure/current/voltage readings to InfluxDB, and raises after a
configured number of total exceptions so supervisor can handle process-level
recovery.
"""

from supervisor_helper import *
from spce_client import SPCeClient, SPCeError, PressureReading, PressureUnit

import socket
import time

import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS


print()
print("----- ULE chamber's GAMMA VACUUM SPCe ion pump controller -> InfluxDB uploader -----")
print()


# >>> App configuration >>>

INTERVAL_s = 30
EX_THRESHOLD = 3

print(f"Polling interval = {INTERVAL_s} s, exception threshold = {EX_THRESHOLD}.")
print()

# <<< App configuration <<<

# >>> load IMAQ config >>>
import tomllib
with open("imaq_config/auth.toml", "rb") as f:
    AUTH = tomllib.load(f)
# <<< load IMAQ config <<<

# >>> SPCe connection >>>

SPCE_IP = "192.168.1.50"
SN = "307207407"
PRESSURE_UNIT = PressureUnit.TORR

# <<< SPCe connection <<<


# >>> InfluxDB configuration >>>
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
# Initialize the InfluxDB Client and the Write API
INFLUXDB_CLIENT = influxdb_client.InfluxDBClient(**AUTH["influxdb"])
INFLUXDB_WRITE_API = INFLUXDB_CLIENT.write_api(write_options=SYNCHRONOUS)
INFLUXDB_QUERY_API = INFLUXDB_CLIENT.query_api()
INFLUXDB_ORG = AUTH["influxdb"]["org"]; INFLUXDB_BUCKET = AUTH["influxdb"]["bucket"]
print(f"InfluxDB client initialized for org='{INFLUXDB_ORG}', bucket='{INFLUXDB_BUCKET}'.")
print()
# <<< InfluxDB configuration <<<



def connect_spce() -> SPCeClient:
    """Connect to the SPCe and set the pressure unit."""
    client = SPCeClient(IP=SPCE_IP)
    client.connect()
    client.set_pressure_unit(PRESSURE_UNIT)
    return client


print(f"Connecting to SPCe at {SPCE_IP}...", end=" ")
spce_client = connect_spce()
print("Done.")
print(spce_client)
print()


ex_count = 0
il = 0

print("Entering main polling loop...")
print()

try:
    while True:
        msg_il = f"Iteration {il}: "

        try:
            # >>>>> query readings >>>>>

            try:
                pressure: PressureReading = spce_client.get_pressure()
                current_A: float = spce_client.get_current_A()
                voltage_V: float = spce_client.get_voltage_V()

            except (socket.timeout, OSError, SPCeError) as ex:
                log_error(msg_il)
                log_error(f"SPCe query failed: {type(ex).__name__}: {ex}")
                log_warn("Re-establishing SPCe connection and retrying once...")

                try:
                    spce_client.close()
                except Exception:
                    pass

                spce_client = connect_spce()
                log_warn("SPCe reconnection succeeded.")

                pressure = spce_client.get_pressure()
                current_A = spce_client.get_current_A()
                voltage_V = spce_client.get_voltage_V()

            if pressure.unit.upper() != "TORR":
                raise ValueError(f"Expected pressure unit 'Torr', got '{pressure.unit}'.")

            influxdb_record = {
                "measurement": "SPCe_IonPump",
                "tags": {
                    "SN": SN,
                    "model": spce_client._model or "",
                    "version": spce_client._version or "",
                    "IP": spce_client._IP,
                    "source": "Ethernet/Telnet",
                },
                "fields": {
                    "Pressure[Torr]": pressure.value,
                    "Current[A]": current_A,
                    "Voltage[V]": voltage_V,
                },
            }

            # <<<<< query readings <<<<<

            # upload to InfluxDB
            INFLUXDB_WRITE_API.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=influxdb_record)

            log(
                msg_il
                + f"Pressure[Torr]={pressure.value:.2e}, "
                + f"Current[mA]={current_A*1e3:.3f}, "
                + f"Voltage[V]={voltage_V:.1f}"
            )

        except Exception as ex:
            log_error(msg_il)
            ex_count += 1
            log_error(f"Error during measurement/upload ({ex_count}/{EX_THRESHOLD}): {type(ex).__name__}: {ex}")

            if ex_count >= EX_THRESHOLD:
                log_error("Exception threshold reached. Raising to supervisor.")
                raise

        time.sleep(INTERVAL_s)
        il += 1

except KeyboardInterrupt:
    log_warn("KeyboardInterrupt received.")

finally:
    log("Shutting down gracefully...", end=" ")
    try:
        spce_client.close()
    except Exception:
        pass

    try:
        INFLUXDB_CLIENT.close()
    except Exception:
        pass

    print("Done")