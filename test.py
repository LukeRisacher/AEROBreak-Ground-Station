import os
import sys
import sqlite3
import time
import random
import subprocess
import shutil
from datetime import datetime

DATABASE = 'telemetry.db'
UPDATE_INTERVAL = 0.1  # 10 Hz
GPS_INTERVAL = 1.0     # 1 Hz

def archive_existing_database():
    if os.path.exists(DATABASE):
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        archive_name = f"telemetry_{timestamp}.db"
        shutil.move(DATABASE, archive_name)
        print(f"[TEST] Archived old database as: {archive_name}")
    else:
        print("[TEST] No existing database to archive.")

def init_db():
    """
    Create the 'telemetry' table in a new database.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            altitude REAL,
            temperature REAL,
            acceleration REAL,
            latitude REAL,
            longitude REAL
        )
    ''')
    conn.commit()
    conn.close()
    print("[TEST] New database initialized.")

def simulate_data():
    """
    Continuously generate & insert simulated telemetry data.
    """
    print("[TEST] Starting data simulation...")
    altitude = 0.0
    velocity = 50.0  # ft/s
    lat, lon = 29.0, -95.0
    next_gps_time = time.time()

    while True:
        current_time = time.time()

        velocity += random.uniform(-0.5, 0.5)
        altitude += velocity * UPDATE_INTERVAL
        if altitude < 0:
            altitude = 0

        temperature = random.uniform(60, 80)
        acceleration = random.uniform(-5, 5)

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        if current_time >= next_gps_time:
            lat += random.uniform(-0.0001, 0.0001)
            lon += random.uniform(-0.0001, 0.0001)
            next_gps_time = current_time + GPS_INTERVAL
            c.execute('''
                INSERT INTO telemetry (timestamp, altitude, temperature, acceleration, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (current_time, altitude, temperature, acceleration, lat, lon))
        else:
            c.execute('''
                INSERT INTO telemetry (timestamp, altitude, temperature, acceleration, latitude, longitude)
                VALUES (?, ?, ?, ?, NULL, NULL)
            ''', (current_time, altitude, temperature, acceleration))

        conn.commit()
        conn.close()
        time.sleep(UPDATE_INTERVAL)

def run_flask_app():
    """
    Launch the Flask app in a subprocess.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, 'app.py')
    return subprocess.Popen([sys.executable, app_path])

if __name__ == '__main__':
    archive_existing_database()
    init_db()

    print("[TEST] Launching Flask app...")
    flask_process = run_flask_app()
    time.sleep(2)  # Give Flask time to initialize

    try:
        simulate_data()
    except KeyboardInterrupt:
        pass
    finally:
        print("[TEST] Terminating Flask app...")
        flask_process.terminate()
        flask_process.wait()
        print("[TEST] Exiting.")
