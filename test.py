import os
import sys
import sqlite3
import time
import random
import subprocess
import signal

DATABASE = 'telemetry.db'
UPDATE_INTERVAL = 0.1  # 10 Hz
GPS_INTERVAL = 1.0     # 1 Hz

def init_db():
    """
    Create the 'telemetry' table if it doesn't already exist.
    We'll do this BEFORE launching the Flask app or inserting data.
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

        # Simple altitude physics
        velocity += random.uniform(-0.5, 0.5)
        altitude += velocity * UPDATE_INTERVAL
        if altitude < 0:
            altitude = 0

        temperature = random.uniform(60, 80)  # Fahrenheit
        acceleration = random.uniform(-5, 5)  # ft/s^2

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
    Launch the Flask app in a subprocess so we can continue to run
    data simulation in the main process.
    """
    # Build an absolute path to app.py to avoid "No such file" on Windows
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, 'app.py')

    # Launch app.py with same Python interpreter
    return subprocess.Popen([sys.executable, app_path])

if __name__ == '__main__':
    # 1) Initialize DB (create table if missing)
    init_db()

    # 2) Launch Flask app as a subprocess
    print("[TEST] Launching Flask app...")
    flask_process = run_flask_app()
    time.sleep(2)  # Give Flask time to initialize

    try:
        # 3) Generate data until user interrupts
        simulate_data()
    except KeyboardInterrupt:
        pass
    finally:
        print("[TEST] Terminating Flask app...")
        flask_process.terminate()
        flask_process.wait()
        print("[TEST] Exiting.")
