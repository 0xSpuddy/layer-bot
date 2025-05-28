"""
Command to manage block time data and backups
"""
import sys
import os
from pathlib import Path
import click
import subprocess

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

@click.group()
def cli():
    """Manage block time data and backups"""
    pass

@click.command(name="create-backup")
@click.option("--reason", default="manual", help="Reason for the backup")
def create_backup(reason):
    """Create a manual backup of the block_time.csv file"""
    from layerbot.utils.block_time import create_backup as do_backup
    backup_file = do_backup(reason)
    if backup_file:
        click.echo(f"Backup created: {backup_file}")
    else:
        click.echo("Backup failed")

@click.command(name="list-backups")
def list_backups():
    """List all available backups of the block_time.csv file"""
    # Run the block_time.py script with the list-backups command
    script_path = Path(__file__).parent.parent / "utils" / "block_time.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "list-backups"], 
        capture_output=True, text=True
    )
    click.echo(result.stdout)
    if result.stderr:
        click.echo(f"Errors: {result.stderr}")

@click.command(name="restore-backup")
@click.option("--file", help="Specific backup file to restore from (default: most recent)")
def restore_backup(file):
    """Restore block_time.csv from a backup file"""
    from layerbot.utils.block_time import restore_from_backup
    success = restore_from_backup(file)
    if success:
        click.echo("Backup restored successfully")
    else:
        click.echo("Backup restoration failed")

@click.command(name="clean-old-records")
def clean_old_records():
    """Clean old records from the block_time.csv file"""
    from layerbot.utils.block_time import clean_old_records as do_clean
    do_clean()

@click.command(name="clean-backups")
def clean_backups():
    """Keep only the most recent backup and delete older ones"""
    from layerbot.utils.block_time import clean_old_backups
    clean_old_backups()

@click.command(name="show-stats")
def show_stats():
    """Show block time statistics"""
    from layerbot.utils.block_time import get_block_time_stats
    stats = get_block_time_stats()
    click.echo("Block Time Statistics:")
    click.echo(f"  5 Minute Average: {stats['five_min']}")
    click.echo(f"  30 Minute Average: {stats['thirty_min']}")
    click.echo(f"  60 Minute Average: {stats['sixty_min']}")
    click.echo(f"  24 Hour Average: {stats['day']}")
    click.echo(f"  7 Day Average: {stats['week']}")

cli.add_command(create_backup)
cli.add_command(list_backups)
cli.add_command(restore_backup)
cli.add_command(clean_old_records)
cli.add_command(clean_backups)
cli.add_command(show_stats)

if __name__ == "__main__":
    cli() 