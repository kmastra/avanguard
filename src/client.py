import socket
import hmac
import hashlib
import time
import os
import argparse
import logging
from dotenv import load_dotenv

# Configuration values for server communication
load_dotenv()
server_ip = os.getenv('SERVER_IP')
server_port = int(os.getenv('SERVER_PORT'))
secret_key = os.getenv('SECRET_KEY').encode()

# Set up basic logging configuration
logging.basicConfig(filename='client_log.txt',
                    level=logging.INFO, format='%(asctime)s - %(message)s')


def main():
    """
    Main function that sets up the command-line arguments and starts the heartbeat sending process.
    """
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Heartbeat Client')
    parser.add_argument('--interval', type=int, default=45,
                        help='Heartbeat interval in seconds')
    args = parser.parse_args()

    # Start sending heartbeats at the specified interval
    send_heartbeat(args.interval)


def create_heartbeat() -> bytes:
    """
    Creates a heartbeat message encoded with HMAC to ensure authenticity.

    Returns:
        bytes: The encoded heartbeat message including the timestamp and HMAC.
    """
    # Generate the current time stamp
    timestamp = str(time.time())

    message = f'heartbeat:{timestamp}'.encode()

    # Generate HMAC for the message
    generated_hmac = hmac.new(secret_key, message, hashlib.sha256).hexdigest()

    # Combine the message parts
    full_message = f'heartbeat:{timestamp}:{generated_hmac}'
    return full_message.encode()


def send_heartbeat(interval: int, iterations: int = None):
    """
    Continuously sends heartbeat messages to the server at a specified interval.

    Args:
        interval (int): The interval between heartbeats in seconds.
        iterations (int, optional): Number of times to send a heartbeat for testing. Defaults to None for infinite loop.
    """
    count = 0
    while iterations is None or count < iterations:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                # Connect to the server
                client_socket.connect((server_ip, server_port))
                heartbeat_message = create_heartbeat()
                # Send the heartbeat message
                client_socket.sendall(heartbeat_message)
                logging.info("Heartbeat sent successfully.")
        except ConnectionRefusedError:
            logging.warning("Connection refused by the server. Retrying...")
        except socket.timeout:
            logging.warning("Connection timed out. Retrying...")
        except socket.error as e:
            logging.warning(f"Socket error: {e}. Retrying...")

        # Wait for the next interval before sending another heartbeat
        time.sleep(interval)
        count += 1


if __name__ == "__main__":
    main()
