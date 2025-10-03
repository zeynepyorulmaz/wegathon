#!/bin/bash

echo "════════════════════════════════════════════════════════════════════════════════"
echo "                    🚀 BACKEND BAŞLATILIYOR... 🚀"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

cd /Users/zeynepyorulmaz/wegathon/python-backend

# Kill existing process
pkill -f "uvicorn app.main:app" 2>/dev/null
sleep 1

# Start backend
echo "✅ Backend başlatılıyor..."
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "                    ✅ BACKEND ÇALIŞIYOR! ✅"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "🔗 Swagger UI: http://localhost:4000/docs"
echo "📖 ReDoc:      http://localhost:4000/redoc"
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
