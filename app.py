from flask import Flask, render_template
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route('/')
def show_deposits():
    # Read the deposits CSV file with Aggregate Timestamp as string
    deposits_df = pd.read_csv('bridge_deposits.csv', dtype={'Aggregate Timestamp': str})
    
    # Get the most recent scan time with error handling
    try:
        # Convert Timestamp column to datetime, ignoring errors
        deposits_df['Timestamp'] = pd.to_datetime(deposits_df['Timestamp'], errors='coerce')
        # Get the maximum timestamp, excluding NaT (Not a Time) values
        most_recent_scan = deposits_df['Timestamp'].max()
        if pd.isna(most_recent_scan):
            most_recent_scan = "No valid timestamps found"
        else:
            most_recent_scan = most_recent_scan.strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception as e:
        print(f"Error processing timestamps: {e}")
        most_recent_scan = "Timestamp data unavailable"
    
    # Filter out deposit IDs 27 and 32
    deposits_df = deposits_df[~deposits_df['Deposit ID'].isin([27, 32])]
    
    # Convert timestamp columns to more readable format
    deposits_df['Timestamp'] = pd.to_datetime(deposits_df['Timestamp'])
    
    # Convert the large numbers to ETH format (divide by 10^18)
    deposits_df['Amount'] = deposits_df['Amount'].apply(lambda x: float(x) / 1e18)
    deposits_df['Tip'] = deposits_df['Tip'].apply(lambda x: float(x) / 1e18)
    
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
    if isinstance(most_recent_scan, str) and most_recent_scan != "No valid timestamps found" and most_recent_scan != "Timestamp data unavailable":
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
    
    # Convert DataFrames to list of dictionaries
    deposits = deposits_df.to_dict('records')
    
    return render_template('deposits.html', deposits=deposits, withdrawals=withdrawals, most_recent_scan=most_recent_scan)

if __name__ == '__main__':
    app.run(debug=True) 