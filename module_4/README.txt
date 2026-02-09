------------------------------------------------------------
Module 4: Testing, CI, & Documentation with AI
------------------------------------------------------------

Overview
========
This module focuses on hardening the GradCafe Analytics application. 
I have implemented a comprehensive test suite achieving 100% code coverage, refactored the application 
to use the "Factory Pattern" for better testability, and generated professional API documentation using Sphinx.

------------------------------------------------------------
1) Testing (100% Coverage)
------------------------------------------------------------
I used Pytest to ensure reliability across all layers of the application (Database, Web Routes, and ETL Logic).

Key Testing Features:
- Mocking: All external dependencies (scraper, network calls, file system) are mocked using `unittest.mock`. 
  Tests never hit the live internet.
- Factory Pattern: Refactored `app.py` to use `create_app()` so a fresh app instance is created for every test.
- Database Isolation: Tests run on a temporary `gradcafe_test` database that is wiped clean after every function.

How to Run Tests:
-----------------
1. Activate your virtual environment.
2. Run the full suite:
   pytest -m "web or buttons or analysis or db or integration"

3. Check Coverage (Should show 100%):
   pytest --cov=. --cov-report=term-missing

------------------------------------------------------------
2) Documentation (Sphinx)
------------------------------------------------------------
I generated full API documentation that covers the Scraper, Cleaner, Loader, and Flask application logic.

To view the documentation:
1. Navigate to: docs/build/html/index.html
2. Open the file in your web browser.

To rebuild documentation manually:
   cd docs
   .\make.bat html

------------------------------------------------------------
3) Architecture & Operational Notes
------------------------------------------------------------
Web/ETL/DB Roles:
- **Web (Flask):** Handles UI and triggers background jobs.
- **ETL (Load/Clean):** Runs in a background thread to keep the UI responsive.
- **DB (Postgres):** Stores structured applicant data.

Concurrency & Gating:
- I implemented a thread lock (`_pull_lock`) in `app.py`.
- If a user clicks "Pull Data" while a job is running, the server returns a `409 Conflict` (Busy) response to prevent race conditions.

Idempotency:
- The database loader uses `ON CONFLICT DO UPDATE` (Upsert). Running the scraper multiple times will not create duplicate rows.

------------------------------------------------------------
4) Setup & Installation
------------------------------------------------------------
Prerequisites:
- Python 3.10+
- PostgreSQL installed locally
- Module 2 output files (optional, as mocks are provided for testing)

Installation:
   pip install -r requirements.txt

Configuration (.env):
   PGHOST=localhost
   PGPORT=5432
   PGUSER=postgres
   PGPASSWORD=your_password
   PGDATABASE=gradcafe

------------------------------------------------------------
Files Overview
------------------------------------------------------------
tests/
   Contains the Pytest suite (e.g., test_real_logic.py, test_force_coverage.py).

docs/
   Contains Sphinx configuration and source files.

app.py
   The Flask application (now using Blueprint and Factory Pattern).

load_data.py
   Handles JSON loading and database Upserts.

query_data.py
   Centralized SQL logic for analysis questions.

scrape.py & clean.py
   Module 2 logic used by the background worker.

generate_answers_pdf.py
   Generates the PDF report for Module 3 submission.