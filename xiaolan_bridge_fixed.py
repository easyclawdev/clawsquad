#!/usr/bin/env python3
"""
XiaoLan Bridge - Fixed (prevents duplicate responses)
"""
import asyncio
import websockets
import json
import os
from datetime import datetime

INBOX = "/tmp/clawsquad_xiaolan_inbox.jsonl"
OUTBOX = "/tmp/clawsquad_xiaolan_outbox.jsonl"
PROCESSED_FILE = "/tmp/xiaolan_processed.txt"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔵 {msg}", flush=True)

def load_processed():
    """Load processed message IDs"""
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_processed(msg_id):
    """Save processed message ID"""
    with open(PROCESSED_FILE, 'a') as f:
        f.write(f"{msg_id}\n")

async def connect():
    uri = "ws://127.0.0.1:8000/ws/xiaolan"
    log(f"Connecting to {uri}...")
    
    processed_ids = load_processed()
    log(f"Loaded {len(processed_ids)} processed message IDs")
    
    # Create files
    open(INBOX, 'a').close()
    open(OUTBOX, 'a').close()
    
    while True:
        try:
            async with websockets.connect(uri, ping_interval=30) as ws:
                log("✅ Connected!")
                
                await ws.send(json.dumps({
                    "type": "system",
                    "content": "🔵 XiaoLan online! @ me to chat."
                }))
                
                async for message in ws:
                    try:
                        data = json.loads(message)
                        msg_type = data.get('type')
                        
                        if msg_type == 'message':
                            content = data.get('content', '')
                            sender = data.get('agent_id', '')
                            timestamp = data.get('timestamp', '')
                            
                            if sender == 'xiaolan':
                                continue
                            
                            # Create unique ID for this message
                            msg_hash = f"{sender}:{timestamp}:{hash(content) % 10000}"
                            
                            # Skip if already processed
                            if msg_hash in processed_ids:
                                log(f"⚠️  Duplicate ignored from {sender}")
                                continue
                            
                            processed_ids.add(msg_hash)
                            save_processed(msg_hash)
                            
                            log(f"📨 From {sender}: {content[:60]}...")
                            
                            # Check for @mention
                            if '@xiaolan' in content.lower():
                                question = content.replace('@xiaolan', '').strip()
                                msg_id = str(int(datetime.now().timestamp() * 1000))
                                
                                log(f"🚨 MENTION from {sender}: {question}")
                                
                                # Write to inbox
                                entry = {
                                    "id": msg_id,
                                    "timestamp": datetime.now().isoformat(),
                                    "from": sender,
                                    "message": question
                                }
                                with open(INBOX, "a") as f:
                                    f.write(json.dumps(entry) + "\n")
                                log(f"💾 Saved to inbox (ID: {msg_id})")
                                
                                # Send ONE acknowledgment only
                                await ws.send(json.dumps({
                                    "type": "message",
                                    "content": f"🔵 {sender}, I received your message! (ID: {msg_id})",
                                    "room": "general"
                                }))
                                log(f"✅ Ack sent")
                        
                        elif msg_type == 'agent_joined':
                            log(f"👋 {data.get('agent_id')} joined")
                        elif msg_type == 'agent_left':
                            log(f"👋 {data.get('agent_id')} left")
                            
                    except json.JSONDecodeError:
                        pass
                        
        except Exception as e:
            log(f"❌ Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(connect())
