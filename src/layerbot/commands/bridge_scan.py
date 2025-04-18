import click
from ..utils.query_layer import get_claim_deposit_txs, get_claimed_deposit_ids, get_withdraw_tokens_txs
from ..utils.query_bridge_reports import update_bridge_deposits_timestamps
from ..bridge_info import main as scan_bridge_contract, update_withdrawal_status

@click.group()
def bridge_scan():
    """Scan bridge-related transactions"""
    pass

@bridge_scan.command()
def deposits():
    """Scan for bridge deposit claims"""
    # 1. First scan the bridge contract for new deposits
    print("\nScanning bridge contract for new deposits...")
    scan_bridge_contract()
    
    # 2. Then scan for claim deposit transactions
    print("\nScanning claim transactions...")
    get_claim_deposit_txs()
    
    # 4. Finally, get claimed deposit IDs to update final status
    print("\nUpdating claimed status...")
    get_claimed_deposit_ids()

    # 3. Update Aggregate Timestamps from oracle data
    print("\nUpdating Aggregate Timestamps...")
    update_bridge_deposits_timestamps()
    
    print("Done scanning deposits")

@bridge_scan.command()
def withdrawals():
    """Scan for bridge withdrawal transactions"""
    print("\nScanning for withdrawals...")
    get_withdraw_tokens_txs()
    
    # Update withdrawal status
    update_withdrawal_status()
    
    print("Done scanning withdrawals") 