# Withdrawals Display Fix

## Date
October 1, 2025

## Problem Identified
Bridge withdrawals were not displaying on the frontend due to two issues:

1. **Missing `Claimed` Column**: The `bridge_withdrawals.csv` file was missing the `Claimed` column that the app expected
2. **Column Reordering Bug**: The `update_withdrawal_status()` function was removing the `Timestamp` column when reordering

## Root Cause

### Issue 1: Missing Claimed Column
The withdrawal scanning process follows this flow:
1. `get_withdraw_tokens_txs()` - Creates initial CSV with transaction data (no `Claimed` column)
2. `update_withdrawal_status()` - **Should** add `Claimed` column
3. `update_withdrawal_amounts()` - Adds `Amount` column  
4. `update_withdrawal_timestamps()` - Adds `Timestamp` column

However, the `Claimed` column was not being persisted properly.

### Issue 2: Column Reordering
The `update_withdrawal_status()` function had a hardcoded column list that excluded `Timestamp`:
```python
base_columns = ['withdraw_id', 'creator', 'recipient', 'success', 'Claimed', 'txhash']
```

This caused the `Timestamp` column (added earlier in the process) to be dropped.

### Issue 3: Wrong Environment Variable
The function was looking for `BRIDGE_CONTRACT_ADDRESS_0` but the environment uses:
- `BRIDGE_CONTRACT_ADDRESS_CURRENT`
- `BRIDGE_CONTRACT_ADDRESS_1`

## Solutions Applied

### 1. Fixed app.py - Handle Missing Claimed Column
**File**: `/home/spuddy/monitoring/palmito/layer-bot/app.py`

Added graceful handling for missing `Claimed` column:
```python
# Add Claimed column if it doesn't exist
if 'Claimed' not in withdrawals_df.columns:
    withdrawals_df['Claimed'] = False  # Default to False for all withdrawals
else:
    withdrawals_df['Claimed'] = withdrawals_df['Claimed'].astype(bool)
```

**Lines**: 373-377

### 2. Fixed bridge_info.py - Preserve All Columns
**File**: `/home/spuddy/monitoring/palmito/layer-bot/src/layerbot/bridge_info.py`

Changed column reordering to preserve all columns:
```python
# Reorder columns to ensure consistent order
column_order = []

# Add columns in preferred order if they exist
preferred_order = ['Timestamp', 'creator', 'recipient', 'success', 'Claimed', 'txhash', 'withdraw_id', 'Amount']
for col in preferred_order:
    if col in df.columns:
        column_order.append(col)

# Add any remaining columns that weren't in the preferred list
for col in df.columns:
    if col not in column_order:
        column_order.append(col)

df = df[column_order]
```

**Lines**: 205-220

### 3. Fixed Environment Variable Reference
**File**: `/home/spuddy/monitoring/palmito/layer-bot/src/layerbot/bridge_info.py`

Updated to use available environment variables:
```python
# Create contract instance - try current first, then fall back to V1
contract_address = os.getenv('BRIDGE_CONTRACT_ADDRESS_CURRENT') or os.getenv('BRIDGE_CONTRACT_ADDRESS_1')
if not contract_address:
    print("Error: BRIDGE_CONTRACT_ADDRESS_CURRENT or BRIDGE_CONTRACT_ADDRESS_1 not found in .env file")
    return
```

**Lines**: 176-180

## Correct CSV Structure

The withdrawals CSV now has the proper column order:
```
Timestamp,creator,recipient,success,Claimed,txhash,withdraw_id,Amount
```

**Key Points**:
- `Claimed` column is positioned after `success` (as required)
- `Timestamp` is preserved as the first column
- All columns are maintained through the update process

## Verification

✅ Ran `update_withdrawal_status()` - Successfully added `Claimed` column  
✅ CSV has correct structure with all columns preserved  
✅ App loads withdrawals without errors  
✅ No linter errors in modified files

## Testing Commands

To verify the fix works:

```bash
source env/bin/activate

# Test withdrawal status update
python -c "from src.layerbot.bridge_info import update_withdrawal_status; update_withdrawal_status()"

# Check CSV structure
head -2 bridge_withdrawals.csv

# Test app loads withdrawals
python -c "from app import app; with app.test_client() as c: print('Status:', c.get('/').status_code)"
```

## Impact

- ✅ Withdrawals now display correctly on the dashboard
- ✅ Withdrawals chart initializes without errors
- ✅ Claimed status is properly tracked
- ✅ All existing functionality preserved
- ✅ Future withdrawal scans will maintain proper column structure

## Files Modified

1. `app.py` - Added handling for missing `Claimed` column
2. `src/layerbot/bridge_info.py` - Fixed column reordering and environment variable

