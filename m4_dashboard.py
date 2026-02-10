#!/usr/bin/env python3
"""
Project Cauldron — M4 Dashboard
===============================
Infrared Dashboard for Mission Control (M4 Pro).
Real-time visualization of the 3-node trading cell.

Cyberpunk/High-Tech aesthetic via Rich library.
Ghost Protocol: Low overhead, high visibility.
"""

import asyncio
import json
import socket
from datetime import datetime
from typing import Dict, Optional

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.style import Style
from rich.table import Table
from rich.text import Text

# ============================================================
# CONFIG
# ============================================================

LISTEN_PORT = 49211
WAR_CHEST_GOAL = 100_000.0

# Cyberpunk color scheme
CYBER_PINK = "#ff0080"
CYBER_CYAN = "#00ffff"
CYBER_GREEN = "#00ff00"
CYBER_YELLOW = "#ffff00"
CYBER_RED = "#ff0000"
CYBER_PURPLE = "#bf00ff"
CYBER_DARK = "#1a1a2e"

# ============================================================
# DASHBOARD
# ============================================================

class InfraredDashboard:
    """Real-time trading cell dashboard."""

    def __init__(self):
        self.console = Console()
        self.last_packet: Optional[Dict] = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", LISTEN_PORT))
        self.sock.setblocking(False)
        self.strike_history: list = []

    def receive_packet(self) -> Optional[Dict]:
        """Non-blocking receive from M1."""
        try:
            data, addr = self.sock.recvfrom(65535)
            return json.loads(data.decode("utf-8"))
        except BlockingIOError:
            return None
        except Exception:
            return None

    def build_header(self, packet: Dict) -> Panel:
        """Build the header panel."""
        uptime = packet.get("uptime_sec", 0)
        hours = int(uptime // 3600)
        mins = int((uptime % 3600) // 60)
        secs = int(uptime % 60)

        header = Text()
        header.append("  PROJECT CAULDRON  ", style=f"bold {CYBER_PINK}")
        header.append("│", style="dim")
        header.append(f" INFRARED DASHBOARD ", style=f"bold {CYBER_CYAN}")
        header.append("│", style="dim")
        header.append(f" UPTIME: {hours:02d}:{mins:02d}:{secs:02d} ", style=CYBER_GREEN)

        return Panel(
            header,
            style=f"bold {CYBER_PINK}",
            border_style=CYBER_PINK,
        )

    def build_war_chest(self, packet: Dict) -> Panel:
        """Build the War Chest progress panel."""
        war_chest = packet.get("war_chest", 0)
        progress_pct = packet.get("progress_pct", 0)

        # Progress bar characters
        bar_width = 40
        filled = int(bar_width * progress_pct / 100)
        empty = bar_width - filled

        bar = Text()
        bar.append("  $100K NODE #2 FUNDING GOAL\n\n", style=f"bold {CYBER_CYAN}")
        bar.append("  [", style="dim")
        bar.append("█" * filled, style=CYBER_GREEN if progress_pct >= 50 else CYBER_YELLOW)
        bar.append("░" * empty, style="dim")
        bar.append("]", style="dim")
        bar.append(f" {progress_pct:.1f}%\n\n", style=f"bold {CYBER_GREEN}")

        bar.append(f"  WAR CHEST: ", style="dim")
        bar.append(f"${war_chest:,.2f}", style=f"bold {CYBER_GREEN}" if war_chest > 0 else f"bold {CYBER_RED}")
        bar.append(f" / ${WAR_CHEST_GOAL:,.0f}", style="dim")

        return Panel(
            bar,
            title="[bold]WAR CHEST[/bold]",
            title_align="left",
            border_style=CYBER_GREEN,
        )

    def build_pulse_sync(self, packet: Dict) -> Panel:
        """Build the Pulse Sync Meter panel."""
        nodes = packet.get("nodes", {})
        avg_latency = packet.get("avg_latency_ms", 0)

        table = Table(show_header=True, header_style=f"bold {CYBER_CYAN}", box=None)
        table.add_column("NODE", style="dim", width=10)
        table.add_column("STATUS", width=10)
        table.add_column("LATENCY", width=12)
        table.add_column("JITTER", width=10)
        table.add_column("SYNC", width=8)

        for node_id, data in nodes.items():
            status = data.get("status", "OFFLINE")
            latency = data.get("latency_ms", 0)
            jitter = data.get("latency_jitter", 0)

            # Status styling
            if status == "RUNNING":
                status_style = CYBER_GREEN
            elif status == "OFFLINE":
                status_style = CYBER_RED
            else:
                status_style = CYBER_YELLOW

            # Latency styling (target <10ms)
            if latency < 10:
                latency_style = CYBER_GREEN
                sync_icon = "●"
            elif latency < 50:
                latency_style = CYBER_YELLOW
                sync_icon = "◐"
            else:
                latency_style = CYBER_RED
                sync_icon = "○"

            table.add_row(
                node_id.upper(),
                Text(status, style=status_style),
                Text(f"{latency:.1f}ms", style=latency_style),
                Text(f"±{jitter:.1f}ms", style="dim"),
                Text(sync_icon, style=latency_style),
            )

        # Overall sync status
        sync_text = Text()
        sync_text.append("\n  AVG LATENCY: ", style="dim")
        if avg_latency < 10:
            sync_text.append(f"{avg_latency:.1f}ms ", style=f"bold {CYBER_GREEN}")
            sync_text.append("OPTIMAL", style=CYBER_GREEN)
        elif avg_latency < 50:
            sync_text.append(f"{avg_latency:.1f}ms ", style=f"bold {CYBER_YELLOW}")
            sync_text.append("NOMINAL", style=CYBER_YELLOW)
        else:
            sync_text.append(f"{avg_latency:.1f}ms ", style=f"bold {CYBER_RED}")
            sync_text.append("DEGRADED", style=CYBER_RED)

        content = Group(table, sync_text)

        return Panel(
            content,
            title="[bold]PULSE SYNC METER[/bold]",
            title_align="left",
            border_style=CYBER_CYAN,
        )

    def build_system_health(self, packet: Dict) -> Panel:
        """Build the System Health panel (M1 Engine)."""
        system = packet.get("system", {})
        cpu = system.get("cpu_percent", 0)
        ram = system.get("ram_percent", 0)
        ram_used = system.get("ram_used_gb", 0)
        ram_total = system.get("ram_total_gb", 0)

        health = Text()
        health.append("  M1 EXECUTION VAULT\n\n", style=f"bold {CYBER_PURPLE}")

        # CPU bar
        cpu_bar_width = 20
        cpu_filled = int(cpu_bar_width * cpu / 100)
        health.append("  CPU  [", style="dim")
        health.append("█" * cpu_filled, style=CYBER_GREEN if cpu < 70 else CYBER_RED)
        health.append("░" * (cpu_bar_width - cpu_filled), style="dim")
        health.append(f"] {cpu:5.1f}%\n", style=CYBER_GREEN if cpu < 70 else CYBER_RED)

        # RAM bar
        ram_bar_width = 20
        ram_filled = int(ram_bar_width * ram / 100)
        health.append("  RAM  [", style="dim")
        health.append("█" * ram_filled, style=CYBER_CYAN if ram < 80 else CYBER_YELLOW)
        health.append("░" * (ram_bar_width - ram_filled), style="dim")
        health.append(f"] {ram:5.1f}%\n", style=CYBER_CYAN if ram < 80 else CYBER_YELLOW)

        health.append(f"\n  {ram_used:.1f}GB / {ram_total:.1f}GB", style="dim")

        return Panel(
            health,
            title="[bold]SYSTEM HEALTH[/bold]",
            title_align="left",
            border_style=CYBER_PURPLE,
        )

    def build_strike_log(self, packet: Dict) -> Panel:
        """Build the Strike Log panel."""
        strikes = packet.get("strike_log", [])

        if not strikes:
            content = Text("  Awaiting 3-SD wall hits...", style="dim italic")
        else:
            table = Table(show_header=True, header_style=f"bold {CYBER_YELLOW}", box=None)
            table.add_column("TIME", width=10)
            table.add_column("NODE", width=10)
            table.add_column("P&L", width=12)
            table.add_column("ACTION", width=20)

            for strike in reversed(strikes[-10:]):
                pnl = strike.get("pnl", 0)
                pnl_style = CYBER_GREEN if pnl > 0 else CYBER_RED

                table.add_row(
                    strike.get("time", "—"),
                    strike.get("node", "—").upper(),
                    Text(f"${pnl:+,.0f}", style=pnl_style),
                    strike.get("action", "—"),
                )

            content = table

        return Panel(
            content,
            title="[bold]STRIKE LOG[/bold]",
            title_align="left",
            border_style=CYBER_YELLOW,
        )

    def build_node_actions(self, packet: Dict) -> Panel:
        """Build the Node Actions panel."""
        nodes = packet.get("nodes", {})

        table = Table(show_header=True, header_style=f"bold {CYBER_PINK}", box=None)
        table.add_column("NODE", width=10)
        table.add_column("LAST ACTION", width=25)
        table.add_column("P&L", width=12)

        for node_id, data in nodes.items():
            pnl = data.get("current_pnl", 0)
            action = data.get("last_action", "—")

            pnl_style = CYBER_GREEN if pnl > 0 else (CYBER_RED if pnl < 0 else "dim")

            table.add_row(
                node_id.upper(),
                action[:25],
                Text(f"${pnl:+,.2f}" if pnl != 0 else "—", style=pnl_style),
            )

        return Panel(
            table,
            title="[bold]NODE STATUS[/bold]",
            title_align="left",
            border_style=CYBER_PINK,
        )

    def build_layout(self, packet: Dict) -> Layout:
        """Build the full dashboard layout."""
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )

        layout["left"].split_column(
            Layout(name="war_chest", size=10),
            Layout(name="pulse_sync"),
        )

        layout["right"].split_column(
            Layout(name="system_health", size=12),
            Layout(name="node_actions", size=10),
            Layout(name="strike_log"),
        )

        # Populate panels
        layout["header"].update(self.build_header(packet))
        layout["war_chest"].update(self.build_war_chest(packet))
        layout["pulse_sync"].update(self.build_pulse_sync(packet))
        layout["system_health"].update(self.build_system_health(packet))
        layout["node_actions"].update(self.build_node_actions(packet))
        layout["strike_log"].update(self.build_strike_log(packet))

        # Footer
        footer = Text()
        timestamp = packet.get("timestamp", "—")
        active = packet.get("active_nodes", 0)
        footer.append(f"  LAST UPDATE: {timestamp}  ", style="dim")
        footer.append("│", style="dim")
        footer.append(f"  ACTIVE NODES: {active}/3  ", style=CYBER_GREEN if active == 3 else CYBER_YELLOW)
        footer.append("│", style="dim")
        footer.append("  [CTRL+C] EXIT  ", style="dim")

        layout["footer"].update(Panel(footer, border_style="dim"))

        return layout

    async def run(self):
        """Main dashboard loop."""
        # Placeholder packet for initial render
        placeholder = {
            "timestamp": datetime.now().isoformat(),
            "uptime_sec": 0,
            "war_chest": 0,
            "war_chest_goal": WAR_CHEST_GOAL,
            "progress_pct": 0,
            "nodes": {
                "node_1": {"status": "WAITING"},
                "node_2": {"status": "WAITING"},
                "node_3": {"status": "WAITING"},
            },
            "active_nodes": 0,
            "avg_latency_ms": 0,
            "system": {},
            "strike_log": [],
        }

        self.last_packet = placeholder

        with Live(
            self.build_layout(self.last_packet),
            console=self.console,
            refresh_per_second=4,
            screen=True,
        ) as live:
            while True:
                # Try to receive packet
                packet = self.receive_packet()
                if packet:
                    self.last_packet = packet

                # Update display
                live.update(self.build_layout(self.last_packet))

                await asyncio.sleep(0.1)  # 10Hz check rate


# ============================================================
# MAIN
# ============================================================

def main():
    dashboard = InfraredDashboard()
    try:
        asyncio.run(dashboard.run())
    except KeyboardInterrupt:
        print("\n[DASHBOARD] Shutdown complete.")


if __name__ == "__main__":
    main()
