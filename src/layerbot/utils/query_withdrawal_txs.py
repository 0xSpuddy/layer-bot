import os
import subprocess
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

def query_transaction_details(tx_hash):
    """
    Query a specific transaction by hash and return the parsed transaction details.
    
    Args:
        tx_hash (str): The transaction hash to query
        
    Returns:
        dict: Transaction details including the amount and timestamp, or None if error
    """
    try:
        # Load environment variables
        load_dotenv()
        
        # Get the Layer RPC URL from environment
        layer_rpc_url = os.getenv('LAYER_RPC_URL')
        if not layer_rpc_url:
            print("Error: LAYER_RPC_URL not found in .env file")
            return None
            
        # Execute the layerd query command
        cmd = ['./layerd', 'query', 'tx', '--type=hash', tx_hash, '--node', layer_rpc_url, '--output', 'json']
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the JSON output
        tx_data = json.loads(result.stdout)
        
        # Extract amount from tx.body.messages[0].amount.amount
        amount = None
        if 'tx' in tx_data and 'body' in tx_data['tx']:
            body = tx_data['tx']['body']
            if 'messages' in body and len(body['messages']) > 0:
                message = body['messages'][0]
                if 'amount' in message and 'amount' in message['amount']:
                    amount_str = message['amount']['amount']
                    # Extract just the numeric part (remove 'loya' suffix if present)
                    amount = amount_str.replace('loya', '').strip()
        
        # Extract timestamp from raw_data.timestamp (not tx_response.timestamp)
        timestamp = None
        timestamp_str = None
        if 'timestamp' in tx_data:
            timestamp_str = tx_data['timestamp']
            try:
                # Parse ISO format timestamp (e.g., "2024-12-23T10:30:45Z")
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except Exception as e:
                print(f"Error parsing timestamp {timestamp_str}: {e}")
        
        return {
            'tx_hash': tx_hash,
            'amount': amount,
            'timestamp': timestamp,
            'timestamp_str': timestamp_str,
            'raw_data': tx_data
        }
        
    except subprocess.CalledProcessError as e:
        print(f"Error querying transaction {tx_hash}: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON for transaction {tx_hash}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error querying transaction {tx_hash}: {e}")
        return None

def update_withdrawal_amounts():
    """
    Read the bridge_withdrawals.csv file, query each transaction for amount details,
    and update the CSV with the amount information.
    
    Returns:
        bool: True if successful, False if error
    """
    try:
        # Load environment variables
        load_dotenv()
        
        # Get the CSV file path from environment
        csv_file = os.getenv('BRIDGE_WITHDRAWALS_CSV', 'bridge_withdrawals.csv')
        
        if not os.path.exists(csv_file):
            print(f"Withdrawals CSV file not found: {csv_file}")
            return False
            
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        # Check if we already have an 'Amount' column
        if 'Amount' not in df.columns:
            df['Amount'] = ''
        
        # Query each transaction that doesn't have an amount yet
        updated_count = 0
        for index, row in df.iterrows():
            tx_hash = row.get('txhash')
            current_amount = row.get('Amount', '')
            
            # Skip if we already have an amount for this transaction
            if current_amount and current_amount != '':
                continue
                
            if tx_hash and tx_hash != '':
                print(f"Querying transaction {tx_hash} for amount...")
                tx_details = query_transaction_details(tx_hash)
                
                if tx_details and tx_details['amount']:
                    df.at[index, 'Amount'] = tx_details['amount']
                    updated_count += 1
                    print(f"Updated transaction {tx_hash} with amount: {tx_details['amount']}")
                else:
                    print(f"Could not get amount for transaction {tx_hash}")
        
        # Save updated CSV
        df.to_csv(csv_file, index=False)
        print(f"Updated {updated_count} withdrawal amounts in {csv_file}")
        
        return True
        
    except Exception as e:
        print(f"Error updating withdrawal amounts: {e}")
        return False

def update_withdrawal_timestamps():
    """
    Read the bridge_withdrawals.csv file, query each transaction for timestamp details,
    and update the CSV with the timestamp information.
    
    Returns:
        bool: True if successful, False if error
    """
    try:
        # Load environment variables
        load_dotenv()
        
        # Get the CSV file path from environment
        csv_file = os.getenv('BRIDGE_WITHDRAWALS_CSV', 'bridge_withdrawals.csv')
        
        if not os.path.exists(csv_file):
            print(f"Withdrawals CSV file not found: {csv_file}")
            return False
            
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        # Check if we already have a 'Timestamp' column
        if 'Timestamp' not in df.columns:
            # Insert Timestamp as the first column
            df.insert(0, 'Timestamp', '')
        
        # Ensure Timestamp column is string type to avoid dtype warnings
        df['Timestamp'] = df['Timestamp'].astype(str)
        
        # Query each transaction that doesn't have a timestamp yet
        updated_count = 0
        for index, row in df.iterrows():
            tx_hash = row.get('txhash')
            current_timestamp = row.get('Timestamp', '')
            
            # Skip if we already have a timestamp for this transaction
            # Check for both empty strings, NaN values, and 'nan' strings
            if (pd.notna(current_timestamp) and 
                current_timestamp != '' and 
                current_timestamp != 'nan'):
                continue
                
            if tx_hash and tx_hash != '':
                print(f"Querying transaction {tx_hash} for timestamp...")
                tx_details = query_transaction_details(tx_hash)
                
                if tx_details and tx_details['timestamp']:
                    timestamp_str = tx_details['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    df.at[index, 'Timestamp'] = timestamp_str
                    updated_count += 1
                    print(f"Updated transaction {tx_hash} with timestamp: {timestamp_str}")
                else:
                    print(f"Could not get timestamp for transaction {tx_hash}")
        
        # Reorder columns to ensure Timestamp is first
        if 'Timestamp' in df.columns:
            columns = ['Timestamp'] + [col for col in df.columns if col != 'Timestamp']
            df = df[columns]
        
        # Save updated CSV
        df.to_csv(csv_file, index=False)
        print(f"Updated {updated_count} withdrawal timestamps in {csv_file}")
        
        return True
        
    except Exception as e:
        print(f"Error updating withdrawal timestamps: {e}")
        return False

def main():
    """Example usage and testing function."""
    # Test with a specific transaction hash
    test_hash = "F6F09B6C6D4FB14F2108A60FD3FB0B356E76EBA462B5661C785A797896103822"
    
    print(f"Testing transaction query with hash: {test_hash}")
    result = query_transaction_details(test_hash)
    
    if result:
        print(f"Transaction Hash: {result['tx_hash']}")
        print(f"Amount: {result['amount']}")
        print(f"Timestamp: {result['timestamp']}")
        print(f"Timestamp String: {result['timestamp_str']}")
    else:
        print("Failed to query transaction")
    
    # Test updating all withdrawal amounts
    print("\nUpdating all withdrawal amounts...")
    success = update_withdrawal_amounts()
    if success:
        print("Successfully updated withdrawal amounts")
    else:
        print("Failed to update withdrawal amounts")
    
    # Test updating all withdrawal timestamps
    print("\nUpdating all withdrawal timestamps...")
    success = update_withdrawal_timestamps()
    if success:
        print("Successfully updated withdrawal timestamps")
    else:
        print("Failed to update withdrawal timestamps")

if __name__ == "__main__":
    main()
