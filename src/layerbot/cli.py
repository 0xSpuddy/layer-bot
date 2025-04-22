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
from layerbot.commands.estimate_block_time import estimate
from layerbot.commands.manage_block_data import cli as manage_block_data_cli
from layerbot.commands.report_test_value import report_test_value

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

@click.command(name="track-block-time")
@click.option("--daemon", is_flag=True, default=False, help="Run as a daemon, recording block time at regular intervals")
@click.option("--test", is_flag=True, default=False, help="Test block time tracking without starting the tracker")
def track_block_time_cmd(daemon, test):
    """Track block time and record averages to a CSV file"""
    if test:
        click.echo("Testing block time tracking...")
        return track_block_time.track(test=True)
    elif daemon:
        click.echo("Starting block time tracker daemon...")
        return track_block_time.track(daemon=True)
    else:
        click.echo("Starting block time tracker...")
        return track_block_time.track()

@click.command(name="estimate-block")
@click.argument("height", type=int, required=True)
@click.option("--timezone", type=str, help="Timezone for estimated time (e.g. 'America/New_York', 'Europe/London')")
def estimate_block_cmd(height, timezone):
    """
    Estimate when a future block height will be reached.
    
    Examples:
    \b
    layerbot estimate-block 1000000
    layerbot estimate-block 1000000 --timezone "America/New_York" 
    """
    success = estimate(height, timezone)
    return 0 if success else 1

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
cli.add_command(estimate_block_cmd)
cli.add_command(manage_block_data_cli, name="block-data-manage")
cli.add_command(report_test_value)

def create_cli():
    return cli()

if __name__ == '__main__':
    create_cli()
