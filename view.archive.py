from flask import Flask, jsonify, render_template, request
import sqlite3
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def archive_data():
    try:
        db_path = request.args.get('db', 'telemetry.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        c = conn.cursor()

        c.execute('SELECT timestamp, altitude, temperature, acceleration, latitude, longitude FROM telemetry ORDER BY timestamp ASC')
        rows = c.fetchall()
        conn.close()

        if not rows:
            return jsonify({"samples": [], "gps": [], "mode": "archive"})

        min_altitude = min([r[1] for r in rows if r[1] is not None] or [0])

        samples = []
        for r in rows:
            t = r[0]
            alt = r[1] - min_altitude if r[1] is not None else None
            samples.append({
                'timestamp': t,
                'altitude': alt,
                'temperature': r[2],
                'acceleration': r[3]
            })

        # Add velocity
        for i in range(1, len(samples)):
            prev = samples[i - 1]
            curr = samples[i]
            if all(k in prev and k in curr for k in ('altitude', 'timestamp')) and None not in (prev['altitude'], curr['altitude']):
                dt = curr['timestamp'] - prev['timestamp']
                if dt > 0:
                    curr['velocity'] = (curr['altitude'] - prev['altitude']) / dt
                else:
                    curr['velocity'] = None
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
        print("[ERROR] Failed to read archive data:", e)
        return jsonify({"error": str(e), "samples": [], "gps": [], "mode": "archive"})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)
