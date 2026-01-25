# Entry point for Module 1 Flask site.
# Run using: python run.py
# Required: host 0.0.0.0 (or localhost) and port 8080.

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
