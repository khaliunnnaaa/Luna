#!/usr/bin/env bash
# Кодыг EC2 руу хуулж, production compose-ийг асаана. Дахин ажиллуулахад шинэчилнэ.
# Хэрэглээ:  bash deploy/push.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(dirname "$HERE")
source "$HERE/.instance"
SSH="ssh -i $HOME/.ssh/luna-key.pem -o StrictHostKeyChecking=accept-new ubuntu@$IP"
DOMAIN="${IP//./-}.sslip.io"

# Docker суусан эсэх (user-data дуусаагүй бол хүлээнэ)
until $SSH 'docker compose version >/dev/null 2>&1'; do echo "Docker хүлээж байна..."; sleep 10; done

rsync -az --delete -e "ssh -i $HOME/.ssh/luna-key.pem" \
  --exclude .git --exclude .venv --exclude node_modules --exclude .next --exclude __pycache__ \
  --exclude '*.db' --exclude '.env' --exclude '.env.*' --exclude 'backend/uploads' \
  --exclude 'ml/data' --exclude 'data/ocr_images' --exclude 'docs/*.pptx' --exclude 'deploy/.instance' \
  "$ROOT/" "ubuntu@$IP:luna/"

# Нууц: backend/.env (Supabase DATABASE_URL) хуулна; JWT_SECRET-ийг сервер дээр нэг удаа үүсгэнэ
scp -q -i "$HOME/.ssh/luna-key.pem" "$ROOT/backend/.env" "ubuntu@$IP:luna/backend/.env"
$SSH "cd luna && [ -f .env.prod ] || printf 'DOMAIN=$DOMAIN\nJWT_SECRET=%s\n' \$(openssl rand -hex 32) > .env.prod && chmod 600 .env.prod backend/.env"

$SSH "cd luna && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build"
echo "Нээлттэй: https://$DOMAIN"
