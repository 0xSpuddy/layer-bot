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
    This function is deprecated. Use query_bridge_reports.get_bridge_data_before instead.
    """
    print("Warning: get_report_timestamp is deprecated. Use query_bridge_reports.get_bridge_data_before instead.")
    return None

def get_claim_deposit_txs():
    """
    This function is now deprecated. Use get_claimed_deposit_ids() instead.
    """
    print("Warning: get_claim_deposit_txs is deprecated. Use get_claimed_deposit_ids instead.")
    return []

def get_claimed_deposit_ids():
    """
    Query the Layer chain to determine if deposits have been claimed.
    Returns a set of successfully claimed deposit IDs.
    Also captures the timestamp when a deposit is first detected as claimed.
    """
    try:
        # Load environment variables
        load_dotenv()
        
        # Get the Layer RPC URL
        layer_rpc_url = os.getenv('LAYER_RPC_URL')
        if not layer_rpc_url:
            print("Error: LAYER_RPC_URL not found in .env file")
            return set()
            
        # Get the CSV file name from environment
        base_csv = os.getenv('BRIDGE_DEPOSITS_CSV')
        if not base_csv:
            print("Error: BRIDGE_DEPOSITS_CSV not found in .env file")
            return set()
            
        # Read all deposit IDs from CSV
        deposit_ids = set()
        with open(base_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                deposit_ids.add(row['Deposit ID'])
        
        # Query each deposit ID
        claimed_ids = set()
        for deposit_id in deposit_ids:
            print(f"\nChecking deposit ID: {deposit_id}")
            cmd = [
                './layerd',
                'query',
                'bridge',
                'get-deposit-claimed',
                deposit_id,
                '--node',
                layer_rpc_url
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                # Parse the output - expecting a simple true/false response
                is_claimed = 'true' in result.stdout.lower()
                if is_claimed:
                    claimed_ids.add(deposit_id)
                print(f"Deposit {deposit_id} claimed: {is_claimed}")
            except subprocess.CalledProcessError as e:
                print(f"Error querying deposit {deposit_id}: {e.stderr}")
                continue
        
        print(f"\nFound {len(claimed_ids)} claimed deposits")
        
        # Get current timestamp for newly claimed deposits
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Update the CSV file
        rows = []
        with open(base_csv, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                # Update Status column based on query results (maintain backward compatibility)
                if row['Deposit ID'] in claimed_ids:
                    # Check if this is a newly claimed deposit (status wasn't 'completed' before)
                    was_previously_completed = (str(row.get('Status', '')).lower() == 'completed' or 
                                               str(row.get('Claimed', '')).lower() == 'yes')
                    
                    row['Status'] = 'completed'
                    
                    # Capture claim timestamp only if this is the first time we're detecting it as claimed
                    # AND the Claimed Timestamp field exists
                    if 'Claimed Timestamp' in fieldnames:
                        if not was_previously_completed and not row.get('Claimed Timestamp', '').strip():
                            row['Claimed Timestamp'] = current_timestamp
                            print(f"  → First time detected as claimed! Timestamp: {current_timestamp}")
                    
                    # Keep old Claimed column for backward compatibility if it exists
                    if 'Claimed' in row:
                        row['Claimed'] = 'yes'
                else:
                    # Keep existing status for unclaimed deposits (will be calculated in app.py)
                    if 'Claimed' in row:
                        row['Claimed'] = 'no'
                rows.append(row)
        
        # Write back to CSV with updated Status column
        with open(base_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"Updated Status column in {base_csv}")
        return claimed_ids
        
    except Exception as e:
        print(f"Error checking claimed deposit IDs: {e}")
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
        
        # print("\nDebug - Command output received. Starting parse...")
        
        # Parse the output
        transactions = []
        current_tx = None
        next_line_is_withdraw_id = False
        next_line_is_amount = False
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            # print(f"\nProcessing line: '{line}'")
            
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
            # Update the Status column based on whether the deposit ID was successfully claimed
            if row['Deposit ID'] in claimed_ids:
                row['Status'] = 'completed'
                # Keep old Claimed column for backward compatibility if it exists
                if 'Claimed' in row:
                    row['Claimed'] = 'yes'
            else:
                # Keep existing status for unclaimed deposits
                if 'Claimed' in row:
                    row['Claimed'] = 'no'
            rows.append(row)
    
    # Write back to CSV with updated Status column
    with open(base_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Updated Status column in {base_csv}")

    # Add new section for withdraw scan
    print("\nScanning for withdrawals...")
    withdrawals = get_withdraw_tokens_txs()
    print(f"Found {len(withdrawals)} withdrawal transactions")

if __name__ == "__main__":
    main()
