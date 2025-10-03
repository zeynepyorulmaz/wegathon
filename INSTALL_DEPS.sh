#!/bin/bash

echo "════════════════════════════════════════════════════════════════════════════════"
echo "                    📦 DEPENDENCIES YÜKLENIYOR... 📦"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

cd /Users/zeynepyorulmaz/wegathon/python-backend

echo "✅ Requirements.txt'ten paketler yükleniyor..."
pip3 install -r requirements.txt

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "                    ✅ DEPENDENCIES YÜKLENDI! ✅"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Şimdi backend'i başlatabilirsiniz:"
echo "   uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload"
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
