from flask import Flask, request, jsonify
import logging
import datetime
from threading import Timer

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='status_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

# Initialize last heartbeat time
last_heartbeat_time = datetime.datetime.now()

@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    global last_heartbeat_time
    client_id = request.headers.get('Client-ID')
    client_ip = request.remote_addr

    if client_id:
        # Get current time in a variable
        current_time = datetime.datetime.now().strftime("%d-%m %H:%M:%S")

        # Update last heartbeat time
        last_heartbeat_time = datetime.datetime.now()

        # Log the heartbeat
        log_message = f"Heartbeat received from Client ID: {client_id} , with ip: {client_ip} at {current_time}"
        logging.info(log_message)

        return 'OK', 200
    else:
        # Handle regular GET requests
        return jsonify({'error': 'Invalid request'}), 400


def check_heartbeat_timeout():
    global last_heartbeat_time
    current_time = datetime.datetime.now()
    timeout_threshold = datetime.timedelta(minutes=2)

    time_since_last_heartbeat = current_time - last_heartbeat_time
    time_until_next_execution = max(0, 60 - time_since_last_heartbeat.total_seconds())

    if time_since_last_heartbeat > timeout_threshold:
        # Take action when timeout threshold is exceeded
        logging.warning(f"Heartbeat timeout! No heartbeat received for more than 2 minutes. Start the alarm.")

    # Reschedule the timer with the time until the next execution
    timer = Timer(time_until_next_execution, check_heartbeat_timeout)
    timer.daemon = True
    timer.start()

@app.route('/')
def display_log():
    # Read and display the content of the status log
    try:
        with open('status_log.txt', 'r') as log_file:
            log_content = log_file.read().replace('\n', '<br>')
        return f"<html><body>{log_content}</body></html>"
    except FileNotFoundError:
        return 'Status log not found'


'''@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()

    if 'ip' in data and 'status' in data:
        ip = data['ip']
        status = data['status']

        # Log the status update
        log_message = f"Received status update: {ip} {'is online' if status else 'is offline'}"
        logging.info(log_message)

        return jsonify({'message': 'Status updated successfully'})
    else:
        return jsonify({'error': 'Invalid data format'}), 400'''


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
