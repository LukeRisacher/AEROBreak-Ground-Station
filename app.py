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
# Compute "velocity" (ft/s) from altitude changes using a wider window
# ---------------------------------------------------------------------
def compute_velocity(samples, window=5):
    if len(samples) < 2:
        return samples

    samples[0]['velocity'] = 0  # Set v0 = 0 explicitly

    for i in range(1, len(samples)):
        if i < window:
            samples[i]['velocity'] = None
            continue

        curr = samples[i]
        prev = samples[i - window]

        alt1 = curr.get('altitude')
        alt0 = prev.get('altitude')
        t1 = curr.get('timestamp')
        t0 = prev.get('timestamp')

        if None not in (alt0, alt1, t0, t1) and t1 > t0:
            curr['velocity'] = (alt1 - alt0) / (t1 - t0)
        else:
            curr['velocity'] = None

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
