"""Entry point: `gunicorn wsgi:app` in production, `python wsgi.py` locally."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
