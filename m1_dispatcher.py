import socket
import json
import time
import os

# --- SECURITY HARDENING (PHASE 1) ---
# Shifted from default 18789 to custom high-range port
UDP_PORT = 49211 

# REPLACE THIS with your M4 Dashboard's Tailscale IP (e.g., "100.x.y.z")
# If Tailscale isn't active yet, keep as "127.0.0.1" for SSH Tunneling.
DEST_IP = "127.0.0.1" 

# --- PATHS ---
# Common folder where Nova writes JSON status files
MT5_COMMON_PATH = os.path.expanduser("~/Library/Application Support/MetaTrader 5/Terminal/Common/Files")

def get_telemetry():
    """Aggregates data from all active MT5 sandboxes."""
    nodes = {}
    try:
        for file in os.listdir(MT5_COMMON_PATH):
            if file.startswith("nova_status_") and file.endswith(".json"):
                with open(os.path.join(MT5_COMMON_PATH, file), 'r') as f:
                    node_id = file.split("_")[2].split(".")[0]
                    nodes[f"NODE_{node_id}"] = json.load(f)
        return nodes
    except Exception as e:
        return {"error": str(e)}

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"📡 Dispatcher Ignited | Target: {DEST_IP}:{UDP_PORT}")
    print(f"🔒 Security: Port 49211 Active | Tailscale Ready")

    while True:
        data = get_telemetry()
        if data:
            packet = json.dumps(data).encode('utf-8')
            sock.sendto(packet, (DEST_IP, UDP_PORT))
            
        # 500ms sync with Nova's pulse
        time.sleep(0.5)

if __name__ == "__main__":
    main()