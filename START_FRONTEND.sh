#!/bin/bash

echo "════════════════════════════════════════════════════════════"
echo "           🚀 FRONTEND BAŞLATILIYOR 🚀"
echo "════════════════════════════════════════════════════════════"
echo ""

cd /Users/zeynepyorulmaz/wegathon/aiku_frontend-main

# Create .env.local if not exists
if [ ! -f .env.local ]; then
    echo "📝 Creating .env.local..."
    echo "NEXT_PUBLIC_BACKEND_URL=http://localhost:4000" > .env.local
    echo "   ✅ Created"
fi

echo "📦 Checking dependencies..."
if [ ! -d "node_modules" ]; then
    echo "   Installing..."
    npm install
else
    echo "   ✅ Already installed"
fi

echo ""
echo "🚀 Starting frontend..."
echo ""
npm run dev

