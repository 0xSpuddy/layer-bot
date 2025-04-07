from flask import Flask, render_template
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route('/')
def show_deposits():
    # Read the CSV file
    df = pd.read_csv('bridge_deposits.csv')
    
    # Convert timestamp columns to more readable format
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df['Aggregate Timestamp'] = pd.to_numeric(df['Aggregate Timestamp'], errors='coerce')
    
    # Convert the large numbers to ETH format (divide by 10^18)
    df['Amount'] = df['Amount'].apply(lambda x: float(x) / 1e18)
    df['Tip'] = df['Tip'].apply(lambda x: float(x) / 1e18)
    
    # Calculate which rows need highlighting
    current_time = datetime.now().timestamp()
    twelve_hours = 12 * 60 * 60  # 12 hours in seconds
    
    # Ready to claim status (green)
    df['ready_to_claim'] = (
        (df['Claimed'].fillna('no').str.lower() == 'no') & 
        (df['Aggregate Timestamp'].notna()) & 
        ((current_time - df['Aggregate Timestamp']) > twelve_hours)
    )
    
    # Invalid recipient status (red)
    df['invalid_recipient'] = ~df['Recipient'].fillna('').str.startswith('tellor1')
    
    # Sort the dataframe:
    # 1. Unclaimed ('no' or empty) first
    # 2. Then by Deposit ID in descending order
    df['Claimed'] = df['Claimed'].fillna('no')
    df = df.sort_values(
        by=['Claimed', 'Deposit ID'],
        ascending=[True, False],  # True for Claimed (puts 'no' first), False for Deposit ID (descending order)
    )
    
    # Convert DataFrame to list of dictionaries for template rendering
    deposits = df.to_dict('records')
    
    return render_template('deposits.html', deposits=deposits)

if __name__ == '__main__':
    app.run(debug=True) 