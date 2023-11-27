from flask import Flask, request, jsonify
import logging
import threading
import time
from pushbullet import Pushbullet

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='status_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

# Initialize a variable to store the last heartbeat time
elapsed_time = 1
last_heartbeat_time = time.time()
heartbeat_lock = threading.Lock()

# Threshold for considering a client offline (in seconds)
offline_threshold = 120

# Pushbullet Api Key
pushbullet_api_key = 'o.Cl5Zbi4nTU9uUlOPYB82bIbRHmVYbRwi'

# Initialize a variable to save the state of Clients
hawkeye = False


# Telegram Bot Token
# telegram_bot_token = '6812967181:AAGPOZxXMm5zkw49EFJx5eKLSsjNuobXkC8'
# telegram_chat_id  = '5881099950'  # Your personal chat ID or a group chat ID


@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    global hawkeye
    global last_heartbeat_time
    client_id = request.headers.get('Client-ID')
    client_ip = request.remote_addr

    if client_id:
        # Update last heartbeat time
        last_heartbeat_time = time.time()

        # Log the heartbeat
        logging.info(f"Heartbeat from Client ID: {client_id} , with ip: {client_ip}")
        if hawkeye == False:
            hawkeye = True
            if elapsed_time < 300:
                title = "Hawkeye is up!"
                body = f"Possible short power outage. Seconds taken {elapsed_time}."
                send_pushbullet_not(title, body)
            else:
                title = "Hawkeye is up!"
                body = f"Hawkeye back online after {elapsed_time} seconds."
                send_pushbullet_not(title, body)

        return 'OK', 200
    else:
        # Handle regular GET requests
        return jsonify({'error': 'Invalid request'}), 400


def check_heartbeat():
    global last_heartbeat_time
    global elapsed_time
    global hawkeye
    while True:
        time.sleep(60)  # Check every minute
        with heartbeat_lock:
            if last_heartbeat_time is not None:
                elapsed_time = time.time() - last_heartbeat_time
                if elapsed_time > offline_threshold:
                    # Perform the action for an offline client
                    logging.warning(f"More than {offline_threshold} seconds passed since last heartbeat.")
                    hawkeye = False
                    title = "Hawkeye is down!"
                    body = "Take immediate action."
                    send_pushbullet_not(title, body)


# Start the background thread to check for heartbeat
heartbeat_thread = threading.Thread(target=check_heartbeat)
heartbeat_thread.start()


def send_pushbullet_not(title, body):
    pb = Pushbullet(pushbullet_api_key)
    pb.push_note(title, body)
    logging.warning(f"Send via Pushbullet. {title} {body}")


'''def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{telegram_bot_token}/sendMessage'
    params = {'chat_id': telegram_chat_id, 'text': message}
    response = requests.post(url, params=params)
    return response.json()'''


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
