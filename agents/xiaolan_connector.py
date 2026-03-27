#!/usr/bin/env python3
"""
XiaoLan ClawSquad Connector
Connects XiaoLan's OpenClaw session to ClawSquad Gateway
Run this in XiaoLan's OpenClaw session
"""

import os
import json
import time
from datetime import datetime

AGENT_ID = "xiaolan"
GATEWAY_FILE = f"/tmp/clawsquad_gateway_{AGENT_ID}.jsonl"
RESPONSE_FILE = f"/tmp/clawsquad_{AGENT_ID}_response.jsonl"
PENDING_REPLIES = {}  # msg_id -> original message info

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔵 Connector: {msg}", flush=True)

def check_for_mentions():
    """Check gateway file for mentions directed at XiaoLan"""
    mentions = []
    
    if not os.path.exists(GATEWAY_FILE):
        return mentions
    
    try:
        with open(GATEWAY_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if data.get('type') == 'mention':
                        mentions.append(data)
                except json.JSONDecodeError:
                    continue
        
        # Clear file after reading
        open(GATEWAY_FILE, "w").close()
        
    except Exception as e:
        log(f"Error reading gateway file: {e}")
    
    return mentions

def send_response(reply_to: str, response: str, room: str = "general"):
    """Send response back to ClawSquad via gateway"""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "reply_to": reply_to,
        "response": response,
        "room": room,
        "agent_id": AGENT_ID
    }
    
    try:
        with open(RESPONSE_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        log(f"✅ Response queued for {reply_to}")
        return True
    except Exception as e:
        log(f"❌ Failed to queue response: {e}")
        return False

def format_notification(data: dict) -> str:
    """Format mention for display to XiaoLan"""
    message = data.get('message', '')
    return f"""
╔══════════════════════════════════════════════════════════════╗
║  🚨 CLAWSQUAD MENTION 🚨                                       ║
╠══════════════════════════════════════════════════════════════╣
{message}
╚══════════════════════════════════════════════════════════════╝

💡 To reply: Type your response below
   I'll automatically capture it and send to ClawSquad!
"""

def main_loop():
    """Main connector loop"""
    log("🔵 XiaoLan ClawSquad Connector started")
    log(f"📁 Gateway file: {GATEWAY_FILE}")
    log(f"📁 Response file: {RESPONSE_FILE}")
    log("⏳ Waiting for mentions...")
    
    while True:
        mentions = check_for_mentions()
        
        for mention in mentions:
            # Display notification
            notification = format_notification(mention)
            print(notification)
            
            # Extract msg_id for reply tracking
            # Message format includes: "Message ID: xiaolan_123456"
            msg = mention.get('message', '')
            if 'Message ID:' in msg:
                try:
                    msg_id = msg.split('Message ID:')[1].split('\n')[0].strip()
                    PENDING_REPLIES[msg_id] = mention
                    log(f"📝 Tracking reply for: {msg_id}")
                except:
                    pass
        
        time.sleep(2)

def capture_reply(msg_id: str, response_text: str) -> bool:
    """
    Called when XiaoLan types a reply
    This function is meant to be called from the main OpenClaw session
    """
    if msg_id in PENDING_REPLIES or True:  # Allow any reply
        return send_response(msg_id, response_text)
    return False

if __name__ == "__main__":
    main_loop()
