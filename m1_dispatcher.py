import socket
import json
import time
import os
import subprocess
from datetime import datetime

# --- SECURITY HARDENING (PHASE 1) ---
# Shifted from default 18789 to custom high-range port
UDP_PORT = 49211

# REPLACE THIS with your M4 Dashboard's Tailscale IP (e.g., "100.x.y.z")
# If Tailscale isn't active yet, keep as "127.0.0.1" for SSH Tunneling.
DEST_IP = "127.0.0.1"

# --- PATHS ---
# Common folder where Nova writes JSON status files
MT5_COMMON_PATH = os.path.expanduser(
    "~/Library/Application Support/MetaTrader 5/Terminal/Common/Files"
)

# War Chest goal
WAR_CHEST_GOAL = 100_000.0

# Strike threshold ($1000 = potential 3-SD wall hit)
STRIKE_THRESHOLD = 1000.0


def get_system_health():
    """Get CPU and RAM usage — Apple Silicon optimized, no psutil needed."""
    try:
        load = os.getloadavg()[0]
        cpu_count = os.cpu_count() or 8
        cpu_percent = min(100, (load / cpu_count) * 100)

        vm = subprocess.run(
            ["vm_stat"], capture_output=True, text=True, timeout=1
        )
        page_size = 16384  # Apple Silicon page size
        stats = {}
        for line in vm.stdout.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                try:
                    stats[key.strip()] = int(val.strip().rstrip("."))
                except ValueError:
                    pass

        pages_free = stats.get("Pages free", 0)
        pages_active = stats.get("Pages active", 0)
        pages_inactive = stats.get("Pages inactive", 0)
        pages_wired = stats.get("Pages wired down", 0)

        total_used = (pages_active + pages_wired) * page_size
        total_free = (pages_free + pages_inactive) * page_size
        total_mem = total_used + total_free

        ram_percent = (total_used / total_mem * 100) if total_mem > 0 else 0
        ram_gb_used = total_used / (1024 ** 3)
        ram_gb_total = total_mem / (1024 ** 3)

        return {
            "cpu_percent": round(cpu_percent, 1),
            "ram_percent": round(ram_percent, 1),
            "ram_used_gb": round(ram_gb_used, 1),
            "ram_total_gb": round(ram_gb_total, 1),
        }
    except Exception as e:
        return {
            "cpu_percent": 0,
            "ram_percent": 0,
            "ram_used_gb": 0,
            "ram_total_gb": 0,
            "error": str(e),
        }


def get_telemetry():
    """Aggregates data from all active MT5 sandboxes with latency tracking."""
    nodes = {}
    now = time.time()
    try:
        for file in os.listdir(MT5_COMMON_PATH):
            if file.startswith("nova_status_") and file.endswith(".json"):
                filepath = os.path.join(MT5_COMMON_PATH, file)
                mtime = os.path.getmtime(filepath)
                latency_ms = (now - mtime) * 1000

                with open(filepath, "r") as f:
                    data = json.load(f)

                node_id = file.split("_")[2].split(".")[0]
                data["latency_ms"] = round(latency_ms, 1)
                data.setdefault("status", "RUNNING")
                data.setdefault("last_action", "—")
                data.setdefault("current_pnl", 0)
                data.setdefault("latency_jitter", 0)
                nodes[f"node_{node_id}"] = data
        return nodes
    except Exception as e:
        return {}


def build_packet(nodes, start_time, strike_log):
    """Build the full data packet the dashboard expects."""
    node_data = {}
    war_chest = 0.0
    total_latency = 0.0
    active_nodes = 0

    for node_id, data in nodes.items():
        node_data[node_id] = {
            "status": data.get("status", "UNKNOWN"),
            "last_action": data.get("last_action", "—"),
            "current_pnl": data.get("current_pnl", 0),
            "latency_ms": data.get("latency_ms", 0),
            "latency_jitter": data.get("latency_jitter", 0),
        }
        war_chest += float(data.get("current_pnl", 0))
        total_latency += data.get("latency_ms", 0)
        active_nodes += 1

        # Check for 3-SD wall hits
        pnl = float(data.get("current_pnl", 0))
        if abs(pnl) > STRIKE_THRESHOLD:
            strike_log.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "node": node_id,
                "pnl": pnl,
                "action": data.get("last_action", "—"),
            })
            if len(strike_log) > 50:
                strike_log.pop(0)

    progress = min(100, max(0, (war_chest / WAR_CHEST_GOAL) * 100))
    avg_latency = (total_latency / active_nodes) if active_nodes > 0 else 0

    return {
        "timestamp": datetime.now().isoformat(),
        "uptime_sec": round(time.time() - start_time, 1),
        "war_chest": round(war_chest, 2),
        "war_chest_goal": WAR_CHEST_GOAL,
        "progress_pct": round(progress, 2),
        "nodes": node_data,
        "active_nodes": active_nodes,
        "avg_latency_ms": round(avg_latency, 1),
        "system": get_system_health(),
        "strike_log": strike_log[-10:],
    }


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    strike_log = []
    start_time = time.time()

    print(f"📡 Dispatcher Ignited | Target: {DEST_IP}:{UDP_PORT}")
    print(f"🔒 Security: Port {UDP_PORT} Active | Tailscale Ready")
    print(f"🎯 War Chest Goal: ${WAR_CHEST_GOAL:,.0f}")

    while True:
        nodes = get_telemetry()
        packet = build_packet(nodes, start_time, strike_log)
        data = json.dumps(packet).encode("utf-8")
        sock.sendto(data, (DEST_IP, UDP_PORT))

        # 500ms sync with Nova's pulse
        time.sleep(0.5)


if __name__ == "__main__":
    main()
