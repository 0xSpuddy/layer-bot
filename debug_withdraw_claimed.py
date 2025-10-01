#!/usr/bin/env python3

import os
from web3 import Web3
from dotenv import load_dotenv
import json

def load_abi():
    """Load the ABI from the JSON file."""
    with open('contracts/bridge_abi.json', 'r') as f:
        return json.load(f)

def main():
    # Load environment variables
    load_dotenv()
    
    # Get required environment variables - can check either contract
    contract_address = os.getenv('BRIDGE_CONTRACT_ADDRESS_1') or os.getenv('BRIDGE_CONTRACT_ADDRESS_0')
    rpc_url = os.getenv('ETHEREUM_RPC_URL')
    
    print("=== Debug withdrawClaimed Function ===")
    print(f"Contract Address: {contract_address[:10]}...{contract_address[-10:] if contract_address else 'NOT SET'}")
    print(f"RPC URL: {rpc_url[:20]}...{rpc_url[-10:] if rpc_url else 'NOT SET'}")
    
    if not contract_address:
        print("❌ Error: BRIDGE_CONTRACT_ADDRESS_0 or BRIDGE_CONTRACT_ADDRESS_1 not found in .env file")
        return
        
    if not rpc_url:
        print("❌ Error: ETHEREUM_RPC_URL not found in .env file")
        return
    
    try:
        # Initialize Web3
        print("\n1. Testing Web3 connection...")
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not w3.is_connected():
            print("❌ Error: Could not connect to RPC endpoint")
            return
        print("✅ Web3 connected successfully")
        
        # Get network info
        try:
            chain_id = w3.eth.chain_id
            latest_block = w3.eth.block_number
            print(f"✅ Chain ID: {chain_id}")
            print(f"✅ Latest block: {latest_block}")
        except Exception as e:
            print(f"⚠️  Warning: Could not get network info: {e}")
        
        # Load contract ABI
        print("\n2. Loading contract ABI...")
        try:
            abi = load_abi()
            print("✅ ABI loaded successfully")
            
            # Check if withdrawClaimed function exists in ABI
            withdraw_claimed_func = None
            for item in abi:
                if item.get('name') == 'withdrawClaimed' and item.get('type') == 'function':
                    withdraw_claimed_func = item
                    break
            
            if withdraw_claimed_func:
                print("✅ withdrawClaimed function found in ABI")
                print(f"   Inputs: {withdraw_claimed_func['inputs']}")
                print(f"   Outputs: {withdraw_claimed_func['outputs']}")
            else:
                print("❌ withdrawClaimed function NOT found in ABI")
                return
                
        except Exception as e:
            print(f"❌ Error loading ABI: {e}")
            return
        
        # Create contract instance
        print("\n3. Creating contract instance...")
        try:
            contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
            print("✅ Contract instance created successfully")
        except Exception as e:
            print(f"❌ Error creating contract instance: {e}")
            return
        
        # Test basic contract calls first
        print("\n4. Testing basic contract functions...")
        try:
            # Test depositId function (should always work)
            deposit_id = contract.functions.depositId().call()
            print(f"✅ depositId() call successful: {deposit_id}")
        except Exception as e:
            print(f"❌ Error calling depositId(): {e}")
            print("   This suggests the contract address or ABI might be wrong")
            return
        
        # Test withdrawClaimed with different IDs
        print("\n5. Testing withdrawClaimed function...")
        test_withdraw_ids = [1, 2, 3, 39]  # Including the problematic ID 39
        
        for withdraw_id in test_withdraw_ids:
            try:
                result = contract.functions.withdrawClaimed(withdraw_id).call()
                print(f"✅ withdrawClaimed({withdraw_id}) = {result}")
            except Exception as e:
                print(f"❌ withdrawClaimed({withdraw_id}) failed: {e}")
                
                # Try to get more specific error info
                try:
                    # Check if it's a revert with reason
                    w3.eth.call({
                        'to': contract_address,
                        'data': contract.encodeABI(fn_name='withdrawClaimed', args=[withdraw_id])
                    })
                except Exception as call_error:
                    print(f"   Raw call error: {call_error}")
        
        # Check if the contract has any withdraw-related mappings/functions
        print("\n6. Checking contract state...")
        try:
            # Try to call some other functions to see if contract is working
            bridge_state = contract.functions.bridgeState().call()
            print(f"✅ bridgeState() = {bridge_state}")
        except Exception as e:
            print(f"⚠️  bridgeState() failed: {e}")
            
        print("\n=== Debug Summary ===")
        print("If withdrawClaimed fails but other functions work:")
        print("- The withdraw ID might not exist yet")
        print("- The withdraw mapping might be empty for that ID")
        print("- Check if withdrawals.csv has the correct withdraw IDs")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 