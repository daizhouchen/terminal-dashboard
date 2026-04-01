# terminal-dashboard

> One config, one command -- a live terminal dashboard that actually looks good.

An [OpenClaw](https://openclawskill.ai) skill that generates real-time terminal dashboards from YAML configs using Python's [Rich](https://github.com/Textualize/rich) library. Monitor system resources, service health, logs, and custom metrics without leaving your terminal.

## Preview

```
+-------------------------------+-------------------------------+
| System Info                   | Resources                     |
|                               |  Resource  Bar           %    |
|  Hostname   dev-server-01     |  CPU       ========--   42.3% |
|  Uptime     12d 7h 33m       |  Memory    ===========  78.5% |
|  Load Avg   1.24 ^  (5m:1.1) |  Disk /    =====------  51.2% |
|  CPUs       8                 |  Swap      ==--------   18.0% |
+-------------------------------+-------------------------------+
| Top Processes                 | Status Checks                 |
|  PID   Name          CPU% M% |  Check              Status    |
|  1823  python3       12.3 2.1|  sshd               * ACTIVE  |
|  944   node          8.7  1.5|  cron                * ACTIVE  |
|  1102  postgres      5.2  3.8|  systemd-resolved    * ACTIVE  |
|  772   nginx         2.1  0.9|  Internet            * OK      |
|  CPU History: _.-'^-.._.-'   |                               |
+-------------------------------+-------------------------------+
```

## Panel Types

| Type | Border | Description | Data Sources | Options |
|------|--------|-------------|--------------|---------|
| `metrics` | Blue | Key/value cards with trend arrows (up/down) | `hostname`, `uptime`, `load_average` | `sources` list |
| `progress` | Green | Color-coded progress bars (green <60%, yellow <85%, red 85%+) | `cpu`, `memory`, `disk` | `sources` list |
| `log` | Yellow | Scrolling tail of a log file, auto-refreshed | Any file path | `source` path, `lines` count |
| `status` | Red | Green/yellow/red status lights via `systemctl is-active` | Any systemd service name | `checks` list |

## Installation

```bash
npx @anthropic-ai/claw@latest skill add daizhouchen/terminal-dashboard
```

## Quick Start

### Option 1: Generate from config

```bash
# Generate a standalone dashboard script from a YAML config
python3 scripts/generate_dashboard.py assets/config_template.yaml --output my_dashboard.py

# Run the generated dashboard
python3 my_dashboard.py
```

The generator reads YAML and emits a self-contained Python script. The generated script has no runtime dependency on the generator itself.

### Option 2: Run the built-in example

```bash
python3 scripts/dashboard_example.py
```

The example dashboard monitors in a 2x2 grid:
- **System Info** -- hostname, uptime, load average with trend arrows, CPU count
- **Resources** -- CPU, memory, disk, and swap usage with color-coded progress bars
- **Top Processes** -- top 5 processes by CPU usage plus a mini ASCII sparkline chart of CPU history (rolling 60 samples)
- **Status Checks** -- systemd service status for sshd, cron, systemd-resolved, and internet connectivity (DNS to 8.8.8.8)

## Configuration Guide

The full YAML config reference with all supported options:

```yaml
title: "System Monitor"
refresh_interval: 2
layout: "2x2"
panels:
  - type: metrics
    title: "System Info"
    sources: [hostname, uptime, load_average]
  - type: progress
    title: "Resources"
    sources: [cpu, memory, disk]
  - type: log
    title: "Recent Logs"
    source: "/var/log/syslog"
    lines: 10
  - type: status
    title: "Services"
    checks: [nginx, mysql, redis]
```

### Top-level keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `title` | string | `"Dashboard"` | Title shown in the generated script header |
| `refresh_interval` | number | `2` | Seconds between data refreshes |
| `layout` | string | `"2x2"` | Grid arrangement as `ROWSxCOLS` (e.g. `1x4`, `2x2`, `3x1`) |
| `panels` | list | `[]` | Ordered list of panel definitions filling the grid left-to-right, top-to-bottom |

### Panel-specific keys

| Panel type | Key | Type | Default | Description |
|------------|-----|------|---------|-------------|
| `metrics` | `sources` | list | `[hostname, uptime, load_average]` | Which metric rows to display |
| `progress` | `sources` | list | `[cpu, memory, disk]` | Which resource bars to display |
| `log` | `source` | string | `"/var/log/syslog"` | Path to the log file to tail |
| `log` | `lines` | int | `10` | Number of tail lines to show |
| `status` | `checks` | list | `[]` | Systemd service names to check |

Grid cells beyond the panel count are filled with an empty placeholder panel.

## How It Works

```
config.yaml --> generate_dashboard.py --> dashboard.py --> terminal
   (YAML)         (code generator)      (standalone)     (Rich Live)
```

1. **Define** -- Write a YAML config specifying title, refresh rate, layout grid, and panels
2. **Generate** -- `generate_dashboard.py` reads the config and emits a complete Python script with all panel-builder functions baked in
3. **Run** -- Execute the generated script; it uses `rich.live.Live` for full-screen real-time rendering
4. **Iterate** -- Edit the config, regenerate, and rerun

The config can also be JSON. If `pyyaml` is not installed, a built-in minimal YAML parser handles simple configs.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit the dashboard |
| `r` | Force an immediate refresh |
| `h` | Toggle the help overlay |
| `Ctrl+C` | Graceful shutdown with cleanup |

Keyboard input is captured via a background thread using `tty.setraw()`. Terminal settings are restored on exit.

## Trigger Phrases

This skill activates when the user mentions:

| Chinese | English |
|---------|---------|
| "终端仪表盘" | "CLI dashboard" |
| "命令行监控" | "command line monitoring" |
| "系统状态" | "system status" |

## Project Structure

```
terminal-dashboard/
├── SKILL.md                       # Skill definition, workflow, and trigger config
├── README.md                      # This file
├── .gitignore
├── scripts/
│   ├── generate_dashboard.py      # YAML/JSON config --> standalone dashboard script
│   └── dashboard_example.py       # Ready-to-run 2x2 system monitor (no config needed)
├── assets/
│   └── config_template.yaml       # Default YAML config template
└── references/                    # Reserved for reference materials
```

## Customization Guide

**Change the grid layout** -- Set `layout` to any `ROWSxCOLS` value. A `1x4` layout produces a single row of four panels; `3x1` stacks three panels vertically.

**Add more services to monitor** -- Extend the `checks` list in a `status` panel with any systemd unit name.

**Tail a different log** -- Change the `source` path and `lines` count in a `log` panel to point at any readable file.

**Adjust refresh speed** -- Lower `refresh_interval` for faster updates (increases CPU usage), raise it for lighter polling.

**Modify the generated script** -- The output of `generate_dashboard.py` is plain Python. Edit it directly to add custom panels, change colors, or integrate additional data sources.

## Requirements

- Python 3.8+

```bash
pip install rich psutil pyyaml
```

| Package | Purpose | Required? |
|---------|---------|-----------|
| `rich` | Terminal rendering (Live, Layout, Panel, ProgressBar) | Yes |
| `psutil` | CPU, memory, disk, swap, process info | Yes (for progress/process panels) |
| `pyyaml` | YAML config parsing | Optional (fallback parser included) |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add or improve panel types in `scripts/generate_dashboard.py`
4. Test with `scripts/dashboard_example.py`
5. Submit a pull request

## License

MIT
