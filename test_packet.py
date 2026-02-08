#!/usr/bin/env python3
"""Test packet sender for Cauldron dashboard."""

import socket
import json
from datetime import datetime

packet = {
    'timestamp': datetime.now().isoformat(),
    'uptime_sec': 3661,
    'war_chest': 25000.00,
    'progress_pct': 25.0,
    'nodes': {
        'node_1': {'status': 'RUNNING', 'last_action': 'BUY XAUUSD', 'current_pnl': 8500.00, 'latency_ms': 5.2, 'latency_jitter': 1.1},
        'node_2': {'status': 'RUNNING', 'last_action': 'HOLD', 'current_pnl': 9200.50, 'latency_ms': 6.8, 'latency_jitter': 0.9},
        'node_3': {'status': 'RUNNING', 'last_action': 'TP1 hit', 'current_pnl': 7300.00, 'latency_ms': 4.5, 'latency_jitter': 0.7}
    },
    'active_nodes': 3,
    'avg_latency_ms': 5.5,
    'system': {'cpu_percent': 23.5, 'ram_percent': 45.2, 'ram_used_gb': 7.2, 'ram_total_gb': 16.0},
    'strike_log': []
}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(json.dumps(packet).encode(), ('127.0.0.1', 9999))
print('Packet sent to 127.0.0.1:9999')
