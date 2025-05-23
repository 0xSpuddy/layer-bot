from web3 import Web3
from eth_abi.abi import encode

# Step 1: Input string
# input_str = "cypherpunk purity spiral milady"
input_query_str = "knock knock"
input_value_str = "who is there?"

# Step 2: ABI encode the string as type 'string'
abi_encoded_query = encode(['string'], [input_query_str])
abi_encoded_value = encode(['string'], [input_value_str])

# Step 3: Convert the ABI-encoded bytes into hex format
hex_output_query = Web3.to_hex(abi_encoded_query)
hex_output_value = Web3.to_hex(abi_encoded_value)

# Convert hex to bytes and then compute keccak hash
query_id_bytes = Web3.keccak(hexstr=hex_output_query)
query_id_hex = Web3.to_hex(query_id_bytes)

# Output the result
print(f"Input query string: {input_query_str}")
print(f"Input value string: {input_value_str}")
print(f"ABI-encoded (hex): {hex_output_query}")
print(f"ABI-encoded (hex): {hex_output_value}")
print(f"Query ID: {query_id_hex}")