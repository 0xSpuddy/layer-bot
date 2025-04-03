from eth_abi import encode
from eth_utils import keccak
import subprocess
import json
import base64
import os
from dotenv import load_dotenv
import csv

def generate_queryId(deposit_id):
    """
    Generate queryData and queryId for a bridge deposit.
    Follows the Solidity pattern:
    bytes queryData = abi.encode("TRBBridge", abi.encode(true,depositId));
    bytes32 queryId = keccak256(queryData);
    """
    # Encode the inner tuple (true, deposit_id)
    inner_data = encode(['bool', 'uint256'], [True, deposit_id])
    
    # Encode the outer tuple ("TRBBridge", inner_data)
    query_data = encode(['string', 'bytes'], ['TRBBridge', inner_data])
    
    # Generate queryId using keccak256
    query_id = keccak(query_data)
    
    return {
        'queryData': query_data.hex(),
        'queryId': query_id.hex()
    }

def get_report_timestamp(query_id):
    """
    Query the Layer chain for the report timestamp using the layerd binary.
    Returns the timestamp as a string, or None if the query fails.
    """
    try:
        # Load environment variables
        load_dotenv()
        
        # Get the Layer RPC URL
        layer_rpc_url = os.getenv('LAYER_RPC_URL')
        if not layer_rpc_url:
            print("Error: LAYER_RPC_URL not found in .env file")
            return None
            
        # Execute the layerd query command with the RPC URL
        cmd = ['./layerd', 'query', 'oracle', 'get-current-aggregate-report', query_id, '--node', layer_rpc_url]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the output to get the timestamp
        output_lines = result.stdout.split('\n')
        for line in output_lines:
            if line.startswith('timestamp:'):
                return line.split('"')[1]
        
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error querying Layer chain: {e.stderr}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def get_claim_deposit_txs():
    """
    Query the Layer chain for all claim deposit transactions and save them to a CSV file.
    Returns a list of dictionaries containing txhash and deposit_ids for each transaction.
    """
    try:
        # Load environment variables
        load_dotenv()
        
        # Get the Layer RPC URL
        layer_rpc_url = os.getenv('LAYER_RPC_URL')
        if not layer_rpc_url:
            print("Error: LAYER_RPC_URL not found in .env file")
            return []
            
        # Get the CSV file name from environment
        base_csv = os.getenv('BRIDGE_DEPOSITS_CSV')
        if not base_csv:
            print("Error: BRIDGE_DEPOSITS_CSV not found in .env file")
            return []
            
        # Create the transactions CSV filename
        txs_csv = base_csv.replace('.csv', '_txs.csv')
        
        # Execute the layerd query command
        cmd = ['./layerd', 'query', 'txs', '--query', 'message.action=\'/layer.bridge.MsgClaimDepositsRequest\'', '--node', layer_rpc_url]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        print("\nDebug - Raw Query Output:")
        print(result.stdout)
        
        # Parse the output
        transactions = []
        current_tx = None
        parsing_deposit_ids = False
        pending_deposit_ids = []
        last_raw_log = None
        
        print("\nDebug - Parsing Process:")
        for line in result.stdout.split('\n'):
            line = line.strip()
            print(f"\nProcessing line: '{line}'")
            
            # Check for raw_log line
            if line.startswith('raw_log:'):
                last_raw_log = line
                print(f"Found raw_log line: {line}")
                continue
            
            # Start parsing deposit IDs
            if line.startswith('deposit_ids:'):
                print("Found deposit_ids line, starting to parse IDs")
                parsing_deposit_ids = True
                pending_deposit_ids = []  # Reset pending deposit IDs
                continue
                
            # Parse deposit IDs
            if parsing_deposit_ids and line.startswith('-'):
                print(f"Found deposit ID line: {line}")
                try:
                    deposit_id = line.split('"')[1]
                    print(f"Extracted deposit ID: {deposit_id}")
                    pending_deposit_ids.append(deposit_id)
                    print(f"Current pending deposit IDs: {pending_deposit_ids}")
                except Exception as e:
                    print(f"Error parsing deposit ID: {e}")
                    print(f"Line: {line}")
            elif parsing_deposit_ids and not line.startswith('-'):
                print("Ending deposit IDs parsing")
                parsing_deposit_ids = False
            
            # Extract txhash
            if line.startswith('txhash:'):
                print(f"Found txhash line: {line}")
                if current_tx:
                    print(f"Adding previous transaction: {current_tx}")
                    transactions.append(current_tx)
                
                # Determine success based on raw_log
                success = last_raw_log == 'raw_log: ""' if last_raw_log else False
                print(f"Transaction success: {success} (raw_log: {last_raw_log})")
                
                current_tx = {
                    'txhash': line.split('txhash: ')[1].strip(),
                    'deposit_ids': pending_deposit_ids,
                    'success': success
                }
                print(f"Created new transaction: {current_tx}")
                pending_deposit_ids = []  # Reset pending deposit IDs
                last_raw_log = None  # Reset last_raw_log
        
        # Add the last transaction if it exists
        if current_tx:
            print(f"Adding final transaction: {current_tx}")
            transactions.append(current_tx)
        
        print(f"\nFound {len(transactions)} transactions")
        for tx in transactions:
            print(f"Transaction: txhash={tx.get('txhash', 'N/A')}, deposit_ids={tx.get('deposit_ids', [])}, success={tx.get('success', False)}")
        
        # Save to CSV
        with open(txs_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['txhash', 'deposit_ids', 'success'])
            writer.writeheader()
            for tx in transactions:
                # Convert deposit_ids list to string for CSV storage
                tx['deposit_ids'] = ','.join(tx['deposit_ids'])
                # Convert success boolean to yes/no string
                tx['success'] = 'yes' if tx['success'] else 'no'
                writer.writerow(tx)
            
        print(f"Saved {len(transactions)} claim deposit transactions to {txs_csv}")
        return transactions
        
    except subprocess.CalledProcessError as e:
        print(f"Error querying Layer chain: {e.stderr}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

def get_claimed_deposit_ids():
    """
    Read the transactions CSV and update the main CSV file with claimed status.
    Returns a set of successfully claimed deposit IDs.
    """
    try:
        # First get the latest transaction data
        print("Getting latest claim deposit transactions...")
        transactions = get_claim_deposit_txs()
        if not transactions:
            print("No transactions found")
            return set()
            
        # Load environment variables
        load_dotenv()
        
        # Get the CSV file names from environment
        base_csv = os.getenv('BRIDGE_DEPOSITS_CSV')
        if not base_csv:
            print("Error: BRIDGE_DEPOSITS_CSV not found in .env file")
            return set()
            
        # Create the transactions CSV filename
        txs_csv = base_csv.replace('.csv', '_txs.csv')
        
        # Read the transactions CSV to get claimed status
        claimed_status = {}  # deposit_id -> success status
        with open(txs_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Split comma-separated deposit IDs
                deposit_ids = row['deposit_ids'].split(',')
                success = row['success']
                # Record success status for each deposit ID
                for deposit_id in deposit_ids:
                    claimed_status[deposit_id] = success
        
        print(f"Found claim status for {len(claimed_status)} deposit IDs")
        
        # Read the main CSV and update Claimed column
        rows = []
        with open(base_csv, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                deposit_id = row['Deposit ID']
                # Update Claimed column based on transaction status
                row['Claimed'] = claimed_status.get(deposit_id, 'no')
                rows.append(row)
        
        # Write back to CSV with updated Claimed column
        with open(base_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"Updated Claimed column in {base_csv}")
        
        # Return set of successfully claimed deposit IDs
        claimed_ids = {deposit_id for deposit_id, success in claimed_status.items() if success == 'yes'}
        print(f"Found {len(claimed_ids)} successfully claimed deposit IDs")
        print(f"Claimed IDs: {claimed_ids}")
        return claimed_ids
        
    except Exception as e:
        print(f"Error reading claimed deposit IDs: {e}")
        return set()

def get_loya_balance(address):
    """Query the Layer chain for an address's loya balance."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get the Layer RPC URL
        layer_rpc_url = os.getenv('LAYER_RPC_URL')
        if not layer_rpc_url:
            print("Error: LAYER_RPC_URL not found in .env file")
            return None
            
        # Execute the layerd query command
        cmd = ['./layerd', 'query', 'bank', 'balance', address, 'loya', '--node', layer_rpc_url]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the output to get the balance amount
        output_lines = result.stdout.split('\n')
        for line in output_lines:
            if 'amount:' in line:
                return line.split('"')[1]  # Extract amount from "amount: "103249751""
        
        return "0"  # Return "0" if no balance found
        
    except subprocess.CalledProcessError as e:
        print(f"Error querying Layer chain: {e.stderr}")
        return "0"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "0"

def main():
    # Example usage
    deposit_id = 1
    result = generate_queryId(deposit_id)
    print(f"Deposit ID: {deposit_id}")
    print(f"Query Data: {result['queryData']}")
    print(f"Query ID: {result['queryId']}")
    
    # Get the timestamp
    timestamp = get_report_timestamp(result['queryId'])
    if timestamp:
        print(f"Report Timestamp: {timestamp}")
    else:
        print("No timestamp found")
        
    # Get claim deposit transactions
    print("\nFetching claim deposit transactions...")
    transactions = get_claim_deposit_txs()
    print(f"Found {len(transactions)} claim deposit transactions")
    
    # Get successfully claimed deposit IDs
    print("\nGetting claimed deposit IDs...")
    claimed_ids = get_claimed_deposit_ids()
    
    # Load environment variables
    load_dotenv()
    
    # Get the CSV file name from environment
    base_csv = os.getenv('BRIDGE_DEPOSITS_CSV')
    if not base_csv:
        print("Error: BRIDGE_DEPOSITS_CSV not found in .env file")
        return
        
    # Read the existing CSV
    rows = []
    with open(base_csv, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            # Update the Claimed column based on whether the deposit ID was successfully claimed
            row['Claimed'] = 'yes' if row['Deposit ID'] in claimed_ids else 'no'
            rows.append(row)
    
    # Write back to CSV with updated Claimed column
    with open(base_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Updated Claimed column in {base_csv}")

if __name__ == "__main__":
    main()
