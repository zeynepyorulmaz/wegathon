## Trip Prompt Parser API

FastAPI service that parses natural-language travel requests into structured JSON using a nano model (default OpenAI `gpt-4o-mini`). Swagger is available at `/docs`.

### Setup

1. Create `.env.local` with your keys:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=... # optional
LLM_PROVIDER=openai   # or anthropic
MODEL=gpt-4o-mini     # or claude-3-haiku
PROMPT_PATH=./prompt-parser.md
```

2. Install deps and run:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### API

- POST `/parse`

```json
{
  "input": "Eşimle 15 Ekim Berlin’e 3-4 gün gidelim, bütçe sonra.",
  "locale": "tr-TR"
}
```

Returns structured JSON per `prompt-parser.md` (lean schema, no metadata):

```json
{
  "departure": {"city": "İstanbul", "country": "TR", "detected": false},
  "destination": {"city": "Berlin", "country": "DE", "detected": true},
  "dates": {"start_date": "2025-10-15", "end_date": "2025-10-18", "duration": 4},
  "travelers": {"composition": "couple", "count": 2, "children": []},
  "budget": {"amount": null, "currency": "TRY", "per_person": false, "specified": false},
  "travel_style": {"type": "mid_range", "luxury_level": "mid_range", "tempo": "balanced"},
  "preferences": [],
  "special_occasions": []
}
```

Health check: GET `/health`

### Benchmark

Run 10 prompts concurrently and print a JSON summary:

```bash
python /Users/ilkeryoru/Desktop/wegathlon/scripts/parse_bench.py
```



