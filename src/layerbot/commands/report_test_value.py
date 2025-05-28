import click
import time
import subprocess
import requests
from dotenv import load_dotenv
import os

def get_eth_price():
    """Fetch current ETH/USD price from CoinGecko."""
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd')
        response.raise_for_status()
        return float(response.json()['ethereum']['usd'])
    except Exception as e:
        click.echo(click.style(f"Error fetching ETH price: {e}", fg='red'))
        return None

def encode_price_to_hex(price_float):
    """Convert price to 18 decimal hex string."""
    # Multiply by 10^18 to add 18 decimals
    price_with_decimals = int(price_float * 10**18)
    # Convert to hex and remove '0x' prefix
    hex_price = hex(price_with_decimals)[2:]
    # Pad with zeros to ensure 64 characters (32 bytes)
    return hex_price.zfill(64)

def apply_price_difference(base_price, percentage_diff):
    """Apply a percentage difference to the base price."""
    difference = base_price * (percentage_diff / 100)
    return base_price + difference

@click.command('report-test-value')
def report_test_value():
    """Report a test value on Layer chain."""
    # Load environment variables
    load_dotenv()
    account_name = os.getenv('ACCOUNT_NAME')
    layer_rpc_url = os.getenv('LAYER_RPC_URL', '').strip()

    if not account_name or not layer_rpc_url:
        click.echo(click.style("Error: Required environment variables missing. Please check ACCOUNT_NAME and LAYER_RPC_URL", fg='red'))
        return

    # Display the account name to be used
    click.echo(f"\nUsing account: {account_name}")
    
    # Get current ETH price from CoinGecko
    eth_price = get_eth_price()
    if eth_price is None:
        return

    click.echo(f"\nCurrent ETH/USD price from CoinGecko: ${eth_price:,.2f}")
    
    # Ask if user wants to report an incorrect value
    report_incorrect = click.confirm('\nDo you want to report an incorrect value?', default=False)
    
    if report_incorrect:
        percentage_diff = click.prompt(
            'Enter the percentage difference to apply (positive for increase, negative for decrease)',
            type=float,
            default=15.0
        )
        modified_price = apply_price_difference(eth_price, percentage_diff)
        click.echo(f"\nOriginal price: ${eth_price:,.2f}")
        click.echo(f"Modified price: ${modified_price:,.2f} ({percentage_diff:+.1f}%)")
        eth_price = modified_price
    
    # Encode the price
    eth_usd_query_data = "00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000000953706f745072696365000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000003657468000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000037573640000000000000000000000000000000000000000000000000000000000"
    eth_usd_value_data = encode_price_to_hex(eth_price)

    # Show transaction details for confirmation
    click.echo('\nTransaction Details:')
    click.echo(f'Account: {account_name}')
    click.echo(f'Query Data: {eth_usd_query_data}')
    click.echo(f'Value Data: {eth_usd_value_data}')
    click.echo(f'Price to report: ${eth_price:,.2f}')
    
    if not click.confirm('\nDo you want to proceed with this report?'):
        click.echo('Report cancelled.')
        return

    try:
        # Construct the commands
        tip_cmd = [
            './layerd',
            'tx',
            'oracle',
            'tip',
            eth_usd_query_data,
            '10000loya',
            '--from', account_name,
            '--gas', '600000',
            '--fees', '15loya',
            '--chain-id', 'layertest-4',
            '--sign-mode', 'textual',
            '--yes',
            '--node', layer_rpc_url
        ]
        # Report command
        report_cmd = [
            './layerd',
            'tx',
            'oracle',
            'submit-value',
            eth_usd_query_data,
            eth_usd_value_data,
            '--from', account_name,
            '--gas', '500000',
            '--fees', '15loya',
            '--chain-id', 'layertest-4',
            '--yes',
            '--node', layer_rpc_url
        ]

        # Execute the command
        tip_result = subprocess.run(tip_cmd, capture_output=True, text=True, check=True)
        print(f"tip_result: {tip_result.stdout}")
        time.sleep(4)
        report_result = subprocess.run(report_cmd, capture_output=True, text=True, check=True)
        print(f"report_result: {report_result.stdout}")
        
        # Parse the output to find txhash and raw_log
        tip_output_lines = tip_result.stdout.split('\n')
        tip_raw_log = None
        tip_txhash = None

        report_output_lines = report_result.stdout.split('\n')
        report_raw_log = None
        report_txhash = None
        
        for line in tip_output_lines:
            if line.startswith('raw_log:'):
                tip_raw_log = line.split('raw_log: ')[1].strip('"')
            elif line.startswith('txhash:'):
                tip_txhash = line.split('txhash: ')[1].strip()

        # Check if tip transaction succeeded
        if tip_raw_log == "":
            click.echo(click.style(f"\nTip transaction succeeded! Transaction hash: {tip_txhash}", fg='green'))
        else:
            click.echo(click.style("\nTip transaction failed!", fg='red'))
            click.echo(f"Raw log: {tip_raw_log}")

        # Check if report transaction succeeded
        for line in report_output_lines:
            if line.startswith('raw_log:'):
                report_raw_log = line.split('raw_log: ')[1].strip('"')
            elif line.startswith('txhash:'):
                report_txhash = line.split('txhash: ')[1].strip()

        if report_raw_log == "":
            click.echo(click.style(f"\nReport transaction succeeded! Transaction hash: {report_txhash}", fg='green'))
        else:
            click.echo(click.style("\nReport transaction failed!", fg='red'))
            click.echo(f"Raw log: {report_raw_log}")

    except subprocess.CalledProcessError as e:
        click.echo(click.style("\nError executing command:", fg='red'))
        click.echo(f"Return code: {e.returncode}")
        click.echo(f"Error output: {e.stderr}")
    except Exception as e:
        click.echo(click.style(f"\nUnexpected error: {e}", fg='red'))
