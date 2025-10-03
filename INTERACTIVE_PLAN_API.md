# 🎯 Interactive Plan API - Frontend Integration Guide

## Overview

Interactive Plan formatı, her zaman dilimi için **birden fazla aktivite seçeneği** sunar. Kullanıcı kendi tercihlerine göre seçim yapabilir.

---

## 📊 JSON Structure

### Response Format

```typescript
interface ActivityOption {
  text: string;           // Ana aktivite açıklaması
  description: string;    // Neden iyi / kime uygun
  price?: number;         // Fiyat (opsiyonel)
  duration?: number;      // Süre (dakika)
  location?: string;      // Konum
  booking_url?: string;   // Rezervasyon linki
}

interface TimeSlot {
  day: number;            // Gün numarası (1, 2, 3...)
  startTime: string;      // Başlangıç saati (HH:MM)
  endTime: string;        // Bitiş saati (HH:MM)
  options: ActivityOption[]; // 4 farklı seçenek
  block_type?: string;    // morning, afternoon, evening...
}

interface InteractivePlan {
  trip_summary: string;
  destination: string;
  start_date: string;
  end_date: string;
  total_days: number;
  time_slots: TimeSlot[];  // Tüm zaman dilimleri
  
  // Metadata
  flights?: any;
  lodging?: any;
  pricing?: any;
  weather?: any[];
}
```

---

## 🚀 API Endpoints

### 1. Direct Interactive Plan

```http
POST /api/plan/interactive
```

**Request:**
```json
{
  "prompt": "İstanbul'dan Berlin'e 20 Kasım 2 kişi 3 gün",
  "language": "tr",
  "currency": "EUR"
}
```

**Response:**
```json
{
  "trip_summary": "3 günlük Berlin seyahati...",
  "destination": "Berlin",
  "start_date": "2023-11-20",
  "end_date": "2023-11-23",
  "total_days": 3,
  "time_slots": [
    {
      "day": 1,
      "startTime": "08:00",
      "endTime": "10:00",
      "block_type": "morning",
      "options": [
        {
          "text": "Otele yakın kafede geleneksel Alman kahvaltısı",
          "description": "Hızlı ve lezzetli; yerel tatları deneyimlemek için ideal."
        },
        {
          "text": "Café Einstein'da klasik Avusturya kahvaltısı",
          "description": "Atmosferi ve zengin kahvaltısı ile kahve severler için harika."
        },
        {
          "text": "Müzeler Adası'nda hızlı takeaway kahvaltı",
          "description": "Sabah turuna hızla başlamak isteyenler için uygun."
        },
        {
          "text": "Otelde kahvaltı sonrası Tiergarten Park yürüyüşü",
          "description": "Rahat ve sakin başlangıç; doğa severler için ideal."
        }
      ]
    },
    {
      "day": 1,
      "startTime": "10:00",
      "endTime": "12:00",
      "block_type": "morning",
      "options": [
        {
          "text": "Brandenburg Kapısı ve Reichstag turu",
          "description": "Tarihi yerler görmek isteyenler için mükemmel."
        },
        {
          "text": "Müze Adası'nda Pergamon Müzesi",
          "description": "Sanat ve tarih meraklıları için kapsamlı tur."
        },
        {
          "text": "Berlin Duvarı Anıtı ziyareti",
          "description": "Tarihi anlamak isteyenler için önemli durak."
        },
        {
          "text": "Hackesche Höfe alışveriş ve sanat keşfi",
          "description": "Modern Berlin kültürü deneyimlemek için ideal."
        }
      ]
    }
  ],
  "flights": {...},
  "lodging": {...},
  "pricing": {...}
}
```

---

### 2. Interactive Plan from Conversation

```http
POST /api/chat/interactive
```

**Request:**
```json
{
  "session_id": "uuid-from-chat-start"
}
```

**Response:**
Yukarıdaki ile aynı `InteractivePlan` formatı.

---

## 💡 Use Cases

### 1. **Choose Your Own Adventure Style**
Her zaman dilimi için 4 seçenek sun:
- Ekonomik seçenek
- Lüks/konfor seçenek
- Aktif/macera seçenek
- Kültürel/rahat seçenek

### 2. **Personalized Itinerary Builder**
Kullanıcı her slotta tercih ettiğini seçer, kendi planını oluşturur.

### 3. **Smart Recommendations**
AI her seçeneğin "kime uygun" olduğunu açıklar:
- "Kahve severler için"
- "Zaman kazanmak isteyenler için"
- "Bütçe dostu seçenek"

---

## 🎨 Frontend Implementation

### React Example

```tsx
import { useState } from 'react';

interface TimeSlot {
  day: number;
  startTime: string;
  endTime: string;
  options: ActivityOption[];
}

const InteractivePlanViewer = () => {
  const [plan, setPlan] = useState<InteractivePlan | null>(null);
  const [selections, setSelections] = useState<Record<string, number>>({});

  const fetchPlan = async (prompt: string) => {
    const res = await fetch('/api/plan/interactive', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        language: 'tr',
        currency: 'TRY'
      })
    });
    const data = await res.json();
    setPlan(data);
  };

  const selectOption = (slotIndex: number, optionIndex: number) => {
    setSelections({
      ...selections,
      [slotIndex]: optionIndex
    });
  };

  return (
    <div>
      <h1>{plan?.trip_summary}</h1>
      
      {plan?.time_slots.map((slot, slotIdx) => (
        <div key={slotIdx} className="time-slot">
          <h3>
            Day {slot.day} • {slot.startTime} - {slot.endTime}
          </h3>
          
          <div className="options-grid">
            {slot.options.map((option, optIdx) => (
              <div
                key={optIdx}
                className={`option-card ${selections[slotIdx] === optIdx ? 'selected' : ''}`}
                onClick={() => selectOption(slotIdx, optIdx)}
              >
                <h4>{option.text}</h4>
                <p>{option.description}</p>
                {option.price && <span>€{option.price}</span>}
              </div>
            ))}
          </div>
        </div>
      ))}
      
      <button onClick={saveMyPlan}>
        Save My Custom Plan
      </button>
    </div>
  );
};
```

---

### Vue Example

```vue
<template>
  <div class="interactive-plan">
    <h1>{{ plan?.trip_summary }}</h1>
    
    <div v-for="(slot, index) in plan?.time_slots" :key="index" class="time-slot">
      <div class="time-header">
        <span>Day {{ slot.day }}</span>
        <span>{{ slot.startTime }} - {{ slot.endTime }}</span>
      </div>
      
      <div class="options">
        <div 
          v-for="(option, optIdx) in slot.options" 
          :key="optIdx"
          :class="['option', { selected: isSelected(index, optIdx) }]"
          @click="selectOption(index, optIdx)"
        >
          <h4>{{ option.text }}</h4>
          <p>{{ option.description }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const plan = ref<InteractivePlan | null>(null);
const selections = ref<Record<number, number>>({});

const fetchPlan = async (prompt: string) => {
  const res = await fetch('/api/plan/interactive', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, language: 'tr' })
  });
  plan.value = await res.json();
};

const selectOption = (slotIdx: number, optIdx: number) => {
  selections.value[slotIdx] = optIdx;
};

const isSelected = (slotIdx: number, optIdx: number) => {
  return selections.value[slotIdx] === optIdx;
};
</script>
```

---

## 🎨 UI/UX Recommendations

### 1. **Card Grid Layout**
```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│  Budget     │   Comfort   │  Adventure  │  Cultural   │
│  Option     │   Option    │   Option    │   Option    │
│             │             │             │             │
│  💰 €20     │   🏨 €45    │   🚴 €35    │   🎭 €30    │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

### 2. **Icons for Option Types**
- 💰 Budget-friendly
- 🏨 Comfort/Luxury
- 🚴 Active/Adventure
- 🎭 Cultural/Relaxed
- ☕ Food lovers
- 📸 Photo opportunities

### 3. **Selection State**
- Unselected: Gray border
- Hovered: Blue border
- Selected: Blue background + checkmark

### 4. **Save & Export**
User selects their preferred options → Generate personalized PDF/iCal

---

## 🔄 Workflow

```
1. User starts conversation
   POST /api/chat/start
   → session_id

2. AI collects info
   POST /api/chat/continue (multiple times)
   → plan created

3. Get interactive version
   POST /api/chat/interactive
   → time_slots with options

4. User selects preferences
   Frontend tracks selections

5. Optional: Save custom plan
   POST /api/save-custom (future endpoint)
```

---

## 🎯 Benefits

### For Users:
✅ Personalized control  
✅ See alternatives  
✅ Match preferences  
✅ Learn why each option is good

### For Developers:
✅ Clean JSON structure  
✅ Easy to render  
✅ Flexible UI options  
✅ Rich metadata

### For Business:
✅ Higher engagement  
✅ User empowerment  
✅ Data on preferences  
✅ Upsell opportunities

---

## 📊 Example: Full Day Structure

```json
{
  "day": 2,
  "time_slots": [
    {
      "startTime": "08:00",
      "endTime": "09:00",
      "options": [...]  // 4 breakfast options
    },
    {
      "startTime": "09:00",
      "endTime": "12:00",
      "options": [...]  // 4 morning activity options
    },
    {
      "startTime": "12:00",
      "endTime": "14:00",
      "options": [...]  // 4 lunch options
    },
    {
      "startTime": "14:00",
      "endTime": "17:00",
      "options": [...]  // 4 afternoon activity options
    },
    {
      "startTime": "17:00",
      "endTime": "19:00",
      "options": [...]  // 4 relaxation options
    },
    {
      "startTime": "19:00",
      "endTime": "22:00",
      "options": [...]  // 4 dinner/evening options
    }
  ]
}
```

---

## 🚀 Quick Start

```bash
# 1. Create interactive plan directly
curl -X POST http://localhost:4000/api/plan/interactive \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "İstanbul Berlin 3 gün 2 kişi",
    "language": "tr"
  }'

# 2. Or from conversation
# First start chat
curl -X POST http://localhost:4000/api/chat/start \
  -H "Content-Type: application/json" \
  -d '{"initial_message":"Berlin 3 gün","language":"tr"}'

# Continue until plan is ready...
# Then get interactive format
curl -X POST http://localhost:4000/api/chat/interactive \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<SESSION_ID>"}'
```

---

## 🎉 Result

**Perfect for modern, engaging travel planning UIs!**

✅ Multiple options per time slot  
✅ AI-generated descriptions  
✅ User choice & personalization  
✅ Ready for frontend integration  

**Your friend can now build the interactive UI! 🚀**

