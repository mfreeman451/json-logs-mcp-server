#!/usr/bin/env python3
"""
JSON Logs MCP Server - Local stdio Version
Save as: json_logs_mcp_server.py

This server analyzes JSON log files using stdio transport for local access.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import anyio
import click
import mcp.types as types
from mcp.server.lowlevel import Server
from pydantic import AnyUrl

# Configuration
LOG_DIR = "/Users/mfreeman/src/nco-mcp/logs"


class JsonLogAnalyzer:
    """Core class for analyzing JSON log files"""

    def __init__(self, log_directory: str = LOG_DIR):
        self.log_directory = Path(log_directory)
        self.log_files_cache = {}
        self._refresh_log_files()

    def _refresh_log_files(self):
        """Refresh the cache of available log files"""
        if not self.log_directory.exists():
            self.log_files_cache = {}
            return

        log_files = []
        for file_path in self.log_directory.glob("*.log*"):
            if file_path.is_file():
                stat = file_path.stat()
                log_files.append({
                    "path": str(file_path),
                    "name": file_path.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x["modified"], reverse=True)
        self.log_files_cache = {f["name"]: f for f in log_files}

    def get_log_files(self) -> List[Dict[str, Any]]:
        """Get list of available log files"""
        self._refresh_log_files()
        return list(self.log_files_cache.values())

    def parse_log_entry(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single JSON log line"""
        try:
            entry = json.loads(line.strip())
            # Validate required fields
            required_fields = ["timestamp", "level", "message", "module", "function", "line"]
            if all(field in entry for field in required_fields):
                # Parse timestamp for easier filtering
                entry["parsed_timestamp"] = datetime.fromisoformat(entry["timestamp"])
                return entry
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
        return None

    def read_log_file(self, filename: str, max_lines: Optional[int] = None) -> List[Dict[str, Any]]:
        """Read and parse a log file"""
        if filename not in self.log_files_cache:
            self._refresh_log_files()
            if filename not in self.log_files_cache:
                raise FileNotFoundError(f"Log file {filename} not found")

        file_path = Path(self.log_files_cache[filename]["path"])
        entries = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if max_lines and i >= max_lines:
                        break

                    entry = self.parse_log_entry(line)
                    if entry:
                        entries.append(entry)
        except Exception as e:
            raise RuntimeError(f"Error reading log file {filename}: {str(e)}")

        return entries

    def query_logs(self,
                   files: Optional[List[str]] = None,
                   level: Optional[str] = None,
                   module: Optional[str] = None,
                   function: Optional[str] = None,
                   message_contains: Optional[str] = None,
                   start_time: Optional[str] = None,
                   end_time: Optional[str] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """Query logs with various filters"""

        # Determine which files to search
        if files is None:
            files = list(self.log_files_cache.keys())

        all_entries = []
        for filename in files:
            try:
                entries = self.read_log_file(filename)
                all_entries.extend(entries)
            except (FileNotFoundError, RuntimeError):
                continue

        # Apply filters
        filtered_entries = []
        for entry in all_entries:
            # Level filter
            if level and entry.get("level", "").upper() != level.upper():
                continue

            # Module filter
            if module and entry.get("module", "") != module:
                continue

            # Function filter
            if function and entry.get("function", "") != function:
                continue

            # Message contains filter
            if message_contains and message_contains.lower() not in entry.get("message", "").lower():
                continue

            # Time range filters
            timestamp = entry.get("parsed_timestamp")
            if start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time)
                    if timestamp and timestamp < start_dt:
                        continue
                except ValueError:
                    pass

            if end_time:
                try:
                    end_dt = datetime.fromisoformat(end_time)
                    if timestamp and timestamp > end_dt:
                        continue
                except ValueError:
                    pass

            filtered_entries.append(entry)

        # Sort by timestamp (newest first) and limit
        filtered_entries.sort(key=lambda x: x.get("parsed_timestamp", datetime.min), reverse=True)
        return filtered_entries[:limit]

    def aggregate_logs(self,
                       files: Optional[List[str]] = None,
                       group_by: str = "level") -> Dict[str, Any]:
        """Aggregate log data by specified criteria"""

        if files is None:
            files = list(self.log_files_cache.keys())

        all_entries = []
        for filename in files:
            try:
                entries = self.read_log_file(filename)
                all_entries.extend(entries)
            except (FileNotFoundError, RuntimeError):
                continue

        # Group entries
        groups = {}
        for entry in all_entries:
            if group_by == "level":
                key = entry.get("level", "UNKNOWN")
            elif group_by == "module":
                key = entry.get("module", "UNKNOWN")
            elif group_by == "function":
                key = entry.get("function", "UNKNOWN")
            elif group_by == "hour":
                timestamp = entry.get("parsed_timestamp")
                if timestamp:
                    key = timestamp.strftime("%Y-%m-%d %H:00")
                else:
                    key = "UNKNOWN"
            else:
                key = entry.get(group_by, "UNKNOWN")

            if key not in groups:
                groups[key] = []
            groups[key].append(entry)

        # Calculate statistics
        result = {
            "group_by": group_by,
            "total_entries": len(all_entries),
            "groups": {}
        }

        for key, entries in groups.items():
            result["groups"][key] = {
                "count": len(entries),
                "percentage": round((len(entries) / len(all_entries)) * 100, 2) if all_entries else 0,
                "first_seen": min(
                    e.get("parsed_timestamp", datetime.max) for e in entries).isoformat() if entries else None,
                "last_seen": max(
                    e.get("parsed_timestamp", datetime.min) for e in entries).isoformat() if entries else None
            }

        return result

    def get_log_stats(self, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get overall statistics for log files"""
        if files is None:
            files = list(self.log_files_cache.keys())

        total_entries = 0
        levels = {}
        modules = set()
        functions = set()
        earliest_time = None
        latest_time = None

        for filename in files:
            try:
                entries = self.read_log_file(filename)
                total_entries += len(entries)

                for entry in entries:
                    # Count levels
                    level = entry.get("level", "UNKNOWN")
                    levels[level] = levels.get(level, 0) + 1

                    # Collect modules and functions
                    modules.add(entry.get("module", "UNKNOWN"))
                    functions.add(entry.get("function", "UNKNOWN"))

                    # Track time range
                    timestamp = entry.get("parsed_timestamp")
                    if timestamp:
                        if earliest_time is None or timestamp < earliest_time:
                            earliest_time = timestamp
                        if latest_time is None or timestamp > latest_time:
                            latest_time = timestamp

            except (FileNotFoundError, RuntimeError):
                continue

        return {
            "total_files": len(files),
            "total_entries": total_entries,
            "levels": levels,
            "unique_modules": sorted(list(modules)),
            "unique_functions": len(functions),
            "time_range": {
                "earliest": earliest_time.isoformat() if earliest_time else None,
                "latest": latest_time.isoformat() if latest_time else None,
                "span_hours": round((latest_time - earliest_time).total_seconds() / 3600,
                                    2) if earliest_time and latest_time else None
            }
        }


# Initialize the log analyzer
log_analyzer = JsonLogAnalyzer()


@click.command()
@click.option("--port", default=8000, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type",
)
def main(port: int, transport: str) -> int:
    """Run the JSON Logs MCP Server"""

    if transport == "stdio":
        print(f"🚀 Starting JSON Logs MCP Server with stdio transport...", file=sys.stderr)
        print(f"📁 Log directory: {log_analyzer.log_directory.absolute()}", file=sys.stderr)

        # Check if logs directory exists
        if not log_analyzer.log_directory.exists():
            print(f"⚠️  Warning: Logs directory '{log_analyzer.log_directory}' does not exist", file=sys.stderr)
            print("   Create it and add some .log files to get started", file=sys.stderr)
        else:
            log_files = log_analyzer.get_log_files()
            print(f"📄 Found {len(log_files)} log files", file=sys.stderr)

    # Create the MCP server
    app = Server("json-logs-mcp-server")

    @app.list_resources()
    async def list_resources() -> list[types.Resource]:
        """List available log files as resources"""
        log_files = log_analyzer.get_log_files()
        resources = []

        for log_file in log_files:
            resources.append(
                types.Resource(
                    uri=AnyUrl(f"logs://{log_file['name']}"),
                    name=f"Log file: {log_file['name']}",
                    description=f"Size: {log_file['size']} bytes, Modified: {log_file['modified']}",
                    mimeType="application/json"
                )
            )

        return resources

    @app.read_resource()
    async def read_resource(uri: AnyUrl) -> str:
        """Read a specific log file"""
        if uri.scheme != "logs":
            raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

        filename = uri.path.lstrip("/") if uri.path else ""
        if not filename:
            raise ValueError("No filename specified in URI")

        try:
            entries = log_analyzer.read_log_file(filename, max_lines=1000)
            # Remove parsed_timestamp for JSON serialization
            for entry in entries:
                entry.pop("parsed_timestamp", None)

            return json.dumps(entries, indent=2, default=str)
        except FileNotFoundError:
            raise ValueError(f"Log file not found: {filename}")

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List available tools"""
        return [
            types.Tool(
                name="query_logs",
                description="Search and filter log entries across log files",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Log files to search (default: all files)"
                        },
                        "level": {
                            "type": "string",
                            "description": "Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
                        },
                        "module": {
                            "type": "string",
                            "description": "Filter by module name"
                        },
                        "function": {
                            "type": "string",
                            "description": "Filter by function name"
                        },
                        "message_contains": {
                            "type": "string",
                            "description": "Filter by message content (case-insensitive)"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time filter (ISO format)"
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time filter (ISO format)"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 100,
                            "description": "Maximum number of results"
                        }
                    }
                }
            ),
            types.Tool(
                name="aggregate_logs",
                description="Aggregate log data by specified criteria",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Log files to analyze (default: all files)"
                        },
                        "group_by": {
                            "type": "string",
                            "enum": ["level", "module", "function", "hour"],
                            "default": "level",
                            "description": "Field to group by"
                        }
                    }
                }
            ),
            types.Tool(
                name="get_log_stats",
                description="Get overall statistics for log files",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Log files to analyze (default: all files)"
                        }
                    }
                }
            ),
            types.Tool(
                name="list_log_files",
                description="List available log files with metadata",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Handle tool calls"""
        try:
            if name == "query_logs":
                results = log_analyzer.query_logs(**arguments)
                # Remove parsed_timestamp for JSON serialization
                for entry in results:
                    entry.pop("parsed_timestamp", None)

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2, default=str)
                    )
                ]

            elif name == "aggregate_logs":
                results = log_analyzer.aggregate_logs(**arguments)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2, default=str)
                    )
                ]

            elif name == "get_log_stats":
                results = log_analyzer.get_log_stats(arguments.get("files"))
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2, default=str)
                    )
                ]

            elif name == "list_log_files":
                results = log_analyzer.get_log_files()
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2, default=str)
                    )
                ]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )
            ]

    # Set up transport
    if transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.responses import Response
        from starlette.routing import Mount, Route
        from starlette.middleware.cors import CORSMiddleware

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(
                    request.scope, request.receive, request._send
            ) as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )
            return Response()

        # Create Starlette app with CORS
        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        # Add CORS middleware
        starlette_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        print(f"🌐 Server starting at http://localhost:{port}")
        print(f"🔗 SSE endpoint: http://localhost:{port}/sse")
        print(f"📨 Messages endpoint: http://localhost:{port}/messages/")
        print(f"🔧 Use this URL in Claude Desktop: http://localhost:{port}/sse")

        import uvicorn
        uvicorn.run(starlette_app, host="0.0.0.0", port=port)
    else:
        # stdio transport (local)
        from mcp.server.stdio import stdio_server

        async def arun():
            async with stdio_server() as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        anyio.run(arun)

    return 0


if __name__ == "__main__":
    main()