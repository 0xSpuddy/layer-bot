import click
import subprocess
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

layer_rpc_url = os.getenv('LAYER_RPC_URL', '').strip()
account_name = os.getenv('ACCOUNT_NAME')
account_tellor_address = os.getenv('ACCOUNT_TELLOR_ADDRESS')

# Clean the URL
layer_rpc_url = ''.join(c for c in layer_rpc_url if ord(c) >= 32)  # Remove control characters
layer_rpc_url = layer_rpc_url.strip()  # Remove leading/trailing whitespace


@click.command('request-withdrawal')
@click.argument('creator', type=str, required=False)
@click.argument('recipient', type=str, required=False)
@click.argument('amount', type=str, required=False)
@click.option('--fees', default='5loya', help='Transaction fees (default: 5loya)')
@click.option('--chain-id', default='layertest-4', help='Chain ID (default: layertest-4)')
def request_withdrawal(creator, recipient, amount, fees, chain_id):
    """Request a token withdrawal from Layer chain to Ethereum.
    
    Example:
        layerbot request-withdrawal tellor1vw2yy9nf3wz7hey89tpw5hn0yr3hkrzt889x47 7660794eF8f978Ea0922DC29B3b534d93e1fc94A 6900000loya
    """
    # Debug prints for environment variables
    click.echo("\nDebug - Environment Variables:")
    click.echo(f"LAYER_RPC_URL: {layer_rpc_url}")
    click.echo(f"ACCOUNT_NAME: {account_name}")
    click.echo(f"ACCOUNT_TELLOR_ADDRESS: {account_tellor_address}")

    if not all([layer_rpc_url, account_name]):
        click.echo(click.style("Error: Required environment variables missing. Please check LAYER_RPC_URL and ACCOUNT_NAME", fg='red'))
        return

    # Get parameters if not provided as arguments
    if not creator:
        default_creator = account_tellor_address or "tellor1vw2yy9nf3wz7hey89tpw5hn0yr3hkrzt889x47"
        creator = click.prompt('Creator address', 
                              type=str,
                              default=default_creator,
                              show_default=True)
    
    if not recipient:
        default_recipient = "7660794eF8f978Ea0922DC29B3b534d93e1fc94A"
        recipient = click.prompt('Recipient address (Ethereum)', 
                                type=str,
                                default=default_recipient,
                                show_default=True)
    
    if not amount:
        default_amount = "6900000loya"
        amount = click.prompt('Amount to withdraw', 
                             type=str,
                             default=default_amount,
                             show_default=True)

    # Confirm the transaction details
    click.echo('\nTransaction Details:')
    click.echo(f'Creator: {creator}')
    click.echo(f'Recipient: {recipient}')
    click.echo(f'Amount: {amount}')
    click.echo(f'Fees: {fees}')
    click.echo(f'Chain ID: {chain_id}')
    click.echo(f'Account: {account_name}')
    
    if not click.confirm('\nDo you want to proceed with this transaction?'):
        click.echo('Transaction cancelled.')
        return
    
    max_retries = 7
    attempt = 1
    
    while attempt <= max_retries:
        try:
            # Construct the command piece by piece
            base_cmd = ['./layerd', 'tx', 'bridge', 'withdraw-tokens']
            args = [creator, recipient, amount]
            flags = [
                '--from', account_name,
                '--chain-id', chain_id,
                '--fees', fees,
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
                click.echo(click.style(f"\nWithdrawal request submitted successfully! Transaction hash: {txhash}", fg='green'))
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
