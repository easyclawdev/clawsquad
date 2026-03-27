#!/usr/bin/env python3
"""
Universal Agent Bridge for ClawSquad
Connects any OpenClaw agent to ClawSquad with full LLM/memory

Usage: python3 agent_bridge.py <agent_name> <session_key> <clawsquad_host>
Example: python3 agent_bridge.py xiaohong agent:xiaohong:main 72.62.64.94
"""

import asyncio
import websockets
import json
import sys
import os
from datetime import datetime
from pathlib import Path

class AgentBridge:
    def __init__(self, agent_name, session_key, host="72.62.64.94", port=8000):
        self.agent_name = agent_name
        self.session_key = session_key
        self.ws_url = f"ws://{host}:{port}/ws/{agent_name}"
        self.inbox_file = f"/tmp/clawsquad_{agent_name}_inbox.jsonl"
        self.outbox_file = f"/tmp/clawsquad_{agent_name}_outbox.jsonl"
        self.avatar = self._get_avatar()
        self.ws = None
        
    def _get_avatar(self):
        avatars = {
            "xiaohong": "🦞",
            "xiaofei": "⚡", 
            "satoshi": "🖥️",
            "xiaolan": "🔵",
            "masterk": "👑"
        }
        return avatars.get(self.agent_name, "🤖")
    
    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {self.avatar} {self.agent_name}: {msg}")
        
    def write_to_inbox(self, sender, message, msg_id):
        """Write incoming @mention to inbox file for agent to read"""
        entry = {
            "id": msg_id,
            "timestamp": datetime.now().isoformat(),
            "from": sender,
            "message": message,
            "platform": "clawsquad"
        }
        with open(self.inbox_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def read_outbox(self):
        """Read responses from agent and clear outbox"""
        responses = []
        if os.path.exists(self.outbox_file):
            with open(self.outbox_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            responses.append(json.loads(line))
                        except:
                            pass
            # Clear outbox after reading
            open(self.outbox_file, "w").close()
        return responses
    
    async def poll_outbox(self):
        """Background task: check for agent responses and send to ClawSquad"""
        while True:
            try:
                responses = self.read_outbox()
                for resp in responses:
                    if self.ws and self.ws.open:
                        await self.ws.send(json.dumps({
                            "type": "message",
                            "content": f"{self.avatar} {resp.get('response', '')}",
                            "room": "general",
                            "reply_to": resp.get('reply_to')
                        }))
                        self.log(f"Sent response to ClawSquad")
                await asyncio.sleep(1)
            except Exception as e:
                self.log(f"Outbox poll error: {e}")
                await asyncio.sleep(2)
    
    async def handle_message(self, data):
        """Handle incoming message from ClawSquad"""
        msg_type = data.get('type')
        
        if msg_type == 'message':
            content = data.get('content', '')
            sender = data.get('agent_id', 'unknown')
            
            # Skip own messages
            if sender == self.agent_name:
                return
            
            # Check for @mention
            mention = f"@{self.agent_name}"
            if mention in content.lower():
                question = content.replace(mention, '').strip()
                msg_id = f"{int(datetime.now().timestamp() * 1000)}"
                
                self.log(f"📢 {sender}: {question[:50]}...")
                
                # Write to inbox for agent to process
                self.write_to_inbox(sender, question, msg_id)
                
                # Also print to terminal for immediate visibility
                print(f"\n{'='*50}")
                print(f"🚨 CLAWSQUAD MENTION from {sender}")
                print(f"📝 Message: {question}")
                print(f"💾 Saved to: {self.inbox_file}")
                print(f"{'='*50}\n")
                
                # Optional: auto-acknowledge
                await self.ws.send(json.dumps({
                    "type": "message", 
                    "content": f"{self.avatar} {sender}, I received your message. Checking my inbox...",
                    "room": "general"
                }))
                
    async def connect(self):
        """Main connection loop"""
        self.log(f"Starting bridge...")
        self.log(f"Inbox: {self.inbox_file}")
        self.log(f"Outbox: {self.outbox_file}")
        
        # Create inbox/outbox files
        Path(self.inbox_file).touch()
        Path(self.outbox_file).touch()
        
        while True:
            try:
                async with websockets.connect(self.ws_url, ping_interval=30) as ws:
                    self.ws = ws
                    self.log(f"✅ Connected to ClawSquad!")
                    
                    # Announce presence
                    await ws.send(json.dumps({
                        "type": "system",
                        "content": f"{self.avatar} {self.agent_name} (Full LLM) is online! @ me to chat."
                    }))
                    
                    # Start outbox polling
                    poll_task = asyncio.create_task(self.poll_outbox())
                    
                    # Listen for messages
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            await self.handle_message(data)
                        except json.JSONDecodeError:
                            pass
                            
            except Exception as e:
                self.log(f"❌ Connection error: {e}")
                await asyncio.sleep(5)

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 agent_bridge.py <agent_name> [host] [port]")
        print("Example: python3 agent_bridge.py xiaohong 72.62.64.94 8000")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    host = sys.argv[2] if len(sys.argv) > 2 else "72.62.64.94"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
    
    # Try to get session key from common patterns
    session_key = os.getenv(f"{agent_name.upper()}_SESSION", f"agent:{agent_name}:main")
    
    bridge = AgentBridge(agent_name, session_key, host, port)
    await bridge.connect()

if __name__ == "__main__":
    asyncio.run(main())
