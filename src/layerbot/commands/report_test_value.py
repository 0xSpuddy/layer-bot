import click
import time
import subprocess
from dotenv import load_dotenv
import os

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
    
    # Get user inputs
    click.echo("\nReport Test Value - Input Required Information:")
    # query_data = click.prompt('Enter the query data', type=str)
    # value_data = click.prompt('Enter the value data', type=str)
    query_data = "00000000000000000000000000000000000000000000000000000000000000400000000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000000953706f745072696365000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c0000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000003657468000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000037573640000000000000000000000000000000000000000000000000000000000"
    value_data = "000000000000000000000000000000000000000000000066ffcbfd5e5a300000"

    # Show transaction details for confirmation
    click.echo('\nTransaction Details:')
    click.echo(f'Account: {account_name}')
    click.echo(f'Query Data: {query_data}')
    click.echo(f'Value Data: {value_data}')
    
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
            query_data,
            '10000loya',
            '--from', account_name,
            '--gas', '500000',
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
            query_data,
            value_data,
            '--from', account_name,
            '--gas', '500000',
            '--fees', '15loya',
            '--chain-id', 'layertest-4',
            '--yes',
            '--node', layer_rpc_url
        ]

        # Execute the command
        tip_result = subprocess.run(tip_cmd, capture_output=True, text=True, check=True)
        time.sleep(2)
        report_result = subprocess.run(report_cmd, capture_output=True, text=True, check=True)
        
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
