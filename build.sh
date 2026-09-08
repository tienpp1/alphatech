#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "==> [BUILD] Installing Python Dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> [BUILD] Collecting Static Files via WhiteNoise..."
python manage.py collectstatic --no-input

echo "==> [BUILD] Applying Database Migrations..."
python manage.py migrate --no-input

echo "==> [BUILD] Seeding Platform Demo Dataset (ABC Tech & XYZ IT)..."
python manage.py seed_demo

echo "==> [BUILD] Seeding Student Administrator Accounts..."
python manage.py seed_student_admin

echo "==> [BUILD] Ingesting Enterprise Knowledge & SOPs..."
python scripts/ingest_advanced_enterprise_sops.py || true
python scripts/ingest_advanced_enterprise_sops_phase2.py || true

echo "==> [BUILD] Pre-training Enterprise XGBoost Forecasting Models..."
python scripts/train_enterprise_forecasting_models.py || true

echo "==> [BUILD] Deployment Build Completed Successfully!"
