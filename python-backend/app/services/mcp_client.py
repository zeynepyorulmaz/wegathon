"""
MCP (Model Context Protocol) Client Implementation
Handles full MCP lifecycle: initialize, tools/list, tools/call
"""
import httpx
import json
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logging import logger

class MCPClient:
    """
    Full MCP client with session management and protocol handling.
    Supports the MCP proxy architecture used by Enuygun.
    """
    
    def __init__(self):
        self.session_initialized = False
        self.capabilities: Dict[str, Any] = {}
        self.server_info: Dict[str, Any] = {}
        self.rpc_id = 1
        self.session_id: Optional[str] = None  # Will be set after initialization
        
    def _get_next_id(self) -> int:
        """Get next JSON-RPC ID."""
        current = self.rpc_id
        self.rpc_id += 1
        return current
    
    def _parse_sse_response(self, text: str) -> Dict[str, Any]:
        """
        Parse Server-Sent Events (SSE) format response.
        Format: 
          event: message
          data: {"jsonrpc":"2.0",...}
        """
        lines = text.strip().split('\n')
        data_line = None
        
        for line in lines:
            if line.startswith('data:'):
                data_line = line[5:].strip()  # Remove 'data:' prefix
                break
        
        if data_line:
            try:
                return json.loads(data_line)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse SSE data: {e}")
                return {}
        
        return {}
    
    def _get_url(self) -> str:
        """Build MCP URL with proxy parameters."""
        base = settings.mcp_base_url.rstrip("/")
        # MCP proxy requires target URL as query parameter
        return f"{base}/mcp?url=https://mcp.enuygun.com/mcp&transportType=streamable-http"
    
    def _get_headers(self) -> Dict[str, str]:
        """Build MCP request headers."""
        headers = {
            "Content-Type": "application/json",
            "accept": "application/json, text/event-stream",
            "authorization": "123Bearer",  # Enuygun MCP proxy format
            "x-mcp-proxy-auth": f"Bearer {settings.mcp_api_key}",
            "mcp-protocol-version": "2025-06-18"
        }
        
        # Add session ID if available
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        
        return headers
    
    async def initialize(self) -> bool:
        """
        Initialize MCP session with handshake.
        Must be called before any tools/list or tools/call.
        """
        if self.session_initialized:
            return True
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "wegathon-travel-planner",
                    "version": "1.0.0"
                }
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"🔄 Initializing MCP session...")
                logger.info(f"   URL: {self._get_url()}")
                logger.info(f"   Headers: {self._get_headers()}")
                response = await client.post(
                    self._get_url(),
                    json=payload,
                    headers=self._get_headers()
                )
                logger.info(f"   Status: {response.status_code}")
                logger.info(f"   Response text (first 500 chars): {response.text[:500]}")
                response.raise_for_status()
                
                # Try to extract session ID from response headers
                if "mcp-session-id" in response.headers:
                    self.session_id = response.headers["mcp-session-id"]
                    logger.info(f"   Got session ID from headers: {self.session_id}")
                
                # Parse SSE format response
                data = self._parse_sse_response(response.text)
                
                if "result" in data:
                    result = data["result"]
                    self.capabilities = result.get("capabilities", {})
                    self.server_info = result.get("serverInfo", {})
                    self.session_initialized = True
                    logger.info(f"✅ MCP session initialized: {self.server_info}")
                    logger.info(f"   Session ID: {self.session_id}")
                    
                    # Send initialized notification
                    await self._send_initialized()
                    return True
                elif "error" in data:
                    logger.error(f"❌ MCP initialize error: {data['error']}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ MCP initialize failed: {e}")
            return False
        
        return False
    
    async def _send_initialized(self):
        """Send initialized notification after successful initialize."""
        payload = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    self._get_url(),
                    json=payload,
                    headers=self._get_headers()
                )
        except Exception as e:
            logger.warning(f"⚠️  Failed to send initialized notification: {e}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from MCP server.
        Returns list of tool definitions in MCP format.
        """
        if not self.session_initialized:
            if not await self.initialize():
                logger.error("❌ Cannot list tools: MCP session not initialized")
                return []
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/list",
            "params": {}
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("📋 Fetching tools from MCP server...")
                response = await client.post(
                    self._get_url(),
                    json=payload,
                    headers=self._get_headers()
                )
                logger.info(f"   tools/list Status: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"   tools/list Response: {response.text[:500]}")
                response.raise_for_status()
                data = self._parse_sse_response(response.text)
                
                if "result" in data:
                    result = data["result"]
                    tools = result.get("tools", [])
                    logger.info(f"✅ Got {len(tools)} tools: {[t.get('name') for t in tools]}")
                    return tools
                elif "error" in data:
                    logger.error(f"❌ MCP tools/list error: {data['error']}")
                    return []
                    
        except Exception as e:
            logger.error(f"❌ MCP tools/list failed: {e}")
            return []
        
        return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool with arguments.
        Returns the tool's result or error.
        """
        if not self.session_initialized:
            if not await self.initialize():
                logger.error("❌ Cannot call tool: MCP session not initialized")
                return {"error": "MCP session not initialized"}
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"🔧 Calling MCP tool: {tool_name}")
                response = await client.post(
                    self._get_url(),
                    json=payload,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = self._parse_sse_response(response.text)
                
                if "result" in data:
                    logger.info(f"✅ Tool {tool_name} succeeded")
                    return data["result"]
                elif "error" in data:
                    logger.error(f"❌ Tool {tool_name} error: {data['error']}")
                    return {"error": data["error"]}
                    
        except Exception as e:
            logger.error(f"❌ Tool {tool_name} call failed: {e}")
            return {"error": str(e)}
        
        return {"error": "Unknown error"}


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None

def get_mcp_client() -> MCPClient:
    """Get or create global MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client

