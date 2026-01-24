Module 1 – Personal Developer Website (Flask)

This project is a personal developer website built using Python and the Flask web framework.
It is part of Module 1 for the course and demonstrates the fundamentals of web application
construction, including multi-page routing, HTML templates, CSS styling, and Flask blueprints.

--------------------------------------------------
Requirements
--------------------------------------------------
- Python 3.10 or newer
- Flask (installed via requirements.txt)

--------------------------------------------------
Project Structure
--------------------------------------------------
- run.py               : Entry point used to start the web application
- app/                 : Flask application package
- requirements.txt     : Python dependencies for environment reconstruction
- screenshots.pdf      : Screenshots of the running application (for submission)

--------------------------------------------------
How to Run the Application
--------------------------------------------------

Step 1: Create a virtual environment
    python -m venv .venv

Step 2: Activate the virtual environment (Windows / PowerShell)
    If script execution is blocked, run:
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

    Then activate the environment:
        .venv\Scripts\Activate

Step 3: Install required dependencies
    pip install -r requirements.txt

Step 4: Start the Flask application
    python run.py

Step 5: Open the application in a web browser
    http://localhost:8080

--------------------------------------------------
Notes
--------------------------------------------------
- The application runs on port 8080 as required.
- The web application uses Flask blueprints and HTML templates.
- Navigation is available on all pages and highlights the active tab.
- The environment can be fully reconstructed using requirements.txt.
