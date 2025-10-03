# Trip Planner Backend (Python/FastAPI)

AI-powered trip planning service that generates complete, day-by-day itineraries with flights, hotels, activities, weather, and local transport.

## Features

- **🧠 Expert AI Planner**: Comprehensive travel planning that considers ALL aspects - logistics, weather, culture, budget, pacing, and preferences
- **🤖 Anthropic Claude with MCP Tools**: Advanced tool calling with flights, hotels, weather, and intercity transport
- **🌍 Holistic Travel Thinking**: 
  - Time-aware planning (jet lag, realistic buffers, check-in/out times)
  - Weather-responsive activities (indoor alternatives for rain, optimal timing for outdoor activities)
  - Budget optimization (value-based recommendations, free activities, local spots)
  - Cultural insights (local customs, food recommendations, best visiting times)
- **🔄 Intelligent Revisions**: Update plans with cascade awareness - changes propagate logically through the itinerary
- **📋 Strict JSON Contract**: Always returns valid `TripPlan` schema for frontend rendering
- **🛠️ MCP Integration**: Real-time data from Enuygun MCP server (flights, hotels, weather, buses)
- **💬 Chat Endpoint**: Ask questions and refine plans interactively

## Setup

### 1. Prerequisites
- Python 3.10+
- Virtual environment tool (venv)

### 2. Install Dependencies

```bash
cd python-backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment

Create `.env` file:

```bash
ENV=development
PORT=4000
CORS_ORIGINS=*

# Anthropic (primary LLM with tool calling)
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# MCP / Enuygun API
MCP_BASE_URL=https://mcp.enuygun.com
MCP_API_KEY=your_mcp_key_here

# Optional: OpenAI (if you want to switch LLMs)
OPENAI_API_KEY=sk-proj-your-openai-key
OPENAI_MODEL=gpt-4o-mini

# Optional: WEG proxy
WEG_BASE_URL=https://ai-server.enuygun.tech
WEG_API_KEY=your_weg_key
```

**Important**: Replace placeholder keys with your actual API keys from the WEGathon handbook.

### 4. Run Server

```bash
uvicorn app.main:app --port 4000 --host 0.0.0.0 --reload
```

Server will be available at `http://localhost:4000`

## API Endpoints

### `POST /api/plan`

Generate a new travel plan.

**Request:**
```json
{
  "prompt": "Istanbul to New York on 2025-11-15, return 2025-11-20, 1 adult",
  "currency": "TRY",
  "language": "en"
}
```

**Response:** Full `TripPlan` JSON with flights, hotels, weather, day-by-day itinerary, pricing.

### `POST /api/revise`

Revise an existing plan.

**Request:**
```json
{
  "planId": "2025-10-03T09:17:43.368314Z",
  "instruction": "find a cheaper hotel near Mitte"
}
```

**Response:** Updated `TripPlan` JSON.

### `POST /api/ask_questions`

Chat with the planner AI.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "What's the best time to visit New York?"}
  ]
}
```

**Response:**
```json
{
  "reply": "The best time to visit New York is in spring (April-June) or fall (September-November) when the weather is mild and the city is vibrant with outdoor activities."
}
```

### `GET /api/tools`

List all available MCP tools dynamically discovered from the server.

**Response:**
```json
{
  "count": 4,
  "tools": [
    {
      "name": "flight_search",
      "description": "Search for flights...",
      "parameters": ["origin", "destination", "departure_date", "return_date", "adults"]
    },
    {
      "name": "hotel_search",
      "description": "Search for hotels...",
      "parameters": ["destination_name", "check_in_date", "check_out_date", "adults"]
    }
  ]
}
```

### `POST /api/tools/refresh`

Clear the tools cache and fetch fresh tools from MCP server. Useful during development.

**Response:**
```json
{
  "success": true,
  "message": "Tools cache refreshed successfully",
  "count": 4,
  "tool_names": ["flight_search", "hotel_search", "flight_weather_forecast", "bus_search"]
}
```

## Architecture

- **FastAPI** for async HTTP server
- **Anthropic Claude** with tool use for LLM + MCP integration
- **Dynamic MCP Tool Discovery**: Automatically fetches and uses ALL available tools from MCP server
- **Tool Caching**: Tools are cached on first request for performance
- **Extensible**: New tools added to MCP server are automatically available without code changes
- **Pydantic** for strict JSON schema validation
- **Loguru** for structured logging
- **httpx** for async HTTP calls to MCP and LLMs

### Dynamic Tool Discovery

The planner **automatically discovers all available tools** from the MCP server at startup:

1. **First Request**: Calls `tools/list` on MCP server to get all available tools
2. **Schema Conversion**: Converts MCP tool schemas to Anthropic's format
3. **Caching**: Caches tools for performance (refresh with `/api/tools/refresh`)
4. **Execution**: Any tool from the server can be called dynamically by Claude
5. **Fallback**: Uses hardcoded tools if MCP server is unavailable

**Benefits:**
- ✅ No code changes needed when MCP adds new tools (e.g., restaurant search, activity booking)
- ✅ Always in sync with MCP server capabilities
- ✅ Easy to test and debug with `/api/tools` endpoint
- ✅ Graceful fallback to ensure system always works

## How It Works

### Planning Flow
1. **User Input**: Natural language prompt (e.g., "5 days in Paris from Istanbul, mid-budget, loves museums")
2. **AI Analysis**: Claude analyzes traveler needs, preferences, and constraints
3. **Tool Orchestration**: 
   - Searches flights to understand actual arrival/departure times
   - Finds hotels based on location, budget, and flight schedule
   - Checks weather to inform activity planning and packing suggestions
   - Searches intercity transport if multi-city trip
4. **Comprehensive Planning**:
   - Day 1: Arrival logistics + light activities (considers jet lag, check-in time)
   - Middle days: Balanced activities with realistic pacing, meal breaks, local transport
   - Last day: Checkout + departure logistics (considers flight time, luggage)
   - Weather adaptation: Indoor alternatives for rain, timing optimization for weather
   - Cultural insights: Local customs, best visiting times, food recommendations
5. **JSON Generation**: Complete `TripPlan` with flights, hotels, day-by-day itinerary, pricing, and metadata
6. **Normalization**: Ensures strict schema compliance for reliable frontend rendering

### Revision Flow
1. User requests changes (e.g., "cheaper hotel", "add more food activities")
2. Claude analyzes impact and decides if new tool calls needed
3. Applies changes with cascade awareness (hotel location change → activity adjustments)
4. Returns updated complete plan

## Development

### Running Tests
```bash
pytest
```

### Code Quality
```bash
ruff check .
black .
```

### Hot Reload
Server runs with `--reload` flag by default for development.

## Production Deployment

1. Set `ENV=production` in `.env`
2. Use a production ASGI server (e.g., Gunicorn with Uvicorn workers)
3. Set proper `CORS_ORIGINS` (comma-separated allowed origins)
4. Enable HTTPS
5. Configure rate limiting and API key rotation

## Troubleshomarks

- **401/403 errors**: Check your `ANTHROPIC_API_KEY` and `MCP_API_KEY` in `.env`
- **Empty tool responses**: MCP proxy may need authentication handshake; verify `MCP_BASE_URL` and proxy setup
- **Schema validation errors**: Ensure LLM response includes all required `TripPlan` fields; normalization layer should fill gaps

## License

MIT

