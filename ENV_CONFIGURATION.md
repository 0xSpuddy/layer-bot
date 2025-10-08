# Environment Configuration Guide

## Bridge Contract Configuration

### Required Variables

#### `BRIDGE_CONTRACT_ADDRESS_CURRENT`
The **active** bridge contract being monitored for new deposits.

```bash
BRIDGE_CONTRACT_ADDRESS_CURRENT=0x62733e63499a25E35844c91275d4c3bdb159D29d
```

### Optional Variables

#### `BRIDGE_CONTRACT_ADDRESS_0`, `BRIDGE_CONTRACT_ADDRESS_1`, etc.
Archive contracts for reference only. Historical data is preserved in CSV with contract addresses tagged.

```bash
BRIDGE_CONTRACT_ADDRESS_0=0x5acb5977f35b1A91C4fE0F4386eB669E046776F2
```

#### `BRIDGE_START_DEPOSIT_ID`
Explicitly set where to start scanning deposits. **Only needed in special cases.**

```bash
# Example: Force starting from deposit ID 140
BRIDGE_START_DEPOSIT_ID=140
```

**When to use:**
- Manual override needed
- Testing specific scenarios
- **Not needed for normal operation** - auto-detection handles most cases

### Backwards Compatibility

The system will fall back to `BRIDGE_CONTRACT_ADDRESS_1` if `BRIDGE_CONTRACT_ADDRESS_CURRENT` is not set.

---

## How Deposit ID Detection Works

The script uses **smart auto-detection** to determine where to start scanning:

### 1. **Explicit Override** (if `BRIDGE_START_DEPOSIT_ID` is set)
   - Uses the specified deposit ID
   - Useful for testing or manual control

### 2. **Smart Detection** (default behavior)
   - Reads contract's `depositId()` to see how many deposits exist on-chain
   - Compares with CSV to find the last deposit ID we have
   - Intelligently continues from where we left off

### 3. **Fallback** (if contract call fails)
   - Starts from deposit ID 1
   - Safe default for new deployments

---

## Deployment Scenarios

### Scenario 1: Main Chain (Single Contract)

**Setup:**
```bash
BRIDGE_CONTRACT_ADDRESS_CURRENT=0xYourMainChainContractAddress
```

**Behavior:**
- Starts from deposit ID 1 for fresh deployment
- Automatically continues from last known deposit on subsequent runs
- No manual configuration needed

---

### Scenario 2: Test Chain (Multiple Contracts - Current Setup)

**Setup:**
```bash
BRIDGE_CONTRACT_ADDRESS_CURRENT=0x62733e63499a25E35844c91275d4c3bdb159D29d
BRIDGE_CONTRACT_ADDRESS_0=0x5acb5977f35b1A91C4fE0F4386eB669E046776F2
```

**Behavior:**
- CSV has 139 deposits from old contract (all tagged with `BRIDGE_CONTRACT_ADDRESS_0`)
- New contract starts at deposit ID 140
- Script auto-detects: "CSV has 139 deposits, on-chain has 141, continue from 140"
- Works seamlessly without `BRIDGE_START_DEPOSIT_ID`

---

### Scenario 3: Fresh Deployment

**Setup:**
```bash
BRIDGE_CONTRACT_ADDRESS_CURRENT=0xBrandNewContractAddress
```

**Behavior:**
- Empty CSV or no matching deposits
- Contract has no deposits yet
- Starts from deposit ID 1
- Fully automatic

---

### Scenario 4: Migrating from Old CSV

**Setup:**
```bash
BRIDGE_CONTRACT_ADDRESS_CURRENT=0xNewContractAddress
# If the new contract starts at an unusual ID (not 1):
BRIDGE_START_DEPOSIT_ID=1000
```

**Behavior:**
- Forces scanning to start from deposit ID 1000
- Use sparingly - only when auto-detection doesn't work

---

## Migration from Old Variable Names

### Old Configuration (Deprecated but supported):
```bash
BRIDGE_CONTRACT_ADDRESS_0=0x5acb...76F2
BRIDGE_CONTRACT_ADDRESS_1=0x6273...D29d
```

### New Configuration (Recommended):
```bash
BRIDGE_CONTRACT_ADDRESS_CURRENT=0x6273...D29d  # Active contract
BRIDGE_CONTRACT_ADDRESS_0=0x5acb...76F2        # Archive (optional)
```

### Transition Plan:
1. Add `BRIDGE_CONTRACT_ADDRESS_CURRENT` to your .env
2. Keep `BRIDGE_CONTRACT_ADDRESS_0` and `_1` for backwards compatibility
3. Over time, these will be phased out in favor of semantic naming

---

## Summary

✅ **For most deployments:** Just set `BRIDGE_CONTRACT_ADDRESS_CURRENT`
✅ **Auto-detection handles:** Starting point, contract changes, CSV syncing
✅ **Manual override available:** `BRIDGE_START_DEPOSIT_ID` when needed
✅ **Backwards compatible:** Still supports `_0`, `_1` naming
✅ **Works across chains:** Same code works on main and test chains

**Bottom line:** The system is now smart enough to figure out where to start scanning without manual configuration in 99% of cases.

