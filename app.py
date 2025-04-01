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
# Hybrid downsample: bin older data, keep raw recent tail
# ---------------------------------------------------------------------
def hybrid_binned_downsample(rows, N=100):
    count = len(rows)
    if count == 0:
        return []

    bin_size = max(1, count // N)
    binned = []

    altitudes = [row[1] for row in rows if row[1] is not None]
    min_altitude = min(altitudes) if altitudes else 0

    for i in range(0, bin_size * N, bin_size):
        bin_rows = rows[i:i+bin_size]
        if not bin_rows:
            continue
        def avg(idx):
            vals = [r[idx] for r in bin_rows if r[idx] is not None]
            return sum(vals) / len(vals) if vals else None
        timestamp = bin_rows[len(bin_rows)//2][0]
        binned.append({
            'timestamp': timestamp,
            'altitude': (avg(1) - min_altitude) if avg(1) is not None else None,
            'temperature': avg(2),
            'acceleration': avg(3)
        })

    tail = rows[bin_size * N:]
    for row in tail:
        binned.append({
            'timestamp': row[0],
            'altitude': (row[1] - min_altitude) if row[1] is not None else None,
            'temperature': row[2],
            'acceleration': row[3]
        })

    return binned

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
# Return ALL valid GPS points
# ---------------------------------------------------------------------
def get_all_gps(rows):
    return [
        {
            'timestamp': row[0],
            'latitude': row[4],
            'longitude': row[5]
        }
        for row in rows if row[4] is not None and row[5] is not None
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
        samples = hybrid_binned_downsample(all_rows, N=100)
        with_velocity = compute_velocity(samples)
        gps_points = get_all_gps(all_rows)
        return jsonify({"samples": with_velocity, "gps": gps_points, "mode": "live"})
    except Exception as e:
        print("Error in /data endpoint:", e)
        return jsonify({"error": str(e), "samples": [], "gps": []})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
