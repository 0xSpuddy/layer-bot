import warnings
# Filter warnings before other imports
warnings.filterwarnings('ignore', 
                       message='Network .* does not have a valid ChainId.*',
                       category=UserWarning)

import click
import time
import subprocess
import os
import sys
from layerbot.commands.test import test
from layerbot.commands.bridge_request import bridge_request
from layerbot.commands.claim_deposits import claim_deposits
from layerbot.commands.tip_deposits import tip_deposits
from layerbot.commands.add_public_addrs import add_requester
from layerbot.commands.send_to_requesters import send_to_requesters
from .commands.bridge_scan import bridge_scan, deposits, withdrawals
from layerbot.commands.propose_dispute import propose_dispute
from layerbot.commands import track_block_time

@click.group()
def cli():
    """LayerBot - A tool for monitoring Layer bridge deposits"""
    # Set RPC URL if not already set
    if not os.getenv("LAYER_RPC_URL"):
        os.environ["LAYER_RPC_URL"] = "https://rpc.layer.exchange"
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

@click.command('track-block-time')
@click.option('--daemon', '-d', is_flag=True, help='Run as a daemon process')
@click.option('--test', '-t', is_flag=True, help='Test if block time tracking works without starting the tracker')
def track_block_time_cmd(daemon, test):
    """Track Layer network block time and save to CSV file"""
    if test:
        click.echo("Testing block time tracking functionality...")
        success = track_block_time.track(test=True)
        if success:
            click.echo("Block time tracking test successful!")
            return
        else:
            click.echo("Block time tracking test failed. Please check the errors above.")
            sys.exit(1)
    elif daemon:
        track_block_time.track(daemon=True)
    else:
        track_block_time.track(daemon=False)

cli.add_command(test)
cli.add_command(bridge_request)
cli.add_command(claim_deposits)
cli.add_command(tip_deposits)
cli.add_command(add_requester)
cli.add_command(send_to_requesters)
cli.add_command(bridge_scan)
cli.add_command(propose_dispute)
cli.add_command(bridge_monitor)
cli.add_command(track_block_time_cmd)

def create_cli():
    return cli()

if __name__ == '__main__':
    create_cli()
