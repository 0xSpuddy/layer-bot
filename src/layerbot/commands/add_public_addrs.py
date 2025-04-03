import click
import pandas as pd
import os
from datetime import datetime
from dotenv import load_dotenv
from layerbot.query_layer import get_loya_balance, get_eth_balance, get_septrb_balance

def setup_csv():
    """Setup CSV file with headers if it doesn't exist or if headers are missing."""
    csv_file = 'requester_addresses.csv'
    headers = ['Timestamp', 'Address', 'Discord', 'X', 'Website', 'ETH balance', 'SepTRB balance']
    
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

def check_existing_info(field_name, value):
    """Check if a value exists in a specific column and return associated address if found."""
    if not value:  # Skip empty values
        return None
    try:
        df = pd.read_csv('requester_addresses.csv')
        match = df[df[field_name] == value]
        if not match.empty:
            return match['Address'].iloc[0]
    except Exception as e:
        click.echo(f"Error checking {field_name}: {e}")
    return None

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

def add_address_info(address, discord, x_handle, website, eth_balance, septrb_balance):
    """Add new address with current timestamp and additional info to CSV."""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_row = pd.DataFrame({
            'Timestamp': [timestamp],
            'Address': [address],
            'Discord': [discord],
            'X': [x_handle],
            'Website': [website],
            'ETH balance': [eth_balance],
            'SepTRB balance': [septrb_balance]
        })
        new_row.to_csv('requester_addresses.csv', mode='a', header=False, index=False)
        click.echo(f"Successfully stored address {address}")
        return True
    except Exception as e:
        click.echo(f"Error adding address information: {e}")
        return False

def validate_tellor_address(address):
    return address.startswith('0x')

def refresh_balances():
    """Refresh ETH and SepTRB balances for all addresses in CSV."""
    try:
        # Read the CSV
        df = pd.read_csv('requester_addresses.csv')
        if df.empty:
            click.echo("No addresses found in CSV")
            return None
            
        click.echo("Refreshing balances for all addresses...")
        updated_rows = []
        
        # Process each address
        for index, row in df.iterrows():
            address = row['Address']
            click.echo(f"\nQuerying balances for {address}...")
            
            # Get new ETH balance
            eth_balance = get_eth_balance(address)
            if eth_balance:
                click.echo(f"ETH balance: {eth_balance} ETH")
            else:
                eth_balance = "0"
                click.echo("Could not retrieve ETH balance, using 0")
            
            # Get new SepTRB balance
            septrb_balance = get_septrb_balance(address)
            if septrb_balance:
                click.echo(f"SepTRB balance: {septrb_balance} SepTRB")
            else:
                septrb_balance = "0"
                click.echo("Could not retrieve SepTRB balance, using 0")
            
            # Update row with new balances
            updated_row = row.copy()
            updated_row['ETH balance'] = eth_balance
            updated_row['SepTRB balance'] = septrb_balance
            updated_rows.append(updated_row)
        
        # Create new DataFrame with updated balances
        updated_df = pd.DataFrame(updated_rows)
        
        # Save back to CSV
        updated_df.to_csv('requester_addresses.csv', index=False)
        click.echo("\nSuccessfully updated all balances")
        return updated_df
        
    except Exception as e:
        click.echo(f"Error refreshing balances: {e}")
        return None

@click.command()
def add_requester():
    """Store requester addresses with timestamp."""
    # Setup CSV file
    if not setup_csv():
        click.echo("Failed to setup CSV file")
        return

    # Prompt for address
    address = click.prompt("Please enter the requester EVM address")

    # Validate address format
    if not validate_tellor_address(address):
        click.echo("Invalid address format. Address must start with 0x")
        return

    # Check if address exists
    existing_timestamp = check_address_exists(address)
    if existing_timestamp:
        click.echo(f"Address {address} was already stored on {existing_timestamp}")
        return

    # Prompt for Discord and check if it exists
    while True:
        discord = click.prompt("Enter Discord handle (press Enter to skip)", default='')
        if discord:
            existing_address = check_existing_info('Discord', discord)
            if existing_address:
                click.echo(f"Discord handle {discord} is already associated with address {existing_address}")
                if not click.confirm("Would you like to enter a different Discord handle?"):
                    discord = ''
                    break
            else:
                break
        else:
            break

    # Prompt for X handle and check if it exists
    while True:
        x_handle = click.prompt("Enter X (Twitter) handle (press Enter to skip)", default='')
        if x_handle:
            existing_address = check_existing_info('X', x_handle)
            if existing_address:
                click.echo(f"X handle {x_handle} is already associated with address {existing_address}")
                if not click.confirm("Would you like to enter a different X handle?"):
                    x_handle = ''
                    break
            else:
                break
        else:
            break

    # Prompt for website and check if it exists
    while True:
        website = click.prompt("Enter website (press Enter to skip)", default='')
        if website:
            existing_address = check_existing_info('Website', website)
            if existing_address:
                click.echo(f"Website {website} is already associated with address {existing_address}")
                if not click.confirm("Would you like to enter a different website?"):
                    website = ''
                    break
            else:
                break
        else:
            break

    # Query the address balances
    click.echo("Querying address balances...")
    
    # Get ETH balance
    eth_balance = get_eth_balance(address)
    if eth_balance:
        click.echo(f"Current ETH balance: {eth_balance} ETH")
    else:
        click.echo("Could not retrieve ETH balance, using 0")
        eth_balance = "0"
    
    # Get SepTRB balance
    septrb_balance = get_septrb_balance(address)
    if septrb_balance:
        click.echo(f"Current SepTRB balance: {septrb_balance} SepTRB")
    else:
        click.echo("Could not retrieve SepTRB balance, using 0")
        septrb_balance = "0"

    # Add new address with additional info
    if add_address_info(address, discord, x_handle, website, eth_balance, septrb_balance):
        click.echo("Address and additional information stored successfully")
    else:
        click.echo("Failed to store address information")

if __name__ == '__main__':
    add_requester()
