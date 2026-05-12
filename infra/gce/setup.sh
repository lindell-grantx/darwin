#!/usr/bin/env bash
# Provision a fresh GCE Compute Engine VM (Debian 12) for Darwin v2 supervisor.
#
# Usage (from a GCE Cloud Shell or local with gcloud configured):
#   bash infra/gce/setup.sh
#
# Prereqs:
#   - gcloud configured for the target project
#   - DARWIN_GCP_SECRET_PROJECT set (so the supervisor can resolve
#     darwin-mongodb-uri, darwin-voyage-key via gcloud at startup)
#   - The VM's service account MUST have roles/secretmanager.secretAccessor
#     on both `darwin-mongodb-uri` and `darwin-voyage-key`. Without this,
#     run_all.py's startup secret resolution returns None and the supervisor
#     will crash with "MongoDB URI not set".
#   - GitHub HTTPS access to lindell-grantx/darwin (or a deploy key)
#
# Python version: this script installs python3.11 (Debian 12's apt default).
# pyproject.toml's `requires-python` is pinned to >=3.11 to match.

set -euo pipefail

VM_NAME="${VM_NAME:-darwin-supervisor}"
ZONE="${ZONE:-us-central1-a}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-medium}"
PROJECT="${DARWIN_GCP_SECRET_PROJECT:-grantx-fleet}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-darwin-supervisor@${PROJECT}.iam.gserviceaccount.com}"

echo "Provisioning VM ${VM_NAME} in ${ZONE} (project=${PROJECT})..."

gcloud compute instances create "${VM_NAME}" \
    --project="${PROJECT}" \
    --zone="${ZONE}" \
    --machine-type="${MACHINE_TYPE}" \
    --image-family="debian-12" \
    --image-project="debian-cloud" \
    --boot-disk-size="20GB" \
    --service-account="${SERVICE_ACCOUNT}" \
    --scopes="https://www.googleapis.com/auth/cloud-platform"

echo "VM created. Waiting 30s for SSH..."
sleep 30

echo "Bootstrapping VM..."
gcloud compute ssh "${VM_NAME}" --zone="${ZONE}" --project="${PROJECT}" --command="
  set -euxo pipefail
  # Stock Debian 12 ships neither curl, gnupg, nor the Cloud SDK. We need all
  # three: gcloud is invoked at runtime by run_all.py to resolve secrets, and
  # curl + gnupg are needed to add the Cloud SDK apt repo.
  sudo apt-get update
  sudo apt-get install -y curl gnupg
  curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
  echo 'deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main' | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
  sudo apt-get update
  sudo apt-get install -y google-cloud-cli python3.11 python3.11-venv git
  cd \$HOME
  if [ ! -d darwin ]; then
    git clone https://github.com/lindell-grantx/darwin.git
  fi
  cd darwin
  python3.11 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -e .
  # /etc/darwin.env carries only project IDs. Mongo URI + Voyage key are
  # resolved at startup by run_all.py via gcloud secrets versions access
  # (see darwin.lib.secrets), keeping plaintext secrets off disk. Requires
  # secretAccessor IAM on the VM SA. ANTHROPIC_VERTEX_PROJECT_ID defaults to
  # the same project as Secret Manager; edit /etc/darwin.env post-provision
  # if you need Vertex AI in a different project.
  sudo tee /etc/darwin.env > /dev/null <<EOF
DARWIN_GCP_SECRET_PROJECT=${PROJECT}
ANTHROPIC_VERTEX_PROJECT_ID=${PROJECT}
EOF
  # systemd unit writes to /var/log/darwin/supervisor.log; create it now
  # so the service starts cleanly.
  sudo mkdir -p /var/log/darwin
  sudo chown lcume /var/log/darwin
"

echo "VM bootstrapped. Next: copy the systemd unit and enable it."
echo "  gcloud compute scp infra/systemd/darwin-supervisor.service ${VM_NAME}:/tmp/ --zone=${ZONE}"
echo "  gcloud compute ssh ${VM_NAME} --zone=${ZONE} --command=\"sudo mv /tmp/darwin-supervisor.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now darwin-supervisor\""
