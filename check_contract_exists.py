#!/usr/bin/env python3

import os
from web3 import Web3
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv()
    
    # Check both contract addresses
    contract_address_0 = os.getenv('BRIDGE_CONTRACT_ADDRESS_0')
    contract_address_1 = os.getenv('BRIDGE_CONTRACT_ADDRESS_1')
    rpc_url = os.getenv('ETHEREUM_RPC_URL')
    
    if not rpc_url:
        print("❌ Missing ETHEREUM_RPC_URL")
        return
    
    if not contract_address_0 and not contract_address_1:
        print("❌ Missing bridge contract addresses")
        return
    
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print("❌ Could not connect to RPC")
        return
    
    print(f"Network: Chain ID {w3.eth.chain_id}\n")
    
    # Check both contracts
    for label, contract_address in [("Old (V0)", contract_address_0), ("New (V1)", contract_address_1)]:
        if not contract_address:
            continue
            
        print(f"Checking {label} contract at: {contract_address}")
        
        try:
            # Check if there's code at this address
            code = w3.eth.get_code(contract_address)
            
            if code == b'' or code == '0x':
                print(f"❌ No contract code found at this address!")
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
            
            print()  # Empty line between contracts
                
        except Exception as e:
            print(f"❌ Error checking contract: {e}\n")

if __name__ == "__main__":
    main() 