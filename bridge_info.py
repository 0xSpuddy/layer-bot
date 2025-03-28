import os
from web3 import Web3
from dotenv import load_dotenv
import json
import csv
from datetime import datetime
from query_layer import generate_queryId, get_report_timestamp

def load_abi():
    """Load the ABI from the JSON file."""
    with open('contracts/bridge_abi.json', 'r') as f:
        return json.load(f)

def setup_csv():
    """Setup CSV file with headers if it doesn't exist."""
    csv_file = os.getenv('BRIDGE_DEPOSITS_CSV')
    if not csv_file:
        print("Error: BRIDGE_DEPOSITS_CSV not found in .env file")
        return False
        
    if not os.path.exists(csv_file):
        try:
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Timestamp', 'Deposit ID', 'Sender', 'Recipient', 'Amount', 'Tip', 'Block Height', 'Query ID', 'Report Timestamp'])
            print(f"Created new CSV file: {csv_file}")
            return True
        except Exception as e:
            print(f"Error creating CSV file: {e}")
            return False
    return True

def get_existing_deposit_ids():
    """Read the CSV file and return a set of existing deposit IDs."""
    csv_file = os.getenv('BRIDGE_DEPOSITS_CSV')
    if not csv_file:
        print("Error: BRIDGE_DEPOSITS_CSV not found in .env file")
        return set()
        
    existing_ids = set()
    if os.path.exists(csv_file):
        try:
            with open(csv_file, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'Deposit ID' in row:  # Check if the column exists
                        existing_ids.add(int(row['Deposit ID']))
        except Exception as e:
            print(f"Error reading CSV file: {e}")
    return existing_ids

def save_deposit_to_csv(deposit_id, deposit_info):
    """Save deposit information to CSV file."""
    csv_file = os.getenv('BRIDGE_DEPOSITS_CSV')
    if not csv_file:
        print("Error: BRIDGE_DEPOSITS_CSV not found in .env file")
        return
        
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Generate query ID for this deposit
    query_info = generate_queryId(deposit_id)
    
    # Get the report timestamp from Layer chain
    report_timestamp = get_report_timestamp(query_info['queryId'])
    
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            deposit_id,
            deposit_info[0],
            deposit_info[1],
            deposit_info[2],
            deposit_info[3],
            deposit_info[4],
            query_info['queryId'],
            report_timestamp or ''  # Use empty string if no timestamp found
        ])

def main():
    # Load environment variables
    load_dotenv()
    
    # Get required environment variables
    contract_address = os.getenv('BRIDGE_CONTRACT_ADDRESS')
    if not contract_address:
        print("Error: BRIDGE_CONTRACT_ADDRESS not found in .env file")
        return
        
    # Get the RPC URL from environment
    rpc_url = os.getenv('ETHEREUM_RPC_URL')
    if not rpc_url:
        print("Error: ETHEREUM_RPC_URL not found in .env file")
        return
    
    try:
        print("Starting program execution...")
        
        # Setup CSV file if it doesn't exist
        print("Setting up CSV file...")
        if not setup_csv():
            print("Failed to setup CSV file")
            return
        
        # Get existing deposit IDs from CSV
        print("Getting existing deposit IDs...")
        existing_ids = get_existing_deposit_ids()
        print(f"Found {len(existing_ids)} existing deposits in CSV file")
        
        # Initialize Web3
        print(f"Initializing Web3 with RPC URL: {rpc_url}")
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Verify connection
        print("Verifying Web3 connection...")
        if not w3.is_connected():
            print("Error: Could not connect to the RPC endpoint")
            return
        print("Successfully connected to RPC endpoint")
            
        # Load contract ABI
        print("Loading contract ABI...")
        try:
            abi = load_abi()
            print("Successfully loaded ABI")
        except Exception as e:
            print(f"Error loading ABI: {e}")
            return
        
        # Create contract instance
        print(f"Creating contract instance with address: {contract_address}")
        try:
            contract = w3.eth.contract(address=contract_address, abi=abi)
            print("Successfully created contract instance")
        except Exception as e:
            print(f"Error creating contract instance: {e}")
            return
        
        # 1. Get and print the most recent deposit ID
        print("\nAttempting to get deposit ID...")
        try:
            deposit_id = contract.functions.depositId().call()
            print(f"Most recent deposit ID: {deposit_id}")
        except Exception as e:
            print(f"Error getting deposit ID: {e}")
            print("Contract function call failed. Check if the contract address and ABI are correct.")
            return
        
        # 2. Get and print the current deposit limit
        print("\nAttempting to get deposit limit...")
        try:
            deposit_limit = contract.functions.depositLimit().call()
            deposit_limit_in_eth = int(deposit_limit / 10**18)
            print(f"Current deposit limit: {deposit_limit_in_eth} TRB")
        except Exception as e:
            print(f"Error getting deposit limit: {e}")
            print("Contract function call failed. Check if the contract address and ABI are correct.")
            return
        
        # 3. Iterate through all deposits
        print("\nFetching all deposits...")
        current_deposit_id = 1
        new_deposits = 0
        
        while True:
            try:
                print(f"\nFetching deposit {current_deposit_id}...")
                deposit_info = contract.functions.deposits(current_deposit_id).call()
                
                # Check if this is an empty deposit (zero address sender)
                if deposit_info[0] == '0x0000000000000000000000000000000000000000':
                    print(f"\nNo more deposits found after ID {current_deposit_id - 1}")
                    break
                
                # Only process if this deposit ID is not already in the CSV
                if current_deposit_id not in existing_ids:
                    print(f"Processing new deposit {current_deposit_id}...")
                    # Generate query ID
                    query_info = generate_queryId(current_deposit_id)
                    
                    # Get the report timestamp
                    report_timestamp = get_report_timestamp(query_info['queryId'])
                    
                    # Print to terminal
                    print(f"\nNew Deposit ID: {current_deposit_id}")
                    print(f"Sender: {deposit_info[0]}")
                    print(f"Recipient: {deposit_info[1]}")
                    print(f"Amount: {deposit_info[2]}")
                    print(f"Tip: {deposit_info[3]}")
                    print(f"Block Height: {deposit_info[4]}")
                    print(f"Query ID: {query_info['queryId']}")
                    print(f"Report Timestamp: {report_timestamp or 'Not found'}")
                    
                    # Save to CSV
                    save_deposit_to_csv(current_deposit_id, deposit_info)
                    new_deposits += 1
                
                current_deposit_id += 1
                
            except Exception as e:
                print(f"Error fetching deposit {current_deposit_id}: {e}")
                print("Stopping deposit iteration due to error")
                break
        
        print(f"\nAdded {new_deposits} new deposits to {os.getenv('BRIDGE_DEPOSITS_CSV')}")
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print("Please check your RPC URL and make sure it's a valid EVM chain endpoint")
        import traceback
        print("\nFull error traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 