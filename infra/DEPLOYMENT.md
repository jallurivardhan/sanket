# Sanket — Deployment Guide

## Prerequisites
- Google Cloud account with billing enabled
- gcloud CLI installed and authenticated
- Docker installed
- Redis instance (Redis Cloud free tier works)

## Step 1: Google Cloud Setup

```bash
# Install gcloud CLI if not installed
# https://cloud.google.com/sdk/docs/install

# Login
gcloud auth login
gcloud auth configure-docker

# Set project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

## Step 2: Get Gemini Access

```bash
# Vertex AI is enabled above
# Test Gemini access:
gcloud ai models list --region=us-central1

# In your .env set:
# GOOGLE_CLOUD_PROJECT=your-project-id
# VERTEX_AI_LOCATION=us-central1
# GEMINI_MODEL=gemini-3.1-pro-preview
```

## Step 3: Get Arize Phoenix API Key

1. Go to app.phoenix.arize.com
2. Create free account
3. Go to Settings → API Keys
4. Create new key
5. Add to .env:
   PHOENIX_API_KEY=your-key-here

## Step 4: Get Redis (Free)

Option A — Redis Cloud (Recommended):
1. Go to redis.com/try-free
2. Create free database
3. Copy connection string
4. Add to .env:
   REDIS_URL=redis://username:password@host:port

Option B — Local Docker:
docker run -d -p 6379:6379 redis:7-alpine

## Step 5: Run Locally with Real Gemini

```bash
# Copy and fill env
cp .env.example .env
# Edit .env with your real keys

# Install backend dependencies
pip install -r backend/requirements.txt

# Start backend
python start.py

# Start frontend (new terminal)
cd frontend
npm run dev

# Open dashboard
open http://localhost:5173
```

## Step 6: Deploy to Cloud Run

```bash
# Set your project
export GOOGLE_CLOUD_PROJECT=your-project-id
export REDIS_URL=your-redis-url
export PHOENIX_API_KEY=your-phoenix-key

# Run deployment script
chmod +x infra/deploy.sh
./infra/deploy.sh
```

## Step 7: Deploy Frontend to Vercel (Free)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy frontend
cd frontend
vercel

# Set environment variable in Vercel dashboard:
# VITE_API_URL=https://your-cloudrun-url
# VITE_WS_URL=wss://your-cloudrun-url
```

## Verification After Deployment

```bash
# Test deployed backend
curl https://your-service-url/health

# Run fraud demo against live deployment
curl -X POST \
  "https://your-service-url/api/v1/demo/run?scenario=coordinated_fraud"
```
