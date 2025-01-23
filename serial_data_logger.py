import sqlite3
import serial
import time

DATABASE = 'telemetry.db'

def read_and_store_serial_data(port='COM3', baudrate=115200):
    """
    Continuously read lines from the given serial port and store in the DB.
    (This is just a placeholder. Adjust to your real packet format.)
    """
    ser = serial.Serial(port, baudrate, timeout=1)
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if not line:
            continue

        # Example: Suppose each line is "timestamp,alt,temperature,accel,lat,lon"
        # e.g. "1693467200.123,1000,75.5,1.0,29.001234,-95.001234"
        parts = line.split(',')
        if len(parts) < 6:
            continue  # skip malformed lines

        try:
            t        = float(parts[0])
            altitude = float(parts[1])
            temp     = float(parts[2])
            accel    = float(parts[3])
            lat      = float(parts[4])
            lon      = float(parts[5])
        except ValueError:
            continue  # skip lines that don't parse

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''
            INSERT INTO telemetry (timestamp, altitude, temperature, acceleration, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (t, altitude, temp, accel, lat, lon))
        conn.commit()
        conn.close()

        # you might want to sleep slightly, but usually reading is event-driven
        time.sleep(0.01)

if __name__ == '__main__':
    # You would run this file to do *real* logging from the rocket’s serial port
    read_and_store_serial_data()
