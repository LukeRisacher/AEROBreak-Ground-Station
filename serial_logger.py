import serial
import sqlite3
import time
import logging

# Hardcoded configuration values for a one-launch device system
SERIAL_PORT = "COM3"
BAUD_RATE = 9600
DB_FILE = "telemetry.db"

# Configure logging: outputs both to file and console
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("serial_logger.log"),
        logging.StreamHandler()
    ]
)

def init_db():
    """Initialize the telemetry database and create the table if it doesn't exist."""
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
            logging.info("Database initialized successfully.")
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")

def log_data_to_db(data):
    """Log a single telemetry data point to the database."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("INSERT INTO telemetry VALUES (?, ?, ?, ?, ?, ?)", data)
            conn.commit()
    except Exception as e:
        logging.error(f"Failed to write to database: {e}")

def main():
    init_db()
    while True:
        try:
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                logging.info(f"Listening on serial port {SERIAL_PORT} at {BAUD_RATE} baud.")
                while True:
                    try:
                        line = ser.readline().decode('utf-8').strip()
                        if not line:
                            continue

                        parts = line.split(';')
                        if len(parts) not in (3, 5):
                            logging.warning(f"Malformed data received: {line}")
                            continue

                        try:
                            altitude = float(parts[0])
                            temperature = float(parts[1])
                            acceleration = float(parts[2])
                            latitude = float(parts[3]) if len(parts) > 3 and parts[3] else None
                            longitude = float(parts[4]) if len(parts) > 4 and parts[4] else None
                        except ValueError:
                            logging.warning(f"Failed to parse line: {line}")
                            continue

                        timestamp = time.time()
                        data = (timestamp, altitude, temperature, acceleration, latitude, longitude)
                        log_data_to_db(data)
                    except Exception as inner_err:
                        logging.error(f"Error during serial read: {inner_err}")
        except serial.SerialException as e:
            logging.error(f"Could not open serial port {SERIAL_PORT}: {e}")
            time.sleep(5)  # Wait before retrying

if __name__ == '__main__':
    main()
