# Green Button Energy Analysis Tool

This tool parses Green Button (ESPI) XML data files and generates plots for energy (kWh) and estimated current (Amperes) usage.

## Prerequisites

- Python 3.x
- `venv` module for Python

## Setup

The project uses a virtual environment to manage dependencies. To set it up manually:

```bash
python3 -m venv venv
./venv/bin/pip install pandas matplotlib numpy openpyxl seaborn
```

## Usage

Simply run the provided `run.sh` script to launch the interactive analysis tool.

```bash
./run.sh
```

The tool will:
1. Clear the console and show a colorful interface.
2. Automatically detect `.xml` files. If multiple are found, you'll be prompted to choose one.
3. Show the available date range and the last used date range (if any), allowing you to optionally filter it or reuse the last range by pressing 'L'.
4. Detect your system timezone and apply it to all graphs and data points.
5. Generate up to 8 different visualizations and a detailed CSV file.

## Output

The script creates an `output/` directory and saves the generated plots and data within a timestamped subfolder reflecting the analyzed date range (e.g., `output/20260310_003516_2024-03-09_to_2026-03-09/`):

### Hourly Energy & Ampere Graphs
- `graph1_hourly_timeseries.png`: Hourly usage with background colored by rate tiers.
- `graph2_hourly_avg_profile.png`: Average hourly profile (24h) with background colored by rate tiers.
- `graph3_hourly_ampere_stats.png`: Estimated Ampere stats (Min/Max/Avg) at 120V with background colored by rate tiers.
- `graph4_hourly_avg_cost_profile.png`: Average hourly cost profile with background colored by rate tiers (Requires `TieredRates.txt`).
- `graph5_hourly_usage_heatmap.png`: Heatmap showing hourly usage patterns across all analyzed days.

### Daily Energy & Cost Graphs
- `graph6_daily_usage.png`: Daily usage stacked by rate tiers with totals on top.
- `graph7_daily_cost.png`: Daily cost totals stacked by rate tiers with totals on top (Requires `TieredRates.txt`).

### Period Summary Graphs
- `graph8_tier_distribution.png`: Pie charts showing usage and cost split by rate tiers for the entire period.

### Raw Data
- `hourly_data_points.csv`: Detailed hourly data points including timestamps (local timezone), kWh usage, estimated Amps, applicable rates (¢), and calculated cost (¢).

## Features

- **Interactive Workflow**: Easy file selection and custom date range filtering directly from the terminal.
- **Dynamic Timezone**: Automatically detects and applies system timezone (e.g., EDT, EST, PDT) to all data and labels.
- **Customizable Tiered Rates**: Use `TieredRates.txt` to define peak tiers, costs (¢/kWh), and custom colors (Hex) for graphs.
- **Colorful Terminal Output**: Uses ANSI colors to provide clear feedback and progress updates.
- **Professional Visualizations**: High-quality plots using `matplotlib` and `seaborn` for deeper insights. Default colors are provided even if `TieredRates.txt` is missing for a consistent look.

## Configuration (TieredRates.txt)

If available, the tool reads `TieredRates.txt` to calculate costs and color-code graphs. The file uses a colon-separated format with the following headers:
`time_range:charge_per_kwh:currency_to_display:day_type:tier_name:color_code`

Example:
`0700_till_1100:18.2:¢/kWh:Weekday:On-Peak:#ffaaa5`
