import requests
import time
import uuid

# Server URL to send heartbeat to
serverurl = "http://161.97.65.201:5000/heartbeat"

# Generate a unique client ID using UUID
client_id = str(uuid.uuid4())


def main():
    # Start sending heartbeats
    send_heartbeat()


def send_heartbeat():
    # Infinite loop to continuously send heartbeats
    while True:
        try:
            # Send a GET request to the server with the client ID in the headers
            response = requests.get(serverurl, headers={"Client-ID": client_id})

            # Check the response status code
            if response.status_code == 200:
                print("Heartbeat sent successfully.")
            else:
                print("Failed to send heartbeat.")
        except requests.RequestException as e:
            # Handle exceptions if there is an error sending the heartbeat
            print(f"Error sending heartbeat: {e}")

        # Adjust the interval between heartbeats as needed (currently set to 5 seconds)
        time.sleep(45)


# Entry point of the script
if __name__ == "__main__":
    main()
