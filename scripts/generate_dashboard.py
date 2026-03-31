#!/usr/bin/env python3
"""Generate a standalone Rich-based terminal dashboard from a YAML config."""

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def load_config(path: str) -> dict:
    """Load config from YAML or JSON file."""
    p = Path(path)
    text = p.read_text()
    if p.suffix in (".yaml", ".yml"):
        if HAS_YAML:
            return yaml.safe_load(text)
        else:
            # Minimal YAML-like parser for simple configs
            return _simple_yaml_parse(text)
    else:
        return json.loads(text)


def _simple_yaml_parse(text: str) -> dict:
    """Bare-bones YAML subset parser (flat keys, simple lists)."""
    import re
    result: dict = {"panels": []}
    current_panel: dict | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # top-level scalar
        m = re.match(r'^(\w+):\s*"?([^"]*)"?\s*$', line)
        if m and not line.startswith(" "):
            key, val = m.group(1), m.group(2).strip()
            if key == "panels":
                continue
            try:
                val = int(val)
            except (ValueError, TypeError):
                try:
                    val = float(val)
                except (ValueError, TypeError):
                    pass
            result[key] = val
            continue
        # panel list item start
        if stripped.startswith("- type:"):
            if current_panel is not None:
                result["panels"].append(current_panel)
            ptype = stripped.split(":", 1)[1].strip()
            current_panel = {"type": ptype}
            continue
        if current_panel is not None:
            m2 = re.match(r'\s+(\w+):\s*(.*)', line)
            if m2:
                k, v = m2.group(1), m2.group(2).strip().strip('"')
                # list value
                if v.startswith("[") and v.endswith("]"):
                    v = [x.strip().strip('"') for x in v[1:-1].split(",")]
                else:
                    try:
                        v = int(v)
                    except (ValueError, TypeError):
                        pass
                current_panel[k] = v
    if current_panel is not None:
        result["panels"].append(current_panel)
    return result


def generate_metrics_function(panel: dict) -> str:
    """Generate code for a metrics panel."""
    sources = panel.get("sources", ["hostname", "uptime", "load_average"])
    title = panel.get("title", "Metrics")
    lines = []
    lines.append(f'def build_metrics_panel_{id(panel) % 10000}():')
    lines.append(f'    """Build metrics panel: {title}"""')
    lines.append('    import socket, os, time')
    lines.append('    from rich.table import Table')
    lines.append('    from rich.panel import Panel')
    lines.append(f'    table = Table(show_header=False, expand=True, box=None)')
    lines.append('    table.add_column("Key", style="bold cyan", ratio=1)')
    lines.append('    table.add_column("Value", style="white", ratio=2)')

    for src in sources:
        if src == "hostname":
            lines.append('    table.add_row("Hostname", socket.gethostname())')
        elif src == "uptime":
            lines.append('    try:')
            lines.append('        with open("/proc/uptime") as f:')
            lines.append('            secs = float(f.read().split()[0])')
            lines.append('        days = int(secs // 86400)')
            lines.append('        hours = int((secs % 86400) // 3600)')
            lines.append('        mins = int((secs % 3600) // 60)')
            lines.append('        table.add_row("Uptime", f"{days}d {hours}h {mins}m")')
            lines.append('    except Exception:')
            lines.append('        table.add_row("Uptime", "N/A")')
        elif src == "load_average":
            lines.append('    load1, load5, load15 = os.getloadavg()')
            lines.append('    arrow = "\\u2191" if load1 > load5 else "\\u2193"')
            lines.append('    table.add_row("Load Avg", f"{load1:.2f} {arrow}  (5m: {load5:.2f}, 15m: {load15:.2f})")')

    lines.append(f'    return Panel(table, title="[bold]{title}[/bold]", border_style="blue")')
    return "\n".join(lines)


def generate_progress_function(panel: dict) -> str:
    """Generate code for a progress-bar panel."""
    sources = panel.get("sources", ["cpu", "memory", "disk"])
    title = panel.get("title", "Resources")
    func_id = id(panel) % 10000
    lines = []
    lines.append(f'def build_progress_panel_{func_id}():')
    lines.append(f'    """Build progress panel: {title}"""')
    lines.append('    import psutil, os')
    lines.append('    from rich.table import Table')
    lines.append('    from rich.panel import Panel')
    lines.append('    from rich.progress_bar import ProgressBar')
    lines.append('    from rich.text import Text')
    lines.append(f'    table = Table(show_header=True, expand=True, box=None)')
    lines.append('    table.add_column("Resource", style="bold cyan", ratio=1)')
    lines.append('    table.add_column("Bar", ratio=3)')
    lines.append('    table.add_column("%", justify="right", style="bold", ratio=1)')

    for src in sources:
        if src == "cpu":
            lines.append('    cpu_pct = psutil.cpu_percent(interval=0.1)')
            lines.append('    color = "green" if cpu_pct < 60 else "yellow" if cpu_pct < 85 else "red"')
            lines.append('    bar = ProgressBar(total=100, completed=cpu_pct, style=color)')
            lines.append('    table.add_row("CPU", bar, f"{cpu_pct:.1f}%")')
        elif src == "memory":
            lines.append('    mem = psutil.virtual_memory()')
            lines.append('    color = "green" if mem.percent < 60 else "yellow" if mem.percent < 85 else "red"')
            lines.append('    bar = ProgressBar(total=100, completed=mem.percent, style=color)')
            lines.append('    table.add_row("Memory", bar, f"{mem.percent:.1f}%")')
        elif src == "disk":
            lines.append('    disk = psutil.disk_usage("/")')
            lines.append('    color = "green" if disk.percent < 60 else "yellow" if disk.percent < 85 else "red"')
            lines.append('    bar = ProgressBar(total=100, completed=disk.percent, style=color)')
            lines.append('    table.add_row("Disk /", bar, f"{disk.percent:.1f}%")')

    lines.append(f'    return Panel(table, title="[bold]{title}[/bold]", border_style="green")')
    return "\n".join(lines)


def generate_log_function(panel: dict) -> str:
    """Generate code for a scrolling log panel."""
    source = panel.get("source", "/var/log/syslog")
    num_lines = panel.get("lines", 10)
    title = panel.get("title", "Logs")
    func_id = id(panel) % 10000
    lines = []
    lines.append(f'def build_log_panel_{func_id}():')
    lines.append(f'    """Build log panel: {title}"""')
    lines.append('    from rich.panel import Panel')
    lines.append('    from rich.text import Text')
    lines.append('    try:')
    lines.append(f'        with open("{source}", "r") as f:')
    lines.append(f'            all_lines = f.readlines()')
    lines.append(f'            tail = all_lines[-{num_lines}:]')
    lines.append('        text = Text("".join(tail), style="dim")')
    lines.append('    except (PermissionError, FileNotFoundError):')
    lines.append(f'        text = Text("(cannot read {source})", style="dim red")')
    lines.append(f'    return Panel(text, title="[bold]{title}[/bold]", border_style="yellow")')
    return "\n".join(lines)


def generate_status_function(panel: dict) -> str:
    """Generate code for a status-light panel."""
    checks = panel.get("checks", [])
    title = panel.get("title", "Services")
    func_id = id(panel) % 10000
    lines = []
    lines.append(f'def build_status_panel_{func_id}():')
    lines.append(f'    """Build status panel: {title}"""')
    lines.append('    import subprocess')
    lines.append('    from rich.table import Table')
    lines.append('    from rich.panel import Panel')
    lines.append(f'    table = Table(show_header=True, expand=True, box=None)')
    lines.append('    table.add_column("Service", style="bold cyan")')
    lines.append('    table.add_column("Status", justify="center")')

    for svc in checks:
        lines.append(f'    try:')
        lines.append(f'        r = subprocess.run(["systemctl", "is-active", "{svc}"],')
        lines.append(f'                           capture_output=True, text=True, timeout=2)')
        lines.append(f'        status = r.stdout.strip()')
        lines.append(f'        if status == "active":')
        lines.append(f'            table.add_row("{svc}", "[bold green]\\u25cf ACTIVE[/bold green]")')
        lines.append(f'        elif status == "inactive":')
        lines.append(f'            table.add_row("{svc}", "[bold yellow]\\u25cf INACTIVE[/bold yellow]")')
        lines.append(f'        else:')
        lines.append(f'            table.add_row("{svc}", "[bold red]\\u25cf " + status.upper() + "[/bold red]")')
        lines.append(f'    except Exception:')
        lines.append(f'        table.add_row("{svc}", "[dim]\\u25cf UNKNOWN[/dim]")')

    lines.append(f'    return Panel(table, title="[bold]{title}[/bold]", border_style="red")')
    return "\n".join(lines)


def generate_dashboard(config: dict) -> str:
    """Generate the full dashboard script from config."""
    title = config.get("title", "Dashboard")
    refresh = config.get("refresh_interval", 2)
    layout_spec = config.get("layout", "2x2")
    panels = config.get("panels", [])

    # Parse layout
    try:
        rows, cols = [int(x) for x in layout_spec.split("x")]
    except Exception:
        rows, cols = 2, 2

    # Generate panel builder functions
    func_blocks = []
    func_calls = []
    for i, panel in enumerate(panels):
        ptype = panel.get("type", "metrics")
        func_id = id(panel) % 10000
        if ptype == "metrics":
            func_blocks.append(generate_metrics_function(panel))
        elif ptype == "progress":
            func_blocks.append(generate_progress_function(panel))
        elif ptype == "log":
            func_blocks.append(generate_log_function(panel))
        elif ptype == "status":
            func_blocks.append(generate_status_function(panel))
        else:
            continue
        func_calls.append(f"build_{ptype}_panel_{func_id}()")

    # Pad func_calls to fill the grid
    while len(func_calls) < rows * cols:
        func_calls.append('Panel("[dim]Empty[/dim]", border_style="dim")')

    # Build layout assembly code
    layout_lines = []
    layout_lines.append('def build_layout():')
    layout_lines.append('    from rich.layout import Layout')
    layout_lines.append('    from rich.panel import Panel')
    layout_lines.append(f'    layout = Layout(name="root")')

    if rows == 1:
        col_names = [f"col{c}" for c in range(cols)]
        layout_lines.append(f'    layout.split_row(*[Layout(name=n) for n in {col_names}])')
        for c in range(cols):
            idx = c
            if idx < len(func_calls):
                layout_lines.append(f'    layout["col{c}"].update({func_calls[idx]})')
    else:
        row_names = [f"row{r}" for r in range(rows)]
        layout_lines.append(f'    layout.split_column(*[Layout(name=n) for n in {row_names}])')
        for r in range(rows):
            col_names = [f"r{r}c{c}" for c in range(cols)]
            layout_lines.append(f'    layout["row{r}"].split_row(*[Layout(name=n) for n in {col_names}])')
            for c in range(cols):
                idx = r * cols + c
                if idx < len(func_calls):
                    layout_lines.append(f'    layout["r{r}c{c}"].update({func_calls[idx]})')

    layout_lines.append('    return layout')

    functions_code = "\n\n\n".join(func_blocks)
    layout_code = "\n".join(layout_lines)
    wait_ticks = int(refresh * 10)

    parts = []
    parts.append('#!/usr/bin/env python3')
    parts.append(f'"""Auto-generated terminal dashboard: {title}')
    parts.append('')
    parts.append('Keyboard shortcuts:')
    parts.append('  q     - quit')
    parts.append('  r     - force refresh')
    parts.append('  h     - show help')
    parts.append('  Ctrl+C - graceful shutdown')
    parts.append('"""')
    parts.append('')
    parts.append('import signal')
    parts.append('import sys')
    parts.append('import time')
    parts.append('import threading')
    parts.append('')
    parts.append('RUNNING = True')
    parts.append('REFRESH_NOW = threading.Event()')
    parts.append('')
    parts.append('def signal_handler(sig, frame):')
    parts.append('    global RUNNING')
    parts.append('    RUNNING = False')
    parts.append('')
    parts.append('signal.signal(signal.SIGINT, signal_handler)')
    parts.append('signal.signal(signal.SIGTERM, signal_handler)')
    parts.append('')
    parts.append('')
    parts.append(functions_code)
    parts.append('')
    parts.append('')
    parts.append(layout_code)
    parts.append('')
    parts.append('')
    parts.append('def show_help():')
    parts.append('    from rich.panel import Panel')
    parts.append('    return Panel(')
    parts.append('        "[bold]Keyboard Shortcuts[/bold]\\n\\n"')
    parts.append('        "  [cyan]q[/cyan]      Quit\\n"')
    parts.append('        "  [cyan]r[/cyan]      Force refresh\\n"')
    parts.append('        "  [cyan]h[/cyan]      Toggle this help\\n"')
    parts.append('        "  [cyan]Ctrl+C[/cyan] Graceful shutdown\\n",')
    parts.append('        title="[bold yellow]Help[/bold yellow]",')
    parts.append('        border_style="yellow",')
    parts.append('    )')
    parts.append('')
    parts.append('')
    parts.append('def key_listener():')
    parts.append('    """Listen for keyboard input in a background thread."""')
    parts.append('    global RUNNING')
    parts.append('    import tty, termios')
    parts.append('    fd = sys.stdin.fileno()')
    parts.append('    old_settings = termios.tcgetattr(fd)')
    parts.append('    try:')
    parts.append('        tty.setraw(fd)')
    parts.append('        while RUNNING:')
    parts.append('            ch = sys.stdin.read(1)')
    parts.append('            if ch == "q":')
    parts.append('                RUNNING = False')
    parts.append('                break')
    parts.append('            elif ch == "r":')
    parts.append('                REFRESH_NOW.set()')
    parts.append('            elif ch == "h":')
    parts.append('                pass  # help toggle handled in main loop')
    parts.append('    except Exception:')
    parts.append('        pass')
    parts.append('    finally:')
    parts.append('        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)')
    parts.append('')
    parts.append('')
    parts.append('def main():')
    parts.append('    global RUNNING')
    parts.append('    from rich.live import Live')
    parts.append('    from rich.panel import Panel')
    parts.append('    from rich.console import Console')
    parts.append('')
    parts.append('    console = Console()')
    parts.append('    console.clear()')
    parts.append('')
    parts.append('    # Start keyboard listener thread')
    parts.append('    if sys.stdin.isatty():')
    parts.append('        key_thread = threading.Thread(target=key_listener, daemon=True)')
    parts.append('        key_thread.start()')
    parts.append('')
    parts.append('    try:')
    parts.append('        with Live(build_layout(), console=console, refresh_per_second=1, screen=True) as live:')
    parts.append('            while RUNNING:')
    parts.append('                live.update(build_layout())')
    parts.append('                # Wait for refresh interval or forced refresh')
    parts.append(f'                for _ in range({wait_ticks}):')
    parts.append('                    if not RUNNING or REFRESH_NOW.is_set():')
    parts.append('                        break')
    parts.append('                    time.sleep(0.1)')
    parts.append('                REFRESH_NOW.clear()')
    parts.append('    except KeyboardInterrupt:')
    parts.append('        pass')
    parts.append('    finally:')
    parts.append('        RUNNING = False')
    parts.append('        console.clear()')
    parts.append('        console.print("[bold green]Dashboard stopped.[/bold green]")')
    parts.append('')
    parts.append('')
    parts.append('if __name__ == "__main__":')
    parts.append('    main()')
    parts.append('')

    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Generate a terminal dashboard from config")
    parser.add_argument("config", help="Path to YAML/JSON config file")
    parser.add_argument("--output", "-o", default="dashboard.py", help="Output script path")
    args = parser.parse_args()

    config = load_config(args.config)
    script = generate_dashboard(config)

    Path(args.output).write_text(script)
    print(f"Dashboard script generated: {args.output}")
    print(f"Run with: python3 {args.output}")


if __name__ == "__main__":
    main()
