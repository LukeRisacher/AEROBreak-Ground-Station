import subprocess
import time
from datetime import datetime
import os

LOG_FILE = "core_supervisor.log"


def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(f"[{timestamp}] {msg}")


def start_process(name, cmd):
    log(f"Starting {name} with command: {cmd}")
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def monitor():
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
