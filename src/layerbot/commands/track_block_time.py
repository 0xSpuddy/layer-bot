"""
Command to track block time in the background
"""
import os
import sys
import subprocess
from pathlib import Path

def test_connection():
    """Test if we can get block information"""
    script_path = Path(__file__).parent.parent / "utils" / "block_time.py"
    
    # Import the module
    sys.path.append(str(script_path.parent.parent.parent))
    
    try:
        from src.layerbot.utils.block_time import get_block_info, LAYERD_PATH
        
        print(f"Using layerd binary at: {LAYERD_PATH}")
        
        # Test getting block info
        print("Testing connection to Layer network...")
        height, block_time = get_block_info()
        
        if height is not None and block_time is not None:
            print(f"✓ Successfully retrieved block information:")
            print(f"  Block height: {height}")
            print(f"  Block time: {block_time}")
            return True
        else:
            print("✗ Failed to retrieve block information")
            print("  Please check your layerd binary and network connection.")
            return False
    except Exception as e:
        print(f"Error testing connection: {e}")
        return False

def track(daemon=False, test=False):
    """Track block time and save to CSV file"""
    script_path = Path(__file__).parent.parent / "utils" / "block_time.py"
    
    # If test mode, just verify the connection works
    if test:
        test_result = test_connection()
        return test_result
    
    if daemon:
        # Run the script as a background process
        print("Starting block time tracker as a daemon process")
        
        # Redirect output to a log file
        log_file = "block_time.log"
        with open(log_file, "w") as log:
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=log,
                stderr=log,
                start_new_session=True
            )
        
        print(f"Block time tracker started with PID {process.pid}")
        print(f"Logs are being written to {log_file}")
    else:
        # Run the script in the foreground
        print("Starting block time tracker. Press Ctrl+C to stop.")
        os.execv(sys.executable, [sys.executable, str(script_path)])

if __name__ == "__main__":
    # If run directly, execute with test flag
    track(test=True) 