import hmac
import hashlib
import logging
import time
import asyncio
from datetime import timedelta
from pushbullet import Pushbullet
import configparser
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

config = configparser.ConfigParser()
config.read('config.ini')
logging.basicConfig(filename='status_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')
logging.getLogger('telegram').setLevel(logging.WARNING)
last_heartbeat_time = time.time()
offline_threshold = int(config['Server']['offline_threshold'])
offline = False
failed_heartbeat_time = time.time()
secret_key = config['Key']['secret_key'].encode()
enable_pushbullet = config['Server']['pushbullet_notification']
pushbullet_api_key = config['Server']['pushbullet_api_key']
telegram_bot_token = config['Server']['telegram_bot_token']
telegram_id = config['Server']['telegram_id_to_notify']
TIME_LIMIT = 10
snooze_start_time = None
snooze_duration = 0


async def send_notification(title, body):
    if should_send_notification():
        if enable_pushbullet:
            send_pushbullet_not(title, body)
        await send_telegram_not(f'{title} {body}')
        logging.warning(f'Sent notification: "{title} {body}"')
    else:
        logging.info(f'Notification "{title} {body}" snoozed, not sent.')


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
            logging.warning(f"Failed heartbeat validation - HMAC or timestamp mismatch.")
            return False
    except ValueError as ve:
        logging.error(f"ValueError in validate_heartbeat: {ve} - Data received: {data}")
    except TypeError as te:
        logging.error(f"TypeError in validate_heartbeat: {te} - Data received: {data}")
    except Exception as e:
        logging.error(f"Unexpected error in validate_heartbeat: {e} - Data received: {data}")
    
    return False


async def start_server():
    server = await asyncio.start_server(handle_client, '0.0.0.0', 5000)
    logging.info(f"Server started and is listening for heartbeats...")

    async with server:
        await server.serve_forever()


async def handle_client(reader, writer):
    global last_heartbeat_time, offline, failed_heartbeat_time

    address = writer.get_extra_info('peername')
    logging.warning(f"Connection from {address}.")
    
    data = await reader.read(1024)
    if data and validate_heartbeat(data):
        logging.info("Valid heartbeat received from IP: {address}")

        # Update last heartbeat time and check elapsed time
        elapsed_time = time.time() - last_heartbeat_time
        last_heartbeat_time = time.time()

        if elapsed_time >= offline_threshold and offline:
            offline = False
            temp_time = time.time() - failed_heartbeat_time
            downtime = str(timedelta(seconds=temp_time)).split(".")[0]

            if temp_time < 300:
                # Log and notify for a short power outage
                logging.info(f"Hawkeye back up after {downtime}. Possible short power outage.")
                send_notification("Hawkeye is up!", f"Possible short power outage. Time taken {downtime}.")
            else:
                # Log and notify for normal outage
                logging.info(f"Hawkeye back up after {downtime}.")
                send_notification("Hawkeye is up!", f"Hawkeye back online after {downtime}.")

    writer.close()
    await writer.wait_closed()


async def check_heartbeat():
    global offline, failed_heartbeat_time
    logging.info(f"Heartbeat watchdog started...")
    while True:
        await asyncio.sleep(60)
        elapsed_time = time.time() - last_heartbeat_time

        if elapsed_time > offline_threshold:
            offline = True
            failed_heartbeat_time = last_heartbeat_time
            downtime = str(timedelta(seconds=elapsed_time)).split(".")[0]

            logging.warning(f"More than {offline_threshold} seconds passed since last heartbeat.")
            send_notification("Hawkeye is down!", f"Downtime: {downtime}")


def send_pushbullet_not(title, body):
    pb = Pushbullet(pushbullet_api_key)
    pb.push_note(title, body)
    logging.warning(f'Send via Pushbullet. "{title} {body}"')


async def send_telegram_not(text):
    bot = Bot(telegram_bot_token)
    try:
        await bot.send_message(chat_id=telegram_id, text=text)
        logging.warning(f'Send via Telegram. "{text}"')
    except Exception as e:
        logging.error(f"Failed to send Telegram notification: {e}")


async def telegram_check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_heartbeat_time, offline, snooze_start_time, snooze_duration, offline_threshold

    if last_heartbeat_time is None:
        await update.message.reply_text("No heartbeat has been received yet.")

    else:
        current_time = int(time.time())
        elapsed_time = current_time - last_heartbeat_time
        downtime = str(timedelta(seconds=elapsed_time)).split(".")[0]
        status = "Online" if not offline else "Offline"

        await update.message.reply_text(f"Hawkeye is currently {status} with a threshold of {offline_threshold} seconds.\nLast heartbeat was {downtime} ago.")

        if snooze_start_time is not None:
            snooze_elapsed_time = current_time - snooze_start_time
            if snooze_elapsed_time < snooze_duration:
                await update.message.reply_text(f"Notifications are currently snoozed for {snooze_duration - snooze_elapsed_time} seconds more.")      


async def telegram_snooze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global snooze_start_time, snooze_duration
    
    try:
        if len(context.args) > 0 and context.args[0].lower() == "disable":
            snooze_start_time = None
            snooze_duration = 0
            await update.message.reply_text("Snooze has been disabled. Notifications will resume.")
            return
        
        # Parse duration from the command arguments
        duration = int(context.args[0]) if len(context.args) > 0 else None
        if duration is None or not (5 <= duration <= 36000):
            raise ValueError("Invalid duration")
        
        # Check if a snooze is already active and if it is extent it
        current_time = int(time.time())
        if snooze_start_time is None or (current_time - snooze_start_time) >= snooze_duration:
            snooze_start_time = current_time
            snooze_duration = duration
            await update.message.reply_text(f"Notifications snoozed for {duration} seconds.")
        else:
            elapsed_time = current_time - snooze_start_time
            snooze_duration = snooze_duration - elapsed_time + duration
            snooze_start_time = current_time  # Reset start time to now
            await update.message.reply_text(
                f"Snooze already active. Extending snooze by {duration} seconds. Total snooze time is now {snooze_duration} seconds."
            )

    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /snooze <seconds> (between 5 and 36000) or /snooze disable.")


async def telegram_view_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        lines = int(context.args[0]) if len(context.args) > 0 else 10
        if not (0 <= lines <= 50):
            raise ValueError("Invalid lines count")
        
        with open('status_log.txt', 'r') as log_file:
            lines = log_file.readlines()[-lines:]
            log_text = ''.join(lines)

        await update.message.reply_text(f"Recent logs:\n{log_text}")
    except FileNotFoundError:
        await update.message.reply_text("Log file not found.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /view_logs <seconds> (between 0 and 50).")


async def telegram_set_offile_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global offline_threshold
    try:
        new_threshold = int(context.args[0])
        offline_threshold = new_threshold
        await update.message.reply_text(f"Offline threshold set to {new_threshold} seconds.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /set_threshold <seconds>")


async def telegram_show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Available commands:\n\n"
        "/snooze <seconds> - Snooze notifications for a specified time (between 5 and 36000 seconds).\n"
        "/status - Check if Hawkeye is currently online or offline and the time since the last heartbeat.\n"
        "/set_threshold <seconds> - Set the offline threshold duration in seconds.\n"
        "/extend_snooze <additional_seconds> - Extend the snooze duration by a specified amount of time.\n"
        "/view_logs - View the last 10 lines of the log file for recent events.\n"
        "/help - Show this help message with all available commands.\n"
    )
    await update.message.reply_text(help_text)


def should_send_notification():
    global snooze_start_time, snooze_duration
    if snooze_start_time is not None:
        elapsed_time = int(time.time()) - snooze_start_time
        if elapsed_time < snooze_duration:
            return False
    return True


async  def start_telegram_bot():
    application = Application.builder().token(telegram_bot_token).build()
    application.add_handler(CommandHandler("help", telegram_show_help))
    application.add_handler(CommandHandler("snooze", telegram_snooze))
    application.add_handler(CommandHandler("status", telegram_check_status))
    application.add_handler(CommandHandler("set_threshold", telegram_set_offile_threshold))
    application.add_handler(CommandHandler("view_logs", telegram_view_logs))

    logging.info("Starting Telegram bot...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logging.info("Stopping Telegram bot...")
        await application.stop()

async def main():
    await asyncio.gather(start_server(), check_heartbeat(), start_telegram_bot())

if __name__ == '__main__':
    asyncio.run(main())
    