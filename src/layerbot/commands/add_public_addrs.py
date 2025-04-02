import click
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv

def setup_csv():
    """Setup CSV file with headers if it doesn't exist or if headers are missing."""
    csv_file = 'requester_addresses.csv'
    headers = ['Timestamp', 'Address']
    
    try:
        # Check if file exists and has headers
        if os.path.exists(csv_file):
            with open(csv_file, 'r') as f:
                first_line = f.readline().strip()
                if first_line != ','.join(headers):
                    # Headers don't match, create new file with correct headers
                    click.echo(f"Updating headers in CSV file: {csv_file}")
                    pd.DataFrame(columns=headers).to_csv(csv_file, index=False)
        else:
            # File doesn't exist, create new file with headers
            click.echo(f"Creating new CSV file: {csv_file}")
            pd.DataFrame(columns=headers).to_csv(csv_file, index=False)
        return True
    except Exception as e:
        click.echo(f"Error setting up CSV file: {e}")
        return False

def check_address_exists(address):
    """Check if address exists in CSV and return timestamp if found."""
    try:
        df = pd.read_csv('requester_addresses.csv')
        match = df[df['Address'] == address]
        if not match.empty:
            return match['Timestamp'].iloc[0]
    except Exception as e:
        click.echo(f"Error checking address: {e}")
    return None

def add_address(address):
    """Add new address with current timestamp to CSV."""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_row = pd.DataFrame({'Timestamp': [timestamp], 'Address': [address]})
        new_row.to_csv('requester_addresses.csv', mode='a', header=False, index=False)
        click.echo(f"Successfully stored address {address}")
        return True
    except Exception as e:
        click.echo(f"Error adding address: {e}")
        return False

def validate_tellor_address(address):
    """Basic validation for tellor-prefix addresses."""
    return address.startswith('tellor1')

@click.command()
def add_requester():
    """Store requester addresses with timestamps."""
    # Setup CSV file
    if not setup_csv():
        click.echo("Failed to setup CSV file")
        return

    # Prompt for address
    address = click.prompt("Please enter the requester address (tellor1... format)")

    # Validate address format
    if not validate_tellor_address(address):
        click.echo("Invalid address format. Address must start with 'tellor1' and be 44 characters long")
        return

    # Check if address exists
    existing_timestamp = check_address_exists(address)
    if existing_timestamp:
        click.echo(f"Address {address} was already stored on {existing_timestamp}")
        return

    # Add new address
    if add_address(address):
        click.echo("Address stored successfully")
    else:
        click.echo("Failed to store address")

if __name__ == '__main__':
    add_requester()
