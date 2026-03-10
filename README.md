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
- `hourly_data_points.csv` (all hourly data points in local time)

## Requirements

The analysis script `analyze_energy.py` searches for all `.xml` files in the project directory. If multiple files are found, it will prompt you to choose one.
