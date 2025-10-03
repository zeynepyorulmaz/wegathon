# 💬 Interactive Conversation System

Kullanıcılardan eksik seyahat bilgilerini toplamak için konversasyonel bir sistem.

## 🎯 Özellikler

- ✅ **Akıllı Prompt Parsing** - Kullanıcının girdiğinden bilgi çıkarır
- ✅ **Eksik Bilgi Tespiti** - MCP araçları için gerekli alan kontrolü
- ✅ **Çok Dilli Destek** - Türkçe ve İngilizce sorular
- ✅ **Session Management** - Konuşma durumu takibi
- ✅ **Otomatik Tamamlama** - Eksik tarih/süre hesaplamaları

## 📊 API Akışı

### 1. Prompt Validation
```bash
POST /api/plan/validate
```

**Request:**
```json
{
  "prompt": "Paris'e gitmek istiyorum",
  "language": "tr"
}
```

**Response (Eksik bilgi varsa):**
```json
{
  "ready_to_plan": false,
  "message": "I need some more information...",
  "question": {
    "field": "origin",
    "question": "Nereden seyahat edeceksiniz?",
    "type": "text",
    "example": "İstanbul"
  },
  "session_id": "uuid-here",
  "collected_so_far": {"adults": 1},
  "remaining_questions": 2
}
```

**Response (Tüm bilgi mevcut):**
```json
{
  "ready_to_plan": true,
  "message": "Ready to create your travel plan!",
  "collected_data": {
    "origin": "Istanbul",
    "destination": "Paris",
    "start_date": "15.11.2025",
    "adults": 1
  },
  "session_id": null
}
```

### 2. Answer Questions
```bash
POST /api/plan/answer
```

**Request:**
```json
{
  "session_id": "uuid-from-step-1",
  "answer": "Istanbul"
}
```

**Response:**
```json
{
  "ready_to_plan": false,
  "message": "Got it! One more question:",
  "question": {
    "field": "start_date",
    "question": "When would you like to start?",
    "type": "date",
    "example": "15.11.2025"
  },
  "session_id": "same-uuid",
  "collected_so_far": {"origin": "Istanbul", "adults": 1},
  "remaining_questions": 1
}
```

Tüm sorular cevaplandığında:
```json
{
  "ready_to_plan": true,
  "message": "Perfect! Ready to create your plan!",
  "collected_data": {
    "origin": "Istanbul",
    "destination": "Paris",
    "start_date": "15.11.2025",
    "duration": 3,
    "adults": 1
  },
  "session_id": "uuid",
  "remaining_questions": 0
}
```

### 3. Create Plan
```bash
POST /api/plan/create
```

**Request:**
```json
{
  "session_id": "uuid-from-previous-steps",
  "language": "en",
  "currency": "EUR"
}
```

**Response:** Full `TripPlan` JSON

## 🔄 Tam Akış Örneği

```bash
# 1. Validate prompt
curl -X POST http://localhost:4000/api/plan/validate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"I want to visit Paris","language":"en"}'
# Returns: session_id + first question

# 2. Answer question 1
curl -X POST http://localhost:4000/api/plan/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<uuid>","answer":"Istanbul"}'
# Returns: next question

# 3. Answer question 2
curl -X POST http://localhost:4000/api/plan/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<uuid>","answer":"15.11.2025"}'
# Returns: ready_to_plan=true

# 4. Create plan
curl -X POST http://localhost:4000/api/plan/create \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<uuid>","language":"en","currency":"EUR"}'
# Returns: Full TripPlan
```

## 📝 Parsed Fields

| Field | Description | Example |
|-------|-------------|---------|
| `origin` | Departure city | "Istanbul", "IST" |
| `destination` | Arrival city | "Paris", "CDG" |
| `start_date` | Trip start | "15.11.2025", "2025-11-15" |
| `end_date` | Trip end | "18.11.2025" |
| `duration` | Length in days | 3 |
| `adults` | Number of adults | 1 |

## 🧠 Smart Features

### Auto-extraction
Prompt'tan otomatik çıkarma:
- Cities: "from Istanbul to Paris"
- Dates: "15.11.2025", "November 15"
- Duration: "3 days", "3 gün"
- People: "2 adults", "1 kişi"

### Auto-completion
Eksik bilgileri hesaplama:
- `start_date` + `duration` → `end_date`
- `start_date` + `end_date` → `duration`
- Missing `adults` → defaults to 1

### Multi-language
Questions adapt to language:
- EN: "Where are you traveling from?"
- TR: "Nereden seyahat edeceksiniz?"

## 🎨 Frontend Integration

```javascript
// 1. Validate prompt
const response = await fetch('/api/plan/validate', {
  method: 'POST',
  body: JSON.stringify({ prompt: userInput, language: 'en' })
});

const data = await response.json();

if (data.ready_to_plan) {
  // Skip to plan creation
  createPlan(data.collected_data);
} else {
  // Show question to user
  showQuestion(data.question);
  sessionId = data.session_id;
}

// 2. Submit answers
async function submitAnswer(answer) {
  const response = await fetch('/api/plan/answer', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, answer })
  });
  
  const data = await response.json();
  
  if (data.ready_to_plan) {
    // All info collected, create plan
    createPlan(sessionId);
  } else {
    // Show next question
    showQuestion(data.question);
  }
}

// 3. Create plan
async function createPlan(sessionId) {
  const response = await fetch('/api/plan/create', {
    method: 'POST',
    body: JSON.stringify({ 
      session_id: sessionId, 
      language: 'en', 
      currency: 'EUR' 
    })
  });
  
  const plan = await response.json();
  displayPlan(plan);
}
```

## 🔒 Session Management

Sessions are stored in-memory (use Redis/DB in production):
- Auto-created on first question
- Persists through conversation
- Can be cleaned up after plan creation
- Consider TTL for abandoned sessions (e.g., 30 min)

## 🌍 Supported Patterns

### English
- "from X to Y"
- "visit X"
- "3 days"
- "2 adults"
- Dates: DD.MM.YYYY, YYYY-MM-DD

### Turkish
- "X'dan Y'ye"
- "X'ya gitmek"
- "3 gün"
- "2 kişi"
- Dates: GG.AA.YYYY

## 🚀 Production Considerations

1. **Session Storage**: Use Redis instead of in-memory dict
2. **Session TTL**: Expire abandoned sessions (30min)
3. **Rate Limiting**: Prevent conversation spam
4. **Validation**: Sanitize user inputs
5. **Logging**: Track conversation completion rates
6. **Analytics**: Measure which fields are most often missing

## 📈 Metrics to Track

- Conversation completion rate
- Average questions per session
- Most common missing fields
- Language distribution
- Time to complete conversation

