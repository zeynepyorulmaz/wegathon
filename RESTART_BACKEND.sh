#!/bin/bash
echo "🔄 Restarting backend with OpenSearch logging..."
cd python-backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
