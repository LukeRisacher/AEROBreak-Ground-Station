from flask import Flask, jsonify, render_template
import sqlite3

app = Flask(__name__)
DATABASE = 'telemetry.db'

# ---------------------------------------------------------------------
# Helper: Read ALL rows in ascending timestamp
# ---------------------------------------------------------------------
def get_all_rows():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception as e:
        print("Failed to enable WAL mode:", e)
    c = conn.cursor()
    c.execute('''
        SELECT timestamp, altitude, temperature, acceleration, latitude, longitude
        FROM telemetry
        ORDER BY timestamp ASC
    ''')
    rows = c.fetchall()
    conn.close()
    return rows

# ---------------------------------------------------------------------
# Downsample real rows to exactly N equally spaced entries
# ---------------------------------------------------------------------
def generate_raw_sample_subset(rows, N=100):
    count = len(rows)
    if count == 0:
        return []

    if count <= N:
        subset = rows
    else:
        step = count / (N - 1)
        subset = [rows[min(int(i * step), count - 1)] for i in range(N)]

    altitudes = [row[1] for row in subset if row[1] is not None]
    min_altitude = min(altitudes) if altitudes else 0

    return [
        {
            'timestamp': row[0],
            'altitude': (row[1] - min_altitude) if row[1] is not None else None,
            'temperature': row[2],
            'acceleration': row[3]
        } for row in subset
    ]

# ---------------------------------------------------------------------
# Compute "velocity" (ft/s) from altitude changes
# ---------------------------------------------------------------------
def compute_velocity(samples):
    if len(samples) < 2:
        return samples

    prev_alt = samples[0].get('altitude')
    prev_time = samples[0].get('timestamp')

    for i in range(1, len(samples)):
        curr = samples[i]
        alt = curr.get('altitude')
        t   = curr.get('timestamp')

        if (prev_alt is not None and alt is not None
            and t is not None and prev_time is not None and t > prev_time):
            delta_alt = alt - prev_alt
            dt = t - prev_time
            curr['velocity'] = delta_alt / dt
        else:
            curr['velocity'] = None

        prev_alt = alt
        prev_time = t

    return samples

# ---------------------------------------------------------------------
# Return last 20 real GPS points
# ---------------------------------------------------------------------
def get_last_20_gps(rows, n=20):
    gps_rows = [r for r in rows if (r[4] is not None and r[5] is not None)]
    if not gps_rows:
        return []

    subset = gps_rows[-n:] if len(gps_rows) > n else gps_rows
    return [
        {
            'timestamp': row[0],
            'latitude': row[4],
            'longitude': row[5]
        } for row in subset
    ]

# ---------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data_api():
    try:
        all_rows = get_all_rows()
        samples = generate_raw_sample_subset(all_rows, N=100)
        with_velocity = compute_velocity(samples)
        gps_points = get_last_20_gps(all_rows, n=20)
        return jsonify({"samples": with_velocity, "gps": gps_points, "mode": "live"})
    except Exception as e:
        print("Error in /data endpoint:", e)
        return jsonify({"error": str(e), "samples": [], "gps": []})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
