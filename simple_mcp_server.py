#!/usr/bin/env python3
"""
Minimal debug server to see exactly what Claude Desktop is sending
Save as: debug_server.py
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import json

app = FastAPI()

# Very permissive CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_everything(request: Request, call_next):
    print("\n" + "=" * 80)
    print(f"🔍 REQUEST: {request.method} {request.url}")
    print(f"📋 Headers:")
    for name, value in request.headers.items():
        print(f"   {name}: {value}")

    # Try to read body
    body = b""
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if body:
                print(f"📦 Body ({len(body)} bytes):")
                try:
                    # Try to parse as JSON for pretty printing
                    json_body = json.loads(body.decode())
                    print(json.dumps(json_body, indent=2))
                except:
                    # If not JSON, print raw
                    print(body.decode()[:500] + ("..." if len(body) > 500 else ""))
        except Exception as e:
            print(f"❌ Error reading body: {e}")

    print("=" * 80)

    # Create a new request object with the body
    from starlette.requests import Request as StarletteRequest
    scope = request.scope.copy()

    async def receive():
        return {"type": "http.request", "body": body}

    new_request = StarletteRequest(scope, receive)

    response = await call_next(new_request)

    print(f"📤 RESPONSE: {response.status_code}")
    print("=" * 80 + "\n")

    return response


@app.get("/")
async def root():
    return {"status": "Debug server running", "message": "Check console for request logs"}


@app.get("/mcp")
async def mcp_get():
    return {
        "message": "MCP Debug Server",
        "status": "running",
        "note": "All requests are logged to console"
    }


@app.post("/mcp")
async def mcp_post(request: Request):
    """Handle MCP requests with detailed logging"""

    try:
        body = await request.body()
        if not body:
            return JSONResponse(
                status_code=400,
                content={"error": "Empty request body"}
            )

        # Parse JSON
        try:
            data = json.loads(body.decode())
        except json.JSONDecodeError as e:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid JSON: {e}"}
            )

        print(f"🎯 Parsed MCP request: {data.get('method', 'unknown')}")

        # Basic MCP response
        method = data.get("method", "")
        request_id = data.get("id")

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "resources": {},
                        "tools": {},
                        "prompts": {}
                    },
                    "serverInfo": {
                        "name": "debug-server",
                        "version": "1.0.0"
                    }
                }
            }
        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "test_tool",
                            "description": "A test tool for debugging",
                            "inputSchema": {
                                "type": "object",
                                "properties": {}
                            }
                        }
                    ]
                }
            }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"message": f"Received {method} - check server logs"}
            }

        print(f"📨 Sending response for {method}")
        return JSONResponse(content=response)

    except Exception as e:
        print(f"❌ Error processing MCP request: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
        )


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def catch_all(request: Request, path: str):
    """Catch all other requests"""
    return JSONResponse(
        content={
            "message": f"Caught request to /{path}",
            "method": request.method,
            "note": "Check server console for full details"
        }
    )


if __name__ == "__main__":
    print("🐛 Starting Debug Server...")
    print("📍 URL for Claude Desktop: http://localhost:8001/mcp")
    print("🔍 This server logs ALL requests - check console output")
    print("📋 Use this to see exactly what Claude Desktop sends")
    print("\nTo test manually:")
    print(
        "curl -X POST http://localhost:8001/mcp -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\"}'")
    print("\n" + "=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")