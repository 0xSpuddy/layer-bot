import os
import subprocess
from datetime import datetime

def get_timestamp_from_height(height):
    """Get timestamp from block height using layerd query command."""
    try:
        cmd = [
            './layerd',
            'query',
            'block',
            '--height', str(height)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')
        
        if result.returncode != 0:
            raise Exception(f"layerd command failed with return code {result.returncode}: {result.stderr}")
            
        output = result.stdout
        print(f"Block query output for height {height}: {output[:200]}...")  # Print first 200 chars for debugging

        # Parse the date from this line in the output:
        # time: "2025-06-19T19:32:38.825315717Z"
        # Extract the date string and convert to datetime
        if 'time: "' not in output:
            raise Exception(f"Could not find timestamp in layerd output for height {height}")
            
        date_str = output.split('time: "')[1].split('"')[0]
        
        # Handle nanosecond precision by truncating to microseconds
        # Python's strptime only supports up to microseconds (%f = 6 digits)
        # But the timestamp has nanoseconds (9 digits), so we need to truncate
        if '.' in date_str and 'Z' in date_str:
            # Split into parts: date_time, fractional_seconds, Z
            date_part, fractional_part = date_str.split('.')
            fractional_part = fractional_part.rstrip('Z')
            # Truncate to 6 digits (microseconds) if longer
            if len(fractional_part) > 6:
                fractional_part = fractional_part[:6]
            date_str = f"{date_part}.{fractional_part}Z"
        
        timestamp = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        return timestamp
        
    except Exception as e:
        print(f"Error getting timestamp for block height {height}: {e}")
        raise