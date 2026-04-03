import os
from web3 import Web3
from dotenv import load_dotenv
import json
import csv
from datetime import datetime
from layerbot.utils.query_layer import generate_queryId, get_claimed_deposit_ids
from layerbot.utils.get_timestamp_from_height import get_timestamp_from_height
from layerbot.utils.query_withdrawal_txs import update_withdrawal_amounts
from layerbot.utils.discord_alerts import alert_new_bridge_deposits
import pandas as pd

def load_abi():
    """Load the ABI from the JSON file."""
    with open('contracts/bridge_abi.json', 'r') as f:
        return json.load(f)

def get_deposit_timestamps_from_ethereum(w3, contract):
    """
    Get deposit timestamps from Ethereum Deposit events.
    Returns a dictionary mapping deposit_id -> timestamp
    """
    deposit_timestamps = {}
    
    try:
        # Get all Deposit events from the contract
        print("Fetching Deposit events from Ethereum...")
        
        # Get the event filter for Deposit events
        deposit_event_filter = contract.events.Deposit.create_filter(fromBlock=0, toBlock='latest')
        deposit_events = deposit_event_filter.get_all_entries()
        
        print(f"Found {len(deposit_events)} Deposit events")
        
        for event in deposit_events:
            deposit_id = event['args']['_depositId']
            block_number = event['blockNumber']
            
            # Get the block to get the timestamp
            block = w3.eth.get_block(block_number)
            timestamp = datetime.fromtimestamp(block['timestamp'])
            
            deposit_timestamps[deposit_id] = timestamp
            
        print(f"Collected timestamps for {len(deposit_timestamps)} deposits")
        
    except Exception as e:
        print(f"Error fetching deposit timestamps from Ethereum: {e}")
        
    return deposit_timestamps

def setup_csv():
    """Setup CSV file with headers if it doesn't exist or if headers are missing."""
    csv_file = 'bridge_deposits.csv'    
    headers = ['Timestamp', 'Deposit ID', 'Sender', 'Recipient', 'Amount', 'Tip', 'Block Height', 'Query ID', 'Status', 'Claimed Timestamp', 'Query Data', 'Bridge Contract Address']
    
    try:
        # Check if file exists and has headers
        if os.path.exists(csv_file):
            with open(csv_file, 'r', newline='') as f:
                reader = csv.reader(f)
                first_row = next(reader, None)
                if first_row != headers:
                    # Headers don't match, create new file with correct headers
                    print(f"Updating headers in CSV file: {csv_file}")
                    with open(csv_file, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(headers)
                    return True
        else:
            # File doesn't exist, create new file with headers
            print(f"Creating new CSV file: {csv_file}")
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
            return True
            
        return True
    except Exception as e:
        print(f"Error setting up CSV file: {e}")
        return False

def get_existing_deposit_ids(contract_address=None):
    """Read the CSV file and return a set of existing deposit IDs.
    
    If contract_address is provided, only return IDs for that specific contract.
    This prevents deposit ID collisions between contracts that each start from ID 1.
    """
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
                    if 'Deposit ID' not in row:
                        continue
                    if contract_address and row.get('Bridge Contract Address', '').lower() != contract_address.lower():
                        continue
                    existing_ids.add(int(row['Deposit ID']))
        except Exception as e:
            print(f"Error reading CSV file: {e}")
    return existing_ids


def save_deposit_to_csv(deposit_id, deposit_info, deposit_timestamps, claimed=False, contract_address=None):
    """Save deposit information to CSV file using Ethereum transaction timestamp."""
    csv_file = os.getenv('BRIDGE_DEPOSITS_CSV')
    if not csv_file:
        print("Error: BRIDGE_DEPOSITS_CSV not found in .env file")
        return
        
    # Get timestamp from Ethereum transaction instead of Tellor Layer block height
    timestamp_str = ''
    if deposit_id in deposit_timestamps:
        timestamp_str = deposit_timestamps[deposit_id].strftime('%Y-%m-%d %H:%M:%S')
        print(f"Using Ethereum transaction timestamp for deposit {deposit_id}: {timestamp_str}")
    else:
        print(f"Warning: No Ethereum transaction timestamp found for deposit {deposit_id}, using current time as fallback")
        timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Generate query ID and data for this deposit
    query_info = generate_queryId(deposit_id)
    
    # Use the provided contract address or default to BRIDGE_CONTRACT_ADDRESS_CURRENT
    if contract_address is None:
        contract_address = os.getenv('BRIDGE_CONTRACT_ADDRESS_CURRENT') or os.getenv('BRIDGE_CONTRACT_ADDRESS_1') or os.getenv('BRIDGE_CONTRACT_ADDRESS_0', '')
    
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp_str,
            deposit_id,
            deposit_info[0],
            deposit_info[1],
            deposit_info[2],
            deposit_info[3],
            deposit_info[4],
            query_info['queryId'],
            'completed' if claimed else 'in progress',
            '',  # Claimed Timestamp - empty for new deposits, will be filled when first detected as claimed
            query_info['queryData'],
            contract_address
        ])

def check_withdrawal_status(w3, contract, withdraw_id):
    """Check if a withdrawal has been claimed on Ethereum using the withdrawClaimed mapping."""
    try:
        return contract.functions.withdrawClaimed(withdraw_id).call()
    except Exception as e:
        print(f"Error checking withdrawal status for ID {withdraw_id}: {e}")
        return False

def update_withdrawal_status():
    """Update the claimed status for all withdrawals in the CSV file."""
    csv_file = os.getenv('BRIDGE_WITHDRAWALS_CSV')
    if not csv_file:
        print("Error: BRIDGE_WITHDRAWALS_CSV not found in .env file")
        return

    # Get the RPC URL from environment
    rpc_url = os.getenv('ETHEREUM_RPC_URL')
    if not rpc_url:
        print("Error: ETHEREUM_RPC_URL not found in .env file")
        return

    try:
        # Initialize Web3
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Verify connection
        if not w3.is_connected():
            print("Error: Could not connect to the RPC endpoint")
            return
            
        # Load contract ABI
        abi = load_abi()
        
        # Build contract instances for all configured bridge contracts
        # A withdrawal is claimed if ANY contract reports it as claimed
        raw_addrs = [
            os.getenv('BRIDGE_CONTRACT_ADDRESS_CURRENT'),
            os.getenv('BRIDGE_CONTRACT_ADDRESS_1'),
            os.getenv('BRIDGE_CONTRACT_V2_ADDRESS'),
        ]
        # Deduplicate while preserving order, skip empty values
        seen = set()
        contract_addrs = []
        for a in raw_addrs:
            if a and a.lower() not in seen:
                seen.add(a.lower())
                contract_addrs.append(a)

        if not contract_addrs:
            print("Error: No bridge contract addresses found in .env (BRIDGE_CONTRACT_ADDRESS_CURRENT, BRIDGE_CONTRACT_ADDRESS_1, or BRIDGE_CONTRACT_V2_ADDRESS)")
            return

        contracts = [w3.eth.contract(address=Web3.to_checksum_address(a), abi=abi) for a in contract_addrs]
        print(f"Checking withdrawClaimed against {len(contracts)} contract(s): {contract_addrs}")

        # Read existing CSV file
        if not os.path.exists(csv_file):
            print(f"Withdrawals CSV file not found: {csv_file}")
            return
            
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        # Clean the withdraw_id column — handle both quoted strings ('"68"') and
        # already-numeric values that pandas read back as int/float from a previous cycle
        df['withdraw_id'] = df['withdraw_id'].astype(str).str.replace('"', '').astype(int)
        
        # Add 'Claimed' column if it doesn't exist
        if 'Claimed' not in df.columns:
            df['Claimed'] = False
            
        # Update claimed status for each withdrawal — claimed on any contract counts
        for index, row in df.iterrows():
            withdraw_id = row['withdraw_id']
            is_claimed = any(check_withdrawal_status(w3, c, withdraw_id) for c in contracts)
            df.at[index, 'Claimed'] = is_claimed
            
        # Reorder columns to ensure consistent order: Timestamp, creator, recipient, success, Claimed, txhash, withdraw_id, Amount
        # Build column order based on what exists in the dataframe
        column_order = []
        
        # Add columns in preferred order if they exist
        preferred_order = ['Timestamp', 'creator', 'recipient', 'success', 'Claimed', 'txhash', 'withdraw_id', 'Amount']
        for col in preferred_order:
            if col in df.columns:
                column_order.append(col)
        
        # Add any remaining columns that weren't in the preferred list
        for col in df.columns:
            if col not in column_order:
                column_order.append(col)
        
        df = df[column_order]
            
        # Save updated CSV
        df.to_csv(csv_file, index=False)
        print(f"Updated withdrawal status in {csv_file}")
        
    except Exception as e:
        print(f"Error updating withdrawal status: {e}")

def main(contract_address=None):
    # Load environment variables
    load_dotenv()
    
    # Resolve contract address: use provided arg, then CURRENT, then V1 for backwards compatibility
    if contract_address is None:
        contract_address = os.getenv('BRIDGE_CONTRACT_ADDRESS_CURRENT') or os.getenv('BRIDGE_CONTRACT_ADDRESS_1')
    if not contract_address:
        print("Error: No bridge contract address found. Set BRIDGE_CONTRACT_ADDRESS_CURRENT or BRIDGE_CONTRACT_ADDRESS_1 in .env")
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
        
        # Get existing deposit IDs from CSV, filtered to this contract only
        print("Getting existing deposit IDs...")
        existing_ids = get_existing_deposit_ids(contract_address=contract_address)
        print(f"Found {len(existing_ids)} existing deposits in CSV file for contract {contract_address}")
        
        # Get claimed deposit IDs
        print("Getting claimed deposit IDs...")
        claimed_ids = get_claimed_deposit_ids()
        
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
            contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
            print("Successfully created contract instance")
        except Exception as e:
            print(f"Error creating contract instance: {e}")
            return
        
        # Update withdrawal status
        print("\nUpdating withdrawal status...")
        update_withdrawal_status()
        
        # Update withdrawal amounts
        print("\nUpdating withdrawal amounts...")
        update_withdrawal_amounts()
        
        # Update withdrawal timestamps
        print("\nUpdating withdrawal timestamps...")
        from layerbot.utils.query_withdrawal_txs import update_withdrawal_timestamps
        update_withdrawal_timestamps()
        
        # Get deposit timestamps from Ethereum
        print("\nGetting deposit timestamps from Ethereum...")
        deposit_timestamps = get_deposit_timestamps_from_ethereum(w3, contract)
        
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
        
        # Determine starting deposit ID
        # 1. Check if BRIDGE_START_DEPOSIT_ID is set in .env (for explicit control)
        # 2. If contract has existing deposits on-chain, use that as a hint
        # 3. Otherwise start from next ID after what's in CSV, or 1 if CSV is empty
        
        start_id_override = os.getenv('BRIDGE_START_DEPOSIT_ID')
        if start_id_override:
            current_deposit_id = int(start_id_override)
            print(f"Using BRIDGE_START_DEPOSIT_ID from .env: {current_deposit_id}")
        else:
            # deposit_id is already fetched above; use it directly to avoid a second RPC call
            if deposit_id > 0 and existing_ids:
                # Contract has deposits. If CSV has data, continue from where we left off
                max_csv_id = max(existing_ids)
                if deposit_id > max_csv_id:
                    # There are new deposits on-chain we haven't seen
                    current_deposit_id = max_csv_id + 1
                    print(f"Continuing from CSV max ID + 1: {current_deposit_id} (on-chain has {deposit_id})")
                else:
                    # We're caught up, start from next expected
                    current_deposit_id = deposit_id + 1
                    print(f"CSV is current, checking for new deposits from: {current_deposit_id}")
            else:
                # Fresh contract or fresh CSV — scan from 1 up to deposit_id
                current_deposit_id = 1
                print(f"Starting fresh scan from deposit ID: 1 up to {deposit_id}")
        
        new_deposits = 0
        new_deposits_for_discord = []  # Track new deposits for Discord alerts
        
        print(f"Scanning deposits starting from ID {current_deposit_id} (CSV has {len(existing_ids)} existing deposits, on-chain counter={deposit_id})")
        
        # Iterate up to the on-chain depositId counter.  Contracts may not assign deposit IDs
        # starting from 1 (e.g. V2 continued V1's counter and its first deposit is ID 154),
        # so empty slots are skipped rather than treated as the end of data.
        while current_deposit_id <= deposit_id:
            try:
                print(f"\nFetching deposit {current_deposit_id}...")
                deposit_info = contract.functions.deposits(current_deposit_id).call()
                
                # Empty slot — this contract never stored a deposit at this ID (common for
                # contracts that continue a shared counter from a predecessor contract)
                if deposit_info[0] == '0x0000000000000000000000000000000000000000':
                    print(f"Deposit {current_deposit_id}: empty slot, skipping")
                    current_deposit_id += 1
                    continue
                
                # Only process if this deposit ID is not already in the CSV
                if current_deposit_id not in existing_ids:
                    print(f"Processing new deposit {current_deposit_id}...")
                    # Generate query ID
                    query_info = generate_queryId(current_deposit_id)
                    
                    # Check if deposit has been claimed
                    is_claimed = str(current_deposit_id) in claimed_ids
                    print(f"spud Claimed: {is_claimed}")
                    
                    # Get timestamp for this deposit
                    timestamp_str = ''
                    if current_deposit_id in deposit_timestamps:
                        timestamp_str = deposit_timestamps[current_deposit_id].strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Print to terminal
                    print(f"\nNew Deposit ID: {current_deposit_id}")
                    print(f"Sender: {deposit_info[0]}")
                    print(f"Recipient: {deposit_info[1]}")
                    print(f"Amount: {deposit_info[2]}")
                    print(f"Tip: {deposit_info[3]}")
                    print(f"Block Height: {deposit_info[4]}")
                    print(f"Query ID: {query_info['queryId']}")
                    
                    # Prepare deposit data for Discord alert
                    deposit_data = {
                        'deposit_id': current_deposit_id,
                        'timestamp': timestamp_str,
                        'sender': deposit_info[0],
                        'recipient': deposit_info[1],
                        'amount': str(deposit_info[2]),
                        'tip': str(deposit_info[3]),
                        'block_height': str(deposit_info[4])
                    }
                    new_deposits_for_discord.append(deposit_data)
                    
                    # Save to CSV with the contract address
                    save_deposit_to_csv(current_deposit_id, deposit_info, deposit_timestamps, is_claimed, contract_address)
                    new_deposits += 1
                
                current_deposit_id += 1
                
            except Exception as e:
                print(f"Error fetching deposit {current_deposit_id}: {e}")
                print("Stopping deposit iteration due to error")
                break
        
        print(f"\nAdded {new_deposits} new deposits to {os.getenv('BRIDGE_DEPOSITS_CSV')}")
        
        # Send Discord alerts for new deposits
        if new_deposits_for_discord:
            print(f"\nSending Discord alerts for {len(new_deposits_for_discord)} new deposits...")
            try:
                alert_new_bridge_deposits(new_deposits_for_discord)
                print("Discord alerts sent successfully!")
            except Exception as e:
                print(f"Error sending Discord alerts: {e}")
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        print("Please check your RPC URL and make sure it's a valid EVM chain endpoint")
        import traceback
        print("\nFull error traceback:")
        print(traceback.format_exc())

def collect_withdrawals_from_ethereum():
    """
    Fetch Withdraw events from all configured bridge contracts on Ethereum.

    Since the Layer node is pruned and MsgWithdrawTokens history is not available,
    this is the primary source for claimed withdrawal data.  Ethereum event logs are
    NOT pruned, so this always returns the complete history of claimed withdrawals.

    For each withdrawal ID found in a Withdraw event the following data is recorded:
      - withdraw_id, creator (Layer sender), recipient (ETH address), Amount (loya),
        Claimed=True, Timestamp (ETH block time of the claim), success=True

    The results are MERGED into the existing withdrawals CSV so that any Layer-side
    data already present (txhash, etc.) is preserved.
    """
    load_dotenv()

    csv_file = os.getenv('BRIDGE_WITHDRAWALS_CSV', 'bridge_withdrawals.csv')
    rpc_url = os.getenv('ETHEREUM_RPC_URL')

    if not rpc_url:
        print("Error: ETHEREUM_RPC_URL not found in .env file")
        return

    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            print("Error: Could not connect to Ethereum RPC")
            return

        abi = load_abi()

        # Build deduplicated list of contract addresses to scan
        raw_addrs = [
            os.getenv('BRIDGE_CONTRACT_ADDRESS_CURRENT'),
            os.getenv('BRIDGE_CONTRACT_ADDRESS_1'),
            os.getenv('BRIDGE_CONTRACT_V2_ADDRESS'),
        ]
        seen = set()
        contract_addrs = []
        for a in raw_addrs:
            if a and a.lower() not in seen:
                seen.add(a.lower())
                contract_addrs.append(a)

        if not contract_addrs:
            print("No bridge contract addresses configured")
            return

        # TOKEN_DECIMAL_PRECISION_MULTIPLIER = 1e12:
        #   Withdraw event emits amount in wei (18 dec), CSV stores loya (6 dec relative to TRB)
        #   amount_loya = event_amount_wei / 1e12
        TOKEN_DECIMAL_PRECISION_MULTIPLIER = 10 ** 12

        eth_withdrawals = {}  # withdraw_id (int) -> row dict

        for contract_address in contract_addrs:
            try:
                contract = w3.eth.contract(
                    address=Web3.to_checksum_address(contract_address), abi=abi
                )
                print(f"Fetching Withdraw events from {contract_address}...")
                withdraw_filter = contract.events.Withdraw.create_filter(
                    fromBlock=0, toBlock='latest'
                )
                events = withdraw_filter.get_all_entries()
                print(f"  Found {len(events)} Withdraw events")

                for event in events:
                    withdraw_id = int(event['args']['_depositId'])
                    block = w3.eth.get_block(event['blockNumber'])
                    timestamp = datetime.fromtimestamp(block['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    amount_loya = str(int(event['args']['_amount'] // TOKEN_DECIMAL_PRECISION_MULTIPLIER))
                    recipient = event['args']['_recipient'].lower()
                    creator = event['args']['_sender']  # Layer address string

                    eth_withdrawals[withdraw_id] = {
                        'withdraw_id': str(withdraw_id),
                        'creator': creator,
                        'recipient': recipient,
                        'Amount': amount_loya,
                        'Claimed': True,
                        'txhash': '',  # Layer txhash unknown; filled in by MsgWithdrawTokens scan
                        'success': True,
                        'Timestamp': timestamp,
                    }
                    print(f"  ID={withdraw_id}, {amount_loya} loya, creator={creator[:24]}...")

            except Exception as e:
                print(f"  Error fetching Withdraw events from {contract_address}: {e}")

        print(f"Total: {len(eth_withdrawals)} unique claimed withdrawals from Ethereum events")

        # Load existing CSV to preserve Layer-side data (txhash, etc.)
        existing_rows = {}  # withdraw_id str -> row dict
        if os.path.exists(csv_file):
            try:
                df_existing = pd.read_csv(csv_file)
                df_existing['withdraw_id'] = (
                    df_existing['withdraw_id'].astype(str).str.replace('"', '').str.strip()
                )
                for _, row in df_existing.iterrows():
                    wid = str(row['withdraw_id']).strip()
                    if wid and wid != 'nan':
                        existing_rows[wid] = row.to_dict()
            except Exception as e:
                print(f"Warning: could not read existing withdrawals CSV: {e}")

        # Merge: start with existing data, then overlay Ethereum event data
        merged = {wid: dict(row) for wid, row in existing_rows.items()}

        def _is_blank(val):
            return str(val).strip() in ('', 'nan', 'None')

        for withdraw_id, eth_row in eth_withdrawals.items():
            wid_str = str(withdraw_id)
            if wid_str in merged:
                # Row already known — update claimed status and fill any blanks
                merged[wid_str]['Claimed'] = True
                for field in ('Amount', 'Timestamp', 'creator', 'recipient'):
                    if _is_blank(merged[wid_str].get(field, '')):
                        merged[wid_str][field] = eth_row[field]
            else:
                # New row from Ethereum event
                merged[wid_str] = eth_row

        # Fill stub rows for any withdrawal IDs that exist on the Layer chain but
        # are absent from both Ethereum events and the existing CSV.
        # get-last-withdrawal-id tells us every integer from 1..last_id has a
        # corresponding MsgWithdrawTokens transaction (IDs can't be skipped on Layer).
        try:
            from layerbot.utils.query_layer import get_last_withdrawal_id
            last_id = get_last_withdrawal_id()
            if last_id and last_id > 0:
                print(f"Last withdrawal ID on Layer chain: {last_id}")
                for missing_id in range(1, last_id + 1):
                    if str(missing_id) not in merged:
                        print(f"  Adding stub row for withdrawal ID {missing_id}")
                        merged[str(missing_id)] = {
                            'withdraw_id': str(missing_id),
                            'creator': '',
                            'recipient': '',
                            'Amount': '',
                            'Claimed': '',
                            'txhash': '',
                            'success': '',
                            'Timestamp': '',
                        }
        except Exception as e:
            print(f"Warning: could not fill withdrawal ID gaps: {e}")

        if not merged:
            print("No withdrawal data to save")
            return

        # Write merged data back, sorted by withdraw_id
        def _safe_int(v):
            try:
                return int(str(v).replace('"', '').strip())
            except Exception:
                return 0

        sorted_rows = sorted(merged.values(), key=lambda r: _safe_int(r.get('withdraw_id', 0)))

        all_cols = set()
        for row in sorted_rows:
            all_cols.update(str(k) for k in row.keys())

        preferred = ['Timestamp', 'creator', 'recipient', 'success', 'Claimed', 'txhash', 'withdraw_id', 'Amount']
        final_cols = [c for c in preferred if c in all_cols]
        for c in sorted(all_cols):
            if c not in final_cols:
                final_cols.append(c)

        df_out = pd.DataFrame(sorted_rows, columns=final_cols)
        df_out.to_csv(csv_file, index=False)
        print(f"Saved {len(sorted_rows)} withdrawals to {csv_file}")

    except Exception as e:
        print(f"Error collecting withdrawal data from Ethereum: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    main() 