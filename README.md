# Estudo Quiz

Sessão de estudo em 3 fases: MCQ, lacunas com timer e cenários. Angular + Vite no front, Django no back.

Guia completo: [docs/GUIA.md](docs/GUIA.md).

## Subir local (mínimo)

Na raiz `C:\Users\Pichau\estudo-quiz`.

### Primeira vez

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r apps\api\requirements.txt
copy apps\api\.env.example apps\api\.env
npm install
.\.venv\Scripts\python.exe apps\api\manage.py migrate
```

Coloque o token do Hugging Face em `apps\api\.env`:

```
HF_TOKEN=hf_...
```

### Todo dia (2 terminais)

```powershell
npm run api
```

```powershell
npm run web
```

- Front: http://localhost:5173
- API: http://localhost:8000
