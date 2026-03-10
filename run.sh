#!/bin/bash

# Ensure virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment and installing dependencies..."
    python3 -m venv venv
    ./venv/bin/pip install pandas matplotlib
fi

# Run the analysis script with provided argument
# Default to hourly if no argument provided
./venv/bin/python3 analyze_energy.py
