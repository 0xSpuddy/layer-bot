from flask import Flask, render_template
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route('/')
def show_deposits():
    # Read the deposits CSV file
    deposits_df = pd.read_csv('bridge_deposits.csv')
    
    # Convert timestamp columns to more readable format
    deposits_df['Timestamp'] = pd.to_datetime(deposits_df['Timestamp'])
    deposits_df['Aggregate Timestamp'] = pd.to_numeric(deposits_df['Aggregate Timestamp'], errors='coerce')
    
    # Convert the large numbers to ETH format (divide by 10^18)
    deposits_df['Amount'] = deposits_df['Amount'].apply(lambda x: float(x) / 1e18)
    deposits_df['Tip'] = deposits_df['Tip'].apply(lambda x: float(x) / 1e18)
    
    # Calculate which rows need highlighting
    current_time = datetime.now().timestamp()
    twelve_hours = 12 * 60 * 60  # 12 hours in seconds
    
    # Ready to claim status (green)
    deposits_df['ready_to_claim'] = (
        (deposits_df['Claimed'].fillna('no').str.lower() == 'no') & 
        (deposits_df['Aggregate Timestamp'].notna()) & 
        ((current_time - deposits_df['Aggregate Timestamp']) > twelve_hours)
    )
    
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
        # Clean up the withdraw_id column (remove quotes)
        withdrawals_df['withdraw_id'] = withdrawals_df['withdraw_id'].str.replace('"', '')
        # Convert withdraw_id to numeric for proper sorting
        withdrawals_df['withdraw_id'] = pd.to_numeric(withdrawals_df['withdraw_id'])
        # Sort by withdraw_id in descending order
        withdrawals_df = withdrawals_df.sort_values('withdraw_id', ascending=False)
        withdrawals = withdrawals_df.to_dict('records')
    except Exception as e:
        print(f"Error reading withdrawals CSV: {e}")
        withdrawals = []
    
    # Convert DataFrames to list of dictionaries
    deposits = deposits_df.to_dict('records')
    
    return render_template('deposits.html', deposits=deposits, withdrawals=withdrawals)

if __name__ == '__main__':
    app.run(debug=True) 