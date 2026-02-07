Module 3 — Database Queries + Flask Analysis with help of AI
=====================================================================

This folder contains my Module 3 solution. It connects a PostgreSQL database
to a Flask web application and runs analytical SQL queries against GradCafe
application data.

Project flow
------------
1) Load cleaned GradCafe data into PostgreSQL (automatically via app or load_data.py)
2) Run analytical SQL queries (query_data.py)
3) Render the analysis results on a Flask webpage (app.py)
4) Generate a PDF report of the findings (generate_answers_pdf.py)

NOTE:
- This Flask app includes the required "Pull Data" and "Update Analysis" buttons.
- "Pull Data" runs in a background thread to allow the UI to remain responsive.


------------------------------------------------------------
0) Prerequisites
------------------------------------------------------------
- Python 3.10+
- PostgreSQL installed and running locally
- Module 2 completed (BeautifulSoup is included as a dependency because the overall project depends on Module 2’s output)
  (llm_extend_applicant_data_liv.json)

------------------------------------------------------------
1) Install dependencies
------------------------------------------------------------
From the module_3 directory, run:

    pip install -r requirements.txt

This installs:
- Flask (web application)
- psycopg2-binary (PostgreSQL driver)
- python-dotenv (for loading DATABASE_URL from a .env file)
- beautifulsoup4 (used by Module 2 during scraping)
- reportlab (used for generating the PDF report)

All dependencies should be installed inside the active virtual environment (.venv).

2) Configuration
-----------------
Create a .env file (optional) or rely on the defaults in db.py:
PGHOST=localhost
PGPORT=5432
PGUSER=postgres or module3_user
PGPASSWORD=password or whichever password you select
PGDATABASE=gradcafe or module3_db

3) SQL 
-----------------
All SQL execution is centralized in query_data.py, with helper functions that:
- Safely execute parameterized queries
- Keep database logic separate from Flask route logic
- Make it easy to reproduce results both in the console and in the Flask app
- Format answers into human-readable strings (e.g., adding % signs)


------------------------------------------------------------
Files overview
------------------------------------------------------------

llm_hosting/
    (Copied from Module 2)
    Folder containing the LLM logic required by clean.py.
    
db.py
    PostgreSQL connection helpers and context managers

load_data.py
    Creates the applicants table and upserts cleaned GradCafe data.
    Handles data type conversion (Strings -> Floats/Dates) and 
    URL-based ID extraction. Defaults to looking for the JSON file 
    in the local directory.

scrape.py & clean.py
    (Copied from Module 2 as per instructions)
    The scraper scripts used by the "Pull Data" button to fetch new 
    data locally within the module_3 environment.

query_data.py
    Contains all 11 SQL queries (9 required + 2 extra). Prints console 
    answers and exposes get_analysis() for the Flask app.

app.py
    Flask application. Routes:
      - GET /analysis (The Dashboard)
      - POST /pull-data (Background thread to reload DB using local scrape.py)
      - POST /update-analysis (Refreshes stats)

templates/analysis.html
    HTML template for rendering analysis results. Includes JavaScript 
    logic to disable buttons while data is pulling.

static/styles.css
    UI Styling for the analysis webpage (clean, modern CSS).

generate_answers_pdf.py
    Generates 'module3_analysis.pdf' containing all questions, 
    answers, logic, and SQL code for submission.

limitations.pdf
    Essay on the inherent limitations of anonymous/self-reported data.

llm_extend_applicant_data_liv.json
    The source data file used to populate the database.


------------------------------------------------------------
Summary
------------------------------------------------------------
This project shows:
- End to end integration of PostgreSQL with Python and Flask
- Repeatable load and insertion of JSON data into a database relational table
- Analytical SQL queries over real scraped data
- Dynamic rendering of answers + SQL in a web dashboard
- Concurrency control (threading) to manage long-running data pulls
- Automated PDF report generation