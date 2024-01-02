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
            log_content = log_file.readlines()

        # Get the page number from the request or default to 1
        page_number = int(request.args.get('page', 1))
        lines_per_page = 1000  # Adjust the number of lines per page as needed

        # Reverse the order of lines to show the most recent entries first
        log_content.reverse()

        # Calculate the total number of pages
        total_pages = (len(log_content) + lines_per_page - 1) // lines_per_page

        # Calculate the start and end indices for the current page
        start_index = (page_number - 1) * lines_per_page
        end_index = start_index + lines_per_page

        # Extract the lines for the current page
        current_page = log_content[start_index:end_index]

        # Build the HTML response with basic styling
        response_html = """
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                }
                .log-entry {
                    margin-bottom: 8px;
                }
                .navigation {
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
        """

        response_html += "<h1>Status Log</h1>"

        for entry in current_page:
            response_html += f"<div class='log-entry'>{entry}</div>"

        # Add navigation buttons
        prev_page = max(1, page_number - 1)
        next_page = min(total_pages, page_number + 1)

        first_page = 1
        last_page = total_pages

        nearest_pages = [max(1, page_number - i) for i in range(5, 0, -1)] + [min(total_pages, page_number + i) for i in range(1, 6)]

        navigation_buttons = f"""
            <div class='navigation'>
                <a href="?page={first_page}">First</a> | 
                <a href="?page={prev_page}">Previous</a> | 
                {' | '.join(f'<a href="?page={page}">{page}</a>' for page in nearest_pages)} |
                <a href="?page={next_page}">Next</a> | 
                <a href="?page={last_page}">Last</a>
            </div>
        """

        response_html += navigation_buttons

        response_html += """
        </body>
        </html>
        """

        return response_html
    except FileNotFoundError:
        return 'Status log not found'


if __name__ == '__main__':
    # Log the start of the script
    logging.info(f"Script started at {datetime.now()}")
    app.run(host='0.0.0.0', port=5000)
