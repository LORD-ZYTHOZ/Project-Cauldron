#!/usr/bin/env python3
"""Continuous test packet sender for Cauldron dashboard."""

import socket
import json
import time
import random
from datetime import datetime

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
start = time.time()
war_chest = 12500.50
strikes = []

actions = ['BUY XAUUSD @ 2655', 'SELL XAUUSD @ 2658', 'HOLD — thesis intact',
           'WAIT — no setup', 'TP1 hit — trailing', 'CLOSE_PARTIAL 25%']
strike_actions = ['TP1 hit @ 2660', '3-SD wall bounce', 'Breakeven trail', 'Full TP @ 2675']

print('Sending packets to dashboard... (Ctrl+C to stop)')

i = 0
try:
    while True:
        i += 1
        uptime = time.time() - start + 3600

        # Simulate P&L movement
        war_chest += random.uniform(-50, 150)
        war_chest = max(0, war_chest)

        pnl1 = random.uniform(3000, 6000)
        pnl2 = random.uniform(4000, 8000)
        pnl3 = random.uniform(1500, 4000)

        # Random strike every ~10 packets
        if random.random() < 0.1:
            strikes.append({
                'time': datetime.now().strftime('%H:%M:%S'),
                'node': random.choice(['node_1', 'node_2', 'node_3']),
                'pnl': random.randint(500, 3000),
                'action': random.choice(strike_actions)
            })
            strikes = strikes[-10:]

        packet = {
            'timestamp': datetime.now().isoformat(),
            'uptime_sec': uptime,
            'war_chest': round(war_chest, 2),
            'war_chest_goal': 100000,
            'progress_pct': round(war_chest / 1000, 2),
            'nodes': {
                'node_1': {'status': 'RUNNING', 'last_action': random.choice(actions),
                          'current_pnl': round(pnl1, 2), 'latency_ms': round(random.uniform(3, 12), 1),
                          'latency_jitter': round(random.uniform(0.5, 2), 1)},
                'node_2': {'status': 'RUNNING', 'last_action': random.choice(actions),
                          'current_pnl': round(pnl2, 2), 'latency_ms': round(random.uniform(4, 15), 1),
                          'latency_jitter': round(random.uniform(0.3, 1.5), 1)},
                'node_3': {'status': 'RUNNING', 'last_action': random.choice(actions),
                          'current_pnl': round(pnl3, 2), 'latency_ms': round(random.uniform(2, 10), 1),
                          'latency_jitter': round(random.uniform(0.4, 1.8), 1)}
            },
            'active_nodes': 3,
            'avg_latency_ms': round(random.uniform(4, 10), 1),
            'system': {
                'cpu_percent': round(random.uniform(15, 45), 1),
                'ram_percent': round(random.uniform(40, 60), 1),
                'ram_used_gb': round(random.uniform(6, 10), 1),
                'ram_total_gb': 16.0
            },
            'strike_log': strikes
        }

        sock.sendto(json.dumps(packet).encode(), ('127.0.0.1', 9999))

        if i % 10 == 0:
            print(f'  Packet {i}: War Chest ${war_chest:,.2f} | Strikes: {len(strikes)}')

        time.sleep(0.5)  # 2Hz

except KeyboardInterrupt:
    print(f'\nStopped after {i} packets.')
