# statistical_learning_group_assignment

## Quickstart

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Start backend (Django)

From the repository root:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r ../requirements.txt
python manage.py migrate
python manage.py runserver
```

Backend URL: http://127.0.0.1:8000/

### 2. Start frontend (Vite + React)

Open a second terminal in the repository root:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: shown in terminal after npm run dev (usually http://localhost:5173/)

Keep both terminals running while developing.