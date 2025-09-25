import os
import csv
import subprocess
from dotenv import load_dotenv
import base64
import pandas as pd
from datetime import datetime

def parse_aggregate_response(output):
    """Parse the layerd query response into a dictionary."""
    aggregate_data = {}
    current_section = None
    
    for line in output.split('\n'):
        line = line.strip()
        
        if line.startswith('aggregate:'):
            current_section = 'aggregate'
            # continue
            
        if current_section == 'aggregate' and line:
            if line.startswith('aggregate_power:'):
                aggregate_data['aggregate_power'] = int(line.split('"')[1])
            elif line.startswith('aggregate_reporter:'):
                aggregate_data['aggregate_reporter'] = line.split('aggregate_reporter: ')[1]
            elif line.startswith('aggregate_value:'):
                aggregate_data['aggregate_value'] = line.split('aggregate_value: ')[1]
            elif line.startswith('meta_id:'):
                aggregate_data['meta_id'] = line.split('"')[1]
        
        if line.startswith('timestamp:'):
            aggregate_data['timestamp'] = int(line.split('"')[1])
    
    return aggregate_data

def query_layer_chain(query_id, timestamp):
    """Execute layerd query command and return parsed response."""
    try:
        load_dotenv()
        layer_rpc_url = os.getenv('LAYER_RPC_URL')
        if not layer_rpc_url:
            raise Exception("LAYER_RPC_URL not found in .env file")
            
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
        
        print(f"Querying oracle: get-data-before {query_id} {timestamp}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Result: {result.stdout}")
        return parse_aggregate_response(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"Error querying Layer chain: {e.stderr}")
        return None
    except Exception as e:
        print(f"Error in query_layer_chain: {e}")
        return None

def save_aggregate_data(query_id, data):
    """Save aggregate data to a single CSV file, overwriting old data for each query_id."""
    try:
        filename = "aggregate_data_all.csv"
        headers = ['query_id', 'timestamp', 'aggregate_power', 'aggregate_reporter', 'aggregate_value', 'meta_id']
        
        # Create file if it doesn't exist
        if not os.path.exists(filename):
            print(f"Creating new aggregate file: {filename}")
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
        
        # Read existing data
        existing_data = {}
        with open(filename, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_data[row['query_id']] = row
        
        # Add or update data for this query_id
        existing_data[query_id] = {
            'query_id': query_id,
            'timestamp': data['timestamp'],
            'aggregate_power': data['aggregate_power'],
            'aggregate_reporter': data['aggregate_reporter'],
            'aggregate_value': data['aggregate_value'],
            'meta_id': data['meta_id']
        }
        
        # Write all data back to file
        print(f"Updating aggregate data for query_id {query_id[:10]}...: power={data['aggregate_power']}, timestamp={data['timestamp']}")
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row_data in existing_data.values():
                writer.writerow(row_data)
            
        return True
    except Exception as e:
        print(f"Error saving aggregate data: {e}")
        return False

def get_best_timestamp(query_id):
    """Get the timestamp with highest aggregate_power for a query_id from the single CSV file."""
    try:
        filename = "aggregate_data_all.csv"
        if not os.path.exists(filename):
            return None
            
        df = pd.read_csv(filename)
        if df.empty:
            return None
        
        # Filter data for the specific query_id
        query_data = df[df['query_id'] == query_id]
        if query_data.empty:
            return None
            
        best_row = query_data.loc[query_data['aggregate_power'].idxmax()]
        print(f"Best timestamp for {query_id[:10]}...: {best_row['timestamp']} (power: {best_row['aggregate_power']})")
        return best_row['timestamp']
        
    except Exception as e:
        print(f"Error getting best timestamp: {e}")
        return None

def get_bridge_data_before(query_id):
    """Query bridge data and find best timestamp based on aggregate power."""
    try:
        print(f"\nProcessing query_id: {query_id[:10]}...")
        
        best_data = None
        best_power = -1
        
        # Initial query with max timestamp
        max_timestamp = "10000000000000000000"
        print(f"Initial query with max timestamp: {max_timestamp}")
        current_data = query_layer_chain(query_id, max_timestamp)
        print(f"Current data: {current_data}")
        if not current_data:
            print(f"No initial data found for {query_id[:10]}...")
            return None
        
        # Check if this is the best data so far
        if current_data['aggregate_power'] > best_power:
            best_data = current_data
            best_power = current_data['aggregate_power']
            
        # Iterate up to 15 times using found timestamps
        for i in range(14):
            current_timestamp = current_data['timestamp']
            print(f"Query timestamp: {current_timestamp}")
            current_data = query_layer_chain(query_id, current_timestamp)
            print(f"Current data: {current_data}")
            if not current_data:
                print(f"No more data found after {i+1} iterations")
                break
            
            # Check if this is the best data so far
            if current_data['aggregate_power'] > best_power:
                best_data = current_data
                best_power = current_data['aggregate_power']
        
        # Save only the best data for this query_id
        if best_data:
            print(f"Saving best data with power {best_power}")
            save_aggregate_data(query_id, best_data)
            return best_data['timestamp']
        
        return None
        
    except Exception as e:
        print(f"Error in get_bridge_data_before: {e}")
        return None


def main():
    """Main function to run the script directly."""
    try:
        print("Starting bridge reports update process...")
        
        # Load environment variables
        load_dotenv()
        
        # Check for required environment variables
        csv_file = os.getenv('BRIDGE_DEPOSITS_CSV')
        layer_rpc_url = os.getenv('LAYER_RPC_URL')
        
        if not csv_file or not layer_rpc_url:
            print("Error: Required environment variables not found")
            print("Please ensure BRIDGE_DEPOSITS_CSV and LAYER_RPC_URL are set in .env")
            return
            
        # Run the update process
        if update_bridge_deposits_timestamps():
            print("\nBridge reports update completed successfully")
        else:
            print("\nBridge reports update failed")
            
    except Exception as e:
        print(f"\nError in main process: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
