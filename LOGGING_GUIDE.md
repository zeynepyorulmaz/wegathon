# 📊 Advanced Logging System

OpenSearch entegrasyonu ile profesyonel bir logging sistemi kurulmuştur. Bu sistem tüm log'ları merkezi bir yerde toplayıp analiz etmenizi sağlar.

## 🎯 Özellikler

### ✅ Kurulu Özellikler

1. **Structured Logging**: JSON formatında, query'lenebilir log'lar
2. **Request Tracing**: Her request için unique ID ve context tracking
3. **Performance Monitoring**: Automatic timing for functions and API calls
4. **Error Tracking**: Detaylı exception info ve stack traces
5. **OpenSearch Integration**: Real-time log shipping to OpenSearch
6. **Development-Friendly**: Renkli console output + production JSON logs
7. **Decorators**: Automatic logging with `@log_execution` and `@log_api_call`

### 📍 Log'lanan Yerler

#### Backend (Python)
- ✅ **HTTP Middleware**: Tüm request/response'lar otomatik log'lanır
- ✅ **Plan Generation**: Tüm aşamalar (parsing, AI calls, tool execution)
- ✅ **Tool Calls**: MCP API çağrıları (flight_search, hotel_search, vb.)
- ✅ **AI Responses**: Anthropic API çağrıları ve yanıt süreleri
- ✅ **Errors**: Tüm exception'lar detaylı context ile

## 🚀 Hızlı Başlangıç

### 1. Environment Variables Ekleyin

`.env` dosyanıza şunları ekleyin:

```bash
# Logging Configuration
LOG_LEVEL=INFO
ENABLE_OPENSEARCH_LOGGING=true
OPENSEARCH_URL=http://wegathon-opensearch.uzlas.com:2021
TEAM_NAME=wegathon

# Optional: File logging
ENABLE_FILE_LOGGING=false
LOG_DIR=logs
```

### 2. Backend'i Başlatın

```bash
cd python-backend
python -m uvicorn app.main:app --reload --port 4000
```

### 3. Test Edin

```bash
cd python-backend
python app/scripts/test_logging.py
```

### 4. OpenSearch'te Görüntüleyin

🔗 **Dashboard**: https://wegathon-opensearch.uzlas.com/app/home#/

**Credentials**:
- Username: `wegathon`
- Password: `H7jtlsg3Ibxc9C3q`

## 📖 Kullanım Örnekleri

### Basit Logging

```python
from app.core.logging import logger

logger.info("User logged in")
logger.warning("Rate limit approaching")
logger.error("Database connection failed")
```

### Structured Logging (Önerilen)

```python
logger.info(
    "Plan generation completed",
    extra={
        "event": "plan_generated",
        "duration_seconds": 12.5,
        "destination": "Paris",
        "num_days": 5,
        "has_flights": True
    }
)
```

### Context Tracking

```python
from app.core.logging import set_request_context

# Set context at request start
set_request_context(
    request_id="req-123",
    user_id="user-456",
    session_id="session-789"
)

# All subsequent logs will include this context
logger.info("Processing request")  # Will include request_id, user_id, session_id
```

### Function Decorator (Otomatik Timing)

```python
from app.utils.logging_decorators import log_execution

@log_execution(level="info", include_args=True)
async def process_plan(destination: str, days: int):
    # Function body
    return result

# Automatically logs:
# → app.services.planner.process_plan(destination='Paris', days=5)
# ← app.services.planner.process_plan completed in 234.56ms
```

### API Call Decorator

```python
from app.utils.logging_decorators import log_api_call

@log_api_call("MCP")
async def call_flight_search(params):
    # API call logic
    return response

# Automatically logs:
# 🌐 API Call to MCP: call_flight_search
# ✓ MCP API call completed in 1234.56ms
```

## 🔍 OpenSearch'te Log Arama

### Index Pattern
Log'larınız şu index pattern'de saklanır:
```
wegathon-*
```

### Örnek Queries

#### 1. Tüm Plan Generation İstekleri
```json
{
  "query": {
    "term": {
      "event": "plan_generation_started"
    }
  }
}
```

#### 2. Hata Log'ları
```json
{
  "query": {
    "term": {
      "level": "ERROR"
    }
  }
}
```

#### 3. Belirli Bir Session'ın Log'ları
```json
{
  "query": {
    "term": {
      "session_id": "your-session-id"
    }
  }
}
```

#### 4. Yavaş API Call'lar (>5 saniye)
```json
{
  "query": {
    "bool": {
      "must": [
        { "term": { "event": "tool_call_completed" } },
        { "range": { "duration_seconds": { "gte": 5 } } }
      ]
    }
  }
}
```

## 📊 Log Event Types

Sistemde kullanılan event type'lar:

### Request Lifecycle
- `request_started` - HTTP request başladı
- `request_completed` - HTTP request tamamlandı (status_code, duration_ms)
- `request_failed` - HTTP request hata verdi

### Plan Generation
- `plan_generation_started` - Plan oluşturma başladı
- `prompt_parsing_started` - Prompt parse ediliyor
- `prompt_parsing_completed` - Prompt parse edildi
- `prompt_parsing_failed` - Prompt parse hatası
- `plan_generation_completed` - Plan oluşturma tamamlandı (duration, num_days)

### AI Interactions
- `ai_turn_started` - AI turn başladı
- `ai_response_received` - AI yanıt verdi (stop_reason, duration)
- `ai_call_failed` - AI çağrısı başarısız
- `ai_plan_completed` - AI plan'ı tamamladı

### Tool Calls
- `tools_execution_started` - Tool'lar çalıştırılıyor (num_tools, tool_names)
- `tool_call_started` - Tek tool başladı (tool_name, tool_input)
- `tool_call_completed` - Tool tamamlandı (tool_name, duration, success)
- `tool_call_failed` - Tool hata verdi (tool_name, error)
- `tools_execution_completed` - Tüm tool'lar tamamlandı

### API Calls (External)
- `api_call_started` - External API çağrısı başladı
- `api_call_completed` - External API tamamlandı
- `api_call_failed` - External API hatası

## 🛠 Geliştirme İpuçları

### 1. Development vs Production

**Development** (renkli, okunabilir):
```bash
ENV=development
```

**Production** (JSON, machine-readable):
```bash
ENV=production
```

### 2. Log Level Ayarlama

```bash
# Debug seviyesi (çok detaylı)
LOG_LEVEL=DEBUG

# Info seviyesi (standart)
LOG_LEVEL=INFO

# Warning seviyesi (sadece uyarılar ve hatalar)
LOG_LEVEL=WARNING

# Error seviyesi (sadece hatalar)
LOG_LEVEL=ERROR
```

### 3. File Logging (Opsiyonel)

Local debugging için file logging aktif edilebilir:

```bash
ENABLE_FILE_LOGGING=true
LOG_DIR=logs
```

Bu şu dosyaları oluşturur:
- `logs/wegathon_YYYY-MM-DD.log` - Tüm log'lar
- `logs/wegathon_errors_YYYY-MM-DD.log` - Sadece error'lar (90 gün saklanır)

### 4. Session Tracking

Frontend'den session_id gönderebilirsiniz:

```typescript
// Header ile
headers: {
  'X-Session-ID': 'user-session-123'
}

// Query param ile
fetch('/api/plan?session_id=user-session-123')
```

Bu session_id tüm log'larda otomatik görünür ve arama kolaylaşır.

## 📈 Monitoring & Alerting

### Yararlı Metrikler

1. **Request Duration**
   - Field: `duration_ms`
   - Visualization: Histogram
   - Alert: >5000ms

2. **Error Rate**
   - Field: `level=ERROR`
   - Visualization: Time series
   - Alert: >5 errors/minute

3. **AI Response Time**
   - Field: `event=ai_response_received`, `duration_seconds`
   - Visualization: Percentiles (p50, p95, p99)
   - Alert: p95 >10s

4. **Tool Success Rate**
   - Field: `event=tool_call_completed`, `success=true/false`
   - Visualization: Pie chart
   - Alert: success rate <90%

### Örnek Dashboard Queries

#### Average Plan Generation Time
```json
{
  "aggs": {
    "avg_duration": {
      "avg": {
        "field": "extra.duration_seconds"
      }
    }
  },
  "query": {
    "term": {
      "event": "plan_generation_completed"
    }
  }
}
```

#### Tool Usage Distribution
```json
{
  "aggs": {
    "tool_distribution": {
      "terms": {
        "field": "extra.tool_name.keyword",
        "size": 10
      }
    }
  },
  "query": {
    "term": {
      "event": "tool_call_started"
    }
  }
}
```

## 🎨 Log Format

### Development Output
```
2025-10-04 15:23:45.123 | INFO     | app.services.planner:generate:950 | 🚀 Starting plan generation
```

### Production Output (JSON)
```json
{
  "@timestamp": "2025-10-04T15:23:45.123Z",
  "level": "INFO",
  "logger": "app.services.planner",
  "message": "🚀 Starting plan generation",
  "module": "planner",
  "function": "generate",
  "line": 950,
  "environment": "production",
  "service": "wegathon-backend",
  "request_id": "req-123",
  "session_id": "session-456",
  "extra": {
    "event": "plan_generation_started",
    "prompt_length": 156,
    "language": "tr",
    "currency": "TRY"
  }
}
```

## 🔧 Troubleshooting

### Log'lar OpenSearch'e Gitmiyor

1. Environment variables'ı kontrol edin:
```bash
echo $ENABLE_OPENSEARCH_LOGGING  # should be "true"
echo $OPENSEARCH_URL  # should be set
```

2. Network connectivity test:
```bash
curl http://wegathon-opensearch.uzlas.com:2021/teams-ingest-pipeline/ingest \
  -H "Content-Type: application/json" \
  -d '[{"team":"wegathon","user":"test","action":"test","message":"Hello"}]'
```

3. Backend log'larını kontrol edin:
```bash
# Başlangıçta şunu görmelisiniz:
# ✅ OpenSearch logging enabled: http://wegathon-opensearch.uzlas.com:2021 (team: wegathon)
```

### Log'lar Çok Fazla/Az

Log level'ı ayarlayın:
```bash
# Daha az log
LOG_LEVEL=WARNING

# Daha çok log
LOG_LEVEL=DEBUG
```

### Performance Impact

Logging async ve non-blocking şekilde çalışır, ancak:
- Production'da `LOG_LEVEL=INFO` önerilir (DEBUG çok detaylı)
- OpenSearch timeout'u düşüktür (5 saniye), log gönderimi başarısız olsa bile app çalışmaya devam eder

## 📚 Daha Fazla Bilgi

- **Loguru Documentation**: https://loguru.readthedocs.io/
- **OpenSearch Docs**: https://opensearch.org/docs/
- **FastAPI Middleware**: https://fastapi.tiangolo.com/tutorial/middleware/

---

**Hazırlayan**: AI Assistant  
**Tarih**: 2025-10-04  
**Versiyon**: 1.0

