from eth_abi import encode
from eth_utils import keccak
import subprocess
import json
import base64
import os
from dotenv import load_dotenv
import csv
from web3 import Web3

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

def get_eth_balance(address):
    """Query the ETH balance of an address."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get the Ethereum RPC URL
        eth_rpc_url = os.getenv('ETHEREUM_RPC_URL')
        if not eth_rpc_url:
            print("Error: ETHEREUM_RPC_URL not found in .env file")
            return "0"
            
        # Initialize Web3
        w3 = Web3(Web3.HTTPProvider(eth_rpc_url))
        if not w3.is_connected():
            print("Error: Could not connect to Ethereum RPC")
            return "0"
        
        # Get ETH balance
        balance_wei = w3.eth.get_balance(address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        return str(balance_eth)
        
    except Exception as e:
        print(f"Error querying ETH balance: {e}")
        return "0"

def get_septrb_balance(address):
    """Query the SepTRB token balance of an address."""
    try:
        load_dotenv()
        
        eth_rpc_url = os.getenv('ETHEREUM_RPC_URL')
        if not eth_rpc_url:
            print("Error: ETHEREUM_RPC_URL not found in .env file")
            return "0"
            
        w3 = Web3(Web3.HTTPProvider(eth_rpc_url))
        if not w3.is_connected():
            print("Error: Could not connect to Ethereum RPC")
            return "0"
        
        # SepTRB token contract address
        token_address = "0x80fc34a2f9FfE86F41580F47368289C402DEc660"
        
        # ERC20 balanceOf function signature
        abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        # Create contract instance
        contract = w3.eth.contract(address=token_address, abi=abi)
        
        # Get token balance
        balance_wei = contract.functions.balanceOf(address).call()
        balance_token = w3.from_wei(balance_wei, 'ether')
        return str(balance_token)
        
    except Exception as e:
        print(f"Error querying SepTRB balance: {e}")
        return "0"
    
def get_data_before(query_id, timestamp):
    """
    Query the Layer chain for data before a specific timestamp.
    Returns the aggregate report info before the timestamp.
    """
    try:
        # Load environment variables
        load_dotenv()
        
        # Get the Layer RPC URL
        layer_rpc_url = os.getenv('LAYER_RPC_URL')
        if not layer_rpc_url:
            print("Error: LAYER_RPC_URL not found in .env file")
            return None
            
        # Execute the layerd query command
        cmd = [
            './layerd', 
            'query', 
            'oracle', 
            'get-data-before',
            query_id,
            str(timestamp),
            '--node',
            layer_rpc_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the output
        aggregate_data = {}
        current_section = None
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            
            if line.startswith('aggregate:'):
                current_section = 'aggregate'
                continue
                
            if current_section == 'aggregate' and line:
                if line.startswith('aggregate_power:'):
                    aggregate_data['aggregate_power'] = line.split('"')[1]
                elif line.startswith('aggregate_value:'):
                    aggregate_data['aggregate_value'] = line.split('aggregate_value: ')[1]
                elif line.startswith('height:'):
                    aggregate_data['height'] = line.split('"')[1]
                elif line.startswith('meta_id:'):
                    aggregate_data['meta_id'] = line.split('"')[1]
            
            elif line.startswith('timestamp:'):
                aggregate_data['timestamp'] = line.split('"')[1]
        
        return aggregate_data
        
    except subprocess.CalledProcessError as e:
        print(f"Error querying Layer chain: {e.stderr}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def get_total_reporter_power():
    """
    Query the Layer chain for the total reporter power.
    Returns the total reporter power as a string.
    """

def get_withdraw_tokens_txs():
    """
    Query the Layer chain for all withdraw tokens transactions and save them to a CSV file.
    Returns a list of dictionaries containing transaction details.
    """
    try:
        # Load environment variables
        load_dotenv()
        
        # Get the Layer RPC URL and CSV filename from environment
        layer_rpc_url = os.getenv('LAYER_RPC_URL')
        csv_file = os.getenv('BRIDGE_WITHDRAWALS_CSV', 'bridge_withdrawals.csv')
        
        if not layer_rpc_url:
            print("Error: LAYER_RPC_URL not found in .env file")
            return []
            
        # Execute the layerd query command
        cmd = ['./layerd', 'query', 'txs', '--query', 'message.action=\'/layer.bridge.MsgWithdrawTokens\'', '--node', layer_rpc_url]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        print("\nDebug - Command output received. Starting parse...")
        
        # Parse the output
        transactions = []
        current_tx = None
        next_line_is_withdraw_id = False
        next_line_is_amount = False
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            print(f"\nProcessing line: '{line}'")
            
            # Start of new transaction
            if line.startswith('- code: 0'):
                print("Found new transaction")
                if current_tx:
                    print(f"Adding previous transaction: {current_tx}")
                    transactions.append(current_tx)
                current_tx = {}
                continue
            
            # Check for withdraw_id
            if line.startswith('key: withdraw_id'):
                next_line_is_withdraw_id = True
                continue
            if next_line_is_withdraw_id:
                if line.startswith('value:'):
                    current_tx['withdraw_id'] = line.split('value: ')[1].strip()
                    print(f"Found withdraw_id: {current_tx['withdraw_id']}")
                next_line_is_withdraw_id = False
                
            # Check for amount
            if line.startswith('amount:') and 'key:' not in line:
                next_line_is_amount = True
                continue
            if next_line_is_amount:
                if line.startswith('value:'):
                    amount = line.split('value: ')[1].strip()
                    # Remove 'loya' suffix if present
                    current_tx['amount'] = amount.replace('loya', '').strip()
                    print(f"Found amount: {current_tx['amount']}")
                next_line_is_amount = False
                
            # Check for creator
            if line.startswith('creator:'):
                current_tx['creator'] = line.split('creator: ')[1].strip()
                print(f"Found creator: {current_tx['creator']}")
                
            # Check for recipient
            if line.startswith('recipient:'):
                current_tx['recipient'] = line.split('recipient: ')[1].strip()
                print(f"Found recipient: {current_tx['recipient']}")
                
            # Check for success (raw_log)
            if line.startswith('raw_log:'):
                current_tx['success'] = line.strip() == 'raw_log: ""'
                print(f"Transaction success: {current_tx.get('success')}")
                
            # End of transaction
            if line.startswith('txhash:'):
                if current_tx:
                    current_tx['txhash'] = line.split('txhash: ')[1].strip()
                    print(f"Found txhash: {current_tx['txhash']}")
                    print(f"Final transaction data: {current_tx}")
                    transactions.append(current_tx.copy())
                current_tx = None
        
        # Add the last transaction if it exists
        if current_tx:
            print(f"Adding final transaction: {current_tx}")
            transactions.append(current_tx)
        
        print(f"\nParsing complete. Found {len(transactions)} transactions")
        print("\nAll transactions found:")
        for tx in transactions:
            print(f"Transaction: {tx}")
        
        # Save to CSV
        if transactions:
            # Get all possible fields from all transactions
            fieldnames = set()
            for tx in transactions:
                fieldnames.update(tx.keys())
            fieldnames = sorted(list(fieldnames))
            
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(transactions)
                
            print(f"Saved {len(transactions)} withdraw transactions to {csv_file}")
            print(f"CSV columns: {fieldnames}")
        else:
            print("No withdrawal transactions found")
            
        return transactions
        
    except subprocess.CalledProcessError as e:
        print(f"Error querying Layer chain: {e.stderr}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(f"Error details: {str(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
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

    # Add new section for withdraw scan
    print("\nScanning for withdrawals...")
    withdrawals = get_withdraw_tokens_txs()
    print(f"Found {len(withdrawals)} withdrawal transactions")

if __name__ == "__main__":
    main()
