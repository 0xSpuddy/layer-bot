import click
import time
import subprocess
import requests
from dotenv import load_dotenv
import os

def get_query_data(query_data_input):
    """Return the query data from user input."""
    return query_data_input

@click.command('auto-tipper')
@click.argument('query_data', type=str)
@click.argument('interval', type=int)
def auto_tipper(query_data, interval):
    """Auto tipper for Layer Queries which are not part of the cycle list.
    
    QUERY_DATA: The hex-encoded query data for the oracle tip
    INTERVAL: Interval in seconds between tip transactions
    """
    # Load environment variables
    load_dotenv()
    account_name = os.getenv('ACCOUNT_NAME')
    layer_rpc_url = os.getenv('LAYER_RPC_URL', '').strip()

    if not account_name or not layer_rpc_url:
        click.echo(click.style("Error: Required environment variables missing. Please check ACCOUNT_NAME and LAYER_RPC_URL", fg='red'))
        return

    # Display the account name to be used
    click.echo(f"\nUsing account: {account_name}")
    click.echo(f"Query data: {query_data[:50]}..." if len(query_data) > 50 else f"Query data: {query_data}")
    click.echo(f"Interval: {interval} seconds")
    
    # Get the query data from user input
    query_data_to_use = get_query_data(query_data)

    click.echo(click.style("\nStarting auto-tipper...", fg='blue'))
    click.echo("Press Ctrl+C to stop\n")
    
    tip_count = 0
    
    try:
        while True:
            tip_count += 1
            click.echo(click.style(f"[Tip #{tip_count}] Starting tip transaction...", fg='cyan'))
            
            # Construct the commands
            tip_cmd = [
                './layerd',
                'tx',
                'oracle',
                'tip',
                query_data_to_use,
                '10000loya',
                '--from', account_name,
                '--gas', '600000',
                '--fees', '15loya',
                '--chain-id', 'layertest-4',
                '--sign-mode', 'textual',
                '--yes',
                '--node', layer_rpc_url
            ]

            try:
                # Execute the command
                tip_result = subprocess.run(tip_cmd, capture_output=True, text=True, check=True)
                print(f"tip_result: {tip_result.stdout}")
                
                # Parse the output to find txhash and raw_log
                tip_output_lines = tip_result.stdout.split('\n')
                tip_raw_log = None
                tip_txhash = None
                
                for line in tip_output_lines:
                    if line.startswith('raw_log:'):
                        tip_raw_log = line.split('raw_log: ')[1].strip('"')
                    elif line.startswith('txhash:'):
                        tip_txhash = line.split('txhash: ')[1].strip()

                # Check if tip transaction succeeded
                if tip_raw_log == "":
                    click.echo(click.style(f"[Tip #{tip_count}] Transaction succeeded! Hash: {tip_txhash}", fg='green'))
                else:
                    click.echo(click.style(f"[Tip #{tip_count}] Transaction failed!", fg='red'))
                    click.echo(f"Raw log: {tip_raw_log}")

            except subprocess.CalledProcessError as e:
                click.echo(click.style(f"[Tip #{tip_count}] Error executing command:", fg='red'))
                click.echo(f"Return code: {e.returncode}")
                click.echo(f"Error output: {e.stderr}")
            
            # Wait for the specified interval before the next tip
            if interval > 0:
                click.echo(f"Waiting {interval} seconds before next tip...")
                time.sleep(interval)
            else:
                click.echo(click.style("Interval is 0, stopping after single tip.", fg='yellow'))
                break
                
    except KeyboardInterrupt:
        click.echo(click.style(f"\n\nAuto-tipper stopped by user. Total tips sent: {tip_count}", fg='yellow'))
    except Exception as e:
        click.echo(click.style(f"\nUnexpected error: {e}", fg='red'))
