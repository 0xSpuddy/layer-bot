import click
import os
import subprocess
from dotenv import load_dotenv
from layerbot.list_keys import main as list_keys_main

@click.group()
def test():
    """Test Tellor chain functionality."""
    pass

@test.command('list-keys')
def list_keys():
    """List available keys in the keystore."""
    try:
        # Execute the layerd keys list command
        result = subprocess.run(
            ['./layerd', 'keys', 'list'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Print the output
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(f"Error output: {e.stderr}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


@test.command('claim-deposits')
@click.argument('creator')
@click.argument('deposit_ids')
@click.argument('timestamps')
@click.argument('account_name')
def claim_deposits(creator, deposit_ids, timestamps, account_name):
    """Claim bridge deposits on Layer chain."""
    max_retries = 7
    attempt = 1
    
    while attempt <= max_retries:
        try:
            # Construct the command
            cmd = [
                './layerd', 'tx', 'bridge', 'claim-deposits',
                creator,
                deposit_ids,
                timestamps,
                '--from', account_name,
                '--gas', 'auto',
                '--chain-id', 'layertest-4',
                '--fees', '10loya',
                '--yes'
            ]
            
            # Execute the command
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse the output to find raw_log
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
                print(f"Transaction succeeded! Transaction hash: {txhash}")
                return
            else:
                print(f"Transaction failed (attempt {attempt}/{max_retries})")
                print(f"Raw log: {raw_log}")
                attempt += 1
                
        except subprocess.CalledProcessError as e:
            print(f"Error executing command (attempt {attempt}/{max_retries}): {e}")
            print(f"Error output: {e.stderr}")
            attempt += 1
        except Exception as e:
            print(f"Unexpected error (attempt {attempt}/{max_retries}): {e}")
            attempt += 1
    
    print("Maximum retry attempts reached. Transaction failed.")