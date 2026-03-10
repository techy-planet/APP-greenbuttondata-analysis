import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
import os
import glob
import time
from datetime import datetime, timedelta

# 1. Choose XML File
xml_files = glob.glob('*.xml')
if not xml_files:
    print("No XML files found in current directory.")
    exit(1)

if len(xml_files) == 1:
    filename = xml_files[0]
else:
    print("Multiple XML files found:")
    for i, f in enumerate(xml_files):
        print(f"{chr(ord('a') + i)}) {f}")
    choice = input("Select a file (a, b, c, ...): ").strip().lower()
    idx = ord(choice) - ord('a')
    if 0 <= idx < len(xml_files):
        filename = xml_files[idx]
    else:
        print("Invalid choice. Exiting.")
        exit(1)

# Create output folder
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_base = "output"
folder_name = f"{timestamp}_{os.path.basename(filename)}"
output_dir = os.path.join(output_base, folder_name)
os.makedirs(output_dir, exist_ok=True)

print(f"Analyzing {filename}...")
print(f"Results will be saved in: {output_dir}")

ns = {'espi': 'http://naesb.org/espi', 'atom': 'http://www.w3.org/2005/Atom'}

tree = ET.parse(filename)
root = tree.getroot()

# 2. Extract Interval Data
data = []
for block in root.findall('.//espi:IntervalBlock', ns):
    for reading in block.findall('espi:IntervalReading', ns):
        start = int(reading.find('.//espi:start', ns).text)
        duration_node = reading.find('.//espi:duration', ns)
        duration = int(duration_node.text) if duration_node is not None else 0
        value = int(reading.find('espi:value', ns).text)
        data.append({'timestamp': start, 'duration': duration, 'value': value})

df = pd.DataFrame(data)

# 3. Data Transformation
# Get multiplier from ReadingType (e.g., -3 for Wh)
reading_type = root.find('.//espi:ReadingType', ns)
multiplier = int(reading_type.find('espi:powerOfTenMultiplier', ns).text)

# Detect System Timezone
# Use current system timezone and its offset
local_now = datetime.now().astimezone()
tz_name = local_now.tzname()
tz_offset_seconds = local_now.utcoffset().total_seconds()

print(f"Detected System Timezone: {tz_name} (Offset: {tz_offset_seconds/3600:g}h)")

# Convert to kWh
df['usage_kwh'] = (df['value'] * (10 ** multiplier)) / 1000.0

# Convert Timestamps to Local Time
df['dt_utc'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
df['dt_local'] = df['dt_utc'] + timedelta(seconds=tz_offset_seconds)

# Calculate Amperes (Assuming 120V residential supply)
voltage = 120
df['amps'] = (df['usage_kwh'] * 1000) / voltage

# 4. Filter for Hourly Data and Sort
# We filter for duration=3600 to ignore daily summaries or partial reads
hourly_df = df[df['duration'] == 3600].copy()
hourly_df = hourly_df.sort_values('dt_local')

# 5. Prepare Aggregations
hourly_df['hour'] = hourly_df['dt_local'].dt.hour

# Profile by hour of day
avg_kwh_profile = hourly_df.groupby('hour')['usage_kwh'].mean()
amp_stats = hourly_df.groupby('hour')['amps'].agg(['min', 'max', 'mean'])

# Daily totals
daily_usage = hourly_df.set_index('dt_local').resample('D')['usage_kwh'].sum()

# --- SAVING DATA ---
# Select and rename columns for clarity
csv_df = hourly_df[['dt_local', 'usage_kwh', 'amps']].copy()
csv_df.columns = [f'Local Time ({tz_name})', 'Usage (kWh)', 'Current (Amps)']

# Save to CSV
csv_filename = 'hourly_data_points.csv'
csv_path = os.path.join(output_dir, csv_filename)
csv_df.to_csv(csv_path, index=False, date_format='%Y-%m-%d %H:%M:%S')

print(f"Data points saved to: {csv_path}")

# --- PLOTTING ---

# Graph 1: Hourly Time Series
plt.figure(figsize=(15, 6))
plt.plot(hourly_df['dt_local'], hourly_df['usage_kwh'], color='tab:blue', linewidth=1)
plt.title(f'Hourly Electricity Usage (Time Series) - {tz_name}')
plt.xlabel(f'Date ({tz_name})')
plt.ylabel('Usage (kWh)')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'graph1_hourly_timeseries.png'))
plt.close()

# Graph 2: Average kWh Profile by Hour
plt.figure(figsize=(10, 5))
plt.plot(avg_kwh_profile.index, avg_kwh_profile.values, marker='o', color='tab:orange')
plt.title(f'Average Electricity Usage by Hour of Day ({tz_name})')
plt.xlabel(f'Hour of Day (24h) - {tz_name}')
plt.ylabel('Average Usage (kWh)')
plt.xticks(range(0, 24))
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'graph2_avg_hourly_profile.png'))
plt.close()

# Graph 3: Daily Totals
plt.figure(figsize=(12, 5))
daily_usage.plot(kind='bar', color='tab:green')
plt.title(f'Daily Electricity Usage Total ({tz_name})')
plt.xlabel(f'Date ({tz_name})')
plt.ylabel('Total Daily Usage (kWh)')
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'graph3_daily_usage.png'))
plt.close()

# Graph 4: Ampere Stats Profile (Min, Max, Avg)
plt.figure(figsize=(12, 6))
plt.plot(amp_stats.index, amp_stats['mean'], label='Average Amps', color='blue', marker='o', linewidth=2)
plt.fill_between(amp_stats.index, amp_stats['min'], amp_stats['max'], color='blue', alpha=0.2, label='Min-Max Range')
plt.title(f'Hourly Ampere Profile (at 120V) - Local Time ({tz_name})')
plt.xlabel(f'Hour of Day (24h) - Local Time ({tz_name})')
plt.ylabel('Current (Amperes)')
plt.xticks(range(0, 24))
plt.legend()
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'graph4_ampere_stats.png'))
plt.close()

print(f"Processing complete. Graphs and CSV saved in: {output_dir}")