from flask import Flask, request, jsonify
import logging
import datetime

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='status_log.txt', level=logging.INFO)


@app.route('/heartbeat', method['GET'])
def heartbeat():
    client_id = request.headers.get('Client-ID')
    if client_id:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Log the heartbeat
        log_message = f"Heartbeat received from Client ID: {client_id} at {current_time}"
        logging.info(log_message)

        return 'OK', 200
    else:
        # Handle regular GET requests
        return jsonify({'error': 'Invalid request'}), 400


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
