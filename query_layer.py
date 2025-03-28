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
    Returns a list of dictionaries containing deposit_id, raw_log, and txhash for each transaction.
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
        
        # Parse the output
        transactions = []
        current_tx = {}
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            
            # Start of a new transaction
            if line.startswith('txs:'):
                if current_tx:
                    transactions.append(current_tx)
                current_tx = {}
                continue
                
            # Extract deposit_id
            if 'key: deposit_id' in line:
                current_tx['deposit_id'] = line.split('value: "')[1].strip('"')
                
            # Extract raw_log
            if line.startswith('raw_log:'):
                current_tx['raw_log'] = line.split('raw_log: ')[1].strip('"')
                
            # Extract txhash
            if line.startswith('txhash:'):
                current_tx['txhash'] = line.split('txhash: ')[1].strip()
        
        # Add the last transaction if it exists
        if current_tx:
            transactions.append(current_tx)
        
        # Save to CSV
        with open(txs_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['deposit_id', 'raw_log', 'txhash'])
            writer.writeheader()
            writer.writerows(transactions)
            
        print(f"Saved {len(transactions)} claim deposit transactions to {txs_csv}")
        return transactions
        
    except subprocess.CalledProcessError as e:
        print(f"Error querying Layer chain: {e.stderr}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []

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

if __name__ == "__main__":
    main()
