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
from layerbot.commands.manage_block_data import cli as manage_block_data_cli
from layerbot.commands.report_test_value import report_test_value
import importlib

@click.group(invoke_without_command=True)
@click.option('--auto-tipper', nargs=2, metavar='QUERY_DATA INTERVAL', 
              help='Run auto-tipper with specified query data and interval (in seconds)')
@click.pass_context
def cli(ctx, auto_tipper):
    """LayerBot - A tool for monitoring Layer bridge deposits"""
    # Load environment variables first
    from dotenv import load_dotenv
    load_dotenv()
    
    # Set RPC URL if not already set (use localhost for development)
    if not os.getenv("LAYER_RPC_URL"):
        click.echo(click.style("Error: LAYER_RPC_URL is not set", fg='red'))
        sys.exit(1)
    
    # Handle auto-tipper flag
    if auto_tipper:
        query_data, interval = auto_tipper
        try:
            interval = int(interval)
        except ValueError:
            click.echo(click.style("Error: Interval must be a valid integer", fg='red'))
            sys.exit(1)
        
        # Import and call auto_tipper function directly
        auto_tipper_module = importlib.import_module('layerbot.commands.auto-tipper')
        auto_tipper_func = auto_tipper_module.auto_tipper
        
        # Create a context and invoke the function
        auto_ctx = click.Context(auto_tipper_func)
        auto_ctx.invoke(auto_tipper_func, query_data=query_data, interval=interval)
        sys.exit(0)
    
    # If no auto-tipper flag and no command, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

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
cli.add_command(manage_block_data_cli, name="block-data-manage")
cli.add_command(report_test_value)

def create_cli():
    return cli()

if __name__ == '__main__':
    create_cli()
