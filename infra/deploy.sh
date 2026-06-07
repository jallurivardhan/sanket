#!/bin/bash
set -e

echo "=== Sanket — Google Cloud Deployment ==="

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
REGION="us-central1"
SERVICE_NAME="sanket-backend"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"

# Build and push Docker image
echo ""
echo "Building Docker image..."
cd backend
docker build -t $IMAGE_NAME .
docker push $IMAGE_NAME

# Deploy to Cloud Run
echo ""
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars "ENVIRONMENT=production" \
  --set-env-vars "REDIS_URL=${REDIS_URL}" \
  --set-env-vars "PHOENIX_API_KEY=${PHOENIX_API_KEY}"

echo ""
echo "=== Deployment Complete ==="
gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format "value(status.url)"
