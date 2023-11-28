from flask import Flask, request, jsonify
import logging
import threading
import time
from pushbullet import Pushbullet

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='status_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

# Initialize a variable to store the last heartbeat time ee
last_heartbeat_time = time.time()
heartbeat_lock = threading.Lock()
heartbeat_event = threading.Event()

# Threshold for considering a client offline (in seconds)
offline_threshold = 120

# Pushbullet Api Key
pushbullet_api_key = 'o.Cl5Zbi4nTU9uUlOPYB82bIbRHmVYbRwi'


@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    global last_heartbeat_time
    client_id = request.headers.get('Client-ID')
    client_ip = request.remote_addr

    if client_id:
        # Update last heartbeat time and elapsed time
        # elapsed_time = time.time() - last_heartbeat_time
        last_heartbeat_time = time.time()

        # Log the heartbeat
        logging.info(f"Heartbeat from Client ID: {client_id} , with ip: {client_ip}")
        '''if not hawkeye:
            hawkeye = True
            if elapsed_time < 300:
                title = "Hawkeye is up!"
                body = f"Possible short power outage. Seconds taken {elapsed_time}."
                send_pushbullet_not(title, body)
            else:
                title = "Hawkeye is up!"
                body = f"Hawkeye back online after {elapsed_time} seconds."
                send_pushbullet_not(title, body)'''

        return 'OK', 200
    else:
        # Handle regular GET requests
        return jsonify({'error': 'Invalid request'}), 400


def check_heartbeat():
    global last_heartbeat_time

    while True:
        # Wait for the event to be set (allowing the function to run)
        logging.info("Before waiting for heartbeat event")
        heartbeat_event.wait()
        logging.info("After waiting for heartbeat event")
        # Reset the event to not run the function until set again
        heartbeat_event.clear()
        time.sleep(60)  # Check every minute
        with heartbeat_lock:
            elapsed_time = time.time() - last_heartbeat_time
            if elapsed_time > offline_threshold:
                # Perform the action for an offline client
                logging.warning(f"More than {offline_threshold} seconds passed since last heartbeat.")
                title = "Hawkeye is down!"
                body = "Take immediate action."
                send_pushbullet_not(title, body)
            # elif elapsed_time <= offline_threshold:


# Start the background thread to check for heartbeat
heartbeat_thread = threading.Thread(target=check_heartbeat)
heartbeat_thread.start()


def send_pushbullet_not(title, body):
    pb = Pushbullet(pushbullet_api_key)
    pb.push_note(title, body)
    logging.warning(f"Send via Pushbullet. {title} {body}")


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
    heartbeat_event.set()
    app.run(host='0.0.0.0', port=5000)
