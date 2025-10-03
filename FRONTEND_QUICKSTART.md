# 🚀 Frontend Quick Start Guide

## Your Friend Wants This Format ✅

You asked for this exact JSON structure - **and we deliver it!**

```typescript
const data: Question[] = [
  {
    day: 2,
    startTime: '08:00',
    endTime: '09:00',
    options: [
      {
        text: 'Otele yakın bir kafede geleneksel Alman kahvaltısı',
        description: 'Hızlı ve lezzetli; yerel tatları deneyimlemek için ideal.'
      },
      // ... 3 more options
    ]
  }
]
```

## ✅ We Have It!

Our API returns **exactly this format** with the name `time_slots` instead of `Question[]`:

---

## 🎯 Quick Integration (3 Steps)

### Step 1: Call the API

```bash
POST http://localhost:4000/api/plan/interactive

{
  "prompt": "İstanbul'dan Berlin'e 3 gün 2 kişi",
  "language": "tr",
  "currency": "EUR"
}
```

### Step 2: Get This Response

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
      "options": [
        {
          "text": "Activity description",
          "description": "Why this is good"
        }
      ]
    }
  ]
}
```

### Step 3: Render in React/Vue

```tsx
// React Example
{plan.time_slots.map((slot, index) => (
  <TimeSlot key={index} data={slot} />
))}
```

---

## 📦 Ready-to-Use TypeScript Types

Copy from `FRONTEND_INTEGRATION.ts`:

```typescript
interface ActivityOption {
  text: string;
  description: string;
  price?: number;
  duration?: number;
}

interface TimeSlot {
  day: number;
  startTime: string;
  endTime: string;
  options: ActivityOption[];
}

interface InteractivePlan {
  trip_summary: string;
  destination: string;
  time_slots: TimeSlot[];
}
```

---

## 🎨 UI Example (React)

```tsx
import { useState } from 'react';

function TravelPlanner() {
  const [plan, setPlan] = useState(null);
  const [selections, setSelections] = useState({});

  const fetchPlan = async () => {
    const res = await fetch('http://localhost:4000/api/plan/interactive', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: "İstanbul Berlin 3 gün",
        language: 'tr'
      })
    });
    const data = await res.json();
    setPlan(data);
  };

  return (
    <div>
      <button onClick={fetchPlan}>Plan Trip</button>
      
      {plan?.time_slots.map((slot, slotIdx) => (
        <div key={slotIdx} className="time-slot">
          <h3>Day {slot.day} • {slot.startTime}-{slot.endTime}</h3>
          
          <div className="options-grid">
            {slot.options.map((option, optIdx) => (
              <div
                key={optIdx}
                className={`option ${selections[slotIdx] === optIdx ? 'selected' : ''}`}
                onClick={() => setSelections({ ...selections, [slotIdx]: optIdx })}
              >
                <h4>{option.text}</h4>
                <p>{option.description}</p>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## 🎨 CSS Suggestion

```css
.time-slot {
  margin: 20px 0;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
  margin-top: 15px;
}

.option {
  padding: 15px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.option:hover {
  border-color: #2196F3;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

.option.selected {
  border-color: #2196F3;
  background: #E3F2FD;
}

.option h4 {
  margin: 0 0 10px 0;
  color: #333;
}

.option p {
  margin: 0;
  color: #666;
  font-size: 0.9em;
}
```

---

## 📊 Complete Example Response

```json
{
  "trip_summary": "3 günlük Berlin seyahati - Tarihi yerler, müzeler ve yerel kültür",
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
          "text": "Berlin'da yerel bir kafede kahvaltı",
          "description": "Yerel lezzetleri deneyimlemek isteyenler için ideal."
        },
        {
          "text": "Otelde kahvaltı sonrası şehir yürüyüşü",
          "description": "Rahat başlangıç; şehri tanımak için mükemmel."
        },
        {
          "text": "Berlin'nın ünlü müzelerini ziyaret",
          "description": "Kültür ve sanat meraklıları için harika."
        },
        {
          "text": "Yerel pazarları keşfetme turu",
          "description": "Otantik deneyim arayanlar için eğlenceli."
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
          "text": "Berlin'da yerel bir kafede kahvaltı",
          "description": "Yerel lezzetleri deneyimlemek isteyenler için ideal."
        }
        // ... 3 more options
      ]
    },
    {
      "day": 1,
      "startTime": "12:00",
      "endTime": "14:00",
      "block_type": "afternoon",
      "options": [
        {
          "text": "Berlin'nın tarihi yerlerini gezme",
          "description": "Tarih meraklıları için kapsamlı bir tur."
        },
        {
          "text": "Yerel restoranlarda öğle yemeği ve alışveriş",
          "description": "Rahat ve keyifli bir öğleden sonra."
        },
        {
          "text": "Şehir parklarında piknik ve dinlenme",
          "description": "Doğa ve huzur arayanlar için ideal."
        },
        {
          "text": "Rehberli şehir turu",
          "description": "Şehri detaylı öğrenmek isteyenler için."
        }
      ]
    }
    // ... more time slots for all 3 days
  ]
}
```

---

## 🔥 Features You Get

✅ **Exactly your requested format** (`day`, `startTime`, `endTime`, `options`)  
✅ **4 options per time slot** (budget, comfort, adventure, cultural)  
✅ **Multiple time slots per day** (morning, afternoon, evening)  
✅ **Turkish & English support**  
✅ **Real MCP data** (flights, hotels, weather)  
✅ **24 time slots for 3-day trip** (8 slots per day)

---

## 🎯 Your Exact Use Case

```typescript
// This is EXACTLY what you showed us
const data: Question[] = [
  {
    day: 2,
    startTime: '08:00',
    endTime: '09:00',
    options: [
      {
        text: 'Otele yakın bir kafede geleneksel Alman kahvaltısı (brötchen, peynir, salam).',
        description: 'Hızlı ve lezzetli bir başlangıç; yerel tatları deneyimlemek isteyenler için ideal.',
      },
      // ... more options
    ],
  },
];

// Our API returns this EXACT structure in `time_slots`!
// Just rename:
const data: Question[] = apiResponse.time_slots;
```

---

## 🚀 Test It Now!

```bash
# Terminal
curl -X POST http://localhost:4000/api/plan/interactive \
  -H "Content-Type: application/json" \
  -d '{"prompt":"İstanbul Berlin 3 gün","language":"tr"}'
```

---

## 📚 Additional Resources

- `FRONTEND_INTEGRATION.ts` - Complete TypeScript types + React hooks
- `INTERACTIVE_PLAN_API.md` - Full API documentation
- `SYSTEM_SUMMARY.md` - Complete system overview

---

## 💡 Pro Tips

1. **Cache the plan** - Store in React state/context
2. **Track selections** - Use `Record<number, number>` for user choices
3. **Show progress** - Highlight selected options with different styling
4. **Export feature** - Let users download their customized plan
5. **Mobile-friendly** - Use grid for desktop, stack for mobile

---

## 🎉 You're Ready!

**Your frontend friend can now:**
1. Call `/api/plan/interactive`
2. Get the exact JSON format needed
3. Render time slots with 4 options each
4. Let users select their preferences
5. Build an amazing travel planning UI!

**Backend is ready. Go build something awesome! 🚀**

