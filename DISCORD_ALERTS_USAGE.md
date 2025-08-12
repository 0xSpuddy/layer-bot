# Discord Alerts Usage

## Overview
The Discord alerts system sends notifications to a Discord channel via webhook when new bridge deposits are detected.

## Setup

1. **Discord Webhook Configuration**
   - Create a webhook in your Discord server (Server Settings > Integrations > Webhooks)
   - Copy the webhook URL
   - Add it to your `.env` file:
     ```
     DISCORD_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
     ```

2. **Dependencies**
   - The `requests` library is already included in `requirements.txt`
   - No additional dependencies required

## Features

### New Bridge Deposit Alerts
- Automatically triggered when the bridge monitor detects new deposits
- Includes: Deposit ID, Timestamp, Sender, Recipient, Amount, Tip (if present), Block Height
- Rich formatting with Discord embeds
- Handles both single and multiple deposits

### Alert Types
- **Single Deposit**: Rich embed with full details
- **Multiple Deposits**: Summary with individual deposit details (max 5 shown)
- **Bridge Status**: General bridge monitoring updates

## Usage

### Automatic Alerts (Bridge Monitor)
The bridge monitor automatically sends Discord alerts when new deposits are found:
```bash
layerbot bridge-monitor
```

### Manual Testing
To test the Discord webhook:
```bash
python -c "from src.layerbot.utils.discord_alerts import test_discord_alert; test_discord_alert()"
```

### Custom Alerts in Code
```python
from layerbot.utils.discord_alerts import alert_new_bridge_deposits

# Single deposit
deposit_data = {
    'deposit_id': 123,
    'timestamp': '2024-01-15 12:34:56',
    'sender': '0x123...',
    'recipient': 'tellor1abc...',
    'amount': '1000000000000000000',  # 1 TRB in wei
    'tip': '100000000000000000',     # 0.1 TRB in wei
    'block_height': '12345678'
}

alert_new_bridge_deposits([deposit_data])
```

## Error Handling
- If Discord webhook is not configured, alerts are skipped with a warning
- Network errors are caught and logged
- Bridge monitoring continues even if Discord alerts fail

## Integration Points
- `src/layerbot/bridge_info.py`: Main bridge scanning function
- `src/layerbot/cli.py`: Bridge monitor command (runs every 180 seconds)
- `src/layerbot/commands/bridge_scan.py`: Bridge scan commands

## Future Extensions
The Discord alerts system is designed to be extensible. Additional alert types can be added:
- Withdrawal notifications
- Bridge status changes
- Error alerts
- Performance monitoring
