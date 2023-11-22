import requests

serverurl = "http://161.97.65.201:5000/update_status"
def main():
    local_ips = read_ips("local_ips.txt")

    for ip in local_ips:
        if is_online(ip):
            inform_server(ip, True)
        else:
            inform_server(ip, False)

def read_ips(file_path):
    with open(file_path) as file:
        return [line.strip() for line in file]

def is_online(ip):
    try:
        response = requests.get(f"http://{ip}", timeout=3)
        return response.status_code == 200
    except requests.RequestException:
        return False

def inform_server(ip, status):
    data = {"ip": ip, "status": status}

    try:
        response = requests.post(serverurl, json=data)
        if response.status_code == 200:
            print(f"Status for {ip} sent successfully.")
        else:
            print(f"Failed to send status for {ip}.")
    except requests.RequestException as e:
        print(f"Error sending status for {ip}: {e}")

if __name__ == "__main__":
    main()