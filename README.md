
# Avanguard - System Heartbeat Monitor

Avanguard is a heartbeat monitoring system designed to check and alert the status of network-connected devices. It ensures that critical systems are operational by sending regular heartbeat signals. If a heartbeat is missed, the system sends notifications via Pushbullet and Telegram, making it ideal for monitoring servers or remote systems to detect power outages or system failures.

- **Real-time Monitoring**: Continuously checks the heartbeat of connected systems thtough TCP socket protocol to detect downtimes.
- **Notifications**: Sends alerts through Pushbullet and/or Telegram when a system goes offline.
- **Security**: Uses HMAC for authentication to ensure that the heartbeat signals are valid.
- **Telegram Commands**: Supports Telegram commands such as snooze, status check, and threshold adjustment.
- **Configurable**: Easy to configure through environment variables or a `.env` file.
- **Logging**: Maintains detailed logs of system status and events.
  
## Quick Start

1. Clone the repository: `git clone https://github.com/yourusername/avanguard.git`
2. Make a new virtual enviroment: `python venv venv`
3. Activate the virtual environment: On Windows: `venv\Scripts\activate` On macOS/Linux: `source venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. Set up the environment variables as described in the [Configuration](#configuration) section below.
7. Run the server: `python src/avanguard-server.py`
8. Run the client: `python src/avanguard-client.py`

## Configuration

Avanguard uses environment variables for configuration to keep sensitive data secure. Set the following variables in your environment or `.env` file:

- `SERVER_IP`: IP address of the server to send heartbeats.
- `SERVER_PORT`: Port on which the server listens.
- `SECRET_KEY`: Secret key used for HMAC authentication.
- `PUSHBULLET_API_KEY`: API key for Pushbullet notifications (set `PUSHBULLET_NOTIFICATION=True` to enable).
- `TELEGRAM_BOT_TOKEN`: Token for the Telegram bot.
- `TELEGRAM_ID_TO_NOTIFY`: Telegram user or group ID to send notifications to.

>Note: Ensure your `.env` file is not included in version control. The `.env.example` file is provided as a template and does not contain sensitive data.

## Usage

### Server

Run the server using the following command: `python server.py`

### Client

Start the client to send heartbeats at specified intervals: `python client.py --interval <interval_in_seconds>`
>Replace `<interval_in_seconds>` with the desired interval for sending heartbeat signals.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
Please make sure to update tests as appropriate.

## License
[MIT] (https://choosealicense.com/licenses/mit/)
