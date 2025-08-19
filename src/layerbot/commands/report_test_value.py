import click
import time
import subprocess
import requests
from dotenv import load_dotenv
import os

# Define supported currencies with their CoinGecko IDs and query data
SUPPORTED_CURRENCIES = {
    'eth': {
        'coingecko_id': 'ethereum',
        'symbol': 'ETH',
        'query_data': "00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000000953706f745072696365000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000003657468000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000037573640000000000000000000000000000000000000000000000000000000000"
    },
    'trb': {
        'coingecko_id': 'tellor',
        'symbol': 'TRB',
        'query_data': "00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000000953706f745072696365000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000003747262000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000037573640000000000000000000000000000000000000000000000000000000000"
    },
    'btc': {
        'coingecko_id': 'bitcoin',
        'symbol': 'BTC',
        'query_data': "00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000000953706f745072696365000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000003627463000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000037573640000000000000000000000000000000000000000000000000000000000"
    },
    'cult': {
        'coingecko_id': 'cult-dao',
        'symbol': 'CULT',
        'query_data': "00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000000953706f745072696365000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c000000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000000463756c740000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000037573640000000000000000000000000000000000000000000000000000000000"
    },
    'saga': {
        'coingecko_id': 'saga-2',
        'symbol': 'SAGA',
        'query_data': "00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000000953706f745072696365000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000004736167610000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000037573640000000000000000000000000000000000000000000000000000000000"
    },
    'usdc': {
        'coingecko_id': 'usd-coin',
        'symbol': 'USDC',
        'query_data': "00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000000953706f745072696365000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000004757364630000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000037573640000000000000000000000000000000000000000000000000000000000"
    }
}

def get_multiple_prices(currency_keys):
    """Fetch current prices for multiple currencies from CoinGecko."""
    try:
        # Build the CoinGecko API call for multiple currencies
        coingecko_ids = [SUPPORTED_CURRENCIES[key]['coingecko_id'] for key in currency_keys]
        ids_param = ','.join(coingecko_ids)
        
        response = requests.get(f'https://api.coingecko.com/api/v3/simple/price?ids={ids_param}&vs_currencies=usd')
        response.raise_for_status()
        
        prices = {}
        data = response.json()
        
        for key in currency_keys:
            coingecko_id = SUPPORTED_CURRENCIES[key]['coingecko_id']
            if coingecko_id in data and 'usd' in data[coingecko_id]:
                prices[key] = float(data[coingecko_id]['usd'])
            else:
                click.echo(click.style(f"Warning: Price not found for {key.upper()}", fg='yellow'))
                prices[key] = None
                
        return prices
    except Exception as e:
        click.echo(click.style(f"Error fetching prices: {e}", fg='red'))
        return {}

def get_eth_price():
    """Fetch current ETH/USD price from CoinGecko (legacy function for backward compatibility)."""
    prices = get_multiple_prices(['eth'])
    return prices.get('eth')

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
@click.option('--currency', '-c', 
              type=click.Choice(list(SUPPORTED_CURRENCIES.keys()), case_sensitive=False),
              help='Currency to report (default: shows selection menu)')
@click.option('--all', 'report_all', is_flag=True, 
              help='Report test values for all supported currencies')
def report_test_value(currency, report_all):
    """Report test values on Layer chain for cryptocurrency prices."""
    # Load environment variables
    load_dotenv()
    account_name = os.getenv('ACCOUNT_NAME')
    layer_rpc_url = os.getenv('LAYER_RPC_URL', '').strip()

    if not account_name or not layer_rpc_url:
        click.echo(click.style("Error: Required environment variables missing. Please check ACCOUNT_NAME and LAYER_RPC_URL", fg='red'))
        return

    # Display the account name to be used
    click.echo(f"\nUsing account: {account_name}")
    
    # Determine which currencies to process
    currencies_to_process = []
    
    if report_all:
        currencies_to_process = list(SUPPORTED_CURRENCIES.keys())
        click.echo("\nReporting test values for ALL supported currencies")
    elif currency:
        currencies_to_process = [currency.lower()]
        click.echo(f"\nReporting test value for {currency.upper()}")
    else:
        # Interactive selection
        click.echo("\nSupported currencies:")
        currency_list = list(SUPPORTED_CURRENCIES.keys())
        for i, curr in enumerate(currency_list, 1):
            symbol = SUPPORTED_CURRENCIES[curr]['symbol']
            click.echo(f"  {i}. {symbol} ({curr})")
        
        choice = click.prompt(
            f"\nSelect currency (1-{len(currency_list)}) or 'all' for all currencies",
            type=str
        )
        
        if choice.lower() == 'all':
            currencies_to_process = currency_list
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(currency_list):
                    currencies_to_process = [currency_list[idx]]
                else:
                    click.echo(click.style("Invalid selection", fg='red'))
                    return
            except ValueError:
                click.echo(click.style("Invalid selection", fg='red'))
                return
    
    # Fetch prices for selected currencies
    click.echo(f"\nFetching prices for: {', '.join([c.upper() for c in currencies_to_process])}")
    prices = get_multiple_prices(currencies_to_process)
    
    # Filter out currencies with no price data
    valid_currencies = {k: v for k, v in prices.items() if v is not None}
    
    if not valid_currencies:
        click.echo(click.style("No valid price data found. Exiting.", fg='red'))
        return
    
    # Display current prices
    click.echo("\nCurrent prices from CoinGecko:")
    for curr, price in valid_currencies.items():
        symbol = SUPPORTED_CURRENCIES[curr]['symbol']
        click.echo(f"  {symbol}/USD: ${price:,.2f}")
    
    # Ask if user wants to report incorrect values
    report_incorrect = click.confirm('\nDo you want to report incorrect values?', default=False)
    
    percentage_diff = 0.0
    if report_incorrect:
        percentage_diff = click.prompt(
            'Enter the percentage difference to apply (positive for increase, negative for decrease)',
            type=float,
            default=69.0
        )
        
        click.echo(f"\nApplying {percentage_diff:+.1f}% difference to all prices:")
        for curr in valid_currencies:
            original_price = valid_currencies[curr]
            modified_price = apply_price_difference(original_price, percentage_diff)
            symbol = SUPPORTED_CURRENCIES[curr]['symbol']
            click.echo(f"  {symbol}: ${original_price:,.2f} → ${modified_price:,.2f}")
            valid_currencies[curr] = modified_price
    
    # Show transaction details for confirmation
    click.echo('\nTransaction Details:')
    click.echo(f'Account: {account_name}')
    
    for curr, price in valid_currencies.items():
        symbol = SUPPORTED_CURRENCIES[curr]['symbol']
        query_data = SUPPORTED_CURRENCIES[curr]['query_data']
        value_data = encode_price_to_hex(price)
        
        click.echo(f'\n--- {symbol}/USD ---')
        click.echo(f'Price to report: ${price:,.2f}')
        click.echo(f'Query Data: {query_data[:50]}...')
        click.echo(f'Value Data: {value_data[:50]}...')
    
    if not click.confirm('\nDo you want to proceed with these reports?'):
        click.echo('Reports cancelled.')
        return

    try:
        # Process each currency
        successful_reports = []
        failed_reports = []
        
        for curr, price in valid_currencies.items():
            symbol = SUPPORTED_CURRENCIES[curr]['symbol']
            query_data = SUPPORTED_CURRENCIES[curr]['query_data']
            value_data = encode_price_to_hex(price)
            
            click.echo(f"\n--- Processing {symbol}/USD (${price:,.2f}) ---")
            
            # Construct the commands
            tip_cmd = [
                './layerd',
                'tx',
                'oracle',
                'tip',
                query_data,
                '10000loya',
                '--from', account_name,
                '--gas', '600000',
                '--fees', '15loya',
                '--chain-id', 'layertest-4',
                '--sign-mode', 'textual',
                '--yes',
                '--node', layer_rpc_url
            ]
            
            report_cmd = [
                './layerd',
                'tx',
                'oracle',
                'submit-value',
                query_data,
                value_data,
                '--from', account_name,
                '--gas', '500000',
                '--fees', '15loya',
                '--chain-id', 'layertest-4',
                '--yes',
                '--node', layer_rpc_url
            ]

            # Execute tip command
            try:
                tip_result = subprocess.run(tip_cmd, capture_output=True, text=True, check=True)
                
                # Parse tip result
                tip_raw_log = ""
                tip_txhash = None
                for line in tip_result.stdout.split('\n'):
                    if line.startswith('raw_log:'):
                        tip_raw_log = line.split('raw_log: ')[1].strip('"')
                    elif line.startswith('txhash:'):
                        tip_txhash = line.split('txhash: ')[1].strip()
                
                # Check if tip transaction succeeded
                if tip_raw_log == "":
                    click.echo(click.style(f"Tip transaction succeeded! Hash: {tip_txhash}", fg='green'))
                else:
                    click.echo(click.style(f"Tip transaction failed for {symbol}!", fg='red'))
                    click.echo(f"Raw log: {tip_raw_log}")
                    failed_reports.append(f"{symbol} (tip failed)")
                    continue
                    
            except subprocess.CalledProcessError as e:
                click.echo(click.style(f"Tip transaction failed with error for {symbol}!", fg='red'))
                click.echo(f"Return code: {e.returncode}")
                click.echo(f"Error output: {e.stderr}")
                failed_reports.append(f"{symbol} (tip failed)")
                continue
            
            # Wait before submitting value
            click.echo("Waiting 3 seconds before submitting value...")
            time.sleep(3)
            
            # Retry report command until it succeeds (max 60 attempts = 1 minute)
            max_retries = 60
            retry_count = 0
            report_success = False
            report_txhash = None
            
            while retry_count < max_retries and not report_success:
                retry_count += 1
                click.echo(f"Submitting value for {symbol} (attempt {retry_count}/{max_retries})...")
                
                try:
                    report_result = subprocess.run(report_cmd, capture_output=True, text=True, check=True)
                    
                    # Parse report result
                    report_raw_log = ""
                    for line in report_result.stdout.split('\n'):
                        if line.startswith('raw_log:'):
                            report_raw_log = line.split('raw_log: ')[1].strip('"')
                            report_success = (report_raw_log == "")
                        elif line.startswith('txhash:'):
                            report_txhash = line.split('txhash: ')[1].strip()
                    
                    if report_success:
                        click.echo(click.style(f"Report successful for {symbol}! Hash: {report_txhash}", fg='green'))
                        successful_reports.append(f"{symbol} (${price:,.2f})")
                        break
                    else:
                        click.echo(click.style(f"Report attempt {retry_count} failed for {symbol} - retrying in 1 second...", fg='yellow'))
                        if retry_count < max_retries:
                            time.sleep(1)
                        
                except subprocess.CalledProcessError as e:
                    click.echo(click.style(f"Report attempt {retry_count} failed with error for {symbol} - retrying in 1 second...", fg='yellow'))
                    if retry_count < max_retries:
                        time.sleep(1)
            
            # Check if we exhausted all retries
            if not report_success:
                click.echo(click.style(f"Report failed for {symbol} after {max_retries} attempts!", fg='red'))
                failed_reports.append(f"{symbol} (report failed after {max_retries} attempts)")
            
            # Wait between currencies if processing multiple
            if len(valid_currencies) > 1:
                click.echo("Waiting 2 seconds before processing next currency...")
                time.sleep(2)

        # Display final summary
        click.echo("\n" + "="*50)
        click.echo("REPORT SUMMARY")
        click.echo("="*50)
        
        if successful_reports:
            click.echo(click.style(f"\n✅ Successful reports ({len(successful_reports)}):", fg='green'))
            for report in successful_reports:
                click.echo(f"  • {report}")
        
        if failed_reports:
            click.echo(click.style(f"\n❌ Failed reports ({len(failed_reports)}):", fg='red'))
            for report in failed_reports:
                click.echo(f"  • {report}")
        
        if not successful_reports and not failed_reports:
            click.echo(click.style("\n⚠️  No reports were processed", fg='yellow'))

    except subprocess.CalledProcessError as e:
        click.echo(click.style("\nError executing command:", fg='red'))
        click.echo(f"Return code: {e.returncode}")
        click.echo(f"Error output: {e.stderr}")
    except Exception as e:
        click.echo(click.style(f"\nUnexpected error: {e}", fg='red'))
