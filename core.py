import subprocess
import time
from datetime import datetime
import os
import shutil

LOG_FILE = "core_supervisor.log"
ARCHIVE_DIR = "archive"
DB_FILE = "telemetry.db"


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")


def archive_db():
    if os.path.exists(DB_FILE):
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive_path = os.path.join(ARCHIVE_DIR, f"telemetry-{timestamp}.db")
        shutil.move(DB_FILE, archive_path)
        log(f"Archived existing DB to {archive_path}")
    else:
        log("No telemetry.db found — starting fresh.")


def start_process(name, cmd):
    log(f"Starting {name} with command: {cmd}")
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def monitor():
    archive_db()

    processes = {
        "serial_logger": start_process("serial_logger", ["python", "serial_logger.py"]),
        "app": start_process("app", ["python", "app.py"]),
    }

    while True:
        for name, proc in processes.items():
            ret = proc.poll()
            if ret is not None:
                log(f"{name} exited with code {ret}. Restarting...")
                out, _ = proc.communicate()
                if out:
                    log(f"{name} output before crash:\n{out}")
                processes[name] = start_process(name, ["python", f"{name}.py"])
        time.sleep(2)


if __name__ == "__main__":
    log("Core supervisor starting up...")
    monitor()
