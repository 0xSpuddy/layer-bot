#!/usr/bin/env python3
"""
Test script to check if block time tracking works properly
"""
import os
import sys
import subprocess
import time
import re
from pathlib import Path

def check_layerd_binary():
    """Check if layerd binary is available"""
    print("\n---- Checking layerd binary ----")
    
    # Try using which command
    which_result = subprocess.run(
        ["which", "layerd"], 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True
    )
    
    if which_result.returncode == 0:
        print(f"✓ layerd found at: {which_result.stdout.strip()}")
        return True
    else:
        print("✗ layerd not found in PATH")
        
        # Try running the layerd version command directly
        try:
            version_result = subprocess.run(
                ["layerd", "version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            
            if version_result.returncode == 0:
                print(f"✓ layerd is available. Version: {version_result.stdout.strip()}")
                return True
            else:
                print(f"✗ Error running layerd: {version_result.stderr}")
        except FileNotFoundError:
            print("✗ layerd binary not found in system")
    
    return False

def test_block_query():
    """Test querying block information"""
    print("\n---- Testing layerd query block command ----")
    
    try:
        # Test simple version with direct command
        block_result = subprocess.run(
            "layerd query block", 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            shell=True
        )
        
        if block_result.returncode == 0:
            print("✓ Basic block query works")
            
            # Print some of the output for debugging
            print(f"  Output excerpt: {block_result.stdout[:300]}...")
            
            # Check for height in the expected format
            height_found = False
            for height_pattern in [r'height:\s*"(\d+)"', r'height:\s*(\d+)']:
                if re.search(height_pattern, block_result.stdout):
                    height_found = True
                    print(f"✓ Found height using pattern: {height_pattern}")
                    break
            
            if not height_found:
                print("✗ Could not find height in expected format")
                
            # Check for time in expected format
            time_found = False
            for time_pattern in [
                r'time:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)',
                r'time:\s*"?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)"?'
            ]:
                if re.search(time_pattern, block_result.stdout):
                    time_found = True
                    print(f"✓ Found time using pattern: {time_pattern}")
                    break
            
            if not time_found:
                print("✗ Could not find time in expected format")
                # Look for any time-like string
                time_lines = [line for line in block_result.stdout.split('\n') if 'time' in line]
                if time_lines:
                    print(f"  Found lines with 'time': {time_lines[:3]}")
                    
            return height_found and time_found
        else:
            print(f"✗ Error querying block: {block_result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error during block query test: {e}")
        return False

def test_block_time_module():
    """Test the block_time module"""
    print("\n---- Testing block_time module ----")
    
    # Try to import the module
    try:
        # Add the src directory to the path
        sys.path.append(str(Path(__file__).parent))
        
        from src.layerbot.utils.block_time import get_block_info, LAYERD_PATH
        
        print(f"✓ Successfully imported block_time module")
        print(f"  Using layerd at: {LAYERD_PATH}")
        
        # Try getting block info
        height, block_time = get_block_info()
        
        if height is not None and block_time is not None:
            print(f"✓ Successfully got block info:")
            print(f"  Height: {height}")
            print(f"  Time: {block_time}")
            return True
        else:
            print("✗ Failed to get block info")
            return False
    except ImportError as e:
        print(f"✗ Error importing block_time module: {e}")
        return False
    except Exception as e:
        print(f"✗ Error in block_time module: {e}")
        return False

def check_environment():
    """Check environment variables"""
    print("\n---- Checking environment variables ----")
    
    layer_rpc = os.environ.get("LAYER_RPC_URL")
    if layer_rpc:
        print(f"✓ LAYER_RPC_URL is set to: {layer_rpc}")
    else:
        print("! LAYER_RPC_URL is not set. Setting default value...")
        os.environ["LAYER_RPC_URL"] = "https://rpc.layer.exchange"
        print(f"  Set to: {os.environ['LAYER_RPC_URL']}")

def diagnostic_query():
    """Run a diagnostic query to see raw output"""
    print("\n---- Running diagnostic block query ----")
    try:
        print("Executing: layerd query block")
        result = subprocess.run(
            "layerd query block", 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            shell=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("\nCOMMAND OUTPUT (first 50 lines):")
            lines = result.stdout.split('\n')
            for i, line in enumerate(lines[:50]):
                print(f"{i+1:3d}: {line}")
            print("...")
            if len(lines) > 50:
                print(f"({len(lines) - 50} more lines)")
        else:
            print(f"Command failed with error: {result.stderr}")
    except Exception as e:
        print(f"Error running diagnostic: {e}")

def main():
    """Main test function"""
    print("===== Block Time Tracking Test =====")
    
    check_environment()
    
    layerd_available = check_layerd_binary()
    if not layerd_available:
        print("\n⚠️ Warning: layerd binary not found. Some tests may fail.")
    
    # Run a diagnostic query to see the raw output format
    diagnostic_query()
    
    block_query_works = test_block_query()
    if not block_query_works:
        print("\n⚠️ Warning: block queries not working. Please check your layerd installation.")
    
    module_works = test_block_time_module()
    
    # Print summary
    print("\n===== Test Summary =====")
    print(f"layerd binary available: {'YES' if layerd_available else 'NO'}")
    print(f"Block query works: {'YES' if block_query_works else 'NO'}")
    print(f"Block time module works: {'YES' if module_works else 'NO'}")
    
    if layerd_available and block_query_works and module_works:
        print("\n✅ All tests passed! The block time tracking should work correctly.")
    else:
        print("\n❌ Some tests failed. Please fix the issues before using block time tracking.")

if __name__ == "__main__":
    main() 