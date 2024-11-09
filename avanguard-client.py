import socket
import hmac
import hashlib
import time
import configparser
import argparse

config = configparser.ConfigParser()
config.read('config.ini')

server_ip = config['Client']['server_ip']
server_port = config['Client']['server_port']
secret_key = config['Key']['secret_key']


def main():
    parser = argparse.ArgumentParser(description='Heartbeat Client')
    parser.add_argument('--interval', type=int, default=45, help='Heartbeat interval in seconds')
    args = parser.parse_args()
    send_heartbeat(args.interval)


def create_heartbeat():
    timestamp = str(time.time())
    message = f'heartbeat:{timestamp}'.encode()

    generated_hmac = hmac.new(secret_key, message, hashlib.sha256).hexdigest()

    full_message = f'heartbeat:{timestamp}:{generated_hmac}'
    return full_message.encode()


def send_heartbeat(interval):
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((server_ip, server_port))
                heartbeat_message = create_heartbeat()
                client_socket.sendall(heartbeat_message)
                print("Heartbeat sent successfully.")
        except ConnectionRefusedError:
            print("Connection refused by the server. Retrying...")
        except socket.timeout:
            print("Connection timed out. Retrying...")
        except socket.error as e:
            print(f"Socket error: {e}. Retrying...")

        time.sleep(interval)


if __name__ == "__main__":
    main()
