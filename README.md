# Green Button Energy Analysis Tool

This tool parses Green Button (ESPI) XML data files and generates plots for energy (kWh) and estimated current (Amperes) usage.

## Prerequisites

- Python 3.x
- `venv` module for Python

## Setup

The project uses a virtual environment to manage dependencies. To set it up manually:

```bash
python3 -m venv venv
./venv/bin/pip install pandas matplotlib
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

The script saves the generated plots as PNG files in the project directory:
- `energy_usage_hourly.png`
- `energy_usage_daily.png`
- `amp_usage_hourly.png`

## Requirements

The analysis script `analyze_energy.py` expects the input XML file to be named `Elexicon_Electricity_NonInterval_2026-02-07_2026-03-09.xml` in the same directory.
