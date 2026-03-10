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

You can use the provided `run.sh` script to launch the analysis with different modes.

### Run Hourly Energy Analysis (default)
```bash
./run.sh hourly
```

### Run Daily Energy Analysis
```bash
./run.sh daily
```

### Run Hourly AMP Usage Analysis (Estimated at 120V)
```bash
./run.sh amps
```

## Output

The script creates an `output/` directory and saves the generated plots and data within a timestamped subfolder named after the analyzed XML file (e.g., `output/20260309_233516_Elexicon_Electricity_...xml/`):
- `graph1_hourly_timeseries.png`
- `graph2_avg_hourly_profile.png`
- `graph3_daily_usage.png`
- `graph4_ampere_stats.png`
- `graph5_avg_cost_profile.png` (Average cost profile using tiered rates - only if `TieredRates.txt` is available)
- `graph6_daily_cost.png` (Total daily cost in ¢ - only if `TieredRates.txt` is available)
- `graph7_tier_distribution.png` (Usage and cost split by peak tiers - only if `TieredRates.txt` is available)
- `graph8_usage_heatmap.png` (Heatmap of hourly usage by day - only if `TieredRates.txt` is available)
- `hourly_data_points.csv` (Detailed hourly data including rates and costs)

## Features

- **Tiered Rate Analysis**: Automatically reads `TieredRates.txt` (if available) to calculate costs based on time-of-use (Off-Peak, Mid-Peak, On-Peak) for both weekdays and weekends. All cost visualizations use ¢ as the unit.
- **Dynamic Timezone**: Detects and applies system timezone to all data and labels.
- **Advanced Visualizations**: Includes heatmaps and distribution charts for deeper insights into energy consumption patterns.

## Requirements

The analysis script `analyze_energy.py` searches for all `.xml` files in the project directory. If multiple files are found, it will prompt you to choose one.
