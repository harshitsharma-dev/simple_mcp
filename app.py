from flask import Flask, request, jsonify, Response
import json
import uuid
import threading
import time
from datetime import datetime
import requests
import math
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class MCPServer:
    def __init__(self):
        self.tools = {}
        self.resources = {}
        self.prompts = {}
        self.sessions = {}
        self.capabilities = {
            "tools": {},
            "resources": {},
            "prompts": {},
            "experimental": {}
        }
        self._register_default_tools()
        self._register_default_resources()

    def _register_default_tools(self):
        """Register default tools for the MCP server"""
        self.register_tool("calculator", {
            "name": "calculator",
            "description": "Perform mathematical calculations",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide", "power", "sqrt"],
                        "description": "Mathematical operation to perform"
                    },
                    "a": {
                        "type": "number",
                        "description": "First number"
                    },
                    "b": {
                        "type": "number",
                        "description": "Second number (not required for sqrt)",
                        "optional": True
                    }
                },
                "required": ["operation", "a"]
            }
        }, self._calculator_handler)

        self.register_tool("get_current_time", {
            "name": "get_current_time",
            "description": "Get the current date and time",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone (optional, defaults to UTC)",
                        "optional": True
                    }
                }
            }
        }, self._time_handler)

        self.register_tool("weather_info", {
            "name": "weather_info",
            "description": "Get weather information for a city",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name to get weather for"
                    },
                    "country": {
                        "type": "string",
                        "description": "Country code (optional)",
                        "optional": True
                    }
                },
                "required": ["city"]
            }
        }, self._weather_handler)

    def _register_default_resources(self):
        """Register default resources for the MCP server"""
        self.register_resource("server_info", {
            "uri": "mcp://server/info",
            "name": "Server Information",
            "description": "Information about this MCP server",
            "mimeType": "application/json"
        }, self._server_info_handler)

    def register_tool(self, name: str, schema: Dict, handler):
        """Register a tool with the MCP server"""
        self.tools[name] = {
            "schema": schema,
            "handler": handler
        }
        self.capabilities["tools"][name] = schema

    def register_resource(self, name: str, schema: Dict, handler):
        """Register a resource with the MCP server"""
        self.resources[name] = {
            "schema": schema,
            "handler": handler
        }
        self.capabilities["resources"][name] = schema

    def _calculator_handler(self, params: Dict) -> Dict:
        """Handle calculator tool requests"""
        try:
            operation = params.get("operation")
            a = float(params.get("a", 0))
            b = float(params.get("b", 0))

            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                if b == 0:
                    return {"error": "Division by zero is not allowed"}
                result = a / b
            elif operation == "power":
                result = a ** b
            elif operation == "sqrt":
                if a < 0:
                    return {"error": "Square root of negative number is not allowed"}
                result = math.sqrt(a)
            else:
                return {"error": f"Unknown operation: {operation}"}

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Result: {result}"
                    }
                ],
                "isError": False
            }
        except Exception as e:
            return {"error": str(e)}

    def _time_handler(self, params: Dict) -> Dict:
        """Handle time tool requests"""
        try:
            current_time = datetime.now()
            timezone = params.get("timezone", "UTC")
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Current time ({timezone}): {current_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ],
                "isError": False
            }
        except Exception as e:
            return {"error": str(e)}

    def _weather_handler(self, params: Dict) -> Dict:
        """Handle weather tool requests (mock implementation)"""
        try:
            city = params.get("city", "Unknown")
            country = params.get("country", "")
            
            # Mock weather data (in real implementation, you'd call a weather API)
            mock_weather = {
                "temperature": "22°C",
                "condition": "Partly cloudy",
                "humidity": "65%",
                "wind": "10 km/h"
            }
            
            location = f"{city}, {country}" if country else city
            weather_text = f"Weather in {location}:\n"
            weather_text += f"Temperature: {mock_weather['temperature']}\n"
            weather_text += f"Condition: {mock_weather['condition']}\n"
            weather_text += f"Humidity: {mock_weather['humidity']}\n"
            weather_text += f"Wind: {mock_weather['wind']}"
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": weather_text
                    }
                ],
                "isError": False
            }
        except Exception as e:
            return {"error": str(e)}

    def _server_info_handler(self, params: Dict) -> Dict:
        """Handle server info resource requests"""
        server_info = {
            "name": "Flask MCP Server",
            "version": "1.0.0",
            "description": "A Flask-based Model Context Protocol server",
            "capabilities": list(self.capabilities["tools"].keys()),
            "uptime": time.time(),
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "contents": [
                {
                    "uri": "mcp://server/info",
                    "mimeType": "application/json",
                    "text": json.dumps(server_info, indent=2)
                }
            ]
        }

# Initialize MCP server
mcp_server = MCPServer()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/mcp/initialize', methods=['POST'])
def initialize():
    """Initialize MCP connection"""
    try:
        data = request.get_json()
        session_id = str(uuid.uuid4())
        
        mcp_server.sessions[session_id] = {
            "clientInfo": data.get("clientInfo", {}),
            "created": datetime.now().isoformat()
        }
        
        response = {
            "protocolVersion": "2024-11-05",
            "capabilities": mcp_server.capabilities,
            "serverInfo": {
                "name": "Flask MCP Server",
                "version": "1.0.0"
            },
            "sessionId": session_id
        }
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Initialize error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/mcp/tools/list', methods=['POST'])
def list_tools():
    """List available tools"""
    try:
        tools = []
        for name, tool_data in mcp_server.tools.items():
            tools.append(tool_data["schema"])
        
        return jsonify({"tools": tools})
    except Exception as e:
        logger.error(f"List tools error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/mcp/tools/call', methods=['POST'])
def call_tool():
    """Call a specific tool"""
    try:
        data = request.get_json()
        tool_name = data.get("name")
        arguments = data.get("arguments", {})
        
        if tool_name not in mcp_server.tools:
            return jsonify({"error": f"Tool '{tool_name}' not found"}), 404
        
        handler = mcp_server.tools[tool_name]["handler"]
        result = handler(arguments)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Tool call error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/mcp/resources/list', methods=['POST'])
def list_resources():
    """List available resources"""
    try:
        resources = []
        for name, resource_data in mcp_server.resources.items():
            resources.append(resource_data["schema"])
        
        return jsonify({"resources": resources})
    except Exception as e:
        logger.error(f"List resources error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/mcp/resources/read', methods=['POST'])
def read_resource():
    """Read a specific resource"""
    try:
        data = request.get_json()
        uri = data.get("uri")
        
        # Find resource by URI
        resource_handler = None
        for name, resource_data in mcp_server.resources.items():
            if resource_data["schema"]["uri"] == uri:
                resource_handler = resource_data["handler"]
                break
        
        if not resource_handler:
            return jsonify({"error": f"Resource with URI '{uri}' not found"}), 404
        
        result = resource_handler({})
        return jsonify(result)
    except Exception as e:
        logger.error(f"Resource read error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/mcp/ping', methods=['POST'])
def ping():
    """Ping endpoint for keepalive"""
    return jsonify({"pong": True, "timestamp": datetime.now().isoformat()})

# CORS headers for web clients
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

if __name__ == '__main__':
    # For local development
    app.run(debug=True, host='0.0.0.0', port=5000)
