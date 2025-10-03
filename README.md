# 🌍 Comprehensive Travel Planner - WEGathon 2025

AI-powered travel planning system that thinks about your journey from every angle - flights, accommodation, weather, activities, culture, budget, and logistics.

## 🚀 What Makes This Special

Our travel planner doesn't just find flights and hotels. It creates **comprehensive, realistic, delightful travel plans** by considering:

- ✈️ **Smart Logistics**: Flight times, check-in/out schedules, realistic buffers, jet lag
- 🌤️ **Weather-Responsive Planning**: Indoor alternatives for rain, optimal timing for outdoor activities
- 💰 **Budget Optimization**: Balance cost vs. value, include free activities, suggest local spots
- 🎭 **Cultural Intelligence**: Local customs, best visiting times, authentic food recommendations
- ⏰ **Realistic Pacing**: Mix high/low energy activities, include rest time, avoid over-scheduling
- 🚇 **Local Transport**: Metro passes, walking distances, travel times between locations
- 💬 **Interactive Conversation** - Akıllıca sorular sorar ve eksik bilgileri toplar (YENİ!)

## 🏗️ Architecture

### Backend (Python/FastAPI)
- **Anthropic Claude** with MCP tool calling for intelligent planning
- **MCP Integration** for real-time flight, hotel, weather, and bus data
- **Comprehensive AI System Prompt** that ensures holistic travel thinking
- **Strict JSON Schema** for reliable frontend rendering

📁 `python-backend/` - See detailed documentation in [python-backend/README.md](python-backend/README.md)

## 🎯 Use Cases

1. **Quick Trip Planning**: "3 days in Barcelona from Istanbul, budget-friendly, loves food"
2. **Multi-City Tours**: "Istanbul → Cappadocia → Antalya, 1 week, 2 adults"
3. **Weather-Aware Planning**: Automatically suggests indoor activities for rainy days
4. **Budget Optimization**: "Find cheaper hotel but keep same activities"
5. **Activity Adjustments**: "Add more museum visits, less shopping"

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Anthropic API key
- Enuygun MCP API access

### Setup

```bash
cd python-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
uvicorn app.main:app --port 4000 --reload
```

### Test It

```bash
curl -X POST http://localhost:4000/api/plan \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "5 days in Paris from Istanbul, mid-budget, loves museums",
    "currency": "TRY",
    "language": "en"
  }'
```

## 🤖 How MCP Integration Works

The planner uses **Model Context Protocol (MCP)** with **dynamic tool discovery**:

### Dynamic Tool Discovery
- 🔍 **Auto-discovers ALL available tools** from MCP server at startup
- 🔄 **No code changes needed** when new tools are added to MCP server
- 📦 **Caches tools** for performance (refresh with `/api/tools/refresh`)
- 🎯 **Claude decides** which tools to call, when, and with what parameters

### Example Tools (automatically discovered):
1. **flight_search**: Finds flights and understands actual travel times
2. **hotel_search**: Recommends accommodation based on location, budget, ratings
3. **flight_weather_forecast**: Checks weather to adapt activity planning
4. **bus_search**: Finds intercity transport for multi-city trips
5. **...and any other tools** available on the MCP server!

### Testing Tools
```bash
# List all available tools
curl http://localhost:4000/api/tools

# Refresh tool cache
curl -X POST http://localhost:4000/api/tools/refresh
```

## 📊 Example Output

```json
{
  "summary": "5-day Paris adventure with museum visits, iconic landmarks, and authentic French cuisine...",
  "flights": {
    "outbound": { "segments": [...], "price": 2500, "currency": "TRY" },
    "inbound": { ... }
  },
  "lodging": {
    "selected": { "name": "Hotel Le Marais", "rating": 4.2, "neighborhood": "Marais" }
  },
  "weather": [
    { "dateISO": "2025-11-15", "highC": 14, "lowC": 8, "precipitationChance": 30 }
  ],
  "days": [
    {
      "dateISO": "2025-11-15",
      "blocks": [
        { "label": "morning", "items": [{ "type": "flight", "data": {...} }] },
        { "label": "afternoon", "items": [{ "type": "activity", "data": { "title": "Louvre Museum" } }] }
      ]
    }
  ],
  "pricing": {
    "breakdown": { "flights": 5000, "lodging": 3500, "activities": 1500 },
    "totalEstimated": 10500,
    "currency": "TRY"
  }
}
```

## 🔄 Revision Support

Update existing plans with natural language:

```bash
curl -X POST http://localhost:4000/api/revise \
  -H "Content-Type: application/json" \
  -d '{
    "planId": "2025-10-03T09:17:43.368314Z",
    "plan": { ... existing plan ... },
    "instruction": "find a cheaper hotel in a safe neighborhood"
  }'
```

The AI will:
1. Search for new hotels matching criteria
2. Adjust activities if hotel location changes
3. Update pricing breakdown
4. Maintain plan quality and coherence

## 📚 Documentation

- [Backend Documentation](python-backend/README.md)
- API Endpoints: `/api/plan`, `/api/revise`, `/api/ask_questions`

## 🛠️ Tech Stack

- **FastAPI** - Modern async Python web framework
- **Anthropic Claude 3.5 Sonnet** - Advanced AI with tool calling
- **MCP (Model Context Protocol)** - Real-world data integration
- **Pydantic** - Data validation and schema enforcement
- **httpx** - Async HTTP client

## 📄 License

MIT

---

**Built for WEGathon 2025** - Pushing the boundaries of AI-powered travel planning 🚀