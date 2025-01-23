import sqlite3
from flask import Flask, jsonify, render_template
import os

DATABASE = 'telemetry.db'
app = Flask(__name__)

# -----------------------------------------------------------------------------
# Data Retrieval & Derived Values (READ-ONLY)
# -----------------------------------------------------------------------------
def get_recent_data(count=200):
    """
    Fetch the most recent 'count' rows from the database.
    Calculate derived descent rate from altitude changes.
    Return as a list of dict objects.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        SELECT timestamp, altitude, temperature, acceleration, latitude, longitude
        FROM telemetry
        ORDER BY id DESC
        LIMIT ?
    ''', (count,))
    rows = c.fetchall()
    conn.close()

    rows.reverse()  # chronological order
    data = []
    prev_alt = None
    prev_time = None

    for row in rows:
        t, alt, temp, accel, lat, lon = row
        descent_rate = None
        if prev_alt is not None and prev_time is not None and alt is not None:
            dt = t - prev_time
            if dt != 0:
                # positive descent rate if altitude is dropping
                descent_rate = max(0, (prev_alt - alt) / dt)

        data.append({
            'timestamp': t,
            'altitude': alt,
            'temperature': temp,
            'acceleration': accel,
            'latitude': lat,
            'longitude': lon,
            'descent_rate': descent_rate
        })

        prev_alt = alt
        prev_time = t

    return data

# -----------------------------------------------------------------------------
# Flask Routes
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    """Serve the dashboard HTML."""
    return render_template('index.html')

@app.route('/data')
def data_api():
    """Return recent telemetry data (JSON)."""
    return jsonify(get_recent_data())

# -----------------------------------------------------------------------------
# Main (If you run app.py directly, it will just serve whatever data is in DB)
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    # Note: We do NOT create the DB here. We assume it's already created.
    app.run(debug=True, use_reloader=False)
