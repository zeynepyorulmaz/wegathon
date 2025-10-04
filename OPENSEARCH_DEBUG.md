# 🔍 OpenSearch Logging Debug Rehberi

## 📊 Durum

✅ Backend çalışıyor (port 4000)
✅ OpenSearch ingest endpoint'i çalışıyor
❌ Log'lar OpenSearch dashboard'da görünmüyor

## 🔧 Çözüm Adımları

### 1. Backend'i Kontrol Edin

Backend'i başlattığınız terminalde şu mesajı görüyor musunuz?

```
✅ OpenSearch logging enabled: http://wegathon-opensearch.uzlas.com:2021 (team: wegathon)
```

**GÖRMÜYORSANIZ:**

`.env` dosyasını kontrol edin:
```bash
cd python-backend
cat .env | grep -A 5 "OpenSearch"
```

Şunları görmelisiniz:
```bash
ENABLE_OPENSEARCH_LOGGING=true
OPENSEARCH_URL=http://wegathon-opensearch.uzlas.com:2021
TEAM_NAME=wegathon
```

**Eksikse ekleyin:**
```bash
cat >> .env << 'EOF'

# OpenSearch Logging
LOG_LEVEL=INFO
ENABLE_OPENSEARCH_LOGGING=true
OPENSEARCH_URL=http://wegathon-opensearch.uzlas.com:2021
TEAM_NAME=wegathon
EOF
```

### 2. Backend'i Restart Edin

```bash
# Mevcut backend'i durdurun (Ctrl+C)
# Sonra yeniden başlatın:
./START_BACKEND.sh
```

### 3. Test İsteği Gönderin

```bash
curl -X POST http://localhost:4000/api/plan \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: debug-session-$(date +%s)" \
  -d '{
    "prompt": "İstanbul'dan Paris'e 3 günlük gezi",
    "language": "tr",
    "currency": "TRY"
  }'
```

### 4. Backend Log'larını Kontrol Edin

Backend terminalinde şöyle log'lar görmelisiniz:

```
📥 POST /api/plan
🚀 Starting plan generation
📝 Parsing user prompt
🔄 AI Turn 1/10
🔧 Executing 3 tool(s)
✅ flight_search completed in 2.34s
✅ Plan generated successfully in 15.67s
📤 POST /api/plan → 200 (15670.00ms)
```

### 5. OpenSearch'te Doğru Yere Bakın

OpenSearch Dashboard'da log'ları görmek için:

#### A. Dashboard URL'ini Kontrol Edin

**YANLIŞ** (Observability Logs - boş gelebilir):
```
https://wegathon-opensearch.uzlas.com/app/observability-logs#/
```

**DOĞRU** (Discover - tüm log'ları gösterir):
```
https://wegathon-opensearch.uzlas.com/app/discover#/
```

veya

```
https://wegathon-opensearch.uzlas.com/app/home#/
```

#### B. Index Pattern'i Ayarlayın

OpenSearch Dashboard'da:

1. Sol menüden **"Stack Management"** veya **"Management"** seçin
2. **"Index Patterns"** seçin
3. **"Create index pattern"** tıklayın
4. Index pattern name: `wegathon-*` veya `teams-*` (hangisi varsa)
5. Time field: `@timestamp` veya `timestamp`
6. Create!

#### C. Discover'da Log'ları Görün

1. Sol menüden **"Discover"** seçin
2. Üstten index pattern'i seçin: `wegathon-*` veya `teams-*`
3. Time range'i ayarlayın: **"Last 1 hour"** veya **"Today"**
4. Refresh!

### 6. Manuel Log Testi

Backend olmadan direkt log göndererek test edin:

```bash
curl -X POST "http://wegathon-opensearch.uzlas.com:2021/teams-ingest-pipeline/ingest" \
  -H "Content-Type: application/json" \
  -d '[{
    "team": "wegathon",
    "user": "manual-test",
    "action": "test",
    "message": "Manual test log",
    "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
  }]'
```

**Sonuç:**
- `200 OK` alırsanız: ✅ Log gönderildi
- Hata alırsanız: ❌ Bağlantı veya format sorunu

### 7. Alternatif: Backend Console Log'larını Kullanın

OpenSearch çalışmasa bile, backend console'da tüm log'ları görebilirsiniz:

**Development mode (.env):**
```bash
ENV=development
```

**Çıktı:**
```
2025-10-04 15:23:45.123 | INFO     | app.services.planner:generate:950 | 🚀 Starting plan generation
```

**Production mode (.env):**
```bash
ENV=production
```

**Çıktı (JSON):**
```json
{
  "@timestamp": "2025-10-04T15:23:45.123Z",
  "level": "INFO",
  "message": "🚀 Starting plan generation",
  "event": "plan_generation_started"
}
```

### 8. File Logging (Yedek Çözüm)

OpenSearch çalışmazsa, log'ları dosyaya yazabilirsiniz:

`.env` dosyasına ekleyin:
```bash
ENABLE_FILE_LOGGING=true
LOG_DIR=logs
```

Backend restart ettikten sonra:
```bash
cd python-backend
ls -lh logs/
tail -f logs/wegathon_$(date +%Y-%m-%d).log
```

## 🐛 Yaygın Sorunlar

### Problem 1: "OpenSearch logging enabled" mesajı görünmüyor

**Sebep:** Environment variables yüklenmemiş

**Çözüm:**
```bash
cd python-backend
source .env  # veya
export $(cat .env | xargs)
```

### Problem 2: Dashboard'da index pattern yok

**Sebep:** Henüz log gönderilmemiş veya farklı index'e gidiyor

**Çözüm:**
- Backend'den birkaç request gönderin
- 1-2 dakika bekleyin
- Index Patterns'ı yenileyin
- `teams-*` veya `wegathon-*` pattern'ini deneyin

### Problem 3: Log'lar console'da var ama OpenSearch'te yok

**Sebep:** OpenSearch async ve best-effort çalışır, network hatası olabilir

**Çözüm:**
```bash
# Backend log'larında şunu arayın:
grep "OpenSearch Error" logs/*.log

# veya console'da:
# [OpenSearch Error] Failed to send log: ...
```

### Problem 4: Time range yanlış

**Sebep:** OpenSearch time range çok dar veya geçmişte

**Çözüm:**
- Discover'da time picker'a tıklayın
- "Last 24 hours" veya "Today" seçin
- Veya "Absolute" seçip bugünün tarihini girin

## ✅ Başarı Kriterleri

Log'lar çalışıyorsa görecekleriniz:

1. **Backend Console:**
   ```
   ✅ OpenSearch logging enabled: http://...
   📥 POST /api/plan
   🚀 Starting plan generation
   ```

2. **OpenSearch Discover:**
   - Log entry'leri görünür
   - `team: "wegathon"` field'ı var
   - `message` field'ı okunabilir
   - `@timestamp` güncel

3. **Log Fields:**
   ```json
   {
     "team": "wegathon",
     "user": "system",
     "action": "plan_generation_started",
     "message": "🚀 Starting plan generation",
     "level": "INFO",
     "service": "wegathon-backend",
     "request_id": "...",
     "session_id": "..."
   }
   ```

## 📞 İletişim

Sorun devam ederse:
1. Backend terminal çıktısını screenshot alın
2. `.env` dosyasındaki logging ayarlarını kontrol edin
3. Manuel test log'u sonucunu kontrol edin (curl komutu)

---

**Son güncelleme:** 2025-10-04

