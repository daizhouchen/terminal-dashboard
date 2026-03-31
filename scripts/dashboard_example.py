#!/usr/bin/env python3
"""Ready-to-run example dashboard that monitors system resources.

Uses the rich library for real-time terminal rendering.

Keyboard shortcuts:
  q      - quit
  r      - force refresh
  h      - toggle help overlay
  Ctrl+C - graceful shutdown
"""

import os
import signal
import socket
import sys
import threading
import time

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
RUNNING = True
REFRESH_NOW = threading.Event()
SHOW_HELP = False

# Previous values for trend arrows
_prev_cpu: float | None = None
_prev_load: float | None = None


def _signal_handler(sig, frame):
    global RUNNING
    RUNNING = False


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# ---------------------------------------------------------------------------
# Panel builders
# ---------------------------------------------------------------------------

def build_system_info_panel() -> Panel:
    """Hostname, uptime, load average."""
    global _prev_load
    table = Table(show_header=False, expand=True, box=None)
    table.add_column("Key", style="bold cyan", ratio=1)
    table.add_column("Value", style="white", ratio=2)

    table.add_row("Hostname", socket.gethostname())

    # Uptime
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        days = int(secs // 86400)
        hours = int((secs % 86400) // 3600)
        mins = int((secs % 3600) // 60)
        table.add_row("Uptime", f"{days}d {hours}h {mins}m")
    except Exception:
        table.add_row("Uptime", "N/A")

    # Load average
    load1, load5, load15 = os.getloadavg()
    arrow = "\u2191" if (_prev_load is not None and load1 > _prev_load) else "\u2193"
    _prev_load = load1
    table.add_row(
        "Load Avg",
        f"{load1:.2f} {arrow}  (5m: {load5:.2f}, 15m: {load15:.2f})",
    )

    # CPU count
    table.add_row("CPUs", str(os.cpu_count() or "?"))

    return Panel(table, title="[bold]System Info[/bold]", border_style="blue")


def build_resource_panel() -> Panel:
    """CPU / memory / disk progress bars."""
    global _prev_cpu
    try:
        import psutil
    except ImportError:
        return Panel(
            Text("psutil not installed.\npip install psutil", style="bold red"),
            title="[bold]Resources[/bold]",
            border_style="green",
        )

    table = Table(show_header=True, expand=True, box=None)
    table.add_column("Resource", style="bold cyan", ratio=1)
    table.add_column("Bar", ratio=3)
    table.add_column("%", justify="right", style="bold", ratio=1)

    # CPU
    cpu_pct = psutil.cpu_percent(interval=0.1)
    arrow = ""
    if _prev_cpu is not None:
        arrow = " \u2191" if cpu_pct > _prev_cpu else " \u2193"
    _prev_cpu = cpu_pct
    color = "green" if cpu_pct < 60 else "yellow" if cpu_pct < 85 else "red"
    table.add_row("CPU", ProgressBar(total=100, completed=cpu_pct, style=color), f"{cpu_pct:.1f}%{arrow}")

    # Memory
    mem = psutil.virtual_memory()
    color = "green" if mem.percent < 60 else "yellow" if mem.percent < 85 else "red"
    used_gb = mem.used / (1024 ** 3)
    total_gb = mem.total / (1024 ** 3)
    table.add_row(
        "Memory",
        ProgressBar(total=100, completed=mem.percent, style=color),
        f"{mem.percent:.1f}% ({used_gb:.1f}/{total_gb:.1f}G)",
    )

    # Disk
    disk = psutil.disk_usage("/")
    color = "green" if disk.percent < 60 else "yellow" if disk.percent < 85 else "red"
    used_gb = disk.used / (1024 ** 3)
    total_gb = disk.total / (1024 ** 3)
    table.add_row(
        "Disk /",
        ProgressBar(total=100, completed=disk.percent, style=color),
        f"{disk.percent:.1f}% ({used_gb:.1f}/{total_gb:.1f}G)",
    )

    # Swap
    swap = psutil.swap_memory()
    if swap.total > 0:
        color = "green" if swap.percent < 60 else "yellow" if swap.percent < 85 else "red"
        table.add_row(
            "Swap",
            ProgressBar(total=100, completed=swap.percent, style=color),
            f"{swap.percent:.1f}%",
        )

    return Panel(table, title="[bold]Resources[/bold]", border_style="green")


def _mini_line_chart(values: list[float], width: int = 30, height: int = 5) -> str:
    """Render a tiny ASCII line chart."""
    if not values:
        return ""
    mn, mx = min(values), max(values)
    span = mx - mn if mx != mn else 1.0
    chars = ["\u2581", "\u2582", "\u2583", "\u2584", "\u2585", "\u2586", "\u2587", "\u2588"]
    # Sample or pad to width
    sampled = values[-width:]
    line = ""
    for v in sampled:
        idx = int((v - mn) / span * (len(chars) - 1))
        line += chars[idx]
    return line


# Keep a rolling history for the chart
_cpu_history: list[float] = []


def build_top_processes_panel() -> Panel:
    """Top 5 processes by CPU and a mini CPU chart."""
    try:
        import psutil
    except ImportError:
        return Panel(Text("psutil not installed", style="bold red"), title="[bold]Processes[/bold]")

    # Update CPU history
    cpu_now = psutil.cpu_percent(interval=0)
    _cpu_history.append(cpu_now)
    if len(_cpu_history) > 60:
        _cpu_history.pop(0)

    table = Table(show_header=True, expand=True, box=None)
    table.add_column("PID", style="dim", ratio=1)
    table.add_column("Name", style="cyan", ratio=2)
    table.add_column("CPU%", justify="right", ratio=1)
    table.add_column("Mem%", justify="right", ratio=1)

    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = p.info
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
    for info in procs[:5]:
        table.add_row(
            str(info["pid"]),
            (info["name"] or "?")[:20],
            f'{info["cpu_percent"]:.1f}',
            f'{info["memory_percent"]:.1f}',
        )

    chart = _mini_line_chart(_cpu_history)
    chart_text = Text(f"\nCPU History: {chart}", style="bold green")

    from rich.console import Group
    group = Group(table, chart_text)
    return Panel(group, title="[bold]Top Processes[/bold]", border_style="magenta")


def build_status_panel() -> Panel:
    """Simple ASCII status lights for common services."""
    table = Table(show_header=True, expand=True, box=None)
    table.add_column("Check", style="bold cyan")
    table.add_column("Status", justify="center")

    import subprocess

    for svc in ["sshd", "cron", "systemd-resolved"]:
        try:
            r = subprocess.run(
                ["systemctl", "is-active", svc],
                capture_output=True, text=True, timeout=2,
            )
            status = r.stdout.strip()
            if status == "active":
                table.add_row(svc, "[bold green]\u25cf ACTIVE[/bold green]")
            elif status == "inactive":
                table.add_row(svc, "[bold yellow]\u25cf INACTIVE[/bold yellow]")
            else:
                table.add_row(svc, f"[bold red]\u25cf {status.upper()}[/bold red]")
        except Exception:
            table.add_row(svc, "[dim]\u25cf UNKNOWN[/dim]")

    # Network connectivity
    try:
        s = socket.create_connection(("8.8.8.8", 53), timeout=2)
        s.close()
        table.add_row("Internet", "[bold green]\u25cf OK[/bold green]")
    except Exception:
        table.add_row("Internet", "[bold red]\u25cf DOWN[/bold red]")

    return Panel(table, title="[bold]Status Checks[/bold]", border_style="red")


def build_help_panel() -> Panel:
    return Panel(
        "[bold]Keyboard Shortcuts[/bold]\n\n"
        "  [cyan]q[/cyan]      Quit\n"
        "  [cyan]r[/cyan]      Force refresh\n"
        "  [cyan]h[/cyan]      Toggle this help\n"
        "  [cyan]Ctrl+C[/cyan] Graceful shutdown\n",
        title="[bold yellow]Help[/bold yellow]",
        border_style="yellow",
    )


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

def build_layout() -> Layout:
    layout = Layout(name="root")
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
    )

    header = Panel(
        Text(
            " System Monitor Dashboard ",
            style="bold white on blue",
            justify="center",
        ),
        style="blue",
    )
    layout["header"].update(header)

    if SHOW_HELP:
        layout["body"].update(build_help_panel())
        return layout

    layout["body"].split_column(
        Layout(name="top"),
        Layout(name="bottom"),
    )
    layout["top"].split_row(
        Layout(name="info"),
        Layout(name="resources"),
    )
    layout["bottom"].split_row(
        Layout(name="procs"),
        Layout(name="status"),
    )

    layout["info"].update(build_system_info_panel())
    layout["resources"].update(build_resource_panel())
    layout["procs"].update(build_top_processes_panel())
    layout["status"].update(build_status_panel())

    return layout


# ---------------------------------------------------------------------------
# Keyboard listener
# ---------------------------------------------------------------------------

def key_listener():
    global RUNNING, SHOW_HELP
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while RUNNING:
            ch = sys.stdin.read(1)
            if ch == "q":
                RUNNING = False
                break
            elif ch == "r":
                REFRESH_NOW.set()
            elif ch == "h":
                SHOW_HELP = not SHOW_HELP
                REFRESH_NOW.set()
    except Exception:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global RUNNING

    console = Console()
    console.clear()

    # Start keyboard listener only if stdin is a terminal
    if sys.stdin.isatty():
        t = threading.Thread(target=key_listener, daemon=True)
        t.start()

    try:
        with Live(build_layout(), console=console, refresh_per_second=1, screen=True) as live:
            while RUNNING:
                live.update(build_layout())
                for _ in range(20):  # 2s in 0.1s increments
                    if not RUNNING or REFRESH_NOW.is_set():
                        break
                    time.sleep(0.1)
                REFRESH_NOW.clear()
    except KeyboardInterrupt:
        pass
    finally:
        RUNNING = False
        console.clear()
        console.print("[bold green]Dashboard stopped.[/bold green]")


if __name__ == "__main__":
    main()
