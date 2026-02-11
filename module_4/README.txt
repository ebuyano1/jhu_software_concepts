------------------------------------------------------------
Module 4: Testing, CI, & Documentation with AI
------------------------------------------------------------

Overview
========
This module focuses on hardening the GradCafe Analytics application.
I have implemented a comprehensive test suite achieving 100% code coverage, refactored the application 
to use the "Factory Pattern" for better testability, and generated professional API documentation using Sphinx.
This project is now fully integrated with GitHub Actions for Continuous Integration (CI).

------------------------------------------------------------
1) Testing (100% Coverage & CI/CD)
------------------------------------------------------------
I used Pytest to ensure reliability across all layers of the application (Database, Web Routes, and ETL Logic).
The suite enforces a strict 100% coverage threshold.

Key Testing Features:
- **Mocking:** All external dependencies (scraper, network calls, file system) are mocked using `unittest.mock`. 
    Tests never hit the live internet.
- **Factory Pattern:** Refactored `src/app.py` to use `create_app()` so a fresh app instance is created for every test.
- **Database Isolation:** Tests run on a temporary `gradcafe_test` database. I implemented a robust retry loop with connection polling in `conftest.py` to handle CI/CD latency.
- **Stable Selectors:** The HTML templates (e.g., `analysis.html`) use `data-testid` attributes to ensure tests are resilient to UI changes.

How to Run Tests Locally:
-------------------------
1. Activate your virtual environment.
2. Ensure your PYTHONPATH includes the source directory:
   export PYTHONPATH=src  # (On Windows: set PYTHONPATH=src)

3. Run the full suite with markers:
   pytest -m "web or buttons or analysis or db or integration"

4. Check Coverage (Must show 100%):
   pytest --cov=src --cov-report=term-missing --cov-fail-under=100

------------------------------------------------------------
2) Documentation (Sphinx & Read the Docs)
------------------------------------------------------------
I generated full API documentation that covers the Scraper, Cleaner, Loader, and Flask application logic.
The documentation is hosted live on Read the Docs.

[Live Documentation]: <INSERT YOUR READ THE DOCS LINK HERE>

To build documentation manually:
1. Navigate to the docs folder:
   cd docs
2. Run the build command:
   .\make.bat html  # (On Windows)
   make html        # (On Linux/Mac)
3. Open `docs/_build/html/index.html` in your browser.

------------------------------------------------------------
3) Architecture & Operational Notes
------------------------------------------------------------
The application logic has been moved to a `src/` directory for better structural organization.

Web/ETL/DB Roles:
- **Web (Flask):** Handles UI and triggers background jobs via `src/app.py`.
- **ETL (Load/Clean):** Runs in a background thread to keep the UI responsive.
- **DB (Postgres):** Stores structured applicant data using `src/db.py` connection management.

Concurrency & Gating:
- I implemented a thread lock (`_pull_lock`) in the app factory.
- If a user clicks "Pull Data" while a job is running, the server returns a `409 Conflict` (Busy) response to prevent race conditions.

Idempotency & Robustness:
- **Schema Safety:** `src/load_data.py` uses `CREATE TABLE IF NOT EXISTS` to prevent crashes during restarts.
- **Upserts:** The loader uses `ON CONFLICT DO UPDATE` to ensure running the scraper multiple times does not create duplicate rows.

------------------------------------------------------------
4) Setup & Installation
------------------------------------------------------------
Prerequisites:
- Python 3.10+
- PostgreSQL installed locally
- Git

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
.github/workflows/
   Contains `tests.yml` which defines the CI/CD pipeline for 100% coverage.

tests/
   Contains the Pytest suite:
   - `conftest.py`: Fixtures for app creation and robust DB teardown.
   - `test_db_coverage.py`: Targeted tests for edge cases (DSN overrides, schema existence).
   - `test_*.py`: Feature tests for routes, buttons, and analysis.

src/
   - `app.py`: The Flask application using Blueprint and Factory Pattern.
   - `db.py`: Database connection manager with override support for testing.
   - `load_data.py`: Handles JSON loading, schema creation, and Upserts.
   - `query_data.py`: Centralized SQL logic for analysis questions.
   - `scrape.py` & `clean.py`: Logic used by the background worker.

docs/
   Contains Sphinx configuration (`conf.py`) and `.rst` source files.

------------------------------------------------------------
2) Documentation (Sphinx & Read the Docs)
------------------------------------------------------------
I generated full API documentation that covers the Scraper, Cleaner, Loader, and Flask application logic.
The documentation is hosted live on Read the Docs.

[Live Documentation]: https://jhu-software-concepts-p.readthedocs.io/en/latest/

To build documentation manually:
1. Navigate to the docs folder:
   cd docs
2. Run the build command:
   .\make.bat html  # (On Windows)
   make html        # (On Linux/Mac)
3. Open `docs/_build/html/index.html` in your browser.

-------------------------------------------------------------------

To Run
-------------------------------------------------------------------
$env:PGUSER="module3_user"
$env:PGPASSWORD="NewStrongPass123!"

# This ensures all tests, including the one for line 19, are executed
pytest --cov=src --cov-report=term-missing tests/test_db_coverage.py tests/


Coverage Summary
-------------------------------------------------------------------

# In your PowerShell terminal:
pytest --cov=src --cov-report=term-missing > coverage_summary.txt

.................................                                        [100%]
=============================== tests coverage ================================
______________ coverage: platform win32, python 3.10.11-final-0 _______________

Name                Stmts   Miss Branch BrPart  Cover   Missing
---------------------------------------------------------------
src\app.py             66      0     14      0   100%
src\db.py              38      0      6      0   100%
src\load_data.py       68      0     22      0   100%
src\query_data.py      69      0      8      0   100%
---------------------------------------------------------------
TOTAL                 241      0     50      0   100%
Required test coverage of 100% reached. Total coverage: 100.00%
33 passed in 4.65s
