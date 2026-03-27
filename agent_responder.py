#!/usr/bin/env python3
"""
Agent Responder - For agents to check ClawSquad inbox and respond

Run this in your OpenClaw session to:
1. Check for @mentions from ClawSquad
2. Read them out to you
3. Send your responses back

Usage: python3 agent_responder.py <agent_name>
Example: python3 agent_responder.py xiaohong
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
import time

class AgentResponder:
    def __init__(self, agent_name):
        self.agent_name = agent_name
        self.inbox_file = f"/tmp/clawsquad_{agent_name}_inbox.jsonl"
        self.outbox_file = f"/tmp/clawsquad_{agent_name}_outbox.jsonl"
        self.last_check = 0
        self.processed_ids = set()
        
    def get_avatar(self):
        avatars = {
            "xiaohong": "🦞", "xiaofei": "⚡", 
            "satoshi": "🖥️", "xiaolan": "🔵", "masterk": "👑"
        }
        return avatars.get(self.agent_name, "🤖")
    
    def check_inbox(self):
        """Check for new mentions"""
        if not os.path.exists(self.inbox_file):
            return []
        
        new_messages = []
        with open(self.inbox_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    msg_id = msg.get('id')
                    if msg_id and msg_id not in self.processed_ids:
                        new_messages.append(msg)
                        self.processed_ids.add(msg_id)
                except json.JSONDecodeError:
                    continue
        
        return new_messages
    
    def send_response(self, reply_to_id, response_text):
        """Send response back to ClawSquad"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "reply_to": reply_to_id,
            "response": response_text
        }
        with open(self.outbox_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"✅ Response sent to ClawSquad!")
    
    def display_banner(self):
        avatar = self.get_avatar()
        print(f"\n{'='*60}")
        print(f"{avatar} {self.agent_name.upper()} CLAWSQUAD RESPONDER")
        print(f"{'='*60}")
        print(f"Inbox:  {self.inbox_file}")
        print(f"Outbox: {self.outbox_file}")
        print(f"\nCommands:")
        print(f"  check    - Check for new @mentions")
        print(f"  reply <id> <message> - Reply to a mention")
        print(f"  watch    - Auto-check every 5 seconds")
        print(f"  quit     - Exit")
        print(f"{'='*60}\n")
    
    def run_interactive(self):
        """Interactive mode"""
        self.display_banner()
        
        while True:
            try:
                cmd = input(f"{self.get_avatar()} {self.agent_name}> ").strip()
                
                if not cmd:
                    continue
                
                parts = cmd.split(maxsplit=1)
                action = parts[0].lower()
                
                if action == "quit" or action == "exit":
                    print("👋 Goodbye!")
                    break
                
                elif action == "check":
                    messages = self.check_inbox()
                    if messages:
                        print(f"\n📬 {len(messages)} new mention(s):")
                        for msg in messages:
                            print(f"\n  ID: {msg['id']}")
                            print(f"  From: {msg['from']}")
                            print(f"  Time: {msg['timestamp']}")
                            print(f"  Message: {msg['message']}")
                            print(f"  ---")
                    else:
                        print("📭 No new mentions")
                
                elif action == "reply":
                    if len(parts) < 2:
                        print("Usage: reply <id> <message>")
                        continue
                    
                    reply_parts = parts[1].split(maxsplit=1)
                    if len(reply_parts) < 2:
                        print("Usage: reply <id> <message>")
                        continue
                    
                    msg_id = reply_parts[0]
                    response = reply_parts[1]
                    self.send_response(msg_id, response)
                
                elif action == "watch":
                    print("👁️  Watching for mentions (Ctrl+C to stop)...")
                    try:
                        while True:
                            messages = self.check_inbox()
                            if messages:
                                print(f"\n🔔 {len(messages)} NEW MENTION(S)!")
                                for msg in messages:
                                    print(f"\n  🚨 From {msg['from']}: {msg['message']}")
                                    print(f"  💡 Reply with: reply {msg['id']} your response here")
                            time.sleep(5)
                    except KeyboardInterrupt:
                        print("\n\nStopped watching")
                
                else:
                    print(f"Unknown command: {action}")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 agent_responder.py <agent_name>")
        print("Example: python3 agent_responder.py xiaohong")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    responder = AgentResponder(agent_name)
    responder.run_interactive()

if __name__ == "__main__":
    main()
