# Bridge Contract Migration Summary

## Overview
Successfully migrated the system from a single bridge contract to support two bridge contracts with full historical data preservation.

## Bridge Contract Addresses
- **Old Contract (V0)**: `0x5acb5977f35b1A91C4fE0F4386eB669E046776F2` - **READ ONLY** (no new deposits)
- **New Contract (V1)**: `0x62733e63499a25E35844c91275d4c3bdb159D29d` - **ACTIVE** (all new deposits)

## Changes Made

### 1. Database Schema (CSV)
- ✅ Added new column: `Bridge Contract Address`
- ✅ Backfilled all 139 existing rows with `BRIDGE_CONTRACT_ADDRESS_0`
- ✅ Created backup: `bridge_deposits.csv.backup`

**New CSV Structure:**
```
Timestamp, Deposit ID, Sender, Recipient, Amount, Tip, Block Height, Query ID, Status, Query Data, Bridge Contract Address
```

### 2. Code Updates

#### `src/layerbot/bridge_info.py`
- ✅ Updated `setup_csv()` to include new column header
- ✅ Modified `save_deposit_to_csv()` to accept and write contract address parameter
- ✅ Changed `main()` to use `BRIDGE_CONTRACT_ADDRESS_1` for Ethereum scanning
- ✅ Updated save call to pass contract address to CSV writer

#### `src/layerbot/commands/bridge_request.py`
- ✅ Changed variable from `BRIDGE_CONTRACT_ADDRESS_0` to `BRIDGE_CONTRACT_ADDRESS`
- ✅ Now uses `BRIDGE_CONTRACT_ADDRESS_1` for all bridge requests
- ✅ Updated error messages to reflect new variable name

#### `debug_withdraw_claimed.py`
- ✅ Updated to check both contract addresses (V1 first, V0 as fallback)
- ✅ Improved error messages

#### `check_contract_exists.py`
- ✅ Enhanced to check and display both contract addresses
- ✅ Shows status for both Old (V0) and New (V1) contracts

### 3. Dashboard Updates

#### `templates/deposits.html`
- ✅ Added "Bridge Contract" field to deposit details
- ✅ Shows contract address in expandable row details

### 4. Environment Variables

Required `.env` configuration:
```bash
BRIDGE_CONTRACT_ADDRESS_0=0x5acb5977f35b1A91C4fE0F4386eB669E046776F2
BRIDGE_CONTRACT_ADDRESS_1=0x62733e63499a25E35844c91275d4c3bdb159D29d
```

## Data Integrity

### Historical Data (Preserved)
- ✅ All 139 existing deposits remain unchanged
- ✅ Each historical deposit tagged with `BRIDGE_CONTRACT_ADDRESS_0`
- ✅ Backup created before migration

### New Data (Active)
- ✅ All new deposits will be tagged with `BRIDGE_CONTRACT_ADDRESS_1`
- ✅ Ethereum RPC queries now point to new contract
- ✅ Bridge requests use new contract address

## Behavior

### What Changed
1. **Data Collection**: Now scans `BRIDGE_CONTRACT_ADDRESS_1` for new deposits
2. **CSV Writes**: Automatically includes contract address for all new deposits
3. **Dashboard**: Shows which contract each deposit came from
4. **Bridge Requests**: Uses new contract for all transactions

### What Stayed the Same
1. **Historical Data**: Completely preserved with proper tagging
2. **CSV Format**: Only added one column at the end
3. **Query IDs**: No changes to query ID generation
4. **Status Tracking**: Claim status tracking unchanged

## Future Scalability

This pattern scales easily to additional contracts:
1. Add `BRIDGE_CONTRACT_ADDRESS_2` to `.env`
2. Update `main()` in `bridge_info.py` to use new address
3. All new deposits will be automatically tagged with correct contract

## Verification Steps

To verify the migration worked correctly:

1. **Check CSV structure**:
   ```bash
   head -2 bridge_deposits.csv
   ```
   Should show new column header and old contract address

2. **Check backup exists**:
   ```bash
   ls -lh bridge_deposits.csv.backup
   ```

3. **Verify contract addresses**:
   ```bash
   source env/bin/activate
   python check_contract_exists.py
   ```

4. **Test new deposit collection**:
   ```bash
   source env/bin/activate
   python -m layerbot.bridge_info
   ```
   New deposits should have `BRIDGE_CONTRACT_ADDRESS_1`

## Migration Date
October 1, 2025

## Notes
- The old contract (`BRIDGE_CONTRACT_ADDRESS_0`) will never receive new deposits
- All historical data remains queryable and intact
- The system is now ready to collect data from the new bridge contract

