#!/usr/bin/env python3
"""Simple webhook server to receive Notion automation triggers"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Read the webhook payload
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        print(f"\n[{self.log_date_time_string()}] Webhook received")
        
        try:
            payload = json.loads(post_data)
            print(f"Payload: {json.dumps(payload, indent=2)}")
        except:
            print("No JSON payload")
        
        # Run the sync script
        print("\nRunning sync script...")
        result = subprocess.run(
            ['python3', '/Users/divijrakhra/.openclaw/workspace/projects/personal-site/sync-from-notion.py'],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print(f"Errors: {result.stderr}")
        
        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'success'}).encode())
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")

if __name__ == '__main__':
    server = HTTPServer(('localhost', 8765), WebhookHandler)
    print("Webhook server running on http://localhost:8765")
    print("Waiting for Notion automation triggers...")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
