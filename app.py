from flask import Flask, render_template, request, jsonify
import pandas as pd
from datetime import datetime, timedelta
from layerbot.utils.scan_time import get_last_scan_time
from layerbot.utils.block_time import get_block_time_stats
from layerbot.commands.estimate_block_time import estimate
import subprocess
import json
from pathlib import Path

app = Flask(__name__)

def prepare_chart_data(deposits_df):
    """Prepare deposits data for the chart visualization."""
    try:
        # Create a copy to avoid modifying the original
        df = deposits_df.copy()
        
        # Sort by timestamp for proper chronological order
        df = df.sort_values('Timestamp')
        
        # Prepare individual deposit data (scatter points)
        individual_deposits = []
        cumulative_total = 0
        cumulative_data = []
        
        for _, row in df.iterrows():
            try:
                # Skip rows with invalid data
                if pd.isna(row['Timestamp']) or pd.isna(row['Amount']):
                    continue
                    
                # Individual deposit data
                individual_deposits.append({
                    'x': row['Timestamp'].isoformat(),
                    'y': float(row['Amount']),
                    'deposit_id': int(row['Deposit ID']),
                    'formatted_date': row['Formatted_Timestamp']
                })
                
                # Cumulative total data
                cumulative_total += float(row['Amount'])
                cumulative_data.append({
                    'x': row['Timestamp'].isoformat(),
                    'y': cumulative_total,
                    'count': len(cumulative_data) + 1,
                    'formatted_date': row['Formatted_Timestamp']
                })
            except Exception as e:
                print(f"Error processing row {row.get('Deposit ID', 'unknown')}: {e}")
                continue
        
        return {
            'individual_deposits': individual_deposits,
            'cumulative_deposits': cumulative_data
        }
    
    except Exception as e:
        print(f"Error preparing chart data: {e}")
        return {
            'individual_deposits': [],
            'cumulative_deposits': []
        }

@app.route('/')
def show_deposits():
    # Read the deposits CSV file with Aggregate Timestamp as string
    deposits_df = pd.read_csv('bridge_deposits.csv', dtype={'Aggregate Timestamp': str})
    
    # Get the most recent scan time
    most_recent_scan = get_last_scan_time()
    if not most_recent_scan:
        most_recent_scan = "No scan time available"
    
    # Get block time statistics
    block_time_stats = get_block_time_stats()
    
    # Filter out deposit IDs 27 and 32
    deposits_df = deposits_df[~deposits_df['Deposit ID'].isin([27, 32])]
    
    # Convert timestamp columns to more readable format with error handling
    try:
        deposits_df['Timestamp'] = pd.to_datetime(deposits_df['Timestamp'], errors='coerce')
        # Remove rows with invalid timestamps
        deposits_df = deposits_df.dropna(subset=['Timestamp'])
        deposits_df['Formatted_Timestamp'] = deposits_df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception as e:
        print(f"Error processing timestamps: {e}")
        # Fallback: create dummy timestamps if all fail
        deposits_df['Timestamp'] = pd.to_datetime('1970-01-01')
        deposits_df['Formatted_Timestamp'] = '1970-01-01 00:00:00 UTC'
    
    # Format Aggregate Timestamp for display with error handling
    try:
        numeric_aggregate_timestamps = pd.to_numeric(deposits_df['Aggregate Timestamp'], errors='coerce')
        
        def safe_format_timestamp(x):
            try:
                if pd.notna(x) and x > 0:
                    # Handle both seconds and milliseconds timestamps
                    if x > 1e10:  # If timestamp is in milliseconds
                        x = x / 1000
                    # Check if year is reasonable (between 1970 and 2100)
                    dt = datetime.fromtimestamp(x)
                    if 1970 <= dt.year <= 2100:
                        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
                return 'N/A'
            except (ValueError, OSError, OverflowError) as e:
                print(f"Error formatting timestamp {x}: {e}")
                return 'N/A'
        
        deposits_df['Formatted_Aggregate_Timestamp'] = numeric_aggregate_timestamps.apply(safe_format_timestamp)
    except Exception as e:
        print(f"Error processing aggregate timestamps: {e}")
        deposits_df['Formatted_Aggregate_Timestamp'] = 'N/A'
    
    # Convert the large numbers to ETH format (divide by 10^18)
    deposits_df['Amount'] = deposits_df['Amount'].apply(lambda x: float(x) / 1e18)
    
    # Calculate which rows need highlighting
    current_time = datetime.now().timestamp()
    twelve_hours = 12 * 60 * 60  # 12 hours in seconds
    
    # Convert Aggregate Timestamp to numeric only for comparison, keeping original string value
    numeric_timestamps = pd.to_numeric(deposits_df['Aggregate Timestamp'], errors='coerce')
    
    # Ready to claim status (green)
    deposits_df['ready_to_claim'] = (
        (deposits_df['Claimed'].fillna('no').str.lower() == 'no') & 
        (numeric_timestamps.notna()) & 
        ((current_time - numeric_timestamps) > twelve_hours)
    )
    
    # Recent scan status (pale green)
    if isinstance(most_recent_scan, str) and most_recent_scan != "No scan time available":
        most_recent_scan_time = pd.to_datetime(most_recent_scan).timestamp()
        deposits_df['recent_scan'] = (
            (numeric_timestamps.notna()) & 
            ((most_recent_scan_time - numeric_timestamps) <= twelve_hours) &
            (deposits_df['Claimed'].fillna('no').str.lower() != 'yes')  # Exclude claimed deposits
        )
    else:
        deposits_df['recent_scan'] = False
    
    # Invalid recipient status (red)
    deposits_df['invalid_recipient'] = ~deposits_df['Recipient'].fillna('').str.startswith('tellor1')
    
    # Sort the deposits dataframe
    deposits_df['Claimed'] = deposits_df['Claimed'].fillna('no')
    deposits_df = deposits_df.sort_values(
        by=['Claimed', 'Deposit ID'],
        ascending=[True, False]
    )
    
    # Read the withdrawals CSV file
    try:
        withdrawals_df = pd.read_csv('bridge_withdrawals.csv')
        
        # Handle withdraw_id column
        if withdrawals_df['withdraw_id'].dtype == 'object':
            # If it's a string, clean it up
            withdrawals_df['withdraw_id'] = withdrawals_df['withdraw_id'].str.replace('"', '')
        # Convert to numeric
        withdrawals_df['withdraw_id'] = pd.to_numeric(withdrawals_df['withdraw_id'])
        
        # Convert boolean columns to proper format
        withdrawals_df['success'] = withdrawals_df['success'].astype(bool)
        withdrawals_df['Claimed'] = withdrawals_df['Claimed'].astype(bool)
        
        # Sort by withdraw_id in descending order
        withdrawals_df = withdrawals_df.sort_values('withdraw_id', ascending=False)
        withdrawals = withdrawals_df.to_dict('records')
    except Exception as e:
        print(f"Error reading withdrawals CSV: {e}")
        withdrawals = []
    
    # Prepare chart data for deposits over time visualization
    chart_data = prepare_chart_data(deposits_df)
    
    # Convert DataFrames to list of dictionaries
    deposits = deposits_df.to_dict('records')
    
    return render_template('deposits.html', 
                          deposits=deposits, 
                          withdrawals=withdrawals, 
                          most_recent_scan=most_recent_scan,
                          block_time_stats=block_time_stats,
                          chart_data=chart_data)

@app.route('/estimate-block', methods=['POST'])
def estimate_block():
    try:
        # Get the block height from the request
        block_height = request.form.get('block_height')
        timezone = request.form.get('timezone')  # Optional timezone parameter
        
        if not block_height or not block_height.isdigit():
            return jsonify({'success': False, 'error': 'Invalid block height'})
            
        # Run the layerbot estimate function directly instead of spawning a subprocess
        # This ensures we use the exact height provided by the user
        from layerbot.commands.estimate_block_time import estimate
        import io
        import sys
        
        # Capture stdout to get the output
        old_stdout = sys.stdout
        new_stdout = io.StringIO()
        sys.stdout = new_stdout
        
        # Run the estimation with the user's block height and optional timezone
        success = estimate(int(block_height), timezone)
        
        # Get the captured output
        output = new_stdout.getvalue()
        
        # Restore stdout
        sys.stdout = old_stdout
        
        if not success:
            return jsonify({'success': False, 'error': 'Estimation failed: ' + output})
            
        # Parse the output
        lines = output.strip().split('\n')
        result = {}
        
        # Extract the relevant information from the output
        for line in lines:
            if 'Block Time Estimation' in line or '===' in line:
                continue
                
            if ':' in line:
                key, value = line.split(':', 1)
                result[key.strip()] = value.strip()
        
        # Add the user input to the response
        return jsonify({
            'success': True, 
            'result': result, 
            'raw_output': output,
            'user_input': block_height,
            'timezone': timezone
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False, 
            'error': str(e),
            'traceback': traceback.format_exc()
        })

if __name__ == '__main__':
    app.run(debug=True) 