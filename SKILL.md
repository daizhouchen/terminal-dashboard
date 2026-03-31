---
name: terminal-dashboard
description: >
  生成基于终端的实时数据仪表盘，可监控系统资源、项目状态、
  API 健康度等。当用户提到"终端仪表盘"、"CLI dashboard"、
  "命令行监控"、"系统状态"时使用。
---

# Terminal Dashboard Skill

## Workflow

### Step 1: Determine Data Sources

Identify what the user wants to monitor. Common categories:

- **System resources**: CPU, memory, disk, network, load average
- **Service health**: HTTP endpoints, database connections, Redis, message queues
- **Project status**: Git stats, CI/CD pipelines, deployment state
- **Custom metrics**: API response times, error rates, queue depths
- **Logs**: Tailing log files or journal entries

Ask the user which data sources matter. If unclear, default to system resource monitoring.

### Step 2: Generate Dashboard Script

Use `scripts/generate_dashboard.py` to produce a standalone dashboard from a YAML config:

```bash
python3 scripts/generate_dashboard.py <config.yaml> --output <dashboard.py>
```

The generator reads the config and emits a self-contained Python script that uses
the `rich` library for rendering. No runtime dependency on the generator itself.

Supported panel types:
- **metrics** -- Key/value cards with trend arrows (up/down)
- **progress** -- Progress bars for CPU, memory, disk, etc.
- **log** -- Scrolling tail of a log file
- **status** -- Green/yellow/red status lights for service checks

### Step 3: Configure Layout

Edit the YAML config to adjust:

- `title` -- Dashboard title shown at the top
- `refresh_interval` -- Seconds between updates (default 2)
- `layout` -- Grid arrangement, e.g. "2x2", "1x4", "3x1"
- `panels` -- List of panel definitions (type, title, sources/checks)

A default config template lives at `assets/config_template.yaml`.

### Step 4: Run and Iterate

```bash
python3 <generated_dashboard.py>
```

Keyboard shortcuts while running:
- `q` -- quit
- `r` -- force refresh
- `h` -- show help overlay

Ctrl+C also triggers a graceful shutdown.

### Quick Start (no config needed)

Run the bundled example dashboard directly:

```bash
python3 scripts/dashboard_example.py
```

This shows CPU, memory, disk, load average, and top processes out of the box.
