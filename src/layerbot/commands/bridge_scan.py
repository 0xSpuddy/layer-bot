import click
from ..utils.query_layer import get_claim_deposit_txs, get_claimed_deposit_ids, get_withdraw_tokens_txs

@click.group()
def bridge_scan():
    """Scan bridge-related transactions"""
    pass

@bridge_scan.command()
def deposits():
    """Scan for bridge deposit claims"""
    print("\nFetching claim deposit transactions...")
    transactions = get_claim_deposit_txs()
    print(f"Found {len(transactions)} claim deposit transactions")
    
    print("\nGetting claimed deposit IDs...")
    claimed_ids = get_claimed_deposit_ids()
    print("Done scanning deposits")

@bridge_scan.command()
def withdrawals():
    """Scan for bridge withdrawal transactions"""
    print("\nScanning for withdrawals...")
    withdrawals = get_withdraw_tokens_txs()
    print(f"Found {len(withdrawals)} withdrawal transactions")
    print("Done scanning withdrawals") 