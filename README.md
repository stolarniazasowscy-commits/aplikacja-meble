# Minimal FastAPI app

## Uruchomienie lokalnie

1. Utwórz i aktywuj środowisko wirtualne (opcjonalnie, ale zalecane):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Zainstaluj zależności:
   ```bash
   pip install -r requirements.txt
   ```
3. Uruchom serwer:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Otwórz `http://127.0.0.1:8000/` — endpoint `/` zwraca:
   ```json
   {"status": "ok"}
   ```
