import serial
import sqlite3
import time
import math

SERIAL_PORT = 'COM4'
BAUDRATE = 9600  # Adjust as needed
DATABASE = 'telemetry.db'

def initialize_database():
    """Create the telemetry table if it doesn't exist."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
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
    print("Database initialized or already exists.")

def write_data_to_db(timestamp, altitude, temperature, acceleration, latitude=None, longitude=None):
    """Insert a row into the telemetry table."""
    try:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute('''INSERT INTO telemetry (timestamp, altitude, temperature, acceleration, latitude, longitude)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (timestamp, altitude, temperature, acceleration, latitude, longitude))
        conn.commit()
    except Exception as e:
        print("Database write error:", e)
    finally:
        conn.close()

def parse_serial_line(line):
    """
    Parse the line from the serial port.
    For example, if the Arduino sends a comma-separated string like:
      "alt, temp, accX, accY, accZ"
    then this function converts the first two values to float,
    and calculates the magnitude of the acceleration vector.
    """
    try:
        parts = line.strip().split(';')
        if len(parts) < 5:
            raise ValueError("Not enough data fields")
        alt = float(parts[0])
        temp = float(parts[1])
        # Compute the magnitude of the acceleration vector: sqrt(x^2 + y^2 + z^2)
        acc_x = float(parts[2])
        acc_y = float(parts[3])
        acc_z = float(parts[4])
        acc_magnitude = math.sqrt(acc_x**2 + acc_y**2 + acc_z**2)
        return alt, temp, acc_magnitude
    except Exception as e:
        print("Parsing error:", e)
        return None

def main():
    # Ensure the database and table exist before starting serial reading.
    initialize_database()
    
    # Open the serial port.
    try:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
        print("Listening on", SERIAL_PORT)
    except Exception as e:
        print("Error opening serial port:", e)
        return

    while True:
        try:
            line = ser.readline().decode('utf-8')
            if line:
                parsed = parse_serial_line(line)
                if parsed:
                    altitude, temperature, acceleration = parsed
                    timestamp = time.time()
                    write_data_to_db(timestamp, altitude, temperature, acceleration)
                    print(f"Logged: {timestamp}, {altitude}, {temperature}, {acceleration}")
        except Exception as e:
            print("Error during serial read or DB write:", e)
            time.sleep(1)  # Brief pause on error

if __name__ == '__main__':
    main()
