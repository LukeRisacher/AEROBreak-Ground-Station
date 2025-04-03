from flask import Flask, jsonify, render_template, request
import sqlite3
import os
import logging
import sys

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# Use command-line argument if provided, otherwise default to 'telemetry.db'
default_db = sys.argv[1] if len(sys.argv) > 1 else 'telemetry.db'

def get_db_path():
    # Get the 'db' parameter from the query string, defaulting to default_db
    db_param = request.args.get('db', default_db)
    # If the provided path is not absolute, resolve it relative to the current working directory
    if not os.path.isabs(db_param):
        db_path = os.path.join(os.getcwd(), db_param)
    else:
        db_path = db_param
    logging.info("Using database: %s", db_path)
    return db_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def archive_data():
    try:
        db_path = get_db_path()
        if not os.path.exists(db_path):
            error_msg = f"Database file '{db_path}' not found."
            logging.error(error_msg)
            return jsonify({"error": error_msg, "samples": [], "gps": [], "mode": "archive"})

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        c = conn.cursor()

        try:
            c.execute('''
                SELECT timestamp, altitude, temperature, acceleration, latitude, longitude 
                FROM telemetry 
                ORDER BY timestamp ASC
            ''')
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                error_msg = f"No telemetry table found in database '{db_path}'."
                logging.error(error_msg)
                return jsonify({"error": error_msg, "samples": [], "gps": [], "mode": "archive"})
            else:
                raise

        rows = c.fetchall()
        conn.close()

        if not rows:
            return jsonify({"samples": [], "gps": [], "mode": "archive"})

        valid_alts = [r[1] for r in rows if r[1] is not None]
        min_altitude = min(valid_alts) if valid_alts else 0

        samples = []
        for r in rows:
            t = r[0]
            alt = (r[1] - min_altitude) if r[1] is not None else None
            samples.append({
                'timestamp': t,
                'altitude': alt,
                'temperature': r[2],
                'acceleration': r[3]
            })

        for i in range(1, len(samples)):
            prev = samples[i - 1]
            curr = samples[i]
            if (prev.get('altitude') is not None and curr.get('altitude') is not None
                    and prev.get('timestamp') is not None and curr.get('timestamp') is not None):
                dt = curr['timestamp'] - prev['timestamp']
                curr['velocity'] = (curr['altitude'] - prev['altitude']) / dt if dt > 0 else None
            else:
                curr['velocity'] = None

        gps_points = [
            {
                'timestamp': r[0],
                'latitude': r[4],
                'longitude': r[5]
            } for r in rows if r[4] is not None and r[5] is not None
        ]

        return jsonify({"samples": samples, "gps": gps_points, "mode": "archive"})

    except Exception as e:
        logging.error("[ERROR] Failed to read archive data: %s", e)
        return jsonify({"error": str(e), "samples": [], "gps": [], "mode": "archive"})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)
