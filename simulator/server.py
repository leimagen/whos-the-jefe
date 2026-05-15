import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

INBOX_FILE = "simulator/inbox.json"

def load_inbox():
    if not os.path.exists(INBOX_FILE):
        return []
    with open(INBOX_FILE, "r") as f:
        return json.load(f)

def save_inbox(data):
    with open(INBOX_FILE, "w") as f:
        json.dump(data, f, indent=2)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/reactions":
            reactions = []
            if os.path.exists("simulator/reactions.json"):
                with open("simulator/reactions.json") as f:
                    reactions = json.load(f)
            with open("simulator/reactions.json", "w") as f:
                json.dump([], f)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(reactions).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        path = urlparse(self.path).path

        if path == "/api/inbox":
            save_inbox(body)
            self._respond({"ok": True})

        elif path == "/api/reply":
            replies = []
            if os.path.exists("simulator/replies.json"):
                with open("simulator/replies.json") as f:
                    replies = json.load(f)
            replies.append(body)
            with open("simulator/replies.json", "w") as f:
                json.dump(replies, f, indent=2)
            self._respond({"ok": True})

        elif path == "/api/reaction":
            reactions = []
            if os.path.exists("simulator/reactions.json"):
                with open("simulator/reactions.json") as f:
                    reactions = json.load(f)
            reactions.append(body)
            with open("simulator/reactions.json", "w") as f:
                json.dump(reactions, f, indent=2)
            self._respond({"ok": True})

        else:
            self.send_response(404)
            self.end_headers()

    def _respond(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

def run_server():
    server = HTTPServer(("localhost", 3001), Handler)
    print("API server running on http://localhost:3001")
    server.serve_forever()

if __name__ == "__main__":
    run_server()