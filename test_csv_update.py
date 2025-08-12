#!/usr/bin/env python3

import csv
import os
from dotenv import load_dotenv

def debug_csv_update():
    """Debug the CSV update logic"""
    load_dotenv()
    
    # Get the CSV file name from environment  
    base_csv = os.getenv('BRIDGE_DEPOSITS_CSV')
    print(f"CSV file: {base_csv}")
    
    # Simulate the claimed_ids we got from the function
    claimed_ids = {'1', '2'}
    print(f"Claimed IDs (set): {claimed_ids}")
    print(f"Type of elements in claimed_ids: {type(list(claimed_ids)[0])}")
    
    # Read the CSV and debug the comparison
    print("\n=== Debugging CSV Logic ===")
    with open(base_csv, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i < 5:  # Only check first 5 rows
                deposit_id = row['Deposit ID']
                print(f"Row {i+1}:")
                print(f"  Deposit ID from CSV: '{deposit_id}' (type: {type(deposit_id)})")
                print(f"  Is in claimed_ids: {deposit_id in claimed_ids}")
                print(f"  Would set Claimed to: {'yes' if deposit_id in claimed_ids else 'no'}")
                print()

if __name__ == "__main__":
    debug_csv_update() 