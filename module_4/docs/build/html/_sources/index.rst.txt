Welcome to GradCafe Analytics's documentation!
==============================================

**GradCafe Analytics** is a Python-based tool for scraping, cleaning, storing, and analyzing 
graduate school admission data from TheGradCafe.com.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api

Architecture
============
The system is divided into three core layers:

* **Web Layer (Flask):** Serves the analysis dashboard and provides interactive buttons for data orchestration.
* **ETL Layer (Python):** Handles the scraping (BeautifulSoup), cleaning (LLM standardization), and loading (psycopg2) of data.
* **Database Layer (PostgreSQL):** Stores cleaned applicant records using a structured schema with uniqueness constraints on the ``p_id``.

Setup & Operational Notes
=========================
**Requirements**
* Python 3.10+
* PostgreSQL 15+

**Environment Variables**
* ``DATABASE_URL``: Connection string (e.g., ``postgresql://user:pass@localhost:5432/dbname``).

**Idempotency & Uniqueness**
The system prevents duplicate records by extracting a unique ``p_id`` from the GradCafe result URL. If a pull is attempted with existing data, the database performs an ``UPSERT`` to maintain data integrity without duplication.

**Busy-State Policy**
To prevent database corruption, the application implements a locking mechanism. If a "Pull Data" job is active, subsequent pull or update requests will return a ``409 Conflict``.

Testing Guide
=============
Tests are organized by functionality and must be run using Pytest.

**Running Tests**
To run the full suite with coverage:
.. code-block:: powershell

   pytest --cov=src --cov-report=term-missing

**Markers**
* ``web``: HTML structure and page loads.
* ``buttons``: Endpoint behavior and busy gating.
* ``analysis``: Formatting and decimal precision.
* ``db``: Database schema and idempotency.
* ``integration``: End-to-end data flows.

Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`