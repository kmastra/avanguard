from flask import Flask, request, jsonify
import logging
import threading
import time
from datetime import timedelta, datetime
from pushbullet import Pushbullet
import configparser

# Initialize Flask app
app = Flask(__name__)

# Read configuration from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Configure logging
logging.basicConfig(filename='status_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

# Initialize variables for heartbeat and offline detection
heartbeat_lock = threading.Lock()
last_heartbeat_time = time.time()
offline_threshold = int(config['Server']['offline_threshold'])
offline = False
failed_heartbeat_time = time.time()

# Pushbullet Api Key
pushbullet_api_key = config['Server']['pushbullet_api_key']


@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    global last_heartbeat_time, offline, failed_heartbeat_time
    client_id = request.headers.get('Client-ID')
    client_ip = request.remote_addr

    if client_id:
        # Update last heartbeat time and elapsed time
        last_heartbeat_time = time.time()
        elapsed_time = time.time() - last_heartbeat_time

        # Log the heartbeat
        logging.info(f"Heartbeat from Client ID: {client_id} , with IP: {client_ip}")

        if elapsed_time <= offline_threshold and offline:
            offline = False
            temp_time = time.time() - failed_heartbeat_time
            downtime = str(timedelta(seconds=temp_time)).split(".")[0]

            if temp_time < 300:
                # Log and notify for a short power outage
                logging.info(f"Hawkeye back up after {downtime}. Possible short power outage.")
                title = "Hawkeye is up!"
                body = f"Possible short power outage. Time taken {downtime}."
                send_pushbullet_not(title, body)
            else:
                # Log and notify for normal downtime
                logging.info(f"Hawkeye back up after {downtime}.")
                title = "Hawkeye is up!"
                body = f"Hawkeye back online after {downtime}."
                send_pushbullet_not(title, body)

        return 'OK', 200
    else:
        # Handle regular GET requests
        return jsonify({'error': 'Invalid request'}), 400


def check_heartbeat():
    global offline, failed_heartbeat_time
    while True:
        time.sleep(60)  # Check every minute
        with heartbeat_lock:
            elapsed_time = time.time() - last_heartbeat_time

            if elapsed_time > offline_threshold:
                offline = True
                failed_heartbeat_time = last_heartbeat_time
                downtime = str(timedelta(seconds=elapsed_time)).split(".")[0]

                # Perform the action for an offline client
                logging.warning(f"More than {offline_threshold} seconds passed since last heartbeat.")
                title = "Hawkeye is down!"
                body = f"Downtime: {downtime}"
                send_pushbullet_not(title, body)


# Start the background thread to check for heartbeat
heartbeat_thread = threading.Thread(target=check_heartbeat)
heartbeat_thread.start()


def send_pushbullet_not(title, body):
    pb = Pushbullet(pushbullet_api_key)
    pb.push_note(title, body)
    logging.warning(f'Send via Pushbullet. "{title} {body}"')


@app.route('/')
def display_log():
    # Read and display the content of the status log
    try:
        with open('status_log.txt', 'r') as log_file:
            log_content = log_file.read().replace('\n', '<br>')
        return f"<html><body>{log_content}</body></html>"
    except FileNotFoundError:
        return 'Status log not found'


if __name__ == '__main__':
    # Log the start of the script
    logging.info(f"Script started at {datetime.now()}")
    app.run(host='0.0.0.0', port=5000)
