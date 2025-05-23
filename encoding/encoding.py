from web3 import Web3
from eth_abi.abi import encode

# Step 1: Input string
# input_str = "cypherpunk purity spiral milady"
input_str = "This was just a test of the tellor registry system."

# Step 2: ABI encode the string as type 'string'
abi_encoded = encode(['string'], [input_str])

# Step 3: Convert the ABI-encoded bytes into hex format
hex_output = Web3.to_hex(abi_encoded)

# Output the result
print(f"Input string: {input_str}")
print(f"ABI-encoded (hex): {hex_output}")