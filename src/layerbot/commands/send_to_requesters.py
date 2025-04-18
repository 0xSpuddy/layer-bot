import click
import pandas as pd
import os
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from decimal import Decimal
from layerbot.commands.add_public_addrs import refresh_balances

def get_zero_balance_addresses(df):
    """Get addresses with 0 SepTRB balance from DataFrame."""
    try:
        # Convert SepTRB balance to float and handle any conversion errors
        df['SepTRB balance'] = pd.to_numeric(df['SepTRB balance'], errors='coerce')
        # Find addresses where balance is 0 or NaN
        zero_balance = df[df['SepTRB balance'].fillna(0) == 0]
        
        # Debug output
        click.echo(f"Found {len(zero_balance)} addresses with zero balance")
        for _, row in zero_balance.iterrows():
            click.echo(f"Debug - Address: {row['Address']}, Balance: {row['SepTRB balance']}")
            
        return zero_balance[['Address', 'Discord', 'X']].to_dict('records')
    except Exception as e:
        click.echo(f"Error processing addresses: {e}")
        return []

def send_septrb(w3, contract, sender_address, private_key, recipient, amount):
    """Send SepTRB tokens to recipient."""
    try:
        # Convert amount to wei (18 decimals)
        amount_wei = w3.to_wei(amount, 'ether')
        
        # Build transaction
        nonce = w3.eth.get_transaction_count(sender_address)
        
        # Estimate gas for transfer
        gas_estimate = contract.functions.transfer(
            recipient,
            amount_wei
        ).estimate_gas({'from': sender_address})
        
        # Add 20% buffer to gas estimate
        gas_limit = int(gas_estimate * 1.2)
        
        # Get gas price
        gas_price = w3.eth.gas_price
        
        # Build the transaction
        transaction = contract.functions.transfer(
            recipient,
            amount_wei
        ).build_transaction({
            'chainId': w3.eth.chain_id,
            'gas': gas_limit,  # Using buffered gas limit instead of estimate
            'gasPrice': gas_price,
            'nonce': nonce,
        })
        
        # Sign transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
        
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        # Wait for transaction receipt
        click.echo(f"Waiting for transaction to complete...")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if tx_receipt['status'] == 1:
            click.echo(f"Successfully sent {amount} SepTRB to {recipient}")
            click.echo(f"Transaction hash: {tx_receipt['transactionHash'].hex()}")
            return True
        else:
            click.echo(f"Transaction failed: {tx_receipt}")
            return False
            
    except Exception as e:
        click.echo(f"Error sending tokens: {e}")
        return False

def get_balances(w3, contract, address):
    """Get ETH and TRB balances for an address."""
    try:
        # Get ETH balance
        eth_balance = w3.from_wei(w3.eth.get_balance(address), 'ether')
        
        # Get TRB balance
        trb_balance = w3.from_wei(contract.functions.balanceOf(address).call(), 'ether')
        
        return eth_balance, trb_balance
    except Exception as e:
        click.echo(f"Error getting balances for {address}: {e}")
        return None, None

@click.command()
@click.argument('addresses', type=str)
def send_to_requesters(addresses):
    """Send SepTRB to the provided comma-separated list of addresses."""
    # Load environment variables
    load_dotenv()
    
    # Get required environment variables
    eth_address = os.getenv('ETH_ADDRESS')
    private_key = os.getenv('ETH_PRIVATE_KEY')
    eth_rpc_url = os.getenv('ETHEREUM_RPC_URL')
    
    if not all([eth_address, private_key, eth_rpc_url]):
        click.echo("Error: Missing required environment variables (ETH_ADDRESS, ETH_PRIVATE_KEY, ETHEREUM_RPC_URL)")
        return

    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(eth_rpc_url))
    if not w3.is_connected():
        click.echo("Error: Could not connect to Ethereum RPC")
        return
    
    # SepTRB token contract setup
    token_address = "0x80fc34a2f9FfE86F41580F47368289C402DEc660"
    abi = [
        {
            "constant": False,
            "inputs": [
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"}
            ],
            "name": "transfer",
            "outputs": [{"name": "", "type": "bool"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        }
    ]
    
    contract = w3.eth.contract(address=token_address, abi=abi)
    
    # Split the addresses and clean them up
    address_list = [addr.strip() for addr in addresses.split(',')]
    
    if not address_list:
        click.echo("No addresses provided")
        return
    
    # Validate all addresses first
    valid_addresses = []
    for address in address_list:
        if not Web3.is_address(address):
            click.echo(f"Invalid address format: {address}")
        else:
            valid_addresses.append(address)
    
    if not valid_addresses:
        click.echo("No valid addresses provided")
        return
    
    # Show balances for all valid addresses
    click.echo("\nCurrent balances for each address:")
    for address in valid_addresses:
        eth_balance, trb_balance = get_balances(w3, contract, address)
        if eth_balance is not None and trb_balance is not None:
            click.echo(f"\nAddress: {address}")
            click.echo(f"ETH Balance: {eth_balance:.6f}")
            click.echo(f"TRB Balance: {trb_balance:.6f}")
    
    # Ask for confirmation to send to all addresses
    click.echo(f"\nWill send 99 TRB to {len(valid_addresses)} addresses.")
    if click.prompt("Proceed with sending TRB? (Press Enter for yes, 'n' for no)", default='y').lower() != 'n':
        # Process each address
        for address in valid_addresses:
            click.echo(f"\nSending to {address}...")
            if send_septrb(w3, contract, eth_address, private_key, address, 99):
                click.echo("Successfully sent tokens")
            else:
                if not click.confirm("Transaction failed. Continue with next address?"):
                    break
            click.echo("Waiting 2 seconds before next transaction...")
            import time
            time.sleep(2)
    else:
        click.echo("Operation cancelled")

if __name__ == '__main__':
    send_to_requesters()
