import subprocess
import time
import sys

def start_processes():
    # Launch the serial logger process.
    serial_logger = subprocess.Popen([sys.executable, "serial_logger.py"])
    print(f"Started serial_logger.py with PID {serial_logger.pid}")

    # Launch the Flask app process.
    flask_app = subprocess.Popen([sys.executable, "app.py"])
    print(f"Started app.py with PID {flask_app.pid}")

    return serial_logger, flask_app

def main():
    serial_logger, flask_app = start_processes()

    try:
        while True:
            # Check if the serial logger has stopped.
            if serial_logger.poll() is not None:
                print("serial_logger.py has stopped. Restarting it...")
                serial_logger = subprocess.Popen([sys.executable, "serial_logger.py"])
                print(f"Restarted serial_logger.py with PID {serial_logger.pid}")

            # Check if the Flask app has stopped.
            if flask_app.poll() is not None:
                print("app.py has stopped. Restarting it...")
                flask_app = subprocess.Popen([sys.executable, "app.py"])
                print(f"Restarted app.py with PID {flask_app.pid}")

            time.sleep(1)
    except KeyboardInterrupt:
        print("Keyboard interrupt received, terminating processes...")
        serial_logger.terminate()
        flask_app.terminate()
        serial_logger.wait()
        flask_app.wait()
        print("Both processes terminated.")

if __name__ == "__main__":
    main()
