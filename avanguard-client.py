import requests
import time
import uuid
import argparse

# Server URL to send heartbeat to
serverurl = "http://161.97.65.201:5000/heartbeat"

# Generate a unique client ID using UUID
client_id = str(uuid.uuid4())


def main():
    parser = argparse.ArgumentParser(description='Heartbeat Client')
    parser.add_argument('--interval', type=int, default=45, help='Heartbeat interval in seconds')
    args = parser.parse_args()
    send_heartbeat(args.interval)


def send_heartbeat(interval):
    while True:
        try:
            response = requests.get(serverurl, headers={"Client-ID": client_id})

            if response.status_code == 200:
                print("Heartbeat sent successfully.")
            else:
                print("Failed to send heartbeat.")
        except requests.RequestException as e:
            print(f"Error sending heartbeat: {e}")

        time.sleep(interval)


# Entry point of the script
if __name__ == "__main__":
    main()
