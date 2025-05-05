import click
import subprocess
from dotenv import load_dotenv
import os

@click.command('propose-dispute')
def propose_dispute():
    """Propose a dispute against a reporter on Layer chain."""
    # Load environment variables
    load_dotenv()
    account_name = os.getenv('ACCOUNT_NAME')
    layer_rpc_url = os.getenv('LAYER_RPC_URL', '').strip()

    if not account_name or not layer_rpc_url:
        click.echo(click.style("Error: Required environment variables missing. Please check ACCOUNT_NAME and LAYER_RPC_URL", fg='red'))
        return

    # Get user inputs
    click.echo("\nPropose Dispute - Input Required Values:")
    disputed_reporter = click.prompt('Enter the disputed reporter address', type=str)
    report_meta_id = click.prompt('Enter the report meta ID', type=str)
    report_query_id = click.prompt('Enter the report query ID', type=str)

    # Show transaction details for confirmation
    click.echo('\nTransaction Details:')
    click.echo(f'Disputed Reporter: {disputed_reporter}')
    click.echo(f'Report Meta ID: {report_meta_id}')
    click.echo(f'Report Query ID: {report_query_id}')
    click.echo(f'Warning Message: warning')
    click.echo(f'Dispute Fee: 666999666999loya')
    click.echo(f'Account: {account_name}')
    
    if not click.confirm('\nDo you want to proceed with this dispute?'):
        click.echo('Dispute cancelled.')
        return

    try:
        # Construct the command
        cmd = [
            './layerd',
            'tx',
            'dispute',
            'propose-dispute',
            disputed_reporter,
            report_meta_id,
            report_query_id,
            'warning',
            '666999666999loya',
            'false',
            '--from', account_name,
            '--gas', '600000',
            '--fees', '15loya',
            '--chain-id', 'layertest-4',
            '--yes',
            '--node', layer_rpc_url
        ]

        # Execute the command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the output to find txhash and raw_log
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
            click.echo(click.style(f"\nDispute proposed successfully! Transaction hash: {txhash}", fg='green'))
        else:
            click.echo(click.style("\nTransaction failed!", fg='red'))
            click.echo(f"Raw log: {raw_log}")

    except subprocess.CalledProcessError as e:
        click.echo(click.style("\nError executing command:", fg='red'))
        click.echo(f"Return code: {e.returncode}")
        click.echo(f"Error output: {e.stderr}")
    except Exception as e:
        click.echo(click.style(f"\nUnexpected error: {e}", fg='red'))
