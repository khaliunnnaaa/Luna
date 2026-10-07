# Хамтран ажиллах дүрэм

## Branch
- `main` — үргэлж ажилладаг, шууд push хийхгүй.
- `feature/FR-03-ocr-upload`, `fix/login-error`, `docs/architecture` гэх мэт.

## Commit (Conventional Commits)
```
feat(backend): add placement test endpoint (FR-02)
fix(frontend): katex render on mobile
docs: update ER diagram
```

## Pull Request
1. Issue-тэй холбоно (`Closes #12`).
2. CI (lint + test) ногоон байх ёстой.
3. Багийн дор хаяж 1 хүн review хийнэ.

## Локал ажиллуулах
```bash
cp .env.example .env
docker compose up --build
# Frontend: http://localhost:3000   API docs: http://localhost:8000/docs   MinIO: http://localhost:9001
```
