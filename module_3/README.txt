Module 3 — Database Queries & Flask Analysis
================================================

Overview
------------------------------------------------
This project completes the requirements for Module 3: Database Queries. It loads
GradCafe application data from JSON into a PostgreSQL database, answers the required
analytical questions using SQL, and presents the results through a dynamic Flask
web application.

Based on feedback from the instructor on Module 2 data quality, this module uses
the instructor-provided dataset for analysis to ensure correctness,
consistency, and reproducibility of results.

------------------------------------------------
Assignment Objectives
------------------------------------------------
This submission meets all stated Module 3 requirements:

- Load application data into PostgreSQL using psycopg2
- Store the data in a single relational table with a defined schema
- Answer required analytical questions using SQL queries
- Display results dynamically on a Flask webpage
- Provide interactive controls to:
  - Pull Data into the database
  - Update Analysis results
- Generate a PDF report of all answers and SQL queries
- Document limitations of anonymous, self-reported data
- Commit all required deliverables to GitHub

------------------------------------------------
Database Design
------------------------------------------------
The project uses a single PostgreSQL table named applicants with the following
columns:

- p_id (integer, primary key)
- program (text)
- comments (text)
- date_added (date)
- url (text)
- status (text)
- term (text)
- us_or_international (text)
- gpa (float)
- gre (float)
- gre_v (float)
- gre_aw (float)
- degree (text)
- llm_generated_program (text)
- llm_generated_university (text)

------------------------------------------------
Environment Setup
------------------------------------------------
1. Install dependencies from the `module_3` directory:

    pip install -r requirements.txt

2. Configure the PostgreSQL connection using an environment variable:

    (PowerShell)
    $env:DATABASE_URL="postgresql://USERNAME:PASSWORD@localhost:5432/DATABASE_NAME"

------------------------------------------------
Loading Data into PostgreSQL
------------------------------------------------
Data is loaded using `load_data.py`. To load the instructor provided dataset and
reset the database table:

    python load_data.py --json ../module_2/llm_extend_applicant_data_liv.json --reset

This script:
- Creates the applicants table if it does not already exist
- Clears existing records when `--reset` is used
- Inserts the dataset into PostgreSQL in a repeatable way

------------------------------------------------
SQL Analysis
------------------------------------------------
All required analytical questions are implemented in `query_data.py`, including:

1. Number of Fall 2025 applications
2. Percentage of international applicants
3. Average GPA and GRE metrics
4. Average GPA for American applicants (Fall 2025)
5. Acceptance rate for Fall 2025
6. Additional required and exploratory questions

To run the analysis directly in the console:

    python query_data.py

------------------------------------------------
Flask Web Application
------------------------------------------------
Start the Flask application:

    python app.py

Then open:

    http://localhost:5000/analysis

The web interface:
- Displays each question with its computed answer
- Allows SQL queries to be toggled for transparency
- Includes two interactive buttons:
  - **Pull Data**: loads the JSON dataset into PostgreSQL in the background
  - **Update Analysis**: refreshes results from the database

As required, Update Analysis is disabled while Pull Data is running.

------------------------------------------------
PDF Answers Report
------------------------------------------------
A formatted PDF containing all required answers is generated using:

    python generate_answers_pdf.py

This produces:

    answers_report.pdf

The PDF includes:
- Each question
- The computed answer
- The SQL query used
- A short explanation of why the query answers the question

------------------------------------------------
Limitations of the Data
------------------------------------------------
A written discussion of the limitations of using anonymous, self-reported data
from GradCafe is provided in:

    limitations.pdf

------------------------------------------------
Deliverables Checklist
------------------------------------------------
This repository includes:

- PostgreSQL-backed analysis
- load_data.py
- query_data.py
- Flask web application
- Pull Data and Update Analysis controls
- answers_report.pdf
- limitations.pdf
- Screenshots of console output and the running webpage
- README.txt
- requirements.txt

------------------------------------------------
Notes
------------------------------------------------
The project was developed and tested locally using Python 3.11 and PostgreSQL.
All scripts are rerunnable, and the database can be safely refreshed as needed.
