import os
import hmac
import hashlib
import logging
import time
import asyncio
from datetime import timedelta
from pushbullet import Pushbullet
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

# Load configuration settings from .env
server_ip = os.getenv('SERVER_IP')
server_port = int(os.getenv('SERVER_PORT'))
offline_threshold = int(os.getenv('OFFLINE_THRESHOLD'))
secret_key = os.getenv('SECRET_KEY').encode()
pushbullet_use = os.getenv('PUSHBULLET_NOTIFICATION')
pushbullet_api_key = os.getenv('PUSHBULLET_API_KEY')
telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
telegram_id_to_notify = os.getenv('TELEGRAM_ID_TO_NOTIFY')

# Set up basic logging configuration
logging.basicConfig(filename='server_log.txt',
                    level=logging.INFO, format='%(asctime)s - %(message)s')
logging.getLogger('httpx').setLevel(
    logging.WARNING)  # To avoid clutter in logs

# Initialize variables for tracking heartbeats and system status
last_heartbeat_time = time.time()
offline = False
failed_heartbeat_time = time.time()
TIME_LIMIT = 10
snooze_start_time = None
snooze_duration = 0


async def send_notification(title: str, body: str) -> None:
    """
    Sends a notification via Pushbullet and/or Telegram depending on configuration settings.

    Args:
    title (str): The title of the notification message.
    body (str): The body of the notification message.
    """
    if should_send_notification():
        if pushbullet_use:
            send_pushbullet_not(title, body)
        await send_telegram_not(f'{title} {body}')
        logging.warning(f'Sent notification: "{title} {body}"')
    else:
        logging.info(f'Notification "{title} {body}" snoozed, not sent.')


def validate_heartbeat(data: bytes) -> bool:
    """
    Validates the HMAC and timestamp of the received heartbeat.

    Args:
    data (bytes): The data received from the heartbeat which includes timestamp and HMAC.

    Returns:
    bool: True if the heartbeat is valid, False otherwise.
    """
    try:
        # Split the message into components
        _, timestamp, received_hmac = data.decode().split(":")

        # Recreate the message for HMAC validation
        message = f'heartbeat:{timestamp}'.encode()
        calculated_hmac = hmac.new(
            secret_key, message, hashlib.sha256).hexdigest()

        # Verify HMAC authenticity
        if not hmac.compare_digest(calculated_hmac, received_hmac):
            logging.warning("Failed HMAC validation")
            return False

        # Verify that the timestamp is within the allowed time limit
        current_time = time.time()
        time_difference = current_time - float(timestamp)
        if time_difference < TIME_LIMIT:
            return True
        else:
            logging.warning(
                "Failed timestamp validation - time difference too large.")
            return False
    except ValueError as ve:
        logging.error(f"ValueError in validate_heartbeat: {
                      ve} - Data received: {data}")
        return False
    except TypeError as te:
        logging.error(f"TypeError in validate_heartbeat: {
                      te} - Data received: {data}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error in validate_heartbeat: {
                      e} - Data received: {data}")
        return False


async def start_server() -> None:
    """
    Starts the server that listens for heartbeat messages on a specified port.
    """
    server = await asyncio.start_server(handle_client, '0.0.0.0', 5000)
    logging.info("Server started and is listening for heartbeats...")
    async with server:
        await server.serve_forever()


async def handle_client(reader, writer) -> None:
    """
    Handles incoming connections and processes data from clients to validate heartbeats.

    Args:
        reader (StreamReader): The stream reader object to read data from the client.
        writer (StreamWriter): The stream writer object to send data to the client.
    """
    global last_heartbeat_time, offline, failed_heartbeat_time

    address = writer.get_extra_info('peername')
    logging.warning(f"Connection from {address}.")

    data = await reader.read(1024)
    if data and validate_heartbeat(data):
        logging.info(f"Valid heartbeat received from IP: {address}")

        # Update last heartbeat time and check elapsed time since last valid heartbeat
        elapsed_time = time.time() - last_heartbeat_time
        last_heartbeat_time = time.time()

        # If the system was offline and is now back online, calculate downtime
        if elapsed_time >= offline_threshold and offline:
            offline = False
            temp_time = time.time() - failed_heartbeat_time
            downtime = str(timedelta(seconds=temp_time)).split(".")[0]

            # Notify depending on the length of the downtime
            if temp_time < 300:
                logging.info(f"Hawkeye back up after {
                             downtime}. Possible short power outage.")
                await send_notification("Hawkeye is up!", f"Possible short power outage. Time taken {downtime}.")
            else:
                logging.info(f"Hawkeye back up after {downtime}.")
                await send_notification("Hawkeye is up!", f"Hawkeye back online after {downtime}.")

    writer.close()
    await writer.wait_closed()


async def check_heartbeat() -> None:
    """
    Periodically checks if heartbeats are being received within the expected interval.
    If not, sets the system status to offline and sends notifications.
    """
    global offline, failed_heartbeat_time
    logging.info("Heartbeat watchdog started...")
    while True:
        await asyncio.sleep(60)
        elapsed_time = time.time() - last_heartbeat_time

        if elapsed_time > offline_threshold:
            offline = True
            failed_heartbeat_time = last_heartbeat_time
            downtime = str(timedelta(seconds=elapsed_time)).split(".")[0]

            logging.warning(
                f"More than {offline_threshold} seconds passed since last heartbeat.")
            await send_notification("Hawkeye is down!", f"Downtime: {downtime}")


def send_pushbullet_not(title: str, body: str) -> None:
    """
    Sends a notification through Pushbullet service.

    Args:
        title (str): Title of the notification.
        body (str): Content of the notification.
    """
    pb = Pushbullet(pushbullet_api_key)
    pb.push_note(title, body)
    logging.warning(f'Send via Pushbullet. "{title} {body}"')


async def send_telegram_not(text: str) -> None:
    """
    Sends a notification message through a Telegram bot.

    Args:
        text (str): The message to be sent via Telegram.
    """
    bot = Bot(telegram_bot_token)
    try:
        await bot.send_message(chat_id=telegram_id_to_notify, text=text)
        logging.warning(f'Send via Telegram. "{text}"')
    except Exception as e:
        logging.error(f"Failed to send Telegram notification: {e}")


async def telegram_check_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    A Telegram command handler function that checks the current status of the system and replies to the user.

    Args:
        update (Update): The Telegram update object containing message details.
        context (ContextTypes.DEFAULT_TYPE): Context of the command including arguments.
    """
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


async def telegram_snooze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    A Telegram command handler function that sets or disables a snooze period for notifications.

    Args:
        update (Update): The Telegram update object.
        context (ContextTypes.DEFAULT_TYPE): Context of the command including arguments.
    """
    global snooze_start_time, snooze_duration

    try:
        if len(context.args) > 0 and context.args[0].lower() == "disable":
            snooze_start_time = None
            snooze_duration = 0
            await update.message.reply_text("Snooze has been disabled. Notifications will resume.")
            return

        # Parse and validate duration from the command arguments
        duration = int(context.args[0]) if len(context.args) > 0 else None
        if duration is None or not (5 <= duration <= 36000):
            raise ValueError("Invalid duration")

        # Setting or extending the snooze
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
                f"Snooze already active. Extending snooze by {
                    duration} seconds. Total snooze time is now {snooze_duration} seconds."
            )
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /snooze <seconds> (between 5 and 36000) or /snooze disable.")


async def telegram_view_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    A Telegram command handler function that displays recent log entries.

    Args:
        update (Update): The Telegram update object.
        context (ContextTypes.DEFAULT_TYPE): Context of the command including arguments.
    """
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
        await update.message.reply_text("Usage: /view_logs <lines> (between 0 and 50).")


async def telegram_set_offile_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    A Telegram command handler function that adjusts the offline threshold for notifications.

    Args:
        update (Update): The Telegram update object.
        context (ContextTypes.DEFAULT_TYPE): Context of the command including arguments.
    """
    global offline_threshold
    try:
        new_threshold = int(context.args[0])
        offline_threshold = new_threshold
        await update.message.reply_text(f"Offline threshold set to {new_threshold} seconds.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /set_threshold <seconds>")


async def telegram_show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    A Telegram command handler function that shows a help message with available commands.

    Args:
        update (Update): The Telegram update object.
        context (ContextTypes.DEFAULT_TYPE): Context of the command including arguments.
    """
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


def should_send_notification() -> bool:
    """
    Determines whether a notification should be sent based on the snooze settings.

    Returns:
        bool: True if notifications are not currently snoozed, False otherwise.
    """
    global snooze_start_time, snooze_duration
    if snooze_start_time is not None:
        elapsed_time = int(time.time()) - snooze_start_time
        if elapsed_time < snooze_duration:
            return False
    return True


async def start_telegram_bot() -> None:
    """
    Initializes and starts the Telegram bot with command handlers set up.

    This function configures the bot to listen for commands and manage its lifecycle.
    """
    application = Application.builder().token(telegram_bot_token).build()
    # Adding command handlers for Telegram commands
    application.add_handler(CommandHandler("help", telegram_show_help))
    application.add_handler(CommandHandler("snooze", telegram_snooze))
    application.add_handler(CommandHandler("status", telegram_check_status))
    application.add_handler(CommandHandler(
        "set_threshold", telegram_set_offile_threshold))
    application.add_handler(CommandHandler("view_logs", telegram_view_logs))

    logging.info("Starting Telegram bot...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    try:
        # Keep the bot running until it's manually stopped or an error occurs
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logging.info("Stopping Telegram bot...")
        await application.stop()


async def main() -> None:
    """
    The main coroutine that gathers and runs the server, heartbeat check, and Telegram bot concurrently.
    """
    await asyncio.gather(start_server(), check_heartbeat(), start_telegram_bot())

if __name__ == '__main__':
    asyncio.run(main())
