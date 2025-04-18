import os
from datetime import datetime
import json
from dotenv import load_dotenv

def get_scan_time_file():
    """Get the path to the scan time file."""
    load_dotenv()
    return os.getenv('SCAN_TIME_FILE', 'scan_time.json')

def update_scan_time():
    """Update the last scan time to the current time."""
    scan_time_file = get_scan_time_file()
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    try:
        with open(scan_time_file, 'w') as f:
            json.dump({'last_scan': current_time}, f)
        return current_time
    except Exception as e:
        print(f"Error updating scan time: {e}")
        return None

def get_last_scan_time():
    """Get the last scan time from the file."""
    scan_time_file = get_scan_time_file()
    
    try:
        if os.path.exists(scan_time_file):
            with open(scan_time_file, 'r') as f:
                data = json.load(f)
                return data.get('last_scan')
        return None
    except Exception as e:
        print(f"Error reading scan time: {e}")
        return None 