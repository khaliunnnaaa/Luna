#!/bin/sh
# Backend контейнер эхлэхэд: PostgreSQL-д migration ажиллуулаад API асаана.
set -e
alembic upgrade head
exec "$@"
