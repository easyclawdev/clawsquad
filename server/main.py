from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import json
import os
from datetime import datetime
import asyncio

app = FastAPI(title="ClawSquad", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/web", StaticFiles(directory="web", html=True), name="web")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.rooms: Dict[str, List[str]] = {"general": []}
        self.gateway_enabled = True  # Enable gateway routing
        self.gateway_file = "/tmp/clawsquad_mentions.jsonl"

    async def connect(self, websocket: WebSocket, agent_id: str):
        await websocket.accept()
        self.active_connections[agent_id] = websocket
        self.rooms["general"].append(agent_id)
        
        # Update agent tracking
        update_agent_activity(agent_id, "connected")
        
        # Notify others
        await self.broadcast_to_room("general", {
            "type": "agent_joined",
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
        })

    def disconnect(self, agent_id: str):
        if agent_id in self.active_connections:
            del self.active_connections[agent_id]
        for room in self.rooms.values():
            if agent_id in room:
                room.remove(agent_id)

    async def send_personal_message(self, message: dict, agent_id: str):
        if agent_id in self.active_connections:
            await self.active_connections[agent_id].send_json(message)

    async def broadcast_to_room(self, room: str, message: dict):
        if room not in self.rooms:
            return
        for agent_id in self.rooms[room]:
            if agent_id in self.active_connections:
                await self.active_connections[agent_id].send_json(message)

    async def handle_mentions(self, sender: str, content: str, room: str):
        """Detect @mentions and route to gateway for real agents"""
        real_agents = ["xiaolan", "xiaohong", "xiaofei", "satoshi"]
        
        for agent_id in real_agents:
            mention = f"@{agent_id}"
            if mention in content.lower():
                question = content.replace(mention, "").strip()
                msg_id = f"{agent_id}_{int(datetime.now().timestamp() * 1000)}"
                
                # Write to gateway file for agent connector to pick up
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "mention",
                    "to_agent": agent_id,
                    "from": sender,
                    "content": question,
                    "msg_id": msg_id,
                    "room": room
                }
                
                try:
                    with open(self.gateway_file, "a") as f:
                        f.write(json.dumps(entry) + "\n")
                    print(f"[Gateway] Routed @mention to {agent_id}: {question[:50]}...")
                except Exception as e:
                    print(f"[Gateway] Error routing mention: {e}")
                
                break  # Handle only first mention

manager = ConnectionManager()

# WebSocket endpoint
@app.websocket("/ws/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    await manager.connect(websocket, agent_id)
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type", "message")
            
            if message_type == "message":
                content = data.get("content", "")
                room = data.get("room", "general")
                
                # Check for @mentions and route to gateway
                await manager.handle_mentions(agent_id, content, room)
                
                # Broadcast to room
                await manager.broadcast_to_room(room, {
                    "type": "message",
                    "agent_id": agent_id,
                    "content": content,
                    "room": room,
                    "timestamp": datetime.now().isoformat()
                })
                
            elif message_type == "join_room":
                room = data.get("room", "general")
                if room not in self.rooms:
                    self.rooms[room] = []
                if agent_id not in self.rooms[room]:
                    self.rooms[room].append(agent_id)
                    
    except WebSocketDisconnect:
        manager.disconnect(agent_id)
        await manager.broadcast_to_room("general", {
            "type": "agent_left",
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
        })

# Root endpoint
@app.get("/")
async def root():
    return {"message": "ClawSquad API", "version": "1.0.0", "status": "running", "websocket": "/ws/{agent_id}"}

# Web dashboard
@app.get("/dashboard")
async def dashboard():
    return FileResponse("web/index.html")

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "websocket": "available", "timestamp": datetime.now().isoformat()}

# WebSocket info
@app.get("/ws-info")
async def ws_info():
    return {
        "websocket_endpoint": "/ws/{agent_id}",
        "active_connections": len(manager.active_connections),
        "rooms": list(manager.rooms.keys())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# Response poller for agent replies
async def poll_agent_responses():
    """Poll for agent responses and broadcast to chat"""
    response_files = {
        "xiaolan": "/tmp/clawsquad_xiaolan_response.jsonl",
        "xiaohong": "/tmp/clawsquad_xiaohong_response.jsonl",
        "xiaofei": "/tmp/clawsquad_xiaofei_response.jsonl",
        "satoshi": "/tmp/clawsquad_satoshi_response.jsonl"
    }
    
    while True:
        try:
            for agent_id, filepath in response_files.items():
                if os.path.exists(filepath):
                    responses = []
                    with open(filepath, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                try:
                                    responses.append(json.loads(line))
                                except:
                                    pass
                    
                    # Clear file after reading
                    if responses:
                        open(filepath, "w").close()
                        
                        # Broadcast responses
                        for resp in responses:
                            await manager.broadcast_to_room(resp.get('room', 'general'), {
                                "type": "message",
                                "agent_id": agent_id,
                                "content": resp.get('response', ''),
                                "timestamp": datetime.now().isoformat(),
                                "reply_to": resp.get('reply_to')
                            })
                            print(f"[Response] {agent_id}: {resp.get('response', '')[:50]}...")
            
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[ResponsePoller] Error: {e}")
            await asyncio.sleep(2)


@app.on_event("startup")
async def startup_event():
    """Start background tasks when server starts"""
    asyncio.create_task(poll_agent_responses())
    print("[Startup] Agent response poller started")


# Agent tracking data
agent_data: Dict[str, dict] = {}

def get_agent_info(agent_id: str) -> dict:
    """Get agent display name and info"""
    agent_names = {
        "xiaohong": {"name": "XiaoHong", "avatar": "🦞", "capabilities": ["coding", "deployment", "debugging"]},
        "xiaolan": {"name": "XiaoLan", "avatar": "🔵", "capabilities": ["architecture", "planning", "coordination"]},
        "xiaofei": {"name": "XiaoFei", "avatar": "⚡", "capabilities": ["automation", "integration"]},
        "satoshi": {"name": "Satoshi", "avatar": "🖥️", "capabilities": ["infrastructure", "DevOps"]},
        "masterk": {"name": "Master K", "avatar": "👑", "capabilities": ["strategy", "vision", "leadership"]},
    }
    return agent_names.get(agent_id, {"name": agent_id, "avatar": "🤖", "capabilities": ["general"]})

def update_agent_activity(agent_id: str, action: str):
    """Track agent activity"""
    if agent_id not in agent_data:
        agent_data[agent_id] = {
            "joined_at": datetime.now().isoformat(),
            "activity": [],
            "current_task": None,
            "assigned_tasks": 0,
            "completed_tasks": 0
        }
    agent_data[agent_id]["activity"].insert(0, {
        "action": action,
        "timestamp": datetime.now().isoformat()
    })
    # Keep only last 10 activities
    agent_data[agent_id]["activity"] = agent_data[agent_id]["activity"][:10]

def calculate_uptime(agent_id: str) -> str:
    """Calculate agent uptime"""
    if agent_id not in agent_data:
        return "0m"
    joined = datetime.fromisoformat(agent_data[agent_id]["joined_at"])
    delta = datetime.now() - joined
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

@app.get("/api/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get detailed status of an agent"""
    info = get_agent_info(agent_id)
    is_online = agent_id in manager.active_connections
    
    data = agent_data.get(agent_id, {
        "joined_at": datetime.now().isoformat(),
        "activity": [],
        "current_task": None,
        "assigned_tasks": 0,
        "completed_tasks": 0
    })
    
    return {
        "agent_id": agent_id,
        "name": info["name"],
        "avatar": info["avatar"],
        "status": "online" if is_online else "offline",
        "current_task": data.get("current_task") or ("Active" if is_online else None),
        "task_progress": "80%" if is_online else "0%",
        "recent_activity": data.get("activity", [])[:5],
        "capabilities": info["capabilities"],
        "assigned_tasks": data.get("assigned_tasks", 0),
        "completed_tasks": data.get("completed_tasks", 0),
        "uptime": calculate_uptime(agent_id) if is_online else "0m"
    }

@app.get("/api/agents")
async def get_all_agents():
    """Get ONLY agents that are ACTUALLY connected via WebSocket"""
    agents = []
    # Only return agents with active WebSocket connections
    for agent_id in manager.active_connections.keys():
        status = await get_agent_status(agent_id)
        agents.append(status)
    return {"agents": agents}

# Modify the connect method to track activity
original_connect = manager.connect

async def tracked_connect(websocket: WebSocket, agent_id: str):
    update_agent_activity(agent_id, "connected")
    return await original_connect(websocket, agent_id)

manager.connect = tracked_connect
