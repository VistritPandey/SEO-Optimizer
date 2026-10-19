#!/usr/bin/env bash
# Run from any directory after filling deploy/hosting.env.example in your shell.
set -euo pipefail
REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
: "${PROJECT_ID:?Set the intended Google Cloud project explicitly}"
: "${REGION:=us-central1}"
: "${OPT_FIRESTORE_DATABASE:?Set the intended Firestore database ID explicitly}"
: "${FRONTEND_URL:?Set the deployed Next.js URL}"
: "${GITHUB_APP_ID:?Set the GitHub App ID}"
: "${GITHUB_APP_SLUG:?Set the GitHub App slug}"
: "${GITHUB_CLIENT_ID:?Set the GitHub App OAuth client ID}"
: "${APP_SECRET_RESOURCE:?Existing Secret Manager secret: encryption/session key}"
: "${MODEL_SECRET_RESOURCE:?Existing Secret Manager secret: managed model key}"
: "${GITHUB_KEY_RESOURCE:?Existing Secret Manager secret: GitHub App private PEM}"
: "${GITHUB_OAUTH_RESOURCE:?Existing Secret Manager secret: OAuth client secret}"
: "${GITHUB_WEBHOOK_RESOURCE:?Existing Secret Manager secret: webhook signing secret}"
command -v gcloud >/dev/null || { echo 'Install Google Cloud CLI first.' >&2; exit 1; }
SERVICE_ACCOUNT="your-optimiser@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/your-optimiser/backend:latest"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com firestore.googleapis.com secretmanager.googleapis.com cloudscheduler.googleapis.com identitytoolkit.googleapis.com --project="$PROJECT_ID"
if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create your-optimiser --project="$PROJECT_ID" --display-name='Your Optimiser backend and worker'
fi
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SERVICE_ACCOUNT" --role=roles/datastore.user --quiet >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SERVICE_ACCOUNT" --role=roles/firebaseauth.viewer --quiet >/dev/null
for SECRET_RESOURCE in "$APP_SECRET_RESOURCE" "$MODEL_SECRET_RESOURCE" "$GITHUB_KEY_RESOURCE" "$GITHUB_OAUTH_RESOURCE" "$GITHUB_WEBHOOK_RESOURCE"; do
  gcloud secrets add-iam-policy-binding "$SECRET_RESOURCE" --project="$PROJECT_ID" --member="serviceAccount:$SERVICE_ACCOUNT" --role=roles/secretmanager.secretAccessor --quiet >/dev/null
done
if ! gcloud artifacts repositories describe your-optimiser --project="$PROJECT_ID" --location="$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create your-optimiser --project="$PROJECT_ID" --location="$REGION" --repository-format=docker
fi
if ! gcloud firestore databases describe --database="$OPT_FIRESTORE_DATABASE" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud firestore databases create --database="$OPT_FIRESTORE_DATABASE" --location="$REGION" --type=firestore-native --project="$PROJECT_ID"
fi
BUILD_ACCOUNT="your-optimiser-checks@${PROJECT_ID}.iam.gserviceaccount.com"
BUILD_BUCKET="${PROJECT_ID}-your-optimiser-checks"
if ! gcloud iam service-accounts describe "$BUILD_ACCOUNT" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create your-optimiser-checks --project="$PROJECT_ID" --display-name='Isolated source verification only'
fi
if ! gcloud storage buckets describe "gs://$BUILD_BUCKET" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://$BUILD_BUCKET" --project="$PROJECT_ID" --location="$REGION" --uniform-bucket-level-access --public-access-prevention
fi
gcloud storage buckets update "gs://$BUILD_BUCKET" --lifecycle-file="$REPOSITORY_ROOT/deploy/source-lifecycle.json" --project="$PROJECT_ID"
gcloud storage buckets add-iam-policy-binding "gs://$BUILD_BUCKET" --member="serviceAccount:$SERVICE_ACCOUNT" --role=roles/storage.objectAdmin --project="$PROJECT_ID" >/dev/null
gcloud storage buckets add-iam-policy-binding "gs://$BUILD_BUCKET" --member="serviceAccount:$BUILD_ACCOUNT" --role=roles/storage.objectViewer --project="$PROJECT_ID" >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$BUILD_ACCOUNT" --role=roles/logging.logWriter --quiet >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SERVICE_ACCOUNT" --role=roles/cloudbuild.builds.editor --quiet >/dev/null
gcloud iam service-accounts add-iam-policy-binding "$BUILD_ACCOUNT" --project="$PROJECT_ID" --member="serviceAccount:$SERVICE_ACCOUNT" --role=roles/iam.serviceAccountUser --quiet >/dev/null
gcloud builds submit "$REPOSITORY_ROOT" --tag="$IMAGE" --project="$PROJECT_ID"
ENVIRONMENT="OPT_BUILD_BACKEND=cloud-build,OPT_BUILD_BUCKET=$BUILD_BUCKET,OPT_BUILD_ACCOUNT=$BUILD_ACCOUNT,OPT_BUILD_REGION=$REGION,OPT_ENV=production,OPT_HOSTED=1,OPT_STORAGE=firestore,OPT_FIRESTORE_DATABASE=$OPT_FIRESTORE_DATABASE,GOOGLE_CLOUD_PROJECT=$PROJECT_ID,OPT_DATA_DIR=/tmp/your-optimiser,OPT_REGISTRATION=0,OPT_FRONTEND_URL=$FRONTEND_URL,GITHUB_APP_ID=$GITHUB_APP_ID,GITHUB_APP_SLUG=$GITHUB_APP_SLUG,GITHUB_CLIENT_ID=$GITHUB_CLIENT_ID,OPT_MANAGED_PROVIDER=${MANAGED_PROVIDER:-google},OPT_MANAGED_MODEL=${MANAGED_MODEL:-gemini-3.8-flash}"
SECRETS="OPT_SECRET_KEY=$APP_SECRET_RESOURCE:latest,OPT_MANAGED_API_KEY=$MODEL_SECRET_RESOURCE:latest,GITHUB_PRIVATE_KEY=$GITHUB_KEY_RESOURCE:latest,GITHUB_CLIENT_SECRET=$GITHUB_OAUTH_RESOURCE:latest,GITHUB_WEBHOOK_SECRET=$GITHUB_WEBHOOK_RESOURCE:latest"
gcloud run deploy your-optimiser-api --project="$PROJECT_ID" --region="$REGION" --image="$IMAGE" --service-account="$SERVICE_ACCOUNT" --allow-unauthenticated --port=8000 --memory=1Gi --cpu=1 --max-instances=5 --set-env-vars="$ENVIRONMENT" --set-secrets="$SECRETS"
API_URL="$(gcloud run services describe your-optimiser-api --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')"
gcloud run services update your-optimiser-api --project="$PROJECT_ID" --region="$REGION" --update-env-vars="OPT_PUBLIC_URL=$API_URL"
gcloud run jobs deploy your-optimiser-worker --project="$PROJECT_ID" --region="$REGION" --image="$IMAGE" --service-account="$SERVICE_ACCOUNT" --command=your-optimiser --args=worker,--once --memory=2Gi --cpu=2 --tasks=1 --parallelism=1 --max-retries=0 --task-timeout=900s --set-env-vars="$ENVIRONMENT,OPT_PUBLIC_URL=$API_URL" --set-secrets="$SECRETS"
gcloud run jobs add-iam-policy-binding your-optimiser-worker --project="$PROJECT_ID" --region="$REGION" --member="serviceAccount:$SERVICE_ACCOUNT" --role=roles/run.invoker --quiet >/dev/null
SCHEDULER_ARGS=(--project="$PROJECT_ID" --location="$REGION" --schedule='*/5 * * * *' --uri="https://run.googleapis.com/v2/projects/$PROJECT_ID/locations/$REGION/jobs/your-optimiser-worker:run" --http-method=POST --oauth-service-account-email="$SERVICE_ACCOUNT")
if gcloud scheduler jobs describe your-optimiser-worker --project="$PROJECT_ID" --location="$REGION" >/dev/null 2>&1; then
  gcloud scheduler jobs update http your-optimiser-worker "${SCHEDULER_ARGS[@]}"
else
  gcloud scheduler jobs create http your-optimiser-worker "${SCHEDULER_ARGS[@]}"
fi
printf '\nAPI: %s\nSet frontend OPT_BACKEND_URL to that URL.\nGitHub callback: %s/api/v1/github/callback\nWebhook: %s/webhooks/github\n' "$API_URL" "$API_URL" "$API_URL"
printf 'Configure firebase.json for database %s only before deploying its rules/indexes (see docs/hosted-setup.md).\n' "$OPT_FIRESTORE_DATABASE"
printf 'Enable Firebase Auth providers and authorised frontend domains in the Firebase console.\n'
