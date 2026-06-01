## Backend (FastAPI + SQLite + Alembic)

### Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
mkdir -p data
alembic upgrade head
```

### Rodar API
```bash
uvicorn app.main:app --reload --port 8000
```

### Execução manual
```bash
python run.py
```

### Endpoints
- `GET /health`
- `POST /run` (dispara coleta + geração md/html/pdf)

### Saídas
Geradas em `backend/data/outputs/`:
- `Resumo_Diario_Noticias_Grupo_Onnitech_Concorrentes_YYYYMMDD.md`
- `Resumo_Diario_Noticias_Grupo_Onnitech_Concorrentes_YYYYMMDD.html`
- `Resumo_Diario_Noticias_Grupo_Onnitech_Concorrentes_YYYYMMDD.pdf`

### Regras implementadas
- Janela de 6 meses
- Scraping/consulta pública via Google News RSS
- Remoção de duplicidade por similaridade de título
- Limite de repetição de mesma notícia: até 2 aparições em 30 dias
- Resumo em pt-BR (IA opcional por env; fallback determinístico)

### IA opcional para resumo
Configure no `.env`:
```env
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=gpt-4o-mini
```
Se não configurar, o sistema usa resumo determinístico.

### SMTP (preparado, desativado)
No `.env`:
```env
SMTP_ENABLED=false
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_TO=evandro.prieto@onnitech.com.br
```
