import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_discord_webhook_url():
    """Get Discord webhook URL from environment variables."""
    webhook_url = os.getenv('DISCORD_WEBHOOK')
    if not webhook_url:
        print("Warning: DISCORD_WEBHOOK not found in environment variables")
        return None
    return webhook_url

def send_discord_alert(content, embeds=None):
    """
    Send a message to Discord via webhook.
    
    Args:
        content (str): The main message content
        embeds (list): Optional list of embed objects for rich formatting
    """
    webhook_url = get_discord_webhook_url()
    if not webhook_url:
        print("Discord webhook URL not configured, skipping alert")
        return False
    
    payload = {
        "content": content
    }
    
    if embeds:
        payload["embeds"] = embeds
    
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print(f"Discord alert sent successfully: {content[:50]}...")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Discord alert: {e}")
        return False

def format_amount(amount_wei):
    """
    Format amount from wei to human readable TRB.
    
    Args:
        amount_wei (int): Amount in wei
        
    Returns:
        str: Formatted amount string
    """
    try:
        amount_trb = float(amount_wei) / 10**18
        return f"{amount_trb:.6f} TRB"
    except (ValueError, TypeError):
        return f"{amount_wei} wei"

def create_bridge_deposit_embed(deposit_data):
    """
    Create a rich embed for new bridge deposit.
    
    Args:
        deposit_data (dict): Dictionary containing deposit information
            - deposit_id: Deposit ID
            - timestamp: Timestamp string 
            - sender: Sender address
            - recipient: Recipient address
            - amount: Amount in wei
            - tip: Tip amount in wei (optional)
            - block_height: Block height (optional)
    
    Returns:
        dict: Discord embed object
    """
    embed = {
        "title": "🌉 New Bridge Deposit",
        "color": 0x00ff00,  # Green color
        "timestamp": datetime.utcnow().isoformat(),
        "fields": [
            {
                "name": "📍 Deposit ID",
                "value": f"`{deposit_data['deposit_id']}`",
                "inline": True
            },
            {
                "name": "⏰ Timestamp", 
                "value": deposit_data.get('timestamp', 'N/A'),
                "inline": True
            },
            {
                "name": "👤 Sender",
                "value": f"`{deposit_data['sender']}`",
                "inline": False
            },
            {
                "name": "🎯 Recipient",
                "value": f"`{deposit_data['recipient']}`",
                "inline": False
            },
            {
                "name": "💰 Amount",
                "value": format_amount(deposit_data['amount']),
                "inline": True
            }
        ]
    }
    
    # Add tip field if tip amount is provided and > 0
    if deposit_data.get('tip') and int(deposit_data['tip']) > 0:
        embed["fields"].append({
            "name": "💡 Tip",
            "value": format_amount(deposit_data['tip']),
            "inline": True
        })
    
    # Add block height if provided
    if deposit_data.get('block_height'):
        embed["fields"].append({
            "name": "🧱 Block Height",
            "value": f"`{deposit_data['block_height']}`",
            "inline": True
        })
    
    return embed

def alert_new_bridge_deposits(deposits_list):
    """
    Send Discord alert for new bridge deposits.
    
    Args:
        deposits_list (list): List of deposit dictionaries
    """
    if not deposits_list:
        return
    
    if len(deposits_list) == 1:
        # Single deposit - use rich embed
        deposit = deposits_list[0]
        embed = create_bridge_deposit_embed(deposit)
        send_discord_alert("🚨 **New Bridge Deposit Detected!**", [embed])
    else:
        # Multiple deposits - use summary format
        total_amount = sum(float(d['amount']) for d in deposits_list)
        total_amount_trb = total_amount / 10**18
        
        # Create summary embed
        embed = {
            "title": f"🌉 {len(deposits_list)} New Bridge Deposits",
            "color": 0x0099ff,  # Blue color
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "📊 Summary",
                    "value": f"**{len(deposits_list)}** new deposits\n**{total_amount_trb:.6f} TRB** total volume",
                    "inline": False
                }
            ]
        }
        
        # Add individual deposit details
        for i, deposit in enumerate(deposits_list[:5]):  # Limit to first 5 to avoid embed size limits
            embed["fields"].append({
                "name": f"Deposit #{deposit['deposit_id']}",
                "value": f"**Amount:** {format_amount(deposit['amount'])}\n**From:** `{deposit['sender'][:10]}...`\n**To:** `{deposit['recipient'][:20]}...`",
                "inline": True
            })
        
        if len(deposits_list) > 5:
            embed["fields"].append({
                "name": "...",
                "value": f"And {len(deposits_list) - 5} more deposits",
                "inline": False
            })
        
        send_discord_alert("🚨 **Multiple New Bridge Deposits Detected!**", [embed])

def alert_bridge_deposit_claimed(deposit_id, recipient, amount):
    """
    Send Discord alert when a bridge deposit is claimed.
    
    Args:
        deposit_id (int): Deposit ID that was claimed
        recipient (str): Recipient address
        amount (int): Amount in wei
    """
    embed = {
        "title": "✅ Bridge Deposit Claimed",
        "color": 0xffaa00,  # Orange color
        "timestamp": datetime.utcnow().isoformat(),
        "fields": [
            {
                "name": "📍 Deposit ID",
                "value": f"`{deposit_id}`",
                "inline": True
            },
            {
                "name": "🎯 Recipient",
                "value": f"`{recipient}`",
                "inline": False
            },
            {
                "name": "💰 Amount",
                "value": format_amount(amount),
                "inline": True
            }
        ]
    }
    
    send_discord_alert("💸 **Bridge Deposit Claimed!**", [embed])

def alert_bridge_status(status, message=""):
    """
    Send Discord alert for bridge status changes.
    
    Args:
        status (str): Status type (e.g., "error", "warning", "info")
        message (str): Status message
    """
    colors = {
        "error": 0xff0000,    # Red
        "warning": 0xffaa00,  # Orange  
        "info": 0x0099ff,     # Blue
        "success": 0x00ff00   # Green
    }
    
    icons = {
        "error": "❌",
        "warning": "⚠️", 
        "info": "ℹ️",
        "success": "✅"
    }
    
    embed = {
        "title": f"{icons.get(status, '🔔')} Bridge Status Update",
        "description": message,
        "color": colors.get(status, 0x666666),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    send_discord_alert(f"🌉 **Bridge Monitor Update**", [embed])

# Test function for debugging
def test_discord_alert():
    """Test function to verify Discord webhook is working."""
    test_deposit = {
        "deposit_id": 999,
        "timestamp": "2024-01-15 12:34:56",
        "sender": "0x1234567890123456789012345678901234567890",
        "recipient": "tellor1abcdef1234567890abcdef1234567890abcdef",
        "amount": "1000000000000000000",  # 1 TRB
        "tip": "100000000000000000",      # 0.1 TRB
        "block_height": "12345678"
    }
    
    print("Testing Discord alert...")
    alert_new_bridge_deposits([test_deposit])
    
if __name__ == "__main__":
    test_discord_alert()

