#!/usr/bin/env python3

import subprocess
import os
from dotenv import load_dotenv

def test_claimed_deposits():
    """Test the claimed deposits functionality"""
    load_dotenv()
    
    layer_rpc_url = os.getenv('LAYER_RPC_URL')
    print(f"Layer RPC URL: {layer_rpc_url}")
    
    # Test a few deposit IDs
    test_ids = ['1', '2', '3']
    
    for deposit_id in test_ids:
        print(f"\n=== Testing Deposit ID: {deposit_id} ===")
        cmd = [
            './layerd',
            'query',
            'bridge',
            'get-deposit-claimed',
            deposit_id,
            '--node',
            layer_rpc_url
        ]
        
        print(f"Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            print(f"Return code: {result.returncode}")
            print(f"STDOUT: '{result.stdout}'")
            print(f"STDERR: '{result.stderr}'")
            print(f"STDOUT (repr): {repr(result.stdout)}")
            
            # Test the parsing logic
            is_claimed = 'true' in result.stdout.lower()
            print(f"Parsed as claimed: {is_claimed}")
            
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            print(f"Error output: {e.stderr}")

if __name__ == "__main__":
    test_claimed_deposits() 