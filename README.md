# Estudo Quiz

Sessão de estudo em 3 fases: MCQ, lacunas com timer e cenários. Angular + Vite no front, Django em camadas no back.

Guia: [docs/GUIA.md](docs/GUIA.md).

## Como iniciar

API:

```powershell
cd C:\Users\Pichau\estudo-quiz
.\.venv\Scripts\python.exe apps\api\manage.py migrate
.\.venv\Scripts\python.exe apps\api\manage.py runserver
```

Web (Vite via Angular, porta 5173):

```powershell
cd C:\Users\Pichau\estudo-quiz
npm install
npm run dev:web
```

- Interface: http://localhost:5173
- API: http://localhost:8000/api/
