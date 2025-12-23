from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class MockLBSHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"\nReceived GET request for {self.path}")
        print(f"Headers: {self.headers}")
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        if self.path == "/api/lbs/health":
            response = {"status": "healthy", "version": "mock-1.0"}
        elif self.path == "/api/lbs/dashboard":
            response = {"total_load": 150.5, "message": "Mock Dashboard Data"}
        elif self.path == "/api/lbs/auth/me":
            response = {"user_id": "mock-user-123", "username": "mock_tester"}
        elif self.path == "/api/lbs/tasks":
            response = [{"id": 1, "title": "Mock Task 1", "due_date": "2023-12-25"}]
        else:
            response = {"error": "Not Found"}
            
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        print(f"\nReceived POST request for {self.path}")
        print(f"Headers: {self.headers}")
        
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        print(f"Body: {post_data.decode()}")

        self.send_response(201)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {"id": 999, "status": "created"}
        self.wfile.write(json.dumps(response).encode())

if __name__ == "__main__":
    server = HTTPServer(('localhost', 8100), MockLBSHandler)
    print("Starting Mock LBS Server on http://localhost:8100...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
