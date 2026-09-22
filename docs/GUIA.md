# Estudo Quiz — guia

App local de estudos em **3 fases**: 5 múltiplas escolhas, 5 lacunas com timer de 30s e 5 cenários com timer. No fim há resumo, o que revisar e retentativa com outras perguntas do banco.

## Tecnologias

| Camada | Stack |
| --- | --- |
| Web | Angular 19 + TypeScript, Vite (`ng serve` porta 5173), Bootstrap 5 |
| Contratos | `packages/contracts` (`@estudo-quiz/contracts`) |
| API | Django 6, DRF, SQLite |
| IA | Hugging Face Inference (`openai/gpt-oss-20b` por padrão) |

Token em `apps/api/.env` (`HF_TOKEN`). Não versionar.

## Como iniciar

```powershell
cd C:\Users\Pichau\estudo-quiz
.\.venv\Scripts\python.exe apps\api\manage.py migrate
.\.venv\Scripts\python.exe apps\api\manage.py runserver
```

```powershell
cd C:\Users\Pichau\estudo-quiz
npm install
npm run dev:web
```

Abra `http://localhost:5173`. Cadastre aula → **Gerar banco** → **Iniciar sessão**.

## Monorepo

```
estudo-quiz/
  apps/api/                 Django
    config/
    study/
      domain/               models
      services/             IA, amostragem, score, plano de estudo
      api/                  HTTP
  apps/web/                 Angular + Vite
    src/app/core/
    src/app/features/lessons/
    src/app/features/session/
    src/app/shared/
  packages/contracts/       tipos TS da API
```

O web **não** chama o Hugging Face. Só a API tem o token.

## Rotas da API

| Método | Rota | Função |
| --- | --- | --- |
| CRUD | `/api/lessons/` | Aulas |
| POST | `/api/lessons/:id/generate-bank/` | 8 MCQ + 8 cloze + 8 cenário |
| POST | `/api/lessons/:id/sessions/` | Amostra 5+5+5 (varia na retentativa) |
| GET | `/api/sessions/:id/` | Sessão sem gabarito |
| POST | `/api/sessions/:id/answers/` | Score, `phase_scores`, `study_plan` |

## Rotas do Angular

| URL | Feature |
| --- | --- |
| `/` | Lista de aulas |
| `/aulas/nova` `/aulas/:id/editar` | Cadastro |
| `/aulas/:id` | Detalhe, gerar banco, iniciar |
| `/sessoes/:id` | Runner das 3 fases |
| `/sessoes/:id/resultado` | Resumo e retentar |

`LessonService` e `SessionService` usam `http://localhost:8000/api`. Tipos vêm de `@estudo-quiz/contracts`.
