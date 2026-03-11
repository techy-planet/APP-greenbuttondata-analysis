import glob
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# ANSI Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_GREEN = "\033[32m"
C_CYAN = "\033[36m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_MAGENTA = "\033[35m"


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(text):
    print(f"\n{C_BOLD}{C_CYAN}{'=' * 10} {text} {'=' * 10}{C_RESET}")


def print_success(text):
    print(f"{C_GREEN}✓ {text}{C_RESET}")


def print_warning(text):
    print(f"{C_YELLOW}! {text}{C_RESET}")


def print_error(text):
    print(f"{C_RED}✗ {text}{C_RESET}")


def print_info(text):
    print(f"{C_MAGENTA}ℹ {text}{C_RESET}")


# Clear console at start
clear_console()
print_header("Green Button Energy Analysis")

# Set seaborn style for better aesthetics
sns.set_theme(style="whitegrid")

# 1. Choose XML File
xml_files = sorted(glob.glob('*.xml'))
if not xml_files:
    print_error("No XML files found in current directory.")
    exit(1)

if len(xml_files) == 1:
    filename = xml_files[0]
    print_success(f"Automatically selected: {C_BOLD}{filename}{C_RESET}")
else:
    print(f"{C_BOLD}Multiple XML files found:{C_RESET}")
    for i, f in enumerate(xml_files):
        print(f"  {C_YELLOW}{chr(ord('a') + i)}){C_RESET} {f}")

    while True:
        choice = input(f"\nSelect a file ({C_YELLOW}a, b, c, ...{C_RESET}): ").strip().lower()
        if not choice:
            filename = xml_files[0]
            print_info(f"Using default: {filename}")
            break
        idx = ord(choice) - ord('a')
        if 0 <= idx < len(xml_files):
            filename = xml_files[idx]
            break
        else:
            print_error("Invalid choice. Please try again.")

print_info(f"Analyzing {C_BOLD}{filename}{C_RESET}...")

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
weekday_rates = {}  # hour -> charge
weekend_rates = {}  # hour -> charge
weekday_tier_names = {}  # hour -> tier_name
weekend_tier_names = {}  # hour -> tier_name

# Default colors (eye-soothing palette)
DEFAULT_COLORS = {
    'Off-Peak': '#a8e6cf',
    'Mid-Peak': '#ffd3b6',
    'On-Peak': '#ffaaa5',
    'Other': '#ff4d4d'
}
tier_colors = DEFAULT_COLORS.copy()
tier_names_list = []  # ordered list of tier names for color mapping


# Default Tier Logic (used when TieredRates.txt is missing)
def get_default_tier(hour):
    # Default Night Time: 10 PM (22:00) to 7 AM (07:00)
    if hour >= 22 or hour < 7:
        return 'Off-Peak'
    return 'Other'


if os.path.exists(rates_file):
    print_info(f"Loading rates from {C_BOLD}{rates_file}{C_RESET}...")
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
            color_code = str(row['color_code']).strip() if 'color_code' in row else "#f0f0f0"

            if tier_name not in tier_names_list:
                tier_names_list.append(tier_name)
            tier_colors[tier_name] = color_code

            start_hour = int(time_range.split('_')[0][:2])
            end_hour = int(time_range.split('_')[2][:2])
            if end_hour == 0: end_hour = 24  # 2400 case

            rate_dict = weekday_rates if day_type == 'Weekday' else weekend_rates
            name_dict = weekday_tier_names if day_type == 'Weekday' else weekend_tier_names
            for h in range(start_hour, end_hour):
                rate_dict[h] = charge
                name_dict[h] = tier_name
    except Exception as e:
        print_error(f"Error parsing {rates_file}: {e}")
else:
    print_warning(f"{rates_file} not found. Cost analysis will be skipped.")


def get_rate_info(row):
    dt = row['dt_local']
    hour = dt.hour
    if dt.weekday() < 5:  # Monday-Friday
        return weekday_rates.get(hour, 0.0), weekday_tier_names.get(hour, "Other")
    else:  # Saturday-Sunday
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

print_info(f"Detected System Timezone: {C_BOLD}{tz_name}{C_RESET} (Offset: {tz_offset_seconds / 3600:g}h)")

# Convert to kWh
df['usage_kwh'] = (df['value'] * (10 ** multiplier)) / 1000.0

# Convert Timestamps to Local Time
df['dt_utc'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
df['dt_local'] = df['dt_utc'] + timedelta(seconds=tz_offset_seconds)

# --- DATE RANGE SELECTION ---
print_header("Date Range Selection")
available_start = df['dt_local'].min()
available_end = df['dt_local'].max()

# Look for last run dates in output folder
last_start_str = ""
last_end_str = ""
output_base = "output"
if os.path.exists(output_base):
    subfolders = sorted([f for f in os.listdir(output_base) if os.path.isdir(os.path.join(output_base, f))],
                        reverse=True)
    for folder in subfolders:
        # Pattern: yyyyMMdd_HHmmss_YYYY-MM-DD_to_YYYY-MM-DD
        parts = folder.split('_')
        if len(parts) >= 5 and parts[3] == 'to':
            last_start_str = parts[2]
            last_end_str = parts[4]
            break

print(f"Available range: {C_YELLOW}{available_start}{C_RESET} to {C_YELLOW}{available_end}{C_RESET}")
if last_start_str and last_end_str:
    print(
        f"Last used range: {C_BOLD}{C_GREEN}{last_start_str}{C_RESET} to {C_BOLD}{C_GREEN}{last_end_str}{C_RESET} (Press {C_BOLD}'L'{C_RESET} to reuse)")

print(f"Press {C_BOLD}Enter{C_RESET} to keep default or provide new range below.")

user_start = input(f"Start Date (format: YYYY-MM-DD) [{available_start.date()}]: ").strip()

if user_start.lower() == 'l' and last_start_str and last_end_str:
    user_start = last_start_str
    user_end = last_end_str
    print_info(f"Reusing last range: {user_start} to {user_end}")
else:
    user_end = input(f"End Date   (format: YYYY-MM-DD) [{available_end.date()}]: ").strip()

if user_start:
    try:
        # Use .replace(hour=0, minute=0, second=0) implicitly by pd.to_datetime
        available_start = pd.to_datetime(user_start).tz_localize(df['dt_local'].dt.tz)
    except Exception as e:
        print_error(f"Invalid start date format: {e}. Using default.")

if user_end:
    try:
        # Use .replace(hour=23, minute=59, second=59) for end date
        available_end = pd.to_datetime(user_end).replace(hour=23, minute=59, second=59).tz_localize(
            df['dt_local'].dt.tz)
    except Exception as e:
        print_error(f"Invalid end date format: {e}. Using default.")

# Apply filter
df = df[(df['dt_local'] >= available_start) & (df['dt_local'] <= available_end)].copy()
if df.empty:
    print_error("No data found in the selected range! Exiting.")
    exit(1)

# Create output folder after date range is finalized
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_base = "output"
start_str = available_start.strftime('%Y-%m-%d')
end_str = available_end.strftime('%Y-%m-%d')
folder_name = f"{timestamp}_{start_str}_to_{end_str}"
output_dir = os.path.join(output_base, folder_name)
os.makedirs(output_dir, exist_ok=True)

print_success(f"Analyzing data from {C_BOLD}{available_start}{C_RESET} to {C_BOLD}{available_end}{C_RESET}")
print_info(f"Results will be saved in: {C_BOLD}{output_dir}{C_RESET}")

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
    df['tier'] = df['dt_local'].dt.hour.apply(get_default_tier)
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

# Pre-calculate tier schedule for profile graphs (24 points)
tier_schedule = []
for h in range(24):
    if has_rates:
        tier_schedule.append(weekday_tier_names.get(h, "Other"))
    else:
        tier_schedule.append(get_default_tier(h))

if has_rates:
    avg_cost_profile = hourly_df.groupby('hour')['cost_cents'].mean()
    daily_cost_cents = hourly_df.set_index('dt_local').resample('D')['cost_cents'].sum()

    # Ensure 'Other' has a default color if not in file
    if 'Other' not in tier_colors:
        tier_colors['Other'] = '#f0f0f0'

    tier_usage = hourly_df.groupby('tier')['usage_kwh'].sum()
    tier_cost_cents = hourly_df.groupby('tier')['cost_cents'].sum()

# --- SAVING DATA ---
# Select and rename columns for clarity
csv_df = hourly_df[['dt_local', 'usage_kwh', 'amps', 'tier', 'rate_cents', 'cost_cents']].copy()
csv_df.columns = [f'Local Time ({tz_name})', 'Usage (kWh)', 'Current (Amps)', 'Tier', 'Rate (¢/kWh)', 'Cost (¢)']

# Save to CSV
csv_filename = 'hourly_data_points.csv'
csv_path = os.path.join(output_dir, csv_filename)
csv_df.to_csv(csv_path, index=False, date_format='%Y-%m-%d %H:%M:%S')

print_success(f"Data points saved to: {C_BOLD}{csv_path}{C_RESET}")

# --- PLOTTING ---
print_info("Generating graphs...")

# Graph 1: Hourly Time Series
plt.figure(figsize=(15, 6))
plt.plot(hourly_df['dt_local'], hourly_df['usage_kwh'], color='black', linewidth=1, zorder=3)

# Add background colors for tiers if available
if True:  # Always add background, will use 'Other' if has_rates is False
    from matplotlib.patches import Patch

    # Plot background for each data point
    # To avoid many rectangles, we can find contiguous blocks of the same tier
    # or just iterate and fill per hour (more straightforward)
    for i in range(len(hourly_df)):
        row = hourly_df.iloc[i]
        dt = row['dt_local']
        tier = row['tier']
        color = tier_colors.get(tier, DEFAULT_COLORS['Other'])
        # Fill 1 hour span
        plt.axvspan(dt, dt + timedelta(hours=1), facecolor=color, alpha=0.3, zorder=1)

    # Create custom legend for tiers
    if has_rates:
        legend_elements = [
            Patch(facecolor=tier_colors.get(name), alpha=0.3, label=name)
            for name in tier_names_list
        ]
        plt.legend(handles=legend_elements, loc='upper left')
    else:
        # Show default tiers in legend if no rates
        legend_elements = [
            Patch(facecolor=DEFAULT_COLORS['Off-Peak'], alpha=0.3, label='Off-Peak (Default Night)'),
            Patch(facecolor=DEFAULT_COLORS['Other'], alpha=0.3, label='Other')
        ]
        plt.legend(handles=legend_elements, loc='upper left')

plt.title(f'Hourly Electricity Usage (Time Series) - {tz_name}')
plt.xlabel(f'Date ({tz_name})')
plt.ylabel('Usage (kWh)')
plt.grid(True, alpha=0.3, zorder=0)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'graph1_hourly_timeseries.png'))
plt.close()

# Graph 2: Hourly Average Profile
plt.figure(figsize=(10, 5))
plt.plot(avg_kwh_profile.index, avg_kwh_profile.values, marker='o', color='black', zorder=3)

# Add background colors for tiers if available
if True:  # Always add background, will use 'Other' if has_rates is False
    from matplotlib.patches import Patch

    for h in range(24):
        tier = tier_schedule[h]
        color = tier_colors.get(tier, DEFAULT_COLORS['Other'])
        plt.axvspan(h - 0.5, h + 0.5, facecolor=color, alpha=0.3, zorder=1)

    if has_rates:
        legend_elements = [
            Patch(facecolor=tier_colors.get(name), alpha=0.3, label=f'{name} (Weekday)')
            for name in tier_names_list
        ]
        plt.legend(handles=legend_elements, loc='upper left')
    else:
        legend_elements = [
            Patch(facecolor=DEFAULT_COLORS['Off-Peak'], alpha=0.3, label='Off-Peak (Default Night)'),
            Patch(facecolor=DEFAULT_COLORS['Other'], alpha=0.3, label='Other')
        ]
        plt.legend(handles=legend_elements, loc='upper left')

plt.title(f'Average Electricity Usage by Hour of Day ({tz_name}), {start_str} to {end_str}')
plt.xlabel(f'Hour of Day (24h) - {tz_name}')
plt.ylabel('Average Usage (kWh)')
plt.xticks(range(0, 24))
plt.grid(True, linestyle='--', alpha=0.5, zorder=0)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'graph2_hourly_avg_profile.png'))
plt.close()

# Graph 3: Hourly Ampere Stats Profile (Min, Max, Avg)
plt.figure(figsize=(12, 6))

# Plot the stats
plt.plot(amp_stats.index, amp_stats['mean'], label='Average Amps', color='black', marker='o', linewidth=2, zorder=3)
plt.fill_between(amp_stats.index, amp_stats['min'], amp_stats['max'], color='gray', alpha=0.3, label='Min-Max Range',
                 zorder=2)

# Add background colors for tiers if available
if True:  # Always add background, will use 'Other' if has_rates is False
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D

    # We want to draw vertical spans for each hour's tier
    for h in range(24):
        tier = tier_schedule[h]
        color = tier_colors.get(tier, DEFAULT_COLORS['Other'])
        plt.axvspan(h - 0.5, h + 0.5, facecolor=color, alpha=0.4, zorder=1)

    # Create custom legend for tiers
    legend_elements = []
    if has_rates:
        legend_elements.extend([
            Patch(facecolor=tier_colors.get(name), alpha=0.4, label=f'{name} (Weekday)')
            for name in tier_names_list
        ])
    else:
        # Default tiers if no rates
        legend_elements.extend([
            Patch(facecolor=DEFAULT_COLORS['Off-Peak'], alpha=0.4, label='Off-Peak (Default Night)'),
            Patch(facecolor=DEFAULT_COLORS['Other'], alpha=0.4, label='Other')
        ])

    legend_elements.extend([
        Line2D([0], [0], color='black', marker='o', label='Average Amps'),
        Patch(facecolor='gray', alpha=0.3, label='Min-Max Range')
    ])
    plt.legend(handles=legend_elements, loc='upper left')

plt.title(f'Hourly Ampere Profile (at 120V) - Local Time ({tz_name}), {start_str} to {end_str}')
plt.xlabel(f'Hour of Day (24h) - Local Time ({tz_name})')
plt.ylabel('Current (Amperes)')
plt.xticks(range(0, 24))
plt.grid(True, linestyle='--', alpha=0.5, zorder=0)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'graph3_hourly_ampere_stats.png'))
plt.close()

if has_rates:
    # Graph 4: Hourly Average Cost Profile
    plt.figure(figsize=(10, 5))
    plt.plot(avg_cost_profile.index, avg_cost_profile.values, marker='s', color='black', zorder=3)

    # Add background colors for tiers
    for h in range(24):
        tier = tier_schedule[h]
        color = tier_colors.get(tier, '#f0f0f0')
        plt.axvspan(h - 0.5, h + 0.5, facecolor=color, alpha=0.3, zorder=1)

    legend_elements = [
        Patch(facecolor=tier_colors.get(name), alpha=0.3, label=f'{name} (Weekday)')
        for name in tier_names_list
    ]
    plt.legend(handles=legend_elements, loc='upper left')

    plt.title(f'Average Electricity Cost by Hour of Day ({tz_name}), {start_str} to {end_str}')
    plt.xlabel(f'Hour of Day (24h) - {tz_name}')
    plt.ylabel('Average Cost (¢)')
    plt.xticks(range(0, 24))
    plt.grid(True, linestyle='--', alpha=0.5, zorder=0)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph4_hourly_avg_cost_profile.png'))
    plt.close()

# Graph 5: Hourly Usage Heatmap by Day and Hour
pivot_df = hourly_df.pivot_table(index=hourly_df['dt_local'].dt.date, columns='hour', values='usage_kwh')
plt.figure(figsize=(16, 8))
sns.heatmap(pivot_df, cmap='YlOrRd', annot=False)
plt.title(f'Heatmap of Hourly Usage (kWh) - {tz_name}')
plt.xlabel(f'Hour of Day ({tz_name})')
plt.ylabel('Date')
plt.tight_layout()
plt.savefig(os.path.join(output_dir, 'graph5_hourly_usage_heatmap.png'))
plt.close()

# Graph 6: Daily Usage Totals
plt.figure(figsize=(12, 6))
if has_rates:
    # Stacked bar by tier
    # Prepare data: sum usage per day and tier
    # We use dt_local.dt.date for grouping by day
    daily_tier_usage = hourly_df.groupby([hourly_df['dt_local'].dt.date, 'tier'])['usage_kwh'].sum().unstack().fillna(0)

    # Use the same tier_colors
    current_tier_colors = [tier_colors.get(tier, DEFAULT_COLORS['Other']) for tier in daily_tier_usage.columns]

    ax = daily_tier_usage.plot(kind='bar', stacked=True, color=current_tier_colors, ax=plt.gca())
    plt.legend(title="Rate Tier")

    # Calculate totals for labels
    totals = daily_tier_usage.sum(axis=1)
else:
    # Stacked bar by default tiers
    daily_tier_usage = hourly_df.groupby([hourly_df['dt_local'].dt.date, 'tier'])['usage_kwh'].sum().unstack().fillna(0)
    # Ensure all default tiers are present for consistent coloring
    for t in ['Off-Peak', 'Other']:
        if t not in daily_tier_usage.columns:
            daily_tier_usage[t] = 0.0
    daily_tier_usage = daily_tier_usage[['Off-Peak', 'Other']]

    current_tier_colors = [DEFAULT_COLORS['Off-Peak'], DEFAULT_COLORS['Other']]
    ax = daily_tier_usage.plot(kind='bar', stacked=True, color=current_tier_colors, ax=plt.gca())
    plt.legend(title="Default Tier (Night: 10PM-7AM)")
    totals = daily_tier_usage.sum(axis=1)

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
plt.savefig(os.path.join(output_dir, 'graph6_daily_usage.png'))
plt.close()

if has_rates:
    # Graph 7: Daily Total Cost
    plt.figure(figsize=(12, 6))
    # Stacked bar by tier for cost
    daily_tier_cost = hourly_df.groupby([hourly_df['dt_local'].dt.date, 'tier'])['cost_cents'].sum().unstack().fillna(0)
    current_tier_colors = [tier_colors.get(tier, DEFAULT_COLORS['Other']) for tier in daily_tier_cost.columns]

    ax = daily_tier_cost.plot(kind='bar', stacked=True, color=current_tier_colors, ax=plt.gca())
    plt.legend(title="Rate Tier")

    # Calculate totals for labels
    cost_totals = daily_tier_cost.sum(axis=1)
    for i, total in enumerate(cost_totals):
        if total > 0:
            plt.text(i, total + (cost_totals.max() * 0.01), f'{total:.1f}',
                     ha='center', va='bottom', rotation=90, fontsize=9)

    plt.title(f'Daily Electricity Cost Total ({tz_name})')
    plt.xlabel(f'Date ({tz_name})')
    plt.ylabel('Total Daily Cost (¢)')
    plt.xticks(rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph7_daily_cost.png'))
    plt.close()

    # Graph 8: Tier Distribution (Period Totals)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Get colors for existing tiers in this dataset
    pie_colors1 = [tier_colors.get(t, '#f0f0f0') for t in tier_usage.index]
    tier_usage.plot(kind='pie', autopct='%1.1f%%', ax=ax1, colors=pie_colors1)
    ax1.set_title(f'Usage (kWh) by Rate Tier, {start_str} to {end_str}')
    ax1.set_ylabel('')

    pie_colors2 = [tier_colors.get(t, '#f0f0f0') for t in tier_cost_cents.index]
    tier_cost_cents.plot(kind='pie', autopct='%1.1f%%', ax=ax2, colors=pie_colors2)
    ax2.set_title(f'Cost (¢) by Rate Tier, {start_str} to {end_str}')
    ax2.set_ylabel('')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'graph8_tier_distribution.png'))
    plt.close()

print_header("Processing Complete")
print_success(f"Graphs and CSV saved in: {C_BOLD}{output_dir}{C_RESET}")
