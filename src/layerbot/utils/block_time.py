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
import argparse

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
    """
    Ensures the CSV file exists with proper headers
    """
    if not os.path.exists(CSV_FILE):
        # Create the CSV file with headers
        with open(CSV_FILE, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['timestamp', 'height', 'block_time', 'duration', 'avg_block_time'])
        print(f"Created new CSV file: {CSV_FILE}")
    return True

def record_block_time():
    """
    Record a single block time entry to the CSV file
    """
    try:
        # Get current block info
        height, block_time = get_block_info()
        
        if height is None or block_time is None:
            print("Failed to get block information")
            return False
            
        # Read existing data to calculate average block time
        avg_block_time = None
        duration = None
        
        try:
            df = pd.read_csv(CSV_FILE)
            if not df.empty:
                # Get the last record to calculate duration
                last_row = df.iloc[-1]
                last_height = last_row['height']
                last_time = pd.to_datetime(last_row['block_time'])
                
                current_time = pd.to_datetime(block_time)
                height_diff = height - last_height
                time_diff = (current_time - last_time).total_seconds()
                
                if height_diff > 0:
                    duration = time_diff / height_diff
                    
                    # Calculate average from recent records (last 100 blocks)
                    recent_data = df.tail(100)
                    if len(recent_data) > 1:
                        valid_durations = recent_data.dropna(subset=['duration'])['duration']
                        if not valid_durations.empty:
                            avg_block_time = valid_durations.mean()
                
        except Exception as e:
            print(f"Error calculating averages: {e}")
        
        # Write the new record
        with open(CSV_FILE, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                datetime.now().isoformat(),
                height,
                block_time.isoformat() if hasattr(block_time, 'isoformat') else str(block_time),
                duration,
                avg_block_time
            ])
        
        print(f"Recorded block {height} at {block_time}")
        if duration:
            print(f"  Duration since last: {duration:.2f} seconds")
        if avg_block_time:
            print(f"  Average block time: {avg_block_time:.2f} seconds")
        
        return True
        
    except Exception as e:
        print(f"Error recording block time: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_block_time_stats():
    """
    Calculate block time statistics from the CSV file
    """
    stats = {
        'five_min': 'No data',
        'thirty_min': 'No data',
        'sixty_min': 'No data',
        'day': 'No data', 
        'week': 'No data'
    }
    
    try:
        df = pd.read_csv(CSV_FILE)
        if df.empty:
            return stats
            
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        now = datetime.now()
        
        # Calculate stats for different time periods
        time_periods = {
            'five_min': timedelta(minutes=5),
            'thirty_min': timedelta(minutes=30),
            'sixty_min': timedelta(hours=1),
            'day': timedelta(days=1),
            'week': timedelta(days=7)
        }
        
        for period_name, period_duration in time_periods.items():
            cutoff_time = now - period_duration
            period_data = df[df['timestamp'] >= cutoff_time]
            
            if not period_data.empty and 'duration' in period_data.columns:
                valid_durations = period_data.dropna(subset=['duration'])['duration']
                if not valid_durations.empty:
                    avg_time = valid_durations.mean()
                    stats[period_name] = f"{avg_time:.2f} seconds"
        
        return stats
        
    except Exception as e:
        print(f"Error calculating stats: {e}")
        return stats

def clean_old_records():
    """
    Remove records older than MAX_AGE_DAYS from the CSV file
    """
    try:
        df = pd.read_csv(CSV_FILE)
        if df.empty:
            return
            
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Filter out old records
        cutoff_date = datetime.now() - timedelta(days=MAX_AGE_DAYS)
        df_filtered = df[df['timestamp'] >= cutoff_date]
        
        if len(df_filtered) < len(df):
            # Write the filtered data back
            df_filtered.to_csv(CSV_FILE, index=False)
            removed_count = len(df) - len(df_filtered)
            print(f"Cleaned {removed_count} old records from {CSV_FILE}")
        
    except Exception as e:
        print(f"Error cleaning old records: {e}")
        import traceback
        traceback.print_exc()

def get_block_info():
    """Get current block information using layerd binary command"""
    try:
        # Get the RPC URL from environment
        rpc_url = os.getenv("LAYER_RPC_URL")
        if not rpc_url:
            print("Warning: LAYER_RPC_URL not set, using layerd default")
            # Build command without --node parameter (will use layerd default)
            block_cmd = f"{LAYERD_PATH} query block"
        else:
            # Build command with --node parameter to specify RPC endpoint
            block_cmd = f"{LAYERD_PATH} query block --node {rpc_url}"
        
        print(f"Running command: {block_cmd}")
        
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
                
        # Parse the datetime
        try:
            block_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except ValueError:
            # Fallback parsing
            block_time = datetime.strptime(time_str.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
            block_time = block_time.replace(tzinfo=None)
            
        return height, block_time
        
    except Exception as e:
        print(f"Error getting block info: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def monitor_blocks():
    """
    Main monitoring loop - continuously track block times
    """
    print("Starting block time monitoring...")
    print(f"RPC URL: {RPC_URL}")
    print(f"Using layerd binary: {LAYERD_PATH}")
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print(f"CSV file: {CSV_FILE}")
    print("Press Ctrl+C to stop\n")
    
    # Ensure CSV file exists
    ensure_csv_exists()
    
    try:
        while True:
            # Record current block time
            success = record_block_time()
            
            if success:
                # Clean old records periodically (every 10th iteration)
                if int(time.time()) % (CHECK_INTERVAL * 10) == 0:
                    clean_old_records()
            
            # Wait before next check
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nBlock time monitoring stopped")
    except Exception as e:
        print(f"\nError in block monitoring: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Monitor block times and save to CSV')
    parser.add_argument('--test', action='store_true', help='Test connection and exit')
    parser.add_argument('--stats', action='store_true', help='Show current statistics and exit')
    
    args = parser.parse_args()
    
    if args.test:
        print("Testing block time monitoring...")
        height, block_time = get_block_info()
        if height and block_time:
            print(f"✓ Success: Block {height} at {block_time}")
        else:
            print("✗ Failed to get block information")
    elif args.stats:
        print("Block time statistics:")
        stats = get_block_time_stats()
        for period, value in stats.items():
            print(f"  {period.capitalize()}: {value}")
    else:
        monitor_blocks()
