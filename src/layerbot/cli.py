import warnings
# Filter warnings before other imports
warnings.filterwarnings('ignore', 
                       message='Network .* does not have a valid ChainId.*',
                       category=UserWarning)

import click
import time
import subprocess
from layerbot.commands.test import test
from layerbot.commands.bridge_request import bridge_request
from layerbot.commands.claim_deposits import claim_deposits
from layerbot.commands.tip_deposits import tip_deposits
from layerbot.commands.add_public_addrs import add_requester
from layerbot.commands.send_to_requesters import send_to_requesters
from .commands.bridge_scan import bridge_scan, deposits, withdrawals
from layerbot.commands.propose_dispute import propose_dispute



@click.group()
def cli():
    """LayerBot - A tool for monitoring Layer bridge deposits"""
    pass

@click.command('bridge-monitor')
def bridge_monitor():
    """Monitor bridge deposits by running bridge-scan deposits every 120 seconds."""
    click.echo("Starting bridge monitor...")
    click.echo("Press Ctrl+C to stop")
    
    try:
        while True:
            click.echo("\nRunning bridge-scan deposits...")
            subprocess.run(['layerbot', 'bridge-scan', 'deposits'], check=True)
            click.echo("\nRunning bridge-scan withdrawals...")
            subprocess.run(['layerbot', 'bridge-scan', 'withdrawals'], check=True)
            click.echo("Waiting 180 seconds before next scan...")
            time.sleep(180)
    except KeyboardInterrupt:
        click.echo("\nBridge monitor stopped")
    except Exception as e:
        click.echo(f"\nError in bridge monitor: {e}")

cli.add_command(test)
cli.add_command(bridge_request)
cli.add_command(claim_deposits)
cli.add_command(tip_deposits)
cli.add_command(add_requester)
cli.add_command(send_to_requesters)
cli.add_command(bridge_scan)
cli.add_command(propose_dispute)
cli.add_command(bridge_monitor)

def create_cli():
    return cli()

if __name__ == '__main__':
    create_cli()
