# Архитектур

```mermaid
flowchart LR
  U[Сурагч / Эцэг эх / Админ] --> FE[Next.js frontend]
  FE -->|REST/JSON| API[FastAPI backend]
  API --> DB[(PostgreSQL)]
  API --> S3[(MinIO / S3 — зураг)]
  API -->|/ocr /classify /mastery| ML[ML service]
  ML -. ажиллахгүй бол .-> FB[Гараар оруулах / сангаас сонгох]
```

## Үндсэн хүснэгтүүд (эхний хувилбар)

`users`, `parent_child_links`, `topics`, `topic_prerequisites`, `terms`, `problems`, `hints`,
`solution_steps`, `attempts`, `term_clicks`, `mastery`, `uploads`, `badges`, `user_badges`, `streaks`
