import warnings
# Filter warnings before other imports
warnings.filterwarnings('ignore', 
                       message='Network .* does not have a valid ChainId.*',
                       category=UserWarning)

import click
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from layerbot.bridge_info import setup_csv, get_existing_deposit_ids, save_deposit_to_csv, load_abi
from layerbot.utils.query_layer import get_claimed_deposit_ids, generate_queryId, get_report_timestamp
from web3 import Web3
from layerbot.commands.test import test
from layerbot.commands.bridge_request import bridge_request
from layerbot.commands.claim_deposits import claim_deposits
from layerbot.commands.tip_deposits import tip_deposits
from layerbot.commands.add_public_addrs import add_requester
from layerbot.commands.send_to_requesters import send_to_requesters
from .commands.bridge_scan import bridge_scan
from layerbot.commands.propose_dispute import propose_dispute



@click.group()
def cli():
    """LayerBot - A tool for monitoring Layer bridge deposits"""
    pass

@cli.command()
def bridge_monitor():
    """Monitor bridge deposits and track their status"""
    load_dotenv()
    
    # Get configuration from environment variables
    interval = int(os.getenv('BRIDGE_SCAN_INTERVAL', '120'))
    csv_path = os.getenv('BRIDGE_DEPOSITS_CSV', 'bridge_deposits.csv')
    contract_address = os.getenv('BRIDGE_CONTRACT_ADDRESS')
    rpc_url = os.getenv('ETHEREUM_RPC_URL')
    
    if not all([contract_address, rpc_url]):
        click.echo("Error: Missing required environment variables. Please check BRIDGE_CONTRACT_ADDRESS and ETHEREUM_RPC_URL")
        return
    
    click.echo(f"Starting bridge scan (interval: {interval}s)")
    click.echo(f"Writing to: {csv_path}")
    
    # Initialize Web3 and contract
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        click.echo("Error: Could not connect to Ethereum RPC")
        return
        
    try:
        abi = load_abi()
        contract = w3.eth.contract(address=contract_address, abi=abi)
    except Exception as e:
        click.echo(f"Error setting up contract: {e}")
        return
    
    # Ensure CSV file is set up
    if not setup_csv():
        click.echo("Failed to setup CSV file")
        return
    
    while True:
        try:
            # Get existing deposit IDs
            existing_ids = get_existing_deposit_ids()
            
            # Get claimed deposit IDs
            claimed_ids = get_claimed_deposit_ids()
            
            # Get current deposit ID from contract
            latest_deposit_id = contract.functions.depositId().call()
            
            # Scan for new deposits
            new_deposits = 0
            for current_id in range(1, latest_deposit_id + 1):
                if current_id not in existing_ids:
                    try:
                        # Get deposit info from contract
                        deposit_info = contract.functions.deposits(current_id).call()
                        
                        # Skip empty deposits
                        if deposit_info[0] == '0x0000000000000000000000000000000000000000':
                            continue
                        
                        # Check if deposit is claimed
                        is_claimed = str(current_id) in claimed_ids
                        
                        # Save to CSV
                        save_deposit_to_csv(current_id, deposit_info, is_claimed)
                        new_deposits += 1
                        
                        click.echo(f"New deposit found - ID: {current_id}, "
                                 f"Sender: {deposit_info[0]}, "
                                 f"Amount: {deposit_info[2]}, "
                                 f"Claimed: {'Yes' if is_claimed else 'No'}")
                        
                    except Exception as e:
                        click.echo(f"Error processing deposit {current_id}: {e}")
            
            click.echo(f"[{datetime.now()}] Scan complete. Found {new_deposits} new deposits.")
            time.sleep(interval)
            
        except KeyboardInterrupt:
            click.echo("\nStopping bridge scan...")
            break
        except Exception as e:
            click.echo(f"Error during scan: {e}")
            click.echo("Retrying in 10 seconds...")
            time.sleep(10)

cli.add_command(test)
cli.add_command(bridge_request)
cli.add_command(claim_deposits)
cli.add_command(tip_deposits)
cli.add_command(add_requester)
cli.add_command(send_to_requesters)
cli.add_command(bridge_scan)
cli.add_command(propose_dispute)

def create_cli():
    return cli()

if __name__ == '__main__':
    create_cli()
