import sqlite3
from flask import Flask, jsonify, render_template

app = Flask(__name__)
DATABASE = 'telemetry.db'

# ---------------------------------------------------------------------
# Helper: Read ALL rows in ascending timestamp
# ---------------------------------------------------------------------
def get_all_rows():
    """
    Grabs all rows from 'telemetry' sorted ascending by timestamp.
    Each row: (timestamp, altitude, temperature, acceleration, latitude, longitude)
    """
    conn = sqlite3.connect(DATABASE)
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
# Linear interpolation helper
# ---------------------------------------------------------------------
def linear_interpolate(t, t0, v0, t1, v1):
    """
    Returns linearly interpolated value at time t,
    given (t0, v0) and (t1, v1).
    If v0 or v1 is None, returns None.
    If t0 == t1, returns v0.
    """
    if v0 is None or v1 is None:
        return None
    dt = (t1 - t0)
    if dt == 0:
        return v0
    frac = (t - t0) / dt
    return v0 + (v1 - v0) * frac

# ---------------------------------------------------------------------
# Create "samples" for altitude, temperature, acceleration
# If the DB has <= N rows, return them directly (no interpolation).
# If > N rows, linearly interpolate to exactly N points.
# ---------------------------------------------------------------------
def generate_samples(all_rows, N=200):
    """
    Returns a list of dicts:
      {
        'timestamp': float,
        'altitude': float,
        'temperature': float,
        'acceleration': float
      }
    either directly from the DB rows if len(all_rows) <= N,
    or via interpolation (N points) if len(all_rows) > N.
    """
    count = len(all_rows)
    if count == 0:
        return []

    if count <= N:
        # No interpolation needed; just pass them through
        samples = []
        for row in all_rows:
            samples.append({
                'timestamp': row[0],
                'altitude': row[1],
                'temperature': row[2],
                'acceleration': row[3]
            })
        return samples

    # Otherwise, we have more rows than N -> do interpolation
    t0 = all_rows[0][0]
    tMax = all_rows[-1][0]
    if tMax == t0:
        # all data at same timestamp -> trivial
        row = all_rows[0]
        return [{
            'timestamp': t0,
            'altitude': row[1],
            'temperature': row[2],
            'acceleration': row[3]
        }]

    out = []
    idx = 0

    for i in range(N):
        # time for this sample
        t_sample = t0 + i * (tMax - t0) / (N - 1)

        # move idx so that all_rows[idx].t <= t_sample < all_rows[idx+1].t
        while (idx + 1 < count and all_rows[idx+1][0] <= t_sample):
            idx += 1

        if idx == count - 1:
            # last row
            row = all_rows[-1]
            out.append({
                'timestamp': t_sample,
                'altitude': row[1],
                'temperature': row[2],
                'acceleration': row[3]
            })
        else:
            # bracket
            tA, altA, tmpA, accA, _, _ = all_rows[idx]
            tB, altB, tmpB, accB, _, _ = all_rows[idx+1]

            alt = linear_interpolate(t_sample, tA, altA, tB, altB)
            tmp = linear_interpolate(t_sample, tA, tmpA, tB, tmpB)
            acc = linear_interpolate(t_sample, tA, accA, tB, accB)

            out.append({
                'timestamp': t_sample,
                'altitude': alt,
                'temperature': tmp,
                'acceleration': acc
            })
    return out

# ---------------------------------------------------------------------
# Compute "velocity" (ft/s) from altitude changes
# velocity = (alt[i] - alt[i-1]) / dt
# ---------------------------------------------------------------------
def compute_velocity(samples):
    """
    For consecutive samples, velocity = (alt[i] - alt[i-1]) / (t[i] - t[i-1]).
    If altitude is rising, velocity > 0. If falling, velocity < 0.
    """
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
def get_last_20_gps(all_rows, n=20):
    gps_rows = [r for r in all_rows if (r[4] is not None and r[5] is not None)]
    if not gps_rows:
        return []

    # last n in ascending order
    if len(gps_rows) <= n:
        subset = gps_rows
    else:
        subset = gps_rows[-n:]

    # convert to list of dict
    return [
        {
            'timestamp': row[0],
            'latitude': row[4],
            'longitude': row[5]
        }
        for row in subset
    ]

# ---------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')  # from templates folder

@app.route('/data')
def data_api():
    """
    1) Read all rows
    2) Generate samples (<= N => real points, else 200 interpolated)
    3) Compute velocity
    4) Grab last 20 GPS
    5) Return JSON: { "samples": [...], "gps": [...] }
    """
    all_rows = get_all_rows()
    samples = generate_samples(all_rows, N=200)
    with_velocity = compute_velocity(samples)
    gps_points = get_last_20_gps(all_rows, n=20)

    return jsonify({
        "samples": with_velocity,
        "gps": gps_points
    })

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
