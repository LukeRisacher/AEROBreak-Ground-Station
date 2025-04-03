import subprocess
import time
import logging
import signal
import os
import shutil
from datetime import datetime

# Hardcoded configuration for the launch system
LOG_FILE = "core_supervisor.log"
ARCHIVE_DIR = "archive"
DB_FILE = "telemetry.db"

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# Dictionary to keep track of running processes
processes = {}

def archive_db():
    """
    Archive the existing telemetry database if it exists,
    so that each launch starts with a fresh DB.
    """
    if os.path.exists(DB_FILE):
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        archive_path = os.path.join(ARCHIVE_DIR, f"telemetry-{timestamp}.db")
        shutil.move(DB_FILE, archive_path)
        logging.info(f"Archived existing DB to {archive_path}")
    else:
        logging.info("No telemetry.db found — starting fresh.")

def start_process(name, cmd):
    """
    Start a subprocess with the given command.
    Logs the event and returns the process object.
    """
    logging.info(f"Starting {name} with command: {cmd}")
    try:
        # Use DEVNULL to avoid blocking on output buffering.
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        return proc
    except Exception as e:
        logging.error(f"Failed to start process {name}: {e}")
        return None

def stop_all_processes():
    """
    Terminate all running subprocesses gracefully.
    """
    logging.info("Shutting down all processes...")
    for name, proc in processes.items():
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=10)
                logging.info(f"Process {name} terminated.")
            except Exception as e:
                logging.error(f"Error terminating process {name}: {e}")

def signal_handler(sig, frame):
    """
    Handle termination signals to gracefully shutdown the supervisor.
    """
    logging.info("Received shutdown signal. Exiting...")
    stop_all_processes()
    exit(0)

def monitor():
    """
    Monitor the subprocesses. If any process exits unexpectedly,
    log its output and restart it.
    """
    archive_db()

    # Start initial processes
    processes["serial_logger"] = start_process("serial_logger", ["python", "serial_logger.py"])
    processes["app"] = start_process("app", ["python", "app.py"])

    # Main monitoring loop
    while True:
        for name, proc in list(processes.items()):
            ret = proc.poll()
            if ret is not None:
                logging.warning(f"{name} exited with code {ret}. Restarting...")
                # Restart the process without waiting for buffered output (since we now discard it)
                new_proc = start_process(name, ["python", f"{name}.py"])
                if new_proc:
                    processes[name] = new_proc
                else:
                    logging.error(f"Failed to restart process {name}.")
        time.sleep(2)

if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logging.info("Core supervisor starting up...")
    monitor()
