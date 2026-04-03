import click
import pandas as pd
import subprocess
import time
import os
from dotenv import load_dotenv
from layerbot.utils.query_layer import generate_withdrawal_queryId

# Load environment variables
load_dotenv()

account_name = os.getenv('ACCOUNT_NAME')
if not account_name:
    raise ValueError("ACCOUNT_NAME not found in .env file")

layer_rpc_url = os.getenv('LAYER_RPC_URL')
if not layer_rpc_url:
    raise ValueError("LAYER_RPC_URL not found in .env file")

chain_id = os.getenv('LAYER_CHAIN_ID')
if not chain_id:
    raise ValueError("LAYER_CHAIN_ID not found in .env file")

def execute_tip_tx(query_data):
    """Execute the tip transaction command"""
    cmd = [
        "./layerd", "tx", "oracle", "tip",
        query_data,
        "1111loya",
        "--from", account_name,
        "--fees", "12loya",
        "--gas", "300000",
        "--yes",
        "--chain-id", chain_id,
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

def get_unclaimed_withdrawals():
    """Get list of unclaimed withdrawal IDs"""
    csv_file = os.getenv('BRIDGE_WITHDRAWALS_CSV')
    if not csv_file:
        click.echo("Error: BRIDGE_WITHDRAWALS_CSV not found in .env file")
        return pd.DataFrame()

    df = pd.read_csv(csv_file)
    unclaimed = df[
        df['Claimed'].astype(str).str.lower().isin(['false', 'no', ''])
        | df['Claimed'].isna()
    ]
    return unclaimed.sort_values('withdraw_id')

@click.command()
def tip_withdrawals():
    """Process tips for unclaimed bridge withdrawals"""
    unclaimed = get_unclaimed_withdrawals()

    if unclaimed.empty:
        click.echo("No unclaimed withdrawals found!")
        return

    click.echo("\nUnclaimed Withdrawal IDs:")
    for _, row in unclaimed.iterrows():
        click.echo(f"Withdrawal ID: {row['withdraw_id']}")

    response = click.prompt("\nDo you want to tip for all unclaimed withdrawals? (Press Enter for yes, 'n' for no)", default='')

    if response.lower() != 'n':
        click.echo("\nProcessing tips for all unclaimed withdrawals...")
        for _, row in unclaimed.iterrows():
            withdrawal_id = int(row['withdraw_id'])
            query_data = generate_withdrawal_queryId(withdrawal_id)['queryData']
            click.echo(f"\nProcessing tip for Withdrawal ID: {withdrawal_id}")
            if execute_tip_tx(query_data):
                click.echo("Waiting 6 seconds before next transaction...")
                time.sleep(6)
            else:
                click.echo(f"Stopping due to failed transaction for Withdrawal ID: {withdrawal_id}")
                break
    else:
        withdrawal_ids = click.prompt("\nEnter Withdrawal IDs to tip (comma-separated)")
        selected_ids = [int(id.strip()) for id in withdrawal_ids.split(',')]

        selected_withdrawals = unclaimed[unclaimed['withdraw_id'].isin(selected_ids)]

        for _, row in selected_withdrawals.iterrows():
            withdrawal_id = int(row['withdraw_id'])
            query_data = generate_withdrawal_queryId(withdrawal_id)['queryData']
            click.echo(f"\nProcessing tip for Withdrawal ID: {withdrawal_id}")
            if execute_tip_tx(query_data):
                click.echo("Waiting 6 seconds before next transaction...")
                time.sleep(6)
            else:
                click.echo(f"Stopping due to failed transaction for Withdrawal ID: {withdrawal_id}")
                break

if __name__ == "__main__":
    tip_withdrawals()
