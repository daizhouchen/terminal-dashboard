# terminal-dashboard

> One command, one config file, one beautiful terminal dashboard.

A [Claude Code](https://claude.ai/code) skill that generates customizable terminal-based real-time dashboards using Python's [Rich](https://github.com/Textualize/rich) library — monitor system resources, services, logs, and custom metrics.

## Features

- **4 Panel Types**

  | Type | Description |
  |------|-------------|
  | `metrics` | Key-value cards with trend arrows (up/down/stable) |
  | `progress` | Color-coded progress bars (green/yellow/red thresholds) |
  | `log` | Scrolling log tail with auto-refresh |
  | `status` | Service health lights (running/stopped/unknown) |

- **YAML Configuration** — Define layout and data sources in a simple config file
- **Configurable Grid Layout** — 1x1, 2x1, 2x2, 3x1, and more
- **Keyboard Shortcuts** — `q` quit, `r` refresh, `h` help
- **ASCII CPU History Chart** — Mini sparkline-style CPU usage graph
- **Graceful Shutdown** — Clean Ctrl+C handling

## Installation

```bash
claude skill add daizhouchen/terminal-dashboard
```

## How It Works

1. Define what to monitor in a YAML config file
2. `scripts/generate_dashboard.py` generates a standalone dashboard script
3. Run the generated script — live updates in your terminal

## Quick Start

```bash
# Generate a dashboard from the default config
python3 scripts/generate_dashboard.py assets/config_template.yaml --output my_dashboard.py

# Run it
python3 my_dashboard.py

# Or run the built-in example directly
python3 scripts/dashboard_example.py
```

## Configuration Example

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

## Trigger Phrases

- "终端仪表盘" / "CLI dashboard"
- "命令行监控" / "系统状态"

## Project Structure

```
terminal-dashboard/
├── SKILL.md                       # Skill definition and workflow
├── scripts/
│   ├── generate_dashboard.py      # Config to dashboard script generator
│   └── dashboard_example.py       # Ready-to-run system monitor example
├── assets/
│   └── config_template.yaml       # Default monitoring config
└── README.md
```

## Requirements

- Python 3.8+
- `rich` (`pip install rich`)
- `psutil` (`pip install psutil`)
- `pyyaml` (`pip install pyyaml`) — for config parsing

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit dashboard |
| `r` | Force refresh |
| `h` | Toggle help overlay |

## License

MIT
