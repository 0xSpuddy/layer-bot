import requests
import time
import subprocess
from datetime import datetime, timedelta
import os
import csv
import pandas as pd
from pathlib import Path
import re
import shutil

RPC_URL = os.getenv("LAYER_RPC_URL")
CSV_FILE = "block_time.csv"
CHECK_INTERVAL = 60  # seconds between checks
MAX_AGE_DAYS = 7  # maximum age of records to keep

def find_layerd_binary():
    """Find the layerd binary in various possible locations"""
    # Check if layerd is in PATH
    layerd_in_path = shutil.which('layerd')
    if layerd_in_path:
        return layerd_in_path
    
    # Check common locations
    possible_paths = [
        './layerd',                          # Current directory
        '../layerd',                         # Parent directory
        '~/layerd',                          # Home directory
        '/usr/local/bin/layerd',             # Common system location
        '/usr/bin/layerd',                   # Another common system location
        os.path.expanduser('~/go/bin/layerd')  # Go binary location
    ]
    
    for path in possible_paths:
        expanded_path = os.path.expanduser(path)
        if os.path.isfile(expanded_path) and os.access(expanded_path, os.X_OK):
            return expanded_path
    
    # If we can't find it, return the basic command and hope it's in the PATH
    return 'layerd'

LAYERD_PATH = find_layerd_binary()

def ensure_csv_exists():
    """Create the CSV file if it doesn't exist or update it to the new format"""
    csv_path = Path(CSV_FILE)
    
    # If the file doesn't exist, create it with the new format
    if not csv_path.exists():
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'block_height', 'block_time', 'time_since_last_check', 'avg_block_time'])
        return
    
    # If the file exists, check if it needs to be updated to the new format
    try:
        df = pd.read_csv(CSV_FILE)
        
        # Check if we need to update the format (missing the avg_block_time column)
        if len(df.columns) == 4:
            print("Updating CSV file to new format with avg_block_time column...")
            
            # Add the new column
            df['avg_block_time'] = None
            
            # If there are at least two rows, calculate avg_block_time for existing rows
            if len(df) >= 2:
                for i in range(1, len(df)):
                    # Get previous and current row
                    prev_row = df.iloc[i-1]
                    curr_row = df.iloc[i]
                    
                    # Calculate avg_block_time if possible
                    try:
                        prev_height = int(prev_row['block_height'])
                        curr_height = int(curr_row['block_height'])
                        
                        # Check if time_since_last_check exists and is a valid number
                        if pd.notna(curr_row['time_since_last_check']) and curr_row['time_since_last_check'] != '':
                            time_diff = float(curr_row['time_since_last_check'])
                            
                            if curr_height > prev_height:
                                blocks_created = curr_height - prev_height
                                avg_time = time_diff / blocks_created
                                df.at[i, 'avg_block_time'] = avg_time
                    except Exception as e:
                        print(f"Could not calculate avg_block_time for row {i}: {e}")
            
            # Save the updated file
            df.to_csv(CSV_FILE, index=False)
            print("CSV file updated successfully.")
        else:
            # Check if the file already has the correct format
            expected_columns = ['timestamp', 'block_height', 'block_time', 'time_since_last_check', 'avg_block_time']
            
            # Handle the case where column names are different but there are 5 columns
            if len(df.columns) == 5 and list(df.columns) != expected_columns:
                df.columns = expected_columns
                df.to_csv(CSV_FILE, index=False)
                print("Updated column names to match expected format.")
                
    except Exception as e:
        # If there's any error with the existing file, create a new one
        print(f"Error reading existing CSV file: {e}")
        print("Creating a new file with the correct format...")
        with open(CSV_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'block_height', 'block_time', 'time_since_last_check', 'avg_block_time'])

def clean_old_records():
    """Remove records older than MAX_AGE_DAYS"""
    try:
        if Path(CSV_FILE).exists():
            df = pd.read_csv(CSV_FILE)
            if not df.empty:
                # Convert timestamp string to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Calculate cutoff date
                cutoff_date = datetime.now() - timedelta(days=MAX_AGE_DAYS)
                
                # Check if oldest record is more than MAX_AGE_DAYS old
                if df['timestamp'].min() < cutoff_date:
                    # If so, create a new file with only recent records
                    recent_df = df[df['timestamp'] >= cutoff_date]
                    recent_df.to_csv(CSV_FILE, index=False)
                    print(f"Cleaned old records. Kept {len(recent_df)} recent records.")
    except Exception as e:
        print(f"Error cleaning old records: {e}")

def get_block_info():
    """Get current block information using layerd binary command"""
    try:
        # Run the command to get complete block output
        block_cmd = f"{LAYERD_PATH} query block"
        block_result = subprocess.run(block_cmd, 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.PIPE, 
                                    text=True,
                                    shell=True)
        
        if block_result.returncode != 0:
            print(f"Error getting block info: {block_result.stderr}")
            return None, None
            
        block_output = block_result.stdout
        
        # Parse for height - look for the format shown in the logs
        # First pattern: "height: \"1684332\""
        height_match = re.search(r'height:\s*"(\d+)"', block_output)
        if not height_match:
            # Second pattern: simply "height: 1684332"
            height_match = re.search(r'height:\s*(\d+)', block_output)
            
        if not height_match:
            print("Could not find block height in command output")
            print(f"Output excerpt: {block_output[:200]}...")
            return None, None
            
        height = int(height_match.group(1))
        
        # Get the time - look for both formats
        time_match = re.search(r'time:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)', block_output)
        if not time_match:
            # Try alternative format without Z suffix
            time_match = re.search(r'time:\s*"?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)"?', block_output)
            
        if not time_match:
            print("Could not find time in block output")
            print(f"Output excerpt: {block_output[:200]}...")
            return None, None
            
        time_str = time_match.group(1)
        # Add Z if it's missing and handle any missing microseconds
        if not time_str.endswith('Z'):
            if '.' not in time_str:
                time_str += '.000000Z'
            else:
                time_str += 'Z'
                
        # Convert to datetime
        block_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        
        return height, block_time
    except Exception as e:
        print(f"Error getting block info: {e}")
        print("Exception occurred when processing:")
        # Print additional debugging info
        import traceback
        traceback.print_exc()
        return None, None

def record_block_time():
    """Record block time to CSV file"""
    ensure_csv_exists()
    clean_old_records()
    
    # Get current block info
    height, block_time = get_block_info()
    if height is None or block_time is None:
        return
    
    # Calculate time since last check and average block time
    time_since_last_check = None
    avg_block_time = None
    try:
        df = pd.read_csv(CSV_FILE)
        if not df.empty:
            last_row = df.iloc[-1]
            last_block_time = pd.to_datetime(last_row['block_time'])
            last_height = int(last_row['block_height'])
            
            if last_height < height:
                time_since_last_check = (block_time - last_block_time).total_seconds()
                blocks_created = height - last_height
                
                # Calculate average time per block
                if blocks_created > 0:
                    avg_block_time = time_since_last_check / blocks_created
                    print(f"Blocks created since last check: {blocks_created}")
                    print(f"Average time per block: {avg_block_time:.2f} seconds")
                else:
                    print("No new blocks since last check")
    except Exception as e:
        print(f"Error calculating block times: {e}")
    
    # Record to CSV
    current_time = datetime.now().isoformat()
    block_time_str = block_time.isoformat()
    
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([current_time, height, block_time_str, time_since_last_check, avg_block_time])
    
    print(f"Recorded block {height} at {current_time}")
    if time_since_last_check:
        print(f"Time since last check: {time_since_last_check:.2f} seconds")

def get_block_time_stats():
    """Calculate block time statistics for different time periods"""
    try:
        df = pd.read_csv(CSV_FILE)
        if df.empty:
            return {
                "five_min": "No data",
                "thirty_min": "No data",
                "sixty_min": "No data",
                "day": "No data",
                "week": "No data"
            }
        
        # Convert timestamps to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Define time cutoffs
        now = datetime.now()
        five_min_ago = now - timedelta(minutes=5)
        thirty_min_ago = now - timedelta(minutes=30)
        sixty_min_ago = now - timedelta(minutes=60)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        # Check data availability - determine the oldest record's timestamp
        oldest_timestamp = df['timestamp'].min()
        data_age = now - oldest_timestamp
        data_age_minutes = data_age.total_seconds() / 60
        data_age_hours = data_age_minutes / 60
        data_age_days = data_age_hours / 24
        
        # Filter data for each time period and calculate average
        stats = {}
        
        # Only use rows where avg_block_time is not null
        df_valid = df.dropna(subset=['avg_block_time'])
        
        # Check and calculate stats for each time period
        if data_age_minutes >= 5:
            stats["five_min"] = calculate_average(df_valid, five_min_ago)
        else:
            stats["five_min"] = "Insufficient data (need at least 5 minutes of history)"
            
        if data_age_minutes >= 30:
            stats["thirty_min"] = calculate_average(df_valid, thirty_min_ago)
        else:
            stats["thirty_min"] = "Insufficient data (need at least 30 minutes of history)"
            
        if data_age_minutes >= 60:
            stats["sixty_min"] = calculate_average(df_valid, sixty_min_ago)
        else:
            stats["sixty_min"] = "Insufficient data (need at least 1 hour of history)"
            
        if data_age_hours >= 24:
            stats["day"] = calculate_average(df_valid, day_ago)
        else:
            stats["day"] = f"Insufficient data (need 24 hours, have {data_age_hours:.1f} hours)"
            
        if data_age_days >= 7:
            stats["week"] = calculate_average(df_valid, week_ago)
        else:
            stats["week"] = f"Insufficient data (need 7 days, have {data_age_days:.1f} days)"
        
        return stats
    except Exception as e:
        print(f"Error getting block time stats: {e}")
        import traceback
        traceback.print_exc()
        return {
            "five_min": f"Error: {str(e)}",
            "thirty_min": "Error",
            "sixty_min": "Error",
            "day": "Error",
            "week": "Error"
        }

def calculate_average(df, cutoff_time):
    """Calculate average block time for data after cutoff_time"""
    recent_df = df[df['timestamp'] >= cutoff_time]
    
    # Check if we have at least 2 data points in the time period
    if len(recent_df) < 2:
        return "Insufficient data points in this time period"
    
    # Check if we have meaningful data
    if recent_df['avg_block_time'].isna().all():
        return "No valid measurements in this time period"
    
    # Calculate average of the block times
    average = recent_df['avg_block_time'].mean()
    
    # Check if the average makes sense
    if pd.isna(average) or average <= 0:
        return "Invalid average calculation"
    
    return f"{average:.2f} seconds"

if __name__ == "__main__":
    print(f"Starting block time tracker. Recording every {CHECK_INTERVAL} seconds.")
    print(f"Using layerd binary at: {LAYERD_PATH}")
    while True:
        record_block_time()
        time.sleep(CHECK_INTERVAL)