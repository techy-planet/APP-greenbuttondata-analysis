import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt

# 1. Load and Parse the XML File
# Ensure the filename matches your local file path
filename = 'Elexicon_Electricity_NonInterval_2024-03-09_2026-03-09.xml'
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

# Convert to kWh
df['usage_kwh'] = (df['value'] * (10 ** multiplier)) / 1000.0

# Convert Timestamps to Local Time (EST is UTC-5)
df['dt_utc'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
df['dt_local'] = df['dt_utc'] - pd.Timedelta(hours=5)

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
daily_usage = hourly_df.groupby(hourly_df['dt_local'].dt.date)['usage_kwh'].sum()

# --- PLOTTING ---

# Graph 1: Hourly Time Series
plt.figure(figsize=(15, 6))
plt.plot(hourly_df['dt_local'], hourly_df['usage_kwh'], color='tab:blue', linewidth=1)
plt.title('Hourly Electricity Usage (Time Series)')
plt.xlabel('Date')
plt.ylabel('Usage (kWh)')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('graph1_hourly_timeseries.png')
plt.show()

# Graph 2: Average kWh Profile by Hour
plt.figure(figsize=(10, 5))
plt.plot(avg_kwh_profile.index, avg_kwh_profile.values, marker='o', color='tab:orange')
plt.title('Average Electricity Usage by Hour of Day')
plt.xlabel('Hour of Day (24h)')
plt.ylabel('Average Usage (kWh)')
plt.xticks(range(0, 24))
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig('graph2_avg_hourly_profile.png')
plt.show()

# Graph 3: Daily Totals
plt.figure(figsize=(12, 5))
daily_usage.plot(kind='bar', color='tab:green')
plt.title('Daily Electricity Usage Total')
plt.xlabel('Date')
plt.ylabel('Total Daily Usage (kWh)')
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig('graph3_daily_usage.png')
plt.show()

# Graph 4: Ampere Stats Profile (Min, Max, Avg)
plt.figure(figsize=(12, 6))
plt.plot(amp_stats.index, amp_stats['mean'], label='Average Amps', color='blue', marker='o', linewidth=2)
plt.fill_between(amp_stats.index, amp_stats['min'], amp_stats['max'], color='blue', alpha=0.2, label='Min-Max Range')
plt.title('Hourly Ampere Profile (at 120V)')
plt.xlabel('Hour of Day (24h)')
plt.ylabel('Current (Amperes)')
plt.xticks(range(0, 24))
plt.legend()
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig('graph4_ampere_stats.png')
plt.show()

print("Processing complete. Graphs saved with 'graph_' prefixes.")