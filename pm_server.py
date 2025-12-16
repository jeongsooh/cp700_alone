import socket
import json
import time
import redis
import threading
import asyncio
from ocpp16.data_manager import JsonConfigManager

# 설정값
UDP_PORT = 4210
TCP_PORT = 5000
JSON_FILE = 'ocpp16/shared_data.json'
SERVER_URL = "https://127.0.0.1:443/send"   # FastAPI 서버 주소
CERT_FILE = 'certificate/cert.pem' 

r = redis.Redis(decode_responses=True)
channel = 'energy_updates'

data_manager = JsonConfigManager(JSON_FILE)
data = data_manager.load_data()
REGISTERED_METERS = list(data.get('pm_devices', {}).keys())

# UDP 브로드캐스트 수신 및 응답
def udp_listener():
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_sock.bind(("", UDP_PORT))
    print(f"[UDP] Listening on port {UDP_PORT}...")

    while True:
        data, addr = udp_sock.recvfrom(1024)
        try:
            msg = json.loads(data.decode())
            serial = msg.get("serial")
            print(f"get message: {msg}")
            if msg.get("type") == "meter" and serial in REGISTERED_METERS:
                print(f"[UDP] Registered meter: {serial} from {addr[0]}")
#                 local_ip = socket.gethostbyname(socket.gethostname())
                local_ip = get_local_ip()
                response = json.dumps({
                    "tcp_host": local_ip,
                    "tcp_port": TCP_PORT
                })
                udp_sock.sendto(response.encode(), addr)
                print(f"[UDP] Sent TCP info to {addr[0]} → {local_ip}:{TCP_PORT}")
            else:
                print(f"[UDP] Unregistered meter: {serial} from {addr[0]}")
        except Exception as e:
            print("[UDP] Invalid message:", e)

# TCP 서버: 계측기와 연결 후 데이터 수신
def tcp_server():
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.bind(('', TCP_PORT))
    tcp_sock.listen(5)
    print(f"[TCP] Server listening on port {TCP_PORT}...")

    while True:
        conn, addr = tcp_sock.accept()
        print(f"[TCP] Connected by {addr}")
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                msg = json.loads(data.decode())
                serial = msg.get("serial")
                voltage = msg.get("voltage")
                current = msg.get("current")
                power = msg.get("power")
                energy = msg.get("energy")
                frequency = msg.get("frequency")
                pf = msg.get("pf")
                timestamp = msg.get("timestamp")

                data = f"{current:.3f}A"

                r.publish(channel, data)
                time.sleep(1)

                print(f"[TCP] {serial} → {voltage:.2f}V, {current:.3f}A, {power:.2f}W, {energy}kWh, {frequency:.1f}Hz, pf: {pf:.2f} at {timestamp}")
            except Exception as e:
                print("[TCP] Invalid data:", e)
        conn.close()
        print(f"[TCP] Disconnected from {addr}")

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()

    return ip

# 병렬 실행
if __name__ == "__main__":
    try:
        threading.Thread(target=udp_listener, daemon=True).start()
        asyncio.run(tcp_server())
        # tcp_server()
    except KeyboardInterrupt:
        print("Server stopped.")
