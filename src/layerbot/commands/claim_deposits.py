import click
import subprocess
import os
import csv
import json
from dotenv import load_dotenv
from web3 import Web3

# Load environment variables at the start
load_dotenv()
layer_rpc_url = os.getenv('LAYER_RPC_URL', '').strip()  # Add strip() to remove any whitespace
account_name = os.getenv('ACCOUNT_NAME')
account_tellor_address = os.getenv('ACCOUNT_TELLOR_ADDRESS')
csv_path = os.getenv('BRIDGE_DEPOSITS_CSV', 'bridge_deposits.csv')
ethereum_rpc_url = os.getenv('ETHEREUM_RPC_URL')
BRIDGE_CONTRACT_ADDRESS_0 = os.getenv('BRIDGE_CONTRACT_ADDRESS_0')

# Clean the URL
layer_rpc_url = ''.join(c for c in layer_rpc_url if ord(c) >= 32)  # Remove control characters
layer_rpc_url = layer_rpc_url.strip()  # Remove leading/trailing whitespace


@click.command('claim-deposits')
def claim_deposits():
    """Claim bridge deposits on Layer chain."""
    # Debug prints for environment variables
    click.echo("\nDebug - Environment Variables:")
    click.echo(f"LAYER_RPC_URL: {layer_rpc_url}")
    click.echo(f"ACCOUNT_NAME: {account_name}")
    click.echo(f"ACCOUNT_TELLOR_ADDRESS: {account_tellor_address}")
    click.echo(f"CSV_PATH: {csv_path}")

    if not all([layer_rpc_url, account_name, account_tellor_address, csv_path]):
        click.echo(click.style("Error: Required environment variables missing. Please check LAYER_RPC_URL, ACCOUNT_NAME, ACCOUNT_TELLOR_ADDRESS, and BRIDGE_DEPOSITS_CSV", fg='red'))
        return

    # Prompt for deposit ID
    deposit_id = click.prompt('Enter the deposit ID', type=str)
    click.echo(f"\nDebug - Deposit ID entered: {deposit_id}")

    # Read the CSV file to get timestamp only
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            deposit_found = False
            for row in reader:
                if row['Deposit ID'] == deposit_id:
                    timestamp = row['Timestamp']
                    deposit_found = True
                    click.echo("\nDebug - Found deposit in CSV:")
                    click.echo(f"Timestamp: {timestamp}")
                    break

        if not deposit_found:
            click.echo(click.style(f"Error: Deposit ID {deposit_id} not found in {csv_path}", fg='red'))
            return

        if not timestamp:
            click.echo(click.style(f"Error: No Timestamp found for deposit ID {deposit_id}", fg='red'))
            return

    except FileNotFoundError:
        click.echo(click.style(f"Error: Could not find CSV file at {csv_path}", fg='red'))
        return
    except Exception as e:
        click.echo(click.style(f"Error reading CSV file: {e}", fg='red'))
        return

    # Confirm the transaction details
    click.echo('\nTransaction Details:')
    click.echo(f'Creator: {account_tellor_address}')
    click.echo(f'Deposit ID: {deposit_id}')
    click.echo(f'Timestamp: {timestamp}')
    click.echo(f'Account: {account_name}')
    
    if not click.confirm('\nDo you want to proceed with this transaction?'):
        click.echo('Transaction cancelled.')
        return
    
    max_retries = 7
    attempt = 1
    
    while attempt <= max_retries:
        try:
            # Construct the command piece by piece
            base_cmd = ['./layerd', 'tx', 'bridge', 'claim-deposits']
            args = [account_tellor_address, deposit_id, timestamp]  # Using account_tellor_address as creator
            flags = [
                '--from', account_name,
                '--gas', 'auto',
                '--chain-id', 'layertest-4',
                '--fees', '10loya',
                '--yes',
                '--node', layer_rpc_url
            ]
            
            cmd = base_cmd + args + flags

            # Debug prints for command construction
            click.echo("\nDebug - Command Construction:")
            click.echo(f"Base command: {base_cmd}")
            click.echo(f"Arguments: {args}")
            click.echo(f"Flags: {flags}")
            click.echo(f"Final command: {cmd}")
            click.echo("\nDebug - Command as it will be executed:")
            click.echo(' '.join(cmd))
            
            # Execute the command
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Debug print for command output
            click.echo("\nDebug - Command Output:")
            click.echo(result.stdout)
            if result.stderr:
                click.echo("Debug - Command Error Output:")
                click.echo(result.stderr)
            
            # Parse the output to find raw_log
            output_lines = result.stdout.split('\n')
            raw_log = None
            txhash = None
            
            for line in output_lines:
                if line.startswith('raw_log:'):
                    raw_log = line.split('raw_log: ')[1].strip('"')
                elif line.startswith('txhash:'):
                    txhash = line.split('txhash: ')[1].strip()
            
            # Check if transaction succeeded
            if raw_log == "":
                click.echo(click.style(f"\nTransaction succeeded! Transaction hash: {txhash}", fg='green'))
                return
            else:
                click.echo(click.style(f"\nTransaction failed (attempt {attempt}/{max_retries})", fg='yellow'))
                click.echo(f"Raw log: {raw_log}")
                if attempt < max_retries and click.confirm('\nDo you want to retry?'):
                    attempt += 1
                else:
                    click.echo('Transaction cancelled.')
                    return
                
        except subprocess.CalledProcessError as e:
            click.echo(click.style(f"\nError executing command (attempt {attempt}/{max_retries}): {e}", fg='red'))
            click.echo("Debug - Error details:")
            click.echo(f"Return code: {e.returncode}")
            click.echo(f"Standard output: {e.stdout}")
            click.echo(f"Error output: {e.stderr}")
            if attempt < max_retries and click.confirm('\nDo you want to retry?'):
                attempt += 1
            else:
                click.echo('Transaction cancelled.')
                return
        except Exception as e:
            click.echo(click.style(f"\nUnexpected error (attempt {attempt}/{max_retries}): {e}", fg='red'))
            import traceback
            click.echo("Debug - Full traceback:")
            click.echo(traceback.format_exc())
            if attempt < max_retries and click.confirm('\nDo you want to retry?'):
                attempt += 1
            else:
                click.echo('Transaction cancelled.')
                return
    
    click.echo(click.style('\nMaximum retry attempts reached. Transaction failed.', fg='red'))
