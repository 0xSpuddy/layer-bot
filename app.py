from flask import Flask, render_template
import pandas as pd

app = Flask(__name__)

@app.route('/')
def show_deposits():
    # Read the CSV file
    df = pd.read_csv('bridge_deposits.csv')
    
    # Convert timestamp columns to more readable format
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    # Convert the large numbers to ETH format (divide by 10^18)
    df['Amount'] = df['Amount'].apply(lambda x: float(x) / 1e18)
    df['Tip'] = df['Tip'].apply(lambda x: float(x) / 1e18)
    
    # Convert DataFrame to list of dictionaries for template rendering
    deposits = df.to_dict('records')
    
    return render_template('deposits.html', deposits=deposits)

if __name__ == '__main__':
    app.run(debug=True) 