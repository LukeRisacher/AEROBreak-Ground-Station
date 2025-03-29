import serial
import sqlite3
import time
from datetime import datetime

SERIAL_PORT = "COM3"  # Update as needed
BAUD_RATE = 9600
DB_FILE = "telemetry.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute('''
        CREATE TABLE IF NOT EXISTS telemetry (
            timestamp REAL,
            altitude REAL,
            temperature REAL,
            acceleration REAL,
            latitude REAL,
            longitude REAL
        )
    ''')
    conn.commit()
    conn.close()


def log_data_to_db(data):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("INSERT INTO telemetry VALUES (?, ?, ?, ?, ?, ?)", data)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Failed to write to database: {e}")


def main():
    init_db()
    while True:
        try:
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                print("[INFO] Listening on serial port...")
                while True:
                    try:
                        line = ser.readline().decode('utf-8').strip()
                        if not line:
                            continue

                        parts = line.split(';')
                        if len(parts) not in (3, 5):
                            print(f"[WARN] Malformed data: {line}")
                            continue

                        try:
                            altitude = float(parts[0])
                            temperature = float(parts[1])
                            acceleration = float(parts[2])
                            latitude = float(parts[3]) if len(parts) > 3 and parts[3] else None
                            longitude = float(parts[4]) if len(parts) > 4 and parts[4] else None
                            timestamp = time.time()
                            data = (timestamp, altitude, temperature, acceleration, latitude, longitude)
                            log_data_to_db(data)
                        except ValueError:
                            print(f"[WARN] Failed to parse line: {line}")

                    except Exception as inner_err:
                        print(f"[ERROR] Serial read failed: {inner_err}")

        except serial.SerialException as e:
            print(f"[ERROR] Could not open serial port: {e}")
            time.sleep(5)  # wait and retry


if __name__ == '__main__':
    main()
