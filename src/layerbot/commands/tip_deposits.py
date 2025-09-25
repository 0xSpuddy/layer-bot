import click
import pandas as pd
import subprocess
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

account_name = os.getenv('ACCOUNT_NAME')
if not account_name:
    raise ValueError("ACCOUNT_NAME not found in .env file")

layer_rpc_url = os.getenv('LAYER_RPC_URL')
if not layer_rpc_url:
    raise ValueError("LAYER_RPC_URL not found in .env file")

def execute_tip_tx(query_data):
    """Execute the tip transaction command"""
    cmd = [
        "./layerd", "tx", "oracle", "tip",
        query_data,
        "10000loya",
        "--from", account_name,
        "--fees", "12loya",
        "--gas", "300000",
        "--yes",
        "--chain-id", "layertest-4",
        "--node", layer_rpc_url
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        click.echo("Transaction successful!")
        click.echo(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        click.echo("Transaction failed!")
        click.echo(f"Error: {e.stderr}")
        return False

def get_unclaimed_deposits():
    """Get list of unclaimed deposit IDs"""
    csv_file = os.getenv('BRIDGE_DEPOSITS_CSV')
    if not csv_file:
        click.echo("Error: BRIDGE_DEPOSITS_CSV not found in .env file")
        return pd.DataFrame()
        
    df = pd.read_csv(csv_file)
    # Filter for unclaimed deposits
    unclaimed = df[
        (df['Status'].str.lower() != 'completed')
    ]
    return unclaimed.sort_values('Deposit ID')

@click.command()
def tip_deposits():
    """Process tips for unclaimed bridge deposits"""
    # Get unclaimed deposits
    unclaimed = get_unclaimed_deposits()
    
    if unclaimed.empty:
        click.echo("No unclaimed deposits found!")
        return
    
    click.echo("\nUnclaimed Deposit IDs:")
    for _, row in unclaimed.iterrows():
        click.echo(f"Deposit ID: {row['Deposit ID']}")
    
    # Query data for ERB Bridge tips
    query_data = "000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000009545242427269646765000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000c"
    
    # Ask user if they want to tip all
    response = click.prompt("\nDo you want to tip for all unclaimed deposits? (Press Enter for yes, 'n' for no)", default='')
    
    if response.lower() != 'n':
        click.echo("\nProcessing tips for all unclaimed deposits...")
        for _, row in unclaimed.iterrows():
            click.echo(f"\nProcessing tip for Deposit ID: {row['Deposit ID']}")
            if execute_tip_tx(query_data):
                click.echo("Waiting 6 seconds before next transaction...")
                time.sleep(6)
            else:
                click.echo(f"Stopping due to failed transaction for Deposit ID: {row['Deposit ID']}")
                break
    else:
        # Ask which deposits to tip
        deposit_ids = click.prompt("\nEnter Deposit IDs to tip (comma-separated)")
        selected_ids = [int(id.strip()) for id in deposit_ids.split(',')]
        
        selected_deposits = unclaimed[unclaimed['Deposit ID'].isin(selected_ids)]
        
        for _, row in selected_deposits.iterrows():
            click.echo(f"\nProcessing tip for Deposit ID: {row['Deposit ID']}")
            if execute_tip_tx(query_data):
                click.echo("Waiting 6 seconds before next transaction...")
                time.sleep(6)
            else:
                click.echo(f"Stopping due to failed transaction for Deposit ID: {row['Deposit ID']}")
                break

if __name__ == "__main__":
    claim_deposits() 
