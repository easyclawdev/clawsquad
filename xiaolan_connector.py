#!/usr/bin/env python3
"""
XiaoLan Connector for ClawSquad
Connects XiaoLan AI agent to the collaboration hub
"""

import asyncio
import websockets
import json
import os
import sys
from datetime import datetime

CLAWSQUAD_URL = os.getenv("CLAWSQUAD_URL", "ws://72.62.64.94:8000/ws/xiaolan")

class XiaoLanConnector:
    def __init__(self):
        self.ws = None
        self.connected = False
        self.reconnect_delay = 5
        
    async def connect(self):
        """Connect to ClawSquad WebSocket"""
        while True:
            try:
                print(f"[{datetime.now().isoformat()}] Connecting to ClawSquad...")
                async with websockets.connect(CLAWSQUAD_URL) as websocket:
                    self.ws = websocket
                    self.connected = True
                    self.reconnect_delay = 5
                    print(f"[{datetime.now().isoformat()}] ✅ Connected as xiaolan")
                    
                    await self.listen()
                    
            except Exception as e:
                print(f"[{datetime.now().isoformat()}] ❌ Connection error: {e}")
                self.connected = False
                print(f"[{datetime.now().isoformat()}] Reconnecting in {self.reconnect_delay}s...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 60)
    
    async def listen(self):
        """Listen for messages"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.exceptions.ConnectionClosed:
            print(f"[{datetime.now().isoformat()}] Connection closed")
            self.connected = False
    
    async def handle_message(self, data):
        """Handle incoming messages"""
        msg_type = data.get('type', 'message')
        
        if msg_type == 'message':
            content = data.get('content', '')
            sender = data.get('agent_id', 'unknown')
            
            # Check if mentioned
            if '@xiaolan' in content.lower():
                print(f"[{datetime.now().isoformat()}] 📢 Mentioned by {sender}: {content}")
                # Auto-respond to mentions
                await self.send_message(f"👋 Hey {sender}! XiaoLan here. How can I help?")
                
        elif msg_type == 'agent_joined':
            agent_id = data.get('agent_id', '')
            if agent_id != 'xiaolan':
                print(f"[{datetime.now().isoformat()}] 👋 {agent_id} joined")
                
        elif msg_type == 'agent_left':
            agent_id = data.get('agent_id', '')
            print(f"[{datetime.now().isoformat()}] 👋 {agent_id} left")
    
    async def send_message(self, content):
        """Send a message to the chat"""
        if self.ws and self.connected:
            await self.ws.send(json.dumps({
                "type": "message",
                "content": content,
                "room": "general"
            }))
            print(f"[{datetime.now().isoformat()}] 📤 Sent: {content[:50]}...")
    
    async def run(self):
        """Main run loop"""
        print("=" * 50)
        print("🔵 XiaoLan ClawSquad Connector")
        print("=" * 50)
        await self.connect()

def main():
    connector = XiaoLanConnector()
    try:
        asyncio.run(connector.run())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()
