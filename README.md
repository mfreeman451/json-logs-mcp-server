# JSON Logs MCP Server

A Model Context Protocol (MCP) server that enables Claude Desktop (or any MCP client) to read and analyze JSON-formatted log files. This server provides tools for searching, filtering, aggregating, and analyzing structured log data.

## Features

- 📁 **Browse log files** - List and read JSON-formatted log files
- 🔍 **Search and filter** - Query logs by level, module, function, message content, and time range
- 📊 **Aggregate data** - Group and analyze logs by various criteria
- 📈 **Statistics** - Get comprehensive statistics about your log data
- 🚀 **Fast and efficient** - Optimized for handling large log files

## Prerequisites

- Python 3.11 or higher
- Claude Desktop (or another MCP client)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/mfreeman/json-logs-mcp-server.git
cd json-logs-mcp-server
```

2. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

4. Create the wrapper script:
```bash
cat > run-json-logs-server.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
exec python json_logs_mcp_server.py
EOF
chmod +x run-json-logs-server.sh
```

## Configuration

### Configure Log Directory

By default, the server looks for logs in the `./logs` directory relative to where it's run. You can change this by setting an environment variable or editing the code:

**Option 1: Environment Variable**
```bash
export MCP_JSON_LOGS_DIR="/path/to/your/logs"
```

### Configure Claude Desktop

Add the server to your Claude Desktop configuration file:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "json-logs": {
      "command": "/absolute/path/to/run-json-logs-server.sh",
      "args": [],
      "env": {
        "MCP_JSON_LOGS_DIR": "/path/to/your/logs"
      }
    }
  }
}
```

**Important**: Use the absolute path to the wrapper script.

## Log Format

The server expects JSON log files with one JSON object per line. Each log entry should include these fields:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "INFO",
  "message": "User authentication successful",
  "module": "auth.handler",
  "function": "authenticate_user",
  "line": 42
}
```

### Required Fields:
- `timestamp` - ISO format timestamp
- `level` - Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `message` - Log message
- `module` - Module name
- `function` - Function name
- `line` - Line number

### Sample Log File

Create a file named `example.log` with the following content to test the server:

```json
{"timestamp": "2024-01-15T10:30:45.123456", "level": "INFO", "message": "Application started successfully", "module": "main", "function": "startup", "line": 15}
{"timestamp": "2024-01-15T10:30:46.234567", "level": "DEBUG", "message": "Loading configuration from config.json", "module": "config.loader", "function": "load_config", "line": 42}
{"timestamp": "2024-01-15T10:30:47.345678", "level": "INFO", "message": "Database connection established", "module": "db.connection", "function": "connect", "line": 78}
{"timestamp": "2024-01-15T10:31:02.456789", "level": "WARNING", "message": "Rate limit approaching: 85% of quota used", "module": "api.ratelimit", "function": "check_limits", "line": 156}
{"timestamp": "2024-01-15T10:32:15.567890", "level": "ERROR", "message": "Failed to authenticate user: Invalid credentials", "module": "auth.handler", "function": "authenticate_user", "line": 203}
{"timestamp": "2024-01-15T10:32:16.678901", "level": "INFO", "message": "Retry attempt 1/3 for user authentication", "module": "auth.handler", "function": "retry_auth", "line": 215}
{"timestamp": "2024-01-15T10:33:45.789012", "level": "CRITICAL", "message": "Database connection lost: Connection timeout", "module": "db.connection", "function": "health_check", "line": 92}
{"timestamp": "2024-01-15T10:33:46.890123", "level": "INFO", "message": "Attempting database reconnection", "module": "db.connection", "function": "reconnect", "line": 105}
{"timestamp": "2024-01-15T10:33:48.901234", "level": "INFO", "message": "Database connection restored", "module": "db.connection", "function": "reconnect", "line": 112}
{"timestamp": "2024-01-15T10:35:22.012345", "level": "DEBUG", "message": "Cache hit for key: user_session_abc123", "module": "cache.manager", "function": "get", "line": 67}
```

### Python Logger Configuration Example

Here's how to configure a Python logger to output in the required format:

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        return json.dumps(log_obj)

# Configure logger
logger = logging.getLogger()
handler = logging.FileHandler('app.log')
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Example usage
logger.info("Application started")
logger.error("Something went wrong")
```

## Available Tools

### 1. list_log_files
Lists all available log files with metadata.

**Example usage in Claude:**
- "List all log files"
- "Show me available logs"

### 2. query_logs
Search and filter log entries.

**Parameters:**
- `files` - List of files to search (optional, defaults to all)
- `level` - Filter by log level
- `module` - Filter by module name
- `function` - Filter by function name
- `message_contains` - Search in message content
- `start_time` - Start time filter (ISO format)
- `end_time` - End time filter (ISO format)
- `limit` - Maximum results (default: 100)

**Example usage in Claude:**
- "Show me all ERROR logs from today"
- "Find logs containing 'database connection'"
- "Show errors from the auth module in the last hour"
- "Search for authentication failures"

### 3. aggregate_logs
Aggregate log data by specified criteria.

**Parameters:**
- `files` - Files to analyze (optional)
- `group_by` - Grouping criteria: "level", "module", "function", or "hour"

**Example usage in Claude:**
- "Group logs by level"
- "Show me which modules generate the most logs"
- "Analyze log distribution by hour"
- "What's the breakdown of log levels?"

### 4. get_log_stats
Get comprehensive statistics about log files.

**Example usage in Claude:**
- "Show me log statistics"
- "What's the overall summary of my logs?"
- "How many errors do I have total?"

## Usage Examples

Once configured, you can interact with your logs through Claude Desktop:

### Example 1: Finding Errors
```
You: "Show me all ERROR and CRITICAL logs from the last hour"
Claude: I'll search for ERROR and CRITICAL level logs from the last hour...
[Uses query_logs tool with level and time filters]
```

### Example 2: Analyzing Patterns
```
You: "Which module is generating the most warnings?"
Claude: Let me analyze the distribution of WARNING logs by module...
[Uses query_logs with level filter, then aggregate_logs grouped by module]
```

### Example 3: Debugging Issues
```
You: "Find all database connection errors and show me what happened right before them"
Claude: I'll search for database connection errors and their context...
[Uses query_logs to find specific errors and surrounding log entries]
```

## Running Standalone

You can also run the server standalone for testing (MCP Inspector or other MCP clients):

```bash
# With stdio transport (default)
python json_logs_mcp_server.py
```

## Troubleshooting

### Server won't start
- Check that Python 3.8+ is installed: `python3 --version`
- Ensure all dependencies are installed: `pip install -e .`
- Verify the log directory exists and contains `.log` files

### "spawn python ENOENT" error
- Use `python3` instead of `python` in your configuration
- Use the wrapper script with the full absolute path
- Check that the wrapper script is executable: `chmod +x run-json-logs-server.sh`

### "Module not found" errors
- Make sure you're using the wrapper script that activates the virtual environment
- Check that dependencies are installed in the venv: `source .venv/bin/activate && pip list`
- Reinstall dependencies: `pip install -e .`

### No logs found
- Verify log files exist in the configured directory
- Check that log files have `.log` extension (files matching `*.log*` are found)
- Ensure log files are in the correct JSON format (one JSON object per line)
- Try with the sample log file provided above

### Tools not appearing in Claude
- Restart Claude Desktop after configuration changes
- Check the "Connect Apps" section in Claude Desktop
- Look for error messages in Claude's developer console
- Ensure the server shows as "Connected" in Claude's UI

### Debugging tips
- Run the server manually to see any error messages: `./run-json-logs-server.sh`
- Check server output: When running via stdio, diagnostic messages appear on stderr
- Test with a simple log file first using the sample data above
- Verify JSON format: Each line must be valid JSON with all required fields

## Performance Considerations

- The server loads log files on-demand, not all at once
- Large log files (>100MB) may take a moment to process
- Use the `limit` parameter in queries to control result size
- Consider rotating log files to maintain performance

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details
