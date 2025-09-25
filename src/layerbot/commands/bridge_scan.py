import click
from layerbot.utils.query_layer import get_claimed_deposit_ids, get_withdraw_tokens_txs
from layerbot.bridge_info import update_withdrawal_status
from layerbot.utils.scan_time import update_scan_time
from layerbot.utils.query_withdrawal_txs import update_withdrawal_amounts, update_withdrawal_timestamps

@click.group()
def bridge_scan():
    """Bridge scanning commands"""
    pass

@bridge_scan.command()
def deposits():
    """Scan for new bridge deposits"""
    # Run the main function from bridge_info.py
    from layerbot.bridge_info import main as run_deposits_scan
    run_deposits_scan()

@bridge_scan.command()
def report_status():
    """Update the claimed status of deposits"""
    print("\nUpdating claimed status of deposits...")
    from layerbot.utils.query_layer import update_claimed_status_csv
    update_claimed_status_csv()
    
    # Update the scan time
    scan_time = update_scan_time()
    if scan_time:
        print(f"\nScan completed at: {scan_time}")
        
    print("Done updating deposit claimed status")

@bridge_scan.command()
def withdrawals():
    """Scan for bridge withdrawal transactions"""
    print("\nScanning for withdrawals...")
    get_withdraw_tokens_txs()
    
    # Update withdrawal status
    update_withdrawal_status()
    
    # Update withdrawal amounts by querying individual transactions
    print("\nUpdating withdrawal amounts...")
    update_withdrawal_amounts()
    
    # Update withdrawal timestamps by querying individual transactions
    print("\nUpdating withdrawal timestamps...")
    update_withdrawal_timestamps()
    
    # Update the scan time
    scan_time = update_scan_time()
    if scan_time:
        print(f"\nScan completed at: {scan_time}")
    
    print("Done scanning withdrawals") 