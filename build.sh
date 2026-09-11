#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "==> [BUILD] Installing Python Dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> [BUILD] Applying Django database migrations..."
python manage.py migrate --no-input

echo "==> [BUILD] Collecting Static Files via WhiteNoise..."
python manage.py collectstatic --no-input

echo "==> [BUILD] Artifact build completed."
