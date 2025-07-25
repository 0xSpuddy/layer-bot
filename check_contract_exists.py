#!/usr/bin/env python3

import os
from web3 import Web3
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    contract_address = os.getenv('BRIDGE_CONTRACT_ADDRESS')
    rpc_url = os.getenv('ETHEREUM_RPC_URL')
    
    if not contract_address or not rpc_url:
        print("❌ Missing environment variables")
        return
    
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print("❌ Could not connect to RPC")
        return
    
    print(f"Checking contract at: {contract_address}")
    print(f"Network: Chain ID {w3.eth.chain_id}")
    
    try:
        # Check if there's code at this address
        code = w3.eth.get_code(contract_address)
        
        if code == b'' or code == '0x':
            print("❌ No contract code found at this address!")
            print("   This address either:")
            print("   - Has no contract deployed")
            print("   - Is an EOA (Externally Owned Account)")
            print("   - Contract was deployed on a different network")
        else:
            print(f"✅ Contract code found! ({len(code)} bytes)")
            print(f"   Code preview: {code[:50].hex()}...")
            
            # Get additional info
            balance = w3.eth.get_balance(contract_address)
            print(f"   Contract balance: {w3.from_wei(balance, 'ether')} ETH")
            
    except Exception as e:
        print(f"❌ Error checking contract: {e}")

if __name__ == "__main__":
    main() 