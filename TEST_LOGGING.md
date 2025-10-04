# 🧪 Logging Test Rehberi

## ✅ Hazırlık (Tamamlandı!)

`.env` dosyasına şu satırlar eklendi:
```bash
LOG_LEVEL=INFO
ENABLE_OPENSEARCH_LOGGING=true
OPENSEARCH_URL=http://wegathon-opensearch.uzlas.com:2021
TEAM_NAME=wegathon
```

## 🚀 Test Adımları

### 1. Backend'i Restart Edin

```bash
cd /Users/zeynepyorulmaz/wegathon
./START_BACKEND.sh
```

Başlangıçta şu mesajı görmelisiniz:
```
✅ OpenSearch logging enabled: http://wegathon-opensearch.uzlas.com:2021 (team: wegathon)
```

### 2. Frontend'den İstek Gönderin

**Seçenek A: Mevcut UI'dan**
1. Frontend'i başlatın: `./START_FRONTEND.sh`
2. http://localhost:3000 adresini açın
3. Normal bir plan isteği gönderin (örn: "İstanbul'dan Paris'e 5 günlük gezi")

**Seçenek B: API ile Direkt Test**
```bash
curl -X POST http://localhost:4000/api/plan \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: test-session-123" \
  -d '{
    "prompt": "İstanbul'dan Paris'e 5 günlük gezi",
    "language": "tr",
    "currency": "TRY"
  }'
```

### 3. Log'ları OpenSearch'te Görüntüleyin

🔗 **Dashboard**: https://wegathon-opensearch.uzlas.com/app/home#/

**Login Bilgileri:**
- Username: `wegathon`
- Password: `H7jtlsg3Ibxc9C3q`

**Index Pattern**: `wegathon-*`

### 4. Log'ları Filtreleyin

Dashboard'da şu filtrelerle arayabilirsiniz:

#### a) Session ID ile
```
session_id: "test-session-123"
```

#### b) Event Type ile
```
event: "plan_generation_started"
event: "tool_call_completed"
event: "request_completed"
```

#### c) Log Level ile
```
level: "ERROR"
level: "INFO"
```

#### d) Yavaş Request'ler (>5 saniye)
```
extra.duration_seconds: >5
```

## 📊 Göreceğiniz Log'lar

### HTTP Request Log'ları
```json
{
  "message": "📥 POST /api/plan",
  "event": "request_started",
  "method": "POST",
  "path": "/api/plan",
  "request_id": "abc-123",
  "session_id": "test-session-123"
}

{
  "message": "📤 POST /api/plan → 200 (12345.67ms)",
  "event": "request_completed",
  "status_code": 200,
  "duration_ms": 12345.67
}
```

### Plan Generation Log'ları
```json
{
  "message": "🚀 Starting plan generation",
  "event": "plan_generation_started",
  "prompt_length": 45,
  "language": "tr",
  "currency": "TRY"
}

{
  "message": "📝 Parsing user prompt",
  "event": "prompt_parsing_started"
}

{
  "message": "✅ Prompt parsed successfully: Paris for 5 days",
  "event": "prompt_parsing_completed",
  "destination": "Paris",
  "duration": 5
}
```

### AI & Tool Call Log'ları
```json
{
  "message": "🔄 AI Turn 1/10",
  "event": "ai_turn_started"
}

{
  "message": "🔧 Executing 3 tool(s)",
  "event": "tools_execution_started",
  "tool_names": ["flight_search", "hotel_search", "weather_forecast"]
}

{
  "message": "✅ flight_search completed in 2.34s",
  "event": "tool_call_completed",
  "tool_name": "flight_search",
  "duration_seconds": 2.34,
  "success": true
}

{
  "message": "✅ Plan generated successfully in 15.67s",
  "event": "plan_generation_completed",
  "duration_seconds": 15.67,
  "num_days": 5,
  "has_flights": true
}
```

## 🔍 Örnek OpenSearch Query'leri

### Discover Tab'de KQL Query'leri

1. **Tüm plan generation'ları bul:**
   ```
   event: "plan_generation_started"
   ```

2. **Başarısız request'ler:**
   ```
   event: "request_failed" OR level: "ERROR"
   ```

3. **Belirli bir session'ın tüm log'ları:**
   ```
   session_id: "test-session-123"
   ```

4. **Yavaş tool call'lar (>3 saniye):**
   ```
   event: "tool_call_completed" AND extra.duration_seconds > 3
   ```

5. **Son 1 saat içindeki hatalar:**
   ```
   level: "ERROR" AND @timestamp >= now-1h
   ```

## 📈 Dashboard Önerileri

### 1. Request Performance Dashboard
- Metric: Average `duration_ms` for `request_completed`
- Time Series: Request count per minute
- Pie Chart: Status code distribution

### 2. Plan Generation Dashboard
- Metric: Average `duration_seconds` for `plan_generation_completed`
- Bar Chart: Tool usage distribution
- Line Chart: Success rate over time

### 3. Error Monitoring Dashboard
- Count: `level: "ERROR"` per time bucket
- Table: Recent errors with details
- Alert: >10 errors in 5 minutes

## 🎯 Ne Göreceksiniz?

✅ **Her HTTP request** - method, path, duration, status
✅ **Plan generation aşamaları** - parsing, AI calls, tool execution
✅ **Tool call detayları** - hangi tool çağrıldı, ne kadar sürdü, başarılı mı
✅ **AI response times** - her turn ne kadar sürdü
✅ **Errors & warnings** - detaylı exception bilgisi
✅ **Session tracking** - aynı session'daki tüm log'lar birbirine bağlı

## 💡 Pro Tips

1. **Session ID kullanın**: Frontend'den her request'te `X-Session-ID` header'ı gönderin
2. **Event type'lara göre filtreleyin**: `event` field'ı en önemli filtre
3. **Time range ayarlayın**: Son 15 dakika, son 1 saat gibi
4. **Save search**: Sık kullandığınız query'leri kaydedin
5. **Create visualizations**: Metriklerinizi görselleştirin

## 🐛 Troubleshooting

### Log'lar görünmüyor?
1. Backend log'larında şunu kontrol edin:
   ```
   ✅ OpenSearch logging enabled
   ```

2. Environment variables doğru mu?
   ```bash
   echo $ENABLE_OPENSEARCH_LOGGING  # true olmalı
   ```

3. Network erişimi test edin:
   ```bash
   curl -X POST http://wegathon-opensearch.uzlas.com:2021/teams-ingest-pipeline/ingest \
     -H "Content-Type: application/json" \
     -d '[{"team":"wegathon","user":"test","action":"test","message":"Hello"}]'
   ```

### Console'da log var ama OpenSearch'te yok?
- OpenSearch async ve best-effort çalışır
- Network hatası veya timeout olabilir
- Backend log'larına bakın: `[OpenSearch Error]` mesajı var mı?

### Log'lar çok fazla?
```bash
# .env dosyasında log level'ı yükseltin
LOG_LEVEL=WARNING  # Sadece warning ve error'ları log'lar
```

---

**Hazırlayan**: AI Assistant  
**Tarih**: 2025-10-04
