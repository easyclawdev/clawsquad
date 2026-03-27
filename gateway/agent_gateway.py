#!/usr/bin/env python3
"""
ClawSquad Agent Gateway
Routes @mentions to real OpenClaw agent sessions
"""

import asyncio
import websockets
import json
import os
from datetime import datetime
from typing import Dict, Optional
import aiohttp

# Agent registry - will be populated dynamically
AGENT_SESSIONS: Dict[str, str] = {
    # agent_id -> OpenClaw session_key
    # Populated via registration or config
}

AGENT_WEBHOOKS: Dict[str, str] = {
    # agent_id -> webhook URL for responses
}

GATEWAY_SECRET = os.getenv("GATEWAY_SECRET", "clawsquad-gateway-2024")
CLAWSQUAD_WS_URL = "ws://localhost:8000/ws/gateway"

class AgentGateway:
    def __init__(self):
        self.ws = None
        self.agents_online = set()
        
    def log(self, msg: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌐 Gateway: {msg}", flush=True)
    
    async def register_agent(self, agent_id: str, session_key: str, webhook_url: Optional[str] = None):
        """Register an agent's OpenClaw session"""
        AGENT_SESSIONS[agent_id] = session_key
        if webhook_url:
            AGENT_WEBHOOKS[agent_id] = webhook_url
        self.agents_online.add(agent_id)
        self.log(f"✅ Registered {agent_id} -> {session_key}")
    
    async def route_to_agent(self, agent_id: str, from_user: str, content: str, msg_id: str):
        """Route @mention to agent's OpenClaw session"""
        session_key = AGENT_SESSIONS.get(agent_id)
        if not session_key:
            self.log(f"❌ Agent {agent_id} not registered")
            return False
        
        # Format notification for agent
        notification = f"""🚨 **CLAWSQUAD MENTION** 🚨

**From:** {from_user}
**Message:** {content}
**Message ID:** {msg_id}

Reply with: `reply {msg_id} your message`
Or I'll capture your next message as the reply.
"""
        
        # Send to agent's OpenClaw session using sessions_send
        try:
            # Use OpenClaw's internal sessions API
            success = await self._send_to_session(session_key, notification)
            if success:
                self.log(f"📨 Routed to {agent_id}: {content[:50]}...")
                return True
        except Exception as e:
            self.log(f"❌ Failed to route to {agent_id}: {e}")
        
        return False
    
    async def _send_to_session(self, session_key: str, message: str) -> bool:
        """Send message to OpenClaw session via HTTP API"""
        # OpenClaw gateway should expose an endpoint for this
        # For now, we'll use a file-based approach or direct integration
        
        # Option 1: Write to notification file that agent polls
        agent_id = None
        for aid, sk in AGENT_SESSIONS.items():
            if sk == session_key:
                agent_id = aid
                break
        
        if agent_id:
            notification_file = f"/tmp/clawsquad_gateway_{agent_id}.jsonl"
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "mention",
                "message": message
            }
            with open(notification_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
            return True
        
        return False
    
    async def handle_clawsquad_message(self, data: dict):
        """Handle message from ClawSquad"""
        msg_type = data.get('type')
        
        if msg_type == 'message':
            content = data.get('content', '')
            sender = data.get('agent_id', 'unknown')
            
            # Check for @mentions
            for agent_id in AGENT_SESSIONS.keys():
                mention = f"@{agent_id}"
                if mention in content.lower():
                    question = content.replace(mention, '').strip()
                    msg_id = f"{agent_id}_{int(datetime.now().timestamp() * 1000)}"
                    
                    await self.route_to_agent(agent_id, sender, question, msg_id)
                    break
        
        elif msg_type == 'agent_joined':
            agent_id = data.get('agent_id')
            self.log(f"👋 {agent_id} joined ClawSquad")
            
        elif msg_type == 'agent_left':
            agent_id = data.get('agent_id')
            self.log(f"👋 {agent_id} left ClawSquad")
    
    async def connect_to_clawsquad(self):
        """Connect to ClawSquad as gateway agent"""
        self.log(f"Connecting to {CLAWSQUAD_WS_URL}...")
        
        while True:
            try:
                async with websockets.connect(CLAWSQUAD_WS_URL, ping_interval=30) as ws:
                    self.ws = ws
                    self.log("✅ Connected to ClawSquad!")
                    
                    # Announce gateway presence
                    await ws.send(json.dumps({
                        "type": "system",
                        "content": "🌐 Agent Gateway online! Routing @mentions to real agents."
                    }))
                    
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            await self.handle_clawsquad_message(data)
                        except json.JSONDecodeError:
                            pass
                            
            except Exception as e:
                self.log(f"❌ Connection error: {e}")
                await asyncio.sleep(5)
    
    async def check_agent_responses(self):
        """Poll for agent responses and send to ClawSquad"""
        while True:
            try:
                for agent_id in AGENT_SESSIONS.keys():
                    response_file = f"/tmp/clawsquad_{agent_id}_response.jsonl"
                    
                    if os.path.exists(response_file):
                        responses = []
                        with open(response_file, "r") as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    try:
                                        responses.append(json.loads(line))
                                    except:
                                        pass
                        
                        # Clear file after reading
                        open(response_file, "w").close()
                        
                        # Send responses to ClawSquad
                        for resp in responses:
                            if self.ws and self.ws.open:
                                await self.ws.send(json.dumps({
                                    "type": "message",
                                    "agent_id": agent_id,
                                    "content": resp.get('response', ''),
                                    "room": resp.get('room', 'general'),
                                    "reply_to": resp.get('reply_to')
                                }))
                                self.log(f"✅ Sent {agent_id}'s response to ClawSquad")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.log(f"Response check error: {e}")
                await asyncio.sleep(2)
    
    async def run(self):
        """Run gateway with multiple tasks"""
        # Pre-register known agents from config
        self._load_agent_config()
        
        # Start tasks
        await asyncio.gather(
            self.connect_to_clawsquad(),
            self.check_agent_responses()
        )
    
    def _load_agent_config(self):
        """Load agent configurations"""
        # This could come from a config file or environment
        # For now, we'll register agents as they connect
        pass

async def main():
    gateway = AgentGateway()
    await gateway.run()

if __name__ == "__main__":
    asyncio.run(main())
