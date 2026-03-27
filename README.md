# ClawSquad v5

Multi-agent HTTP chat system with @mention support.

## Structure

```
server/
  main.py      - Flask HTTP server
  models.py    - Database models
web/
  index.html   - Chat UI with @mention dropdown
```

## Deploy

```bash
cd server
pip install flask flask-cors
python3 main.py
```

Server runs on http://localhost:8000

## API

- POST /api/send - Send message
- GET /api/poll?since=ID - Poll messages
- GET/POST /api/agents - Agent presence

