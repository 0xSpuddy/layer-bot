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
bridge_contract_address = os.getenv('BRIDGE_CONTRACT_ADDRESS')

# Clean the URL
layer_rpc_url = ''.join(c for c in layer_rpc_url if ord(c) >= 32)  # Remove control characters
layer_rpc_url = layer_rpc_url.strip()  # Remove leading/trailing whitespace


@click.command('bridge-request')
def bridge_request():
    """Request a bridge transfer to Layer chain."""
    # Get ETH address from env
    eth_address = os.getenv('ETH_ADDRESS')
    
    if not all([ethereum_rpc_url, bridge_contract_address, eth_address]):
        click.echo(click.style("Error: Required environment variables missing. Please check ETHEREUM_RPC_URL, BRIDGE_CONTRACT_ADDRESS, and ETH_ADDRESS", fg='red'))
        return

    try:
        # Initialize Web3
        w3 = Web3(Web3.HTTPProvider(ethereum_rpc_url))
        if not w3.is_connected():
            click.echo(click.style("Error: Could not connect to Ethereum RPC", fg='red'))
            return

        # Set the default account
        w3.eth.default_account = eth_address

        # Load contract ABI
        try:
            with open('contracts/bridge_abi.json', 'r') as f:
                contract_abi = json.load(f)  # Use json.load instead of read()
        except FileNotFoundError:
            click.echo(click.style("Error: Could not find bridge_abi.json", fg='red'))
            return
        except json.JSONDecodeError as e:
            click.echo(click.style(f"Error parsing bridge_abi.json: {e}", fg='red'))
            return
        except Exception as e:
            click.echo(click.style(f"Unexpected error loading ABI: {e}", fg='red'))
            return

        # Initialize contract
        contract = w3.eth.contract(address=bridge_contract_address, abi=contract_abi)

        # Get user inputs with defaults
        default_amount = 69000000000000000000
        default_recipient = "tellor1vw2yy9nf3wz7hey89tpw5hn0yr3hkrzt889x47"
        
        amount = click.prompt('Amount of Tokens to Bridge?', 
                            type=int, 
                            default=default_amount,
                            show_default=True)
        
        tip = 10000000000000000  # Hardcoded tip value
        
        layer_recipient = click.prompt('What is the receiving address on Tellor Layer?', 
                                     type=str,
                                     default=default_recipient,
                                     show_default=True)

        # Show transaction details
        click.echo('\nTransaction Details:')
        click.echo(f'From Address: {eth_address}')
        click.echo(f'Amount: {amount}')
        click.echo(f'Tip: {tip}')
        click.echo(f'Layer Recipient: {layer_recipient}')

        if not click.confirm('\nDo you want to proceed with this transaction?'):
            click.echo('Transaction cancelled.')
            return

        # Build the transaction
        try:
            # First build without gas to estimate
            tx_params = {
                'from': eth_address,
                'gasPrice': w3.eth.gas_price,
                'nonce': w3.eth.get_transaction_count(eth_address),
            }

            # Estimate gas for the transaction
            estimated_gas = contract.functions.depositToLayer(
                amount,
                tip,
                layer_recipient
            ).estimate_gas(tx_params)

            # Add some buffer to the estimate (10%)
            gas_limit = int(estimated_gas * 1.1)
            
            click.echo(f"\nEstimated gas: {estimated_gas}")
            click.echo(f"Gas limit with buffer: {gas_limit}")

            # Build the final transaction with estimated gas
            tx = contract.functions.depositToLayer(
                amount,
                tip,
                layer_recipient
            ).build_transaction({
                'from': eth_address,
                'gas': gas_limit,
                'gasPrice': w3.eth.gas_price,
                'nonce': w3.eth.get_transaction_count(eth_address),
            })

            # Sign and send the transaction
            signed_tx = w3.eth.account.sign_transaction(tx, private_key=os.getenv('ETH_PRIVATE_KEY'))
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

            click.echo(click.style(f"\nTransaction sent! Hash: {tx_hash.hex()}", fg='green'))
            
            # Wait for transaction receipt
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            if receipt['status'] == 1:
                click.echo(click.style("Transaction successful!", fg='green'))
            else:
                click.echo(click.style("Transaction failed!", fg='red'))

        except Exception as e:
            click.echo(click.style(f"\nError building/sending transaction: {e}", fg='red'))
            return

    except Exception as e:
        click.echo(click.style(f"Unexpected error: {e}", fg='red'))
        return 