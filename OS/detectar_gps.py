"""
This script connects to Pixhawk flight controller via MAVLink and waits
for a valid GPS fix (fix_type >= 3). If obtained, it prints the current 
latitude, longitude, and altitude. If no fix is found or a timeout occurs,
a corresponding message is printed.

"""
#Imports
from pymavlink import mavutil

# Main logic to connect to Pixhawk and wait for a valid GPS fix
def main():
    try:
        # Establish MAVLink connection over serial
        connection = mavutil.mavlink_connection('/dev/serial0', baud=57600)
        connection.wait_heartbeat(timeout=10)
        print("Heartbeat detected. Waiting for GPS fix...")

        fix_obtenido = False

        # Loop until a valid GPS fix is obtained or timeout occurs
        while not fix_obtenido:
            msg = connection.recv_match(type='GPS_RAW_INT', blocking=True, timeout=5)

            if not msg:
                print("Timeout waiting for GPS.")
                break

            # Check for valid GPS fix (fix_type >= 3) and valid coordinates
            if msg.fix_type >= 3 and msg.lat not in (0, 0x7FFFFFFF):
                lat = msg.lat / 1e7
                lon = msg.lon / 1e7
                alt = msg.alt / 1000.0

                print("GPS OK")
                print(f"Current position: Latitude={lat:.7f}, longitude={lon:.7f}, altitude={alt:.1f} m")
                fix_obtenido = True
            else:
                print("GPS detected but no valid fix (Waiting for fix >= 3)...")
                break

    except Exception as e:
        print(f"Error: {e}")

# Run the main function if script is executed directly
if __name__ == "__main__":
    main()
