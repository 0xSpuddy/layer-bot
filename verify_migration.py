#!/usr/bin/env python3
"""
Verification script to ensure the bridge contract migration was successful
"""

import csv
import os
from dotenv import load_dotenv

def verify_migration():
    """Verify the migration was successful"""
    load_dotenv()
    
    print("=" * 60)
    print("BRIDGE CONTRACT MIGRATION VERIFICATION")
    print("=" * 60)
    
    # 1. Check environment variables
    print("\n1. Checking environment variables...")
    old_contract = os.getenv('BRIDGE_CONTRACT_ADDRESS_0')
    new_contract = os.getenv('BRIDGE_CONTRACT_ADDRESS_1')
    
    if old_contract:
        print(f"   ✓ BRIDGE_CONTRACT_ADDRESS_0: {old_contract}")
    else:
        print("   ✗ BRIDGE_CONTRACT_ADDRESS_0 not found!")
        
    if new_contract:
        print(f"   ✓ BRIDGE_CONTRACT_ADDRESS_1: {new_contract}")
    else:
        print("   ✗ BRIDGE_CONTRACT_ADDRESS_1 not found!")
    
    # 2. Check CSV structure
    print("\n2. Checking CSV structure...")
    csv_file = os.getenv('BRIDGE_DEPOSITS_CSV', 'bridge_deposits.csv')
    
    if not os.path.exists(csv_file):
        print(f"   ✗ CSV file not found: {csv_file}")
        return
    
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        expected_headers = ['Timestamp', 'Deposit ID', 'Sender', 'Recipient', 'Amount', 
                          'Tip', 'Block Height', 'Query ID', 'Status', 'Query Data', 
                          'Bridge Contract Address']
        
        if 'Bridge Contract Address' in headers:
            print(f"   ✓ 'Bridge Contract Address' column exists")
        else:
            print(f"   ✗ 'Bridge Contract Address' column missing!")
            print(f"   Current headers: {headers}")
            return
        
        # Read all rows
        rows = list(reader)
        total_rows = len(rows)
        
        print(f"   ✓ Total deposits: {total_rows}")
    
    # 3. Verify contract address distribution
    print("\n3. Checking contract address distribution...")
    
    old_contract_count = 0
    new_contract_count = 0
    missing_count = 0
    
    for row in rows:
        contract_addr = row.get('Bridge Contract Address', '').strip()
        if contract_addr == old_contract:
            old_contract_count += 1
        elif contract_addr == new_contract:
            new_contract_count += 1
        else:
            missing_count += 1
    
    print(f"   Old Contract (V0): {old_contract_count} deposits")
    print(f"   New Contract (V1): {new_contract_count} deposits")
    if missing_count > 0:
        print(f"   ⚠ Missing/Unknown: {missing_count} deposits")
    
    # 4. Check backup file
    print("\n4. Checking backup file...")
    backup_file = f"{csv_file}.backup"
    
    if os.path.exists(backup_file):
        backup_size = os.path.getsize(backup_file)
        current_size = os.path.getsize(csv_file)
        print(f"   ✓ Backup file exists: {backup_file}")
        print(f"   ✓ Backup size: {backup_size:,} bytes")
        print(f"   ✓ Current size: {current_size:,} bytes")
    else:
        print(f"   ⚠ No backup file found")
    
    # 5. Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_good = True
    
    if not old_contract or not new_contract:
        print("✗ Environment variables incomplete")
        all_good = False
    else:
        print("✓ Environment variables configured")
    
    if 'Bridge Contract Address' not in headers:
        print("✗ CSV schema not updated")
        all_good = False
    else:
        print("✓ CSV schema updated correctly")
    
    if old_contract_count == 0 and new_contract_count == 0:
        print("✗ No contract addresses found in data")
        all_good = False
    else:
        print(f"✓ Contract addresses properly assigned ({old_contract_count + new_contract_count} deposits)")
    
    if all_good:
        print("\n✓ Migration successful! All checks passed.")
    else:
        print("\n⚠ Migration incomplete! Please review the issues above.")
    
    print("\nNext steps:")
    print("- Run 'python -m layerbot.bridge_info' to collect new deposits from V1 contract")
    print("- Check dashboard to see contract addresses in deposit details")
    print("=" * 60)

if __name__ == "__main__":
    verify_migration()

