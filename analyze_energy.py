import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import glob
import time
from datetime import datetime, timedelta

# Set seaborn style for better aesthetics
sns.set_theme(style="whitegrid")

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

# 2.5 Load Tiered Rates
rates_file = 'TieredRates.txt'
weekday_rates = {} # hour -> charge
weekend_rates = {} # hour -> charge
weekday_tier_names = {} # hour -> tier_name
weekend_tier_names = {} # hour -> tier_name
tier_names_list = [] # ordered list of tier names for color mapping

if os.path.exists(rates_file):
    print(f"Loading rates from {rates_file}...")
    try:
        # Use skipinitialspace=True in case there are leading spaces after the colon
        rates_df = pd.read_csv(rates_file, sep=':')
        # Clean up column names in case they have leading/trailing spaces
        rates_df.columns = rates_df.columns.str.strip()
        
        # Collect unique tier names in order of appearance
        if 'tier_name' in rates_df.columns:
            for t in rates_df['tier_name'].str.strip():
                if t not in tier_names_list:
                    tier_names_list.append(t)
        
        for _, row in rates_df.iterrows():
            time_range = str(row['time_range']).strip()
            charge = float(row['charge_per_kwh'])
            day_type = str(row['day_type']).strip()
            tier_name = str(row['tier_name']).strip() if 'tier_name' in row else "Other"
            
            start_hour = int(time_range.split('_')[0][:2])
            end_hour = int(time_range.split('_')[2][:2])
            if end_hour == 0: end_hour = 24 # 2400 case
            
            rate_dict = weekday_rates if day_type == 'Weekday' else weekend_rates
            name_dict = weekday_tier_names if day_type == 'Weekday' else weekend_tier_names
            for h in range(start_hour, end_hour):
                rate_dict[h] = charge
                name_dict[h] = tier_name
    except Exception as e:
        print(f"Error parsing {rates_file}: {e}")
else:
    print(f"Warning: {rates_file} not found. Cost analysis will be skipped.")

def get_rate_info(row):
    dt = row['dt_local']
    hour = dt.hour
    if dt.weekday() < 5: # Monday-Friday
        return weekday_rates.get(hour, 0.0), weekday_tier_names.get(hour, "Other")
    else: # Saturday-Sunday
        return weekend_rates.get(hour, 0.0), weekend_tier_names.get(hour, "Other")

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

# Apply Rate and Calculate Cost (¢)
has_rates = bool(weekday_rates and weekend_rates)
if has_rates:
    rate_info = df.apply(get_rate_info, axis=1)
    df['rate_cents'] = rate_info.apply(lambda x: x[0])
    df['tier'] = rate_info.apply(lambda x: x[1])
    df['cost_cents'] = df['usage_kwh'] * df['rate_cents']
else:
    df['rate_cents'] = 0.0
    df['tier'] = 'Other'
    df['cost_cents'] = 0.0

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

# Conditional Cost Analysis
has_rates = bool(weekday_rates and weekend_rates)

if has_rates:
    avg_cost_profile = hourly_df.groupby('hour')['cost_cents'].mean()
    daily_cost_cents = hourly_df.set_index('dt_local').resample('D')['cost_cents'].sum()
    
    # Dynamic tier mapping for colors
    # Use a vibrant palette (Set2 or Pastel1)
    colors = sns.color_palette("Set2", len(tier_names_list))
    tier_colors = {name: color for name, color in zip(tier_names_list, colors)}
    tier_colors['Other'] = '#f0f0f0'

    # Mapping for Graph 4 background coloring
    tier_schedule = []
    for h in range(24):
        # Default to weekday for the profile
        tier_schedule.append(weekday_tier_names.get(h, "Other"))

    tier_usage = hourly_df.groupby('tier')['usage_kwh'].sum()
    tier_cost_cents = hourly_df.groupby('tier')['cost_cents'].sum()

# --- SAVING DATA ---
# Select and rename columns for clarity
csv_df = hourly_df[['dt_local', 'usage_kwh', 'amps', 'rate_cents', 'cost_cents']].copy()
csv_df.columns = [f'Local Time ({tz_name})', 'Usage (kWh)', 'Current (Amps)', 'Rate (¢/kWh)', 'Cost (¢)']

# Save to CSV
csv_filename = 'hourly_data_points.csv'
csv_path = os.path.join(output_dir, csv_filename)
csv_df.to_csv(csv_path, index=False, date_format='%Y-%m-%d %H:%M:%S')

print(f"Data points saved to: {csv_path}")

# --- PLOTTING ---

# Graph 1: Hourly Time Series
plt.figure(figsize=(15, 6))
plt.plot(hourly_df['dt_local'], hourly_df['usage_kwh'], color='black', linewidth=1, zorder=3)

# Add background colors for tiers if available
if has_rates:
    from matplotlib.patches import Patch
    # Plot background for each data point
    # To avoid many rectangles, we can find contiguous blocks of the same tier
    # or just iterate and fill per hour (more straightforward)
    for i in range(len(hourly_df)):
        row = hourly_df.iloc[i]
        dt = row['dt_local']
        tier = row['tier']
        color = tier_colors.get(tier, '#f0f0f0')
        # Fill 1 hour span
        plt.axvspan(dt, dt + timedelta(hours=1), facecolor=color, alpha=0.3, zorder=1)

    # Create custom legend for tiers
    legend_elements = [
        Patch(facecolor=tier_colors.get(name), alpha=0.3, label=name)
        for name in tier_names_list
    ]
    plt.legend(handles=legend_elements, loc='upper left')

plt.title(f'Hourly Electricity Usage (Time Series) - {tz_name}')
plt.xlabel(f'Date ({tz_name})')
plt.ylabel('Usage (kWh)')
plt.grid(True, alpha=0.3, zorder=0)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'graph1_hourly_timeseries.png'))
plt.close()

# Graph 2: Average kWh Profile by Hour
plt.figure(figsize=(10, 5))
plt.plot(avg_kwh_profile.index, avg_kwh_profile.values, marker='o', color='black', zorder=3)

# Add background colors for tiers if available
if has_rates:
    from matplotlib.patches import Patch
    for h in range(24):
        tier = tier_schedule[h]
        color = tier_colors.get(tier, '#f0f0f0')
        plt.axvspan(h - 0.5, h + 0.5, facecolor=color, alpha=0.3, zorder=1)
    
    legend_elements = [
        Patch(facecolor=tier_colors.get(name), alpha=0.3, label=f'{name} (Weekday)')
        for name in tier_names_list
    ]
    plt.legend(handles=legend_elements, loc='upper left')

plt.title(f'Average Electricity Usage by Hour of Day ({tz_name})')
plt.xlabel(f'Hour of Day (24h) - {tz_name}')
plt.ylabel('Average Usage (kWh)')
plt.xticks(range(0, 24))
plt.grid(True, linestyle='--', alpha=0.5, zorder=0)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'graph2_avg_hourly_profile.png'))
plt.close()

# Graph 3: Daily Totals
plt.figure(figsize=(12, 6))
if has_rates:
    # Stacked bar by tier
    # Prepare data: sum usage per day and tier
    # We use dt_local.dt.date for grouping by day
    daily_tier_usage = hourly_df.groupby([hourly_df['dt_local'].dt.date, 'tier'])['usage_kwh'].sum().unstack().fillna(0)
    
    # Use the same tier_colors
    current_tier_colors = [tier_colors.get(tier, '#f0f0f0') for tier in daily_tier_usage.columns]
    
    ax = daily_tier_usage.plot(kind='bar', stacked=True, color=current_tier_colors, ax=plt.gca())
    plt.legend(title="Rate Tier")
    
    # Calculate totals for labels
    totals = daily_tier_usage.sum(axis=1)
else:
    # Regular bar chart if no rates
    ax = daily_usage.plot(kind='bar', color=sns.color_palette("viridis", len(daily_usage)), ax=plt.gca())
    totals = daily_usage

# Add total values on top of bars
for i, total in enumerate(totals):
    if total > 0:
        plt.text(i, total + (totals.max() * 0.01), f'{total:.1f}', 
                 ha='center', va='bottom', rotation=90, fontsize=9)

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

# Plot the stats
plt.plot(amp_stats.index, amp_stats['mean'], label='Average Amps', color='black', marker='o', linewidth=2, zorder=3)
plt.fill_between(amp_stats.index, amp_stats['min'], amp_stats['max'], color='gray', alpha=0.3, label='Min-Max Range', zorder=2)

# Add background colors for tiers if available
if has_rates:
    # We want to draw vertical spans for each hour's tier
    for h in range(24):
        tier = tier_schedule[h]
        color = tier_colors.get(tier, '#f0f0f0')
        plt.axvspan(h - 0.5, h + 0.5, facecolor=color, alpha=0.4, zorder=1)
        
    # Create custom legend for tiers
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_elements = [
        Patch(facecolor=tier_colors.get(name), alpha=0.4, label=f'{name} (Weekday)')
        for name in tier_names_list
    ]
    legend_elements.extend([
        Line2D([0], [0], color='black', marker='o', label='Average Amps'),
        Patch(facecolor='gray', alpha=0.3, label='Min-Max Range')
    ])
    plt.legend(handles=legend_elements, loc='upper left')
else:
    plt.legend()

plt.title(f'Hourly Ampere Profile (at 120V) - Local Time ({tz_name})')
plt.xlabel(f'Hour of Day (24h) - Local Time ({tz_name})')
plt.ylabel('Current (Amperes)')
plt.xticks(range(0, 24))
plt.grid(True, linestyle='--', alpha=0.5, zorder=0)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'graph4_ampere_stats.png'))
plt.close()

if has_rates:
    # Graph 5: Average Cost Profile by Hour
    plt.figure(figsize=(10, 5))
    plt.plot(avg_cost_profile.index, avg_cost_profile.values, marker='s', color='tab:red')
    plt.title(f'Average Electricity Cost by Hour of Day ({tz_name})')
    plt.xlabel(f'Hour of Day (24h) - {tz_name}')
    plt.ylabel('Average Cost (¢)')
    plt.xticks(range(0, 24))
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph5_avg_cost_profile.png'))
    plt.close()

    # Graph 6: Daily Total Cost
    plt.figure(figsize=(12, 5))
    daily_cost_cents.plot(kind='bar', color='tab:red')
    plt.title(f'Daily Electricity Cost Total ({tz_name})')
    plt.xlabel(f'Date ({tz_name})')
    plt.ylabel('Total Daily Cost (¢)')
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph6_daily_cost.png'))
    plt.close()

    # Graph 7: Usage and Cost by Rate Tier
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Get colors for existing tiers in this dataset
    pie_colors1 = [tier_colors.get(t, '#f0f0f0') for t in tier_usage.index]
    tier_usage.plot(kind='pie', autopct='%1.1f%%', ax=ax1, colors=pie_colors1)
    ax1.set_title('Usage (kWh) by Rate Tier')
    ax1.set_ylabel('')

    pie_colors2 = [tier_colors.get(t, '#f0f0f0') for t in tier_cost_cents.index]
    tier_cost_cents.plot(kind='pie', autopct='%1.1f%%', ax=ax2, colors=pie_colors2)
    ax2.set_title('Cost (¢) by Rate Tier')
    ax2.set_ylabel('')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph7_tier_distribution.png'))
    plt.close()

    # Graph 8: Heatmap of Usage by Day and Hour
    pivot_df = hourly_df.pivot_table(index=hourly_df['dt_local'].dt.date, columns='hour', values='usage_kwh')
    plt.figure(figsize=(16, 8))
    sns.heatmap(pivot_df, cmap='YlOrRd', annot=False)
    plt.title(f'Heatmap of Hourly Usage (kWh) - {tz_name}')
    plt.xlabel(f'Hour of Day ({tz_name})')
    plt.ylabel('Date')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph8_usage_heatmap.png'))
    plt.close()

print(f"Processing complete. Graphs and CSV saved in: {output_dir}")