import serial
import sqlite3
import time
import logging

# --- Configuration ---
SERIAL_PORT = "COM3"
BAUD_RATE = 9600
DB_FILE = "telemetry.db"
LOG_FILE = "serial_logger.log"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# --- Helpers ---
def parse_float(value):
    """Safely convert a string to float, treating 'null' or empty as None."""
    return float(value) if value and value.lower() != "null" else None

def init_db():
    """Ensure the telemetry table exists in the SQLite database."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute('''
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
            logging.info("Database initialized.")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")

def log_data_to_db(data):
    """Insert a row of telemetry data into the database."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("INSERT INTO telemetry VALUES (?, ?, ?, ?, ?, ?)", data)
            conn.commit()
            logging.info(f"Logged data: {data}")
    except Exception as e:
        logging.error(f"Database write failed: {e}")

# --- Main Serial Listener ---
def main():
    init_db()

    while True:
        try:
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                logging.info(f"Listening on {SERIAL_PORT} at {BAUD_RATE} baud...")
                while True:
                    try:
                        line = ser.readline().decode('utf-8').strip()
                        if not line:
                            continue

                        parts = line.split(';')
                        if len(parts) not in (3, 5):
                            logging.warning(f"Malformed data: {line}")
                            continue

                        altitude = parse_float(parts[0])
                        temperature = parse_float(parts[1])
                        acceleration = parse_float(parts[2])
                        latitude = parse_float(parts[3]) if len(parts) > 3 else None
                        longitude = parse_float(parts[4]) if len(parts) > 4 else None

                        timestamp = time.time()
                        log_data_to_db((timestamp, altitude, temperature, acceleration, latitude, longitude))

                    except Exception as inner_err:
                        logging.error(f"Serial read error: {inner_err}")

        except serial.SerialException as e:
            logging.error(f"Serial port error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
