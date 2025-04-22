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

def create_backup(reason="manual"):
    """Create a timestamped backup of the block_time.csv file
    
    Args:
        reason (str): Reason for the backup, included in the filename
    
    Returns:
        str: Path to the backup file or None if backup failed
    """
    try:
        if not Path(CSV_FILE).exists():
            print(f"Cannot backup {CSV_FILE}: file does not exist")
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{CSV_FILE}.{timestamp}.{reason}.bak"
        
        shutil.copy2(CSV_FILE, backup_file)
        print(f"Created backup of {CSV_FILE} at {backup_file}")
        return backup_file
    except Exception as e:
        print(f"Error creating backup: {e}")
        return None

def restore_from_backup(backup_file=None):
    """Restore block_time.csv from a backup file
    
    Args:
        backup_file (str): Path to the backup file to restore from.
                           If None, uses the most recent backup.
    
    Returns:
        bool: True if restore was successful, False otherwise
    """
    try:
        if backup_file is None:
            # Find the most recent backup
            backups = list(Path('.').glob(f"{CSV_FILE}.*.bak"))
            if not backups:
                print("No backup files found")
                return False
                
            # Sort by modification time (most recent first)
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            backup_file = str(backups[0])
            print(f"Using most recent backup: {backup_file}")
        
        if not Path(backup_file).exists():
            print(f"Backup file {backup_file} does not exist")
            return False
            
        # Create a backup of the current file before restoring
        if Path(CSV_FILE).exists():
            current_backup = f"{CSV_FILE}.before_restore.bak"
            shutil.copy2(CSV_FILE, current_backup)
            print(f"Created backup of current file at {current_backup}")
        
        # Restore from the backup
        shutil.copy2(backup_file, CSV_FILE)
        print(f"Successfully restored {CSV_FILE} from {backup_file}")
        return True
    except Exception as e:
        print(f"Error restoring from backup: {e}")
        import traceback
        traceback.print_exc()
        return False

def clean_old_records():
    """Remove records older than MAX_AGE_DAYS
    
    This function trims the CSV file to keep only records newer than MAX_AGE_DAYS,
    while preserving the historical data structure.
    """
    try:
        if Path(CSV_FILE).exists():
            # Create a backup of the original file
            backup_file = create_backup(reason="before_cleaning")
            
            # Read the CSV file
            df = pd.read_csv(CSV_FILE)
            original_len = len(df)
            
            if not df.empty:
                # Convert timestamp string to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Calculate cutoff date
                cutoff_date = datetime.now() - timedelta(days=MAX_AGE_DAYS)
                
                # Check if oldest record is more than MAX_AGE_DAYS old
                if df['timestamp'].min() < cutoff_date:
                    # Filter to keep only recent records
                    recent_df = df[df['timestamp'] >= cutoff_date]
                    
                    if not recent_df.empty:
                        # Write back only the recent records
                        recent_df.to_csv(CSV_FILE, index=False)
                        removed_count = original_len - len(recent_df)
                        print(f"Cleaned old records. Removed {removed_count} records older than {MAX_AGE_DAYS} days. Kept {len(recent_df)} recent records.")
                    else:
                        # If all records would be removed, keep the most recent MAX_RECORDS_TO_KEEP
                        MAX_RECORDS_TO_KEEP = 100  # Define a minimum number of records to keep
                        if len(df) > MAX_RECORDS_TO_KEEP:
                            # Sort by timestamp (newest first) and keep the most recent records
                            df_sorted = df.sort_values(by='timestamp', ascending=False)
                            df_keep = df_sorted.head(MAX_RECORDS_TO_KEEP)
                            df_keep.to_csv(CSV_FILE, index=False)
                            print(f"All records were older than {MAX_AGE_DAYS} days. Kept the {MAX_RECORDS_TO_KEEP} most recent records.")
                        else:
                            # If we have fewer records than MAX_RECORDS_TO_KEEP, keep all of them
                            print(f"All records are older than {MAX_AGE_DAYS} days, but keeping all {len(df)} existing records as the minimum dataset.")
    except Exception as e:
        print(f"Error cleaning old records: {e}")
        import traceback
        traceback.print_exc()

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

def check_for_duplicates():
    """Check for and remove duplicate records from the CSV file"""
    try:
        if not Path(CSV_FILE).exists():
            return
            
        df = pd.read_csv(CSV_FILE)
        if df.empty:
            return
            
        # Count rows before deduplication
        original_count = len(df)
        
        # Convert timestamps to datetime for proper comparison
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Check for duplicates by block_height (which should be unique)
        duplicates = df.duplicated(subset=['block_height'], keep='last')
        duplicate_count = duplicates.sum()
        
        if duplicate_count > 0:
            # Create a backup before removing duplicates
            create_backup(reason="before_deduplication")
            
            # Keep the most recent entry for each block_height
            df_deduped = df.drop_duplicates(subset=['block_height'], keep='last')
            
            # Sort by timestamp to ensure chronological order
            df_deduped = df_deduped.sort_values(by='timestamp')
            
            # Write back the deduplicated data
            df_deduped.to_csv(CSV_FILE, index=False)
            
            print(f"Removed {duplicate_count} duplicate records. Kept {len(df_deduped)} unique records.")
    except Exception as e:
        print(f"Error checking for duplicates: {e}")
        import traceback
        traceback.print_exc()

def record_block_time():
    """Record block time to CSV file"""
    ensure_csv_exists()
    
    # Get current block info first
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
    
    # After adding the new record, check for duplicates
    check_for_duplicates()
    
    # Only after ensuring we have no duplicates, clean old records
    clean_old_records()

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
    parser = argparse.ArgumentParser(description="Block time tracker utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run the block time tracker")
    run_parser.add_argument("--interval", type=int, default=CHECK_INTERVAL, 
                          help=f"Interval between checks in seconds (default: {CHECK_INTERVAL})")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a backup of the CSV file")
    backup_parser.add_argument("--reason", default="manual", help="Reason for the backup")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from a backup")
    restore_parser.add_argument("--file", help="Specific backup file to restore from (default: most recent)")
    
    # List backups command
    list_parser = subparsers.add_parser("list-backups", help="List available backups")
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean old records from the CSV file")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show block time statistics")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == "run":
        check_interval = args.interval
        print(f"Starting block time tracker. Recording every {check_interval} seconds.")
        print(f"Using layerd binary at: {LAYERD_PATH}")
        while True:
            record_block_time()
            time.sleep(check_interval)
    
    elif args.command == "backup":
        create_backup(args.reason)
    
    elif args.command == "restore":
        restore_from_backup(args.file)
    
    elif args.command == "list-backups":
        backups = list(Path('.').glob(f"{CSV_FILE}.*.bak"))
        if not backups:
            print("No backups found")
        else:
            print(f"Found {len(backups)} backups:")
            # Sort by modification time (newest first)
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for i, backup in enumerate(backups, 1):
                size_kb = backup.stat().st_size / 1024
                mod_time = datetime.fromtimestamp(backup.stat().st_mtime)
                print(f"{i}. {backup} ({size_kb:.1f} KB) - {mod_time}")
    
    elif args.command == "clean":
        clean_old_records()
    
    elif args.command == "stats":
        stats = get_block_time_stats()
        print("Block Time Statistics:")
        print(f"  5 Minute Average: {stats['five_min']}")
        print(f"  30 Minute Average: {stats['thirty_min']}")
        print(f"  60 Minute Average: {stats['sixty_min']}")
        print(f"  24 Hour Average: {stats['day']}")
        print(f"  7 Day Average: {stats['week']}")
    
    else:
        # Default behavior if no command is provided
        print(f"Starting block time tracker. Recording every {CHECK_INTERVAL} seconds.")
        print(f"Using layerd binary at: {LAYERD_PATH}")
        while True:
            record_block_time()
            time.sleep(CHECK_INTERVAL)