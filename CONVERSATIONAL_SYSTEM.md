# 🤖 Conversational Travel Planning System

Tam otomatik, AI-güdümlü seyahat planlama sistemi. Kullanıcıdan eksik bilgileri toplar, plan oluşturur ve revizyon isteklerini yönetir.

---

## ✨ Özellikler

### 1️⃣ **Akıllı Bilgi Toplama**
- Kullanıcının ilk mesajını parse eder
- Eksik bilgiler için **tek tek** doğal sorular sorar
- Her cevabı işleyip bir sonraki soruya geçer
- Tüm bilgi toplandığında otomatik plan oluşturur

### 2️⃣ **Gerçek Zamanlı Plan Oluşturma**
- Gerekli bilgiler toplandığında otomatik plan üretir
- **Her response'da son plan döner**
- MCP tools kullanarak gerçek flight, hotel, weather data çeker

### 3️⃣ **Plan Revizyon Sistemi**
- "2. günü daha rahat yap" gibi natural language komutları anlar
- Planı revize edip güncel halini döner
- Chat history korunur

### 4️⃣ **Session Management**
- Her kullanıcı için benzersiz session ID
- Tüm conversation history saklanır
- Her mesajda son plan döner (varsa)

---

## 🎯 API Endpoints

### **POST /api/chat/start**
Yeni bir conversation başlat.

**Request:**
```json
{
  "initial_message": "İstanbuldan Berlin 3 gün gitmek istiyorum",
  "language": "tr",
  "currency": "EUR"
}
```

**Response:**
```json
{
  "session_id": "uuid-here",
  "message": "Ne zaman gitmeyi planlıyorsunuz?",
  "plan": null,  // İlk mesajda plan yok
  "collected_data": {
    "origin": "Istanbul",
    "destination": "Berlin",
    "start_date": null,
    "adults": null
  },
  "needs_more_info": true,
  "conversation_complete": false
}
```

---

### **POST /api/chat/continue**
Conversation'ı devam ettir.

**Request:**
```json
{
  "session_id": "uuid-from-start",
  "message": "20 Kasım"
}
```

**Response - Hala bilgi toplama:**
```json
{
  "session_id": "uuid-here",
  "message": "Kaç kişi seyahat edeceksiniz?",
  "plan": null,
  "collected_data": {
    "origin": "Istanbul",
    "destination": "Berlin",
    "start_date": "2023-11-20",
    "end_date": "2023-11-23",
    "adults": null
  },
  "needs_more_info": true,
  "conversation_complete": false
}
```

**Response - Plan oluşturuldu:**
```json
{
  "session_id": "uuid-here",
  "message": "Harika! Size detaylı bir plan hazırladım.",
  "plan": {
    "query": {...},
    "summary": "3 günlük Berlin seyahati...",
    "flights": {...},
    "lodging": {...},
    "days": [...],
    "pricing": {...}
  },
  "collected_data": {
    "origin": "Istanbul",
    "destination": "Berlin",
    "start_date": "2023-11-20",
    "end_date": "2023-11-23",
    "adults": 2
  },
  "needs_more_info": false,
  "conversation_complete": true
}
```

**Response - Plan revize edildi:**
```json
{
  "session_id": "uuid-here",
  "message": "2. günü daha rahat hale getirdim.",
  "plan": {
    // Revize edilmiş plan
    "days": [...]
  },
  "needs_more_info": false,
  "conversation_complete": true
}
```

---

## 🔄 Conversation Flow

### Senaryo 1: Eksik Bilgilerle Başlama

```
1. User  → "İstanbuldan Berlin gitmek istiyorum"
   AI    → "Ne zaman gitmeyi planlıyorsunuz?"
   Plan  → ❌ Yok

2. User  → "20 Kasım 3 gün"
   AI    → "Kaç kişi seyahat edeceksiniz?"
   Plan  → ❌ Yok

3. User  → "2 kişi"
   AI    → "Harika! Size detaylı bir plan hazırladım."
   Plan  → ✅ Oluşturuldu (flights, hotels, itinerary...)
```

---

### Senaryo 2: Tam Bilgiyle Başlama

```
1. User  → "İstanbul'dan Berlin'e 20 Kasım 3 gün 2 kişi"
   AI    → "Size detaylı bir plan hazırlıyorum..."
   Plan  → ✅ Direkt oluşturuldu
```

---

### Senaryo 3: Plan Revizyon

```
# Plan oluşturulduktan sonra...

4. User  → "2. günü daha rahat yap, çok yoğun"
   AI    → "2. günü daha rahat hale getirdim..."
   Plan  → ✅ Revize edildi

5. User  → "Daha ucuz otel seçenekleri göster"
   AI    → "Daha ekonomik otel seçenekleri ekledim..."
   Plan  → ✅ Revize edildi

6. User  → "Müze gezilerini kaldır"
   AI    → "Müze etkinliklerini çıkarttım..."
   Plan  → ✅ Revize edildi
```

---

## 🏗️ Mimari

### **Models** (`app/models/conversation.py`)
```python
ConversationSession:
  - session_id: str
  - messages: List[ChatMessage]  # Tüm history
  - collected_data: Dict          # Toplanan bilgiler
  - current_plan: Dict | None     # Güncel plan
  - plan_created: bool            # Plan oluşturuldu mu?

ChatMessage:
  - role: "user" | "assistant"
  - content: str

ChatResponse:
  - session_id: str
  - message: str                  # AI'ın cevabı
  - plan: Dict | None             # Güncel plan
  - needs_more_info: bool         # Daha soru sorulacak mı?
  - conversation_complete: bool   # Plan hazır mı?
```

### **Service** (`app/services/conversation_manager.py`)
```python
process_conversation_turn():
  1. User mesajını history'e ekle
  2. Anthropic'e gönder (conversational prompt ile)
  3. AI'ın response'unu parse et
  4. Action'a göre:
     - "ask_question": Soru sor, bilgi topla
     - "create_plan": generate() çağır, plan oluştur
     - "revise_plan": revise() çağır, planı güncelle
  5. (ai_message, plan, needs_more_info) dön
```

### **Router** (`app/routers/plan.py`)
```python
/api/chat/start:
  - Yeni session oluştur
  - İlk mesajı işle
  - Session'ı sakla
  - ChatResponse dön

/api/chat/continue:
  - Session'ı bul
  - Mesajı işle
  - Session'ı güncelle
  - ChatResponse dön (güncel plan ile)
```

---

## 🎨 Frontend Integration

### React/Vue Example
```javascript
// 1. Start conversation
const startChat = async (message) => {
  const res = await fetch('/api/chat/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      initial_message: message,
      language: 'tr',
      currency: 'EUR'
    })
  });
  const data = await res.json();
  
  // Save session_id
  sessionId = data.session_id;
  
  // Show AI message
  addMessage('assistant', data.message);
  
  // Show plan if available
  if (data.plan) {
    displayPlan(data.plan);
  }
};

// 2. Continue conversation
const sendMessage = async (message) => {
  const res = await fetch('/api/chat/continue', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message: message
    })
  });
  const data = await res.json();
  
  // Show AI response
  addMessage('assistant', data.message);
  
  // Always update plan if available
  if (data.plan) {
    displayPlan(data.plan);
  }
  
  // Check if conversation is complete
  if (data.conversation_complete) {
    showSuccessMessage('Plan hazır!');
  }
};
```

---

## 📊 Collected Data Structure

Conversation boyunca toplanan veri:

```json
{
  "origin": "Istanbul",
  "destination": "Berlin",
  "start_date": "2023-11-20",
  "end_date": "2023-11-23",
  "adults": 2,
  "children": 0,
  "preferences": ["museums", "nightlife"],
  "budget": "mid-range"
}
```

---

## 🔥 Avantajlar

1. **Kullanıcı Dostu**: Form doldurmaya gerek yok, natural chat
2. **Akıllı**: Sadece gerekli bilgileri sorar
3. **Esnek**: İstediği gibi revize edebilir
4. **Şeffaf**: Her adımda ne olduğu belli
5. **Gerçek Zamanlı**: Her response'da güncel plan

---

## 🧪 Test Komutu

```bash
# 1. Conversation başlat
curl -X POST http://localhost:4000/api/chat/start \
  -H "Content-Type: application/json" \
  -d '{"initial_message":"İstanbuldan Berlin 3 gün","language":"tr","currency":"EUR"}'

# Response: session_id al

# 2. Devam et
curl -X POST http://localhost:4000/api/chat/continue \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<SESSION_ID>","message":"20 Kasım"}'

# 3. Kişi sayısını ver (plan oluştur)
curl -X POST http://localhost:4000/api/chat/continue \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<SESSION_ID>","message":"2 kişi"}'

# 4. Revize et
curl -X POST http://localhost:4000/api/chat/continue \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<SESSION_ID>","message":"2. günü daha rahat yap"}'
```

---

## 🚀 Production Considerations

1. **Session Storage**: Redis/DB kullan (şu an in-memory)
2. **Session Timeout**: Eski session'ları temizle
3. **Rate Limiting**: Spam koruması
4. **Error Handling**: Daha detaylı error messages
5. **Language Detection**: Otomatik dil algılama
6. **Analytics**: Conversation metrics

---

## 🎯 Sonuç

**Conversational system artık tamamen çalışıyor!**

✅ Eksik bilgiler için soru soruyor  
✅ Plan otomatik oluşturuyor  
✅ Revize isteklerini handle ediyor  
✅ Her response'da güncel plan dönüyor  
✅ Chat history tutuluyor  
✅ Session management var  

**Production-ready conversational travel planner!** 🎉

