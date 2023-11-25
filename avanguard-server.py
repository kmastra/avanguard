from flask import Flask, request, jsonify
import logging
import threading
import time
from telegram import Bot

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='status_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

# Initialize a variable to store the last heartbeat time
last_heartbeat_time = None
heartbeat_lock = threading.Lock()

# Threshold for considering a client offline (in seconds)
offline_threshold = 120

# Telegram Bot Token
telegram_bot_token = '6812967181:AAGPOZxXMm5zkw49EFJx5eKLSsjNuobXkC8'
chat_id = '5881099950'  # Your personal chat ID or a group chat ID

bot = Bot(token=telegram_bot_token)


@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    global last_heartbeat_time
    client_id = request.headers.get('Client-ID')
    client_ip = request.remote_addr

    if client_id:
        # Update last heartbeat time
        last_heartbeat_time = time.time()

        # Log the heartbeat
        log_message = f"Heartbeat from Client ID: {client_id} , with ip: {client_ip}"
        logging.info(log_message)

        return 'OK', 200
    else:
        # Handle regular GET requests
        return jsonify({'error': 'Invalid request'}), 400


def check_heartbeat():
    global last_heartbeat_time
    while True:
        time.sleep(60)  # Check every minute
        with heartbeat_lock:
            if last_heartbeat_time is not None:
                elapsed_time = time.time() - last_heartbeat_time
                if elapsed_time > offline_threshold:
                    # Perform the action for an offline client
                    action_for_offline_client()
                    last_heartbeat_time = None  # Reset the last heartbeat time

# Start the background thread to check for heartbeat
heartbeat_thread = threading.Thread(target=check_heartbeat)
heartbeat_thread.start()


def action_for_offline_client():
    # This is where you define the action to be taken for an offline client
    # For example, send a notification, update a database, etc.
    logging.warning("Action taken for an offline client")

    # Send a Telegram notification
    message = "⚠️ Client is offline! Please check."
    send_telegram_message(message)


def send_telegram_message(message):
    bot.send_message(chat_id=chat_id, text=message)


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
