#!/usr/bin/env python3
"""
Project Cauldron — M1 Dispatcher
================================
Lightweight async monitor for the Execution Vault (M1 Mac Mini).
Monitors 3 MT5 trading nodes, calculates War Chest progress,
broadcasts to M4 Mission Control via UDP.

Ghost Protocol: Low overhead, minimal footprint.
"""

import asyncio
import json
import os
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# ============================================================
# CONFIG
# ============================================================

# M4 Mission Control endpoint
M4_IP = "192.168.1.100"  # UPDATE: Your M4's local IP
M4_PORT = 9999

# MT5 Common Files path (M1)
MT5_COMMON = Path(
    "/Users/eoh/Library/Application Support/net.metaquotes.wine.metatrader5"
    "/drive_c/users/user/AppData/Roaming/MetaQuotes/Terminal/Common/Files"
)

# Node status files (each node writes its own status)
NODE_FILES = {
    "node_1": "grok_mind_status.json",
    "node_2": "grok_legacy_status.json",
    "node_3": "grok_overlord_status.json",
}

# War Chest goal
WAR_CHEST_GOAL = 100_000.0

# Broadcast interval (ms)
BROADCAST_INTERVAL = 500  # 500ms = 2Hz refresh

# ============================================================
# SYSTEM HEALTH (Apple Silicon optimized)
# ============================================================

def get_system_health() -> Dict:
    """Get CPU and RAM usage — lightweight, no psutil needed."""
    try:
        # CPU load average (1 min)
        load = os.getloadavg()[0]
        cpu_count = os.cpu_count() or 8
        cpu_percent = min(100, (load / cpu_count) * 100)

        # Memory via vm_stat (macOS native)
        import subprocess
        vm = subprocess.run(
            ["vm_stat"], capture_output=True, text=True, timeout=1
        )
        lines = vm.stdout.split("\n")

        # Parse page stats
        page_size = 16384  # Apple Silicon page size
        stats = {}
        for line in lines:
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
        ram_gb_used = total_used / (1024**3)
        ram_gb_total = total_mem / (1024**3)

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


# ============================================================
# NODE MONITOR
# ============================================================

class NodeMonitor:
    """Monitors a single trading node's status file."""

    def __init__(self, node_id: str, filename: str):
        self.node_id = node_id
        self.filepath = MT5_COMMON / filename
        self.last_update = 0.0
        self.last_data: Optional[Dict] = None
        self.latency_samples: list = []

    def read(self) -> Optional[Dict]:
        """Read node status file."""
        if not self.filepath.exists():
            return None

        try:
            mtime = self.filepath.stat().st_mtime
            now = time.time()

            # Calculate latency (time since file was written)
            latency_ms = (now - mtime) * 1000
            self.latency_samples.append(latency_ms)
            if len(self.latency_samples) > 20:
                self.latency_samples.pop(0)

            data = json.loads(self.filepath.read_text(encoding="utf-8"))
            data["latency_ms"] = round(latency_ms, 1)
            data["latency_jitter"] = self._calc_jitter()
            self.last_data = data
            self.last_update = now
            return data

        except (json.JSONDecodeError, IOError):
            return self.last_data

    def _calc_jitter(self) -> float:
        """Calculate latency jitter (standard deviation)."""
        if len(self.latency_samples) < 2:
            return 0.0
        mean = sum(self.latency_samples) / len(self.latency_samples)
        variance = sum((x - mean) ** 2 for x in self.latency_samples) / len(self.latency_samples)
        return round(variance ** 0.5, 2)


# ============================================================
# DISPATCHER
# ============================================================

class Dispatcher:
    """Main dispatcher — aggregates nodes, broadcasts to M4."""

    def __init__(self):
        self.nodes = {
            node_id: NodeMonitor(node_id, filename)
            for node_id, filename in NODE_FILES.items()
        }
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.strike_log: list = []
        self.start_time = time.time()

    def aggregate(self) -> Dict:
        """Aggregate all node data into a single packet."""
        node_data = {}
        war_chest = 0.0
        total_latency = 0.0
        active_nodes = 0

        for node_id, monitor in self.nodes.items():
            data = monitor.read()
            if data:
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

                # Check for 3-SD wall hits (significant moves)
                pnl = float(data.get("current_pnl", 0))
                if abs(pnl) > 1000:  # $1000 threshold = potential wall hit
                    self.strike_log.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "node": node_id,
                        "pnl": pnl,
                        "action": data.get("last_action", "—"),
                    })
                    if len(self.strike_log) > 50:
                        self.strike_log.pop(0)
            else:
                node_data[node_id] = {"status": "OFFLINE"}

        # Calculate progress
        progress = min(100, max(0, (war_chest / WAR_CHEST_GOAL) * 100))
        avg_latency = (total_latency / active_nodes) if active_nodes > 0 else 0

        # Get system health
        health = get_system_health()

        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_sec": round(time.time() - self.start_time, 1),
            "war_chest": round(war_chest, 2),
            "war_chest_goal": WAR_CHEST_GOAL,
            "progress_pct": round(progress, 2),
            "nodes": node_data,
            "active_nodes": active_nodes,
            "avg_latency_ms": round(avg_latency, 1),
            "system": health,
            "strike_log": self.strike_log[-10:],  # Last 10 strikes
        }

    def broadcast(self, packet: Dict):
        """Send packet to M4 via UDP."""
        try:
            data = json.dumps(packet).encode("utf-8")
            self.sock.sendto(data, (M4_IP, M4_PORT))
        except Exception as e:
            print(f"[DISPATCH] Broadcast error: {e}")

    async def run(self):
        """Main loop — aggregate and broadcast."""
        print("=" * 60)
        print("  PROJECT CAULDRON — M1 DISPATCHER")
        print("  Execution Vault Online")
        print("=" * 60)
        print(f"  Target: {M4_IP}:{M4_PORT}")
        print(f"  Nodes: {list(NODE_FILES.keys())}")
        print(f"  War Chest Goal: ${WAR_CHEST_GOAL:,.0f}")
        print("=" * 60)
        print()

        interval = BROADCAST_INTERVAL / 1000.0

        while True:
            packet = self.aggregate()
            self.broadcast(packet)

            # Local status (minimal output)
            print(
                f"\r[{packet['timestamp'][11:19]}] "
                f"War Chest: ${packet['war_chest']:,.2f} "
                f"({packet['progress_pct']:.1f}%) | "
                f"Nodes: {packet['active_nodes']}/3 | "
                f"Latency: {packet['avg_latency_ms']:.0f}ms",
                end="", flush=True
            )

            await asyncio.sleep(interval)


# ============================================================
# MAIN
# ============================================================

def main():
    dispatcher = Dispatcher()
    try:
        asyncio.run(dispatcher.run())
    except KeyboardInterrupt:
        print("\n\n[DISPATCH] Shutdown complete.")


if __name__ == "__main__":
    main()
