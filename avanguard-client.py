import requests
import time
import uuid

serverurl = "http://161.97.65.201:5000/heartbeat"
client_id = str(uuid.uuid4())


def main():
    send_heartbeat()


def send_heartbeat():
    while True:
        try:
            response = requests.get(serverurl, headers={"Client-ID": client_id})
            if response.status_code == 200:
                print("Heartbeat sent successfully.")
            else:
                print("Failed to send heartbeat.")
        except requests.RequestException as e:
            print(f"Error sending heartbeat: {e}")

        time.sleep(5)  # Adjust the interval as needed


if __name__ == "__main__":
    main()
