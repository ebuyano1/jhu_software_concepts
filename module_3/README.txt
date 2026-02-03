Module 3- Database Queries & Flask Analysis (with AI assistance to generate)
=================================================================================

Overview
--------------------------------------------------------------------------------
This project is part of Module 3: Database Queries. It loads cleaned GradCafe
application data (JSON) into a PostgreSQL relational database, performs SQL based
analysis to answer required questions in the instructions provided on Canvas, displays results on a dynamic Flask
webpage, and I document the limitations of using anonymous, self provided data on a public site.

The project builds directly on the cleaned and LLM produced dataset produced in Module 2.

---------------------------------------------------------------------------------
Assignment Objectives 
----------------------------------------------------------------
This project looks to meet all Module 3 requirements:

- Load cleaned GradCafe data into a PostgreSQL database using psycopg2
- Store data in a single relational table with the required schema
- Answer required analytical questions using SQL queries
- Display analysis results dynamically on a Flask webpage
- Implement interactive buttons to:
  - Pull new data from Module 2
  - Update analysis results
- Write a short essay on the limitations of anonymous, self-submitted data
- Produce all required deliverables and commit them to GitHub

----------------------------------------------------------------
Database Setup
----------------------------------------------------------------
This project uses PostgreSQL locally with a one table named applicants.

The table includes the below columns:
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
- degree (float)
- llm_generated_program (text)
- llm_generated_university (text)

----------------------------------------------------------------
Environment Setup
----------------------------------------------------------------
1. Install dependencies (from module_3):

    pip install -r requirements.txt

2. Configure database connection:

    Set the DATABASE_URL environment variable, for example (PowerShell):

    $env:DATABASE_URL="postgresql://USERNAME:PASSWORD@localhost:5432/DATABASE_NAME"

----------------------------------------------------------------
Loading Data into PostgreSQL
----------------------------------------------------------------
To load the cleaned GradCafe data into PostgreSQL:

    python load_data.py --json ../module_2/llm_extend_applicant_data.json

This script:
- Creates the applicants table if it does not exist
- Uses an UPSERT strategy to avoid duplicate records
- Can be run multiple times safely

----------------------------------------------------------------
SQL Analysis
----------------------------------------------------------------
All of the requested analysis questions from the assignment are implemented in
query_data.py, including:

1. Number of Fall 2025 applications
2. Percentage of international applicants
3. Average GPA and GRE metrics
4. Average GPA for American applicants (Fall 2025)
5. Acceptance rate for Fall 2025
6. Average GPA of accepted applicants (Fall 2025)
7. JHU Master’s Computer Science applications
8. PhD Computer Science acceptances at selected universities (2025)
9. Comparison using LLM-generated fields
10. Two additional exploratory questions

To view results in the console:

    python query_data.py

----------------------------------------------------------------
Flask Web Application
----------------------------------------------------------------
Start the Flask app:

    python app.py

Then open in a browser:

    http://localhost:5000/analysis

Webpage features:
- Displays all analysis questions and computed results
- Allows SQL queries to be toggled for transparency
- Includes two interactive buttons:
  - Pull Data: runs Module 2 scraping and cleaning scripts and upserts new data
  - Update Analysis: re-runs SQL queries and refreshes results

Per the requirements, the Update Analysis button is disabled while Pull Data
is running.

----------------------------------------------------------------
PDF Report of Answers
----------------------------------------------------------------
The assignment requirements include a PDF containing:
- Each question
- The computed answer
- The SQL query used
- A brief explanation of why the query answers the question

To generate the PDF:

    python generate_answers_pdf.py

This creates:
    answers_report.pdf

----------------------------------------------------------------
Limitations of the Data
----------------------------------------------------------------
A two paragraph summary of the limitations of using anonymous,
self submitted data on public site GradCafe is provided in:

    limitations.pdf

----------------------------------------------------------------
Deliverables Checklist
----------------------------------------------------------------
Deliverables for Module 3 are included:

- PostgreSQL database with GradCafe data
- load_data.py
- query_data.py
- Flask web application
- Pull Data and Update Analysis buttons
- limitations.pdf
- answers_report.pdf
- Screenshots of console output and running webpage (in the screenshots folder)
- README.txt
- requirements.txt

----------------------------------------------------------------
Notes
----------------------------------------------------------------
This project was developed and tested locally using Python 3.11 and PostgreSQL locally installed
All scripts are re runnable, and the database can be refreshed when needed.
