import socket
import hmac
import hashlib
import logging
import threading
import time
import asyncio
from datetime import timedelta, datetime
from pushbullet import Pushbullet
import configparser
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

config = configparser.ConfigParser()
config.read('config.ini')
logging.basicConfig(filename='status_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')


heartbeat_lock = threading.Lock()
telegram_lock = threading.Lock()
tcp_server_lock = threading.Lock()
last_heartbeat_time = time.time()
offline_threshold = int(config['Server']['offline_threshold'])
offline = False
failed_heartbeat_time = time.time()
secret_key = config['Key']['secret_key'].encode()
pushbullet_api_key = config['Server']['pushbullet_api_key']
telegram_bot_token = config['Server']['telegram_bot_token']
telegram_id = config['Server']['telegram_id_to_notify']
TIME_LIMIT = 10
snooze_start_time = None
snooze_duration = 0


def validate_heartbeat(data):
    try:
        # Split the message into components
        _, timestamp, received_hmac = data.decode().split(":")
        
        # Recreate the message to validate HMAC
        message = f'heartbeat:{timestamp}'.encode()
        calculated_hmac = hmac.new(secret_key, message, hashlib.sha256).hexdigest()
        
        # Validate HMAC and timestamp
        if hmac.compare_digest(calculated_hmac, received_hmac) and (time.time() - float(timestamp)) < TIME_LIMIT:
            return True
        else:
            return False
    except (ValueError, TypeError):

        return False


def start_server():
    global last_heartbeat_time, offline, failed_heartbeat_time

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 5000))
    server_socket.listen(1)
    logging.info(f"Server is listening for heartbeats...")

    while True:
        with tcp_server_lock:
            try:
                client_socket, address = server_socket.accept()
                logging.warning(f"Connection from {address}.")

                data = client_socket.recv(1024)
                if data:
                    if validate_heartbeat(data):
                        logging.info("Valid heartbeat received.")

                        # Update last heartbeat time and elapsed time
                        elapsed_time = time.time() - last_heartbeat_time
                        last_heartbeat_time = time.time()
                        
                        # Log the heartbeat
                        logging.info(f"Heartbeat from IP: {address}.")

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
                                #send_telegram_not(f'{title} {body}')
                            else:
                                # Log and notify for normal downtime
                                logging.info(f"Hawkeye back up after {downtime}.")
                                title = "Hawkeye is up!"
                                body = f"Hawkeye back online after {downtime}."
                                send_pushbullet_not(title, body)
                                #send_telegram_not(f'{title} {body}')
                    else:
                        logging.warning("Invalid or outdated heartbeat received")

            except socket.error as e:
                logging.error(f"Socket error: {e}")
            finally:
                if client_socket:
                    client_socket.close()


tcp_server_thread = threading.Thread(target=start_server)
tcp_server_thread.start()


def check_heartbeat():
    global offline, failed_heartbeat_time
    while True:
        time.sleep(60)
        with heartbeat_lock:
            elapsed_time = time.time() - last_heartbeat_time

            if elapsed_time > offline_threshold:
                offline = True
                failed_heartbeat_time = last_heartbeat_time
                downtime = str(timedelta(seconds=elapsed_time)).split(".")[0]

                logging.warning(f"More than {offline_threshold} seconds passed since last heartbeat.")
                if should_send_notification:
                    title = "Hawkeye is down!"
                    body = f"Downtime: {downtime}"
                    send_pushbullet_not(title, body)
                    #send_telegram_not(f'{title} {body}')


heartbeat_thread = threading.Thread(target=check_heartbeat)
heartbeat_thread.start()


def send_pushbullet_not(title, body):
    pb = Pushbullet(pushbullet_api_key)
    pb.push_note(title, body)
    logging.warning(f'Send via Pushbullet. "{title} {body}"')


async def send_telegram_not(text):
    bot = Bot(telegram_bot_token)
    await bot.send_message(chat_id=telegram_id, text=text)
    logging.warning(f'Send via Telegram. "{text}"')


async def snooze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global snooze_start_time, snooze_duration
    
    try:
        duration = int(context.args[0]) if len(context.args) > 0 else None
        if duration is None or not (5 <= duration <= 36000):
            raise ValueError("Invalid duration")
        
        snooze_start_time = int(time.time())
        snooze_duration = duration
        await update.message.reply_text(f"Notifications snoozed for {duration} seconds.")

    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /snooze <seconds> (between 5 and 36000)")


def should_send_notification():
    if snooze_start_time is not None:
        elapsed_time = int(time.time()) - snooze_start_time
        if elapsed_time < snooze_duration:
            return False
    return True


def start_telegram_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = Application.builder().token(telegram_bot_token).build()
    application.add_handler(CommandHandler("snooze", snooze))
    application.run_polling()

    asyncio.run(run())

def main():
    start_telegram_bot()

if __name__ == '__main__':
    main()
    