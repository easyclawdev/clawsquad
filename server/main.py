from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Dict
from datetime import datetime

app = FastAPI(title='ClawSquad', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, agent_id: str):
        await websocket.accept()
        self.active_connections[agent_id] = websocket
    
    def disconnect(self, agent_id: str):
        if agent_id in self.active_connections:
            del self.active_connections[agent_id]
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket('/ws/{agent_id}')
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    await manager.connect(websocket, agent_id)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast({
                'type': 'message',
                'agent_id': agent_id,
                'content': data.get('content', ''),
                'timestamp': datetime.now().isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(agent_id)

@app.get('/api/agents')
async def get_agents():
    return [{'agent_id': k, 'status': 'online'} for k in manager.active_connections.keys()]

@app.get('/')
async def root():
    return {'message': 'ClawSquad API', 'version': '1.0.0'}

# Serve static files
app.mount('/', StaticFiles(directory='web', html=True), name='static')
