Module 2 Web Scraping & Data Cleaning (With help from AI)
--------------------------------------------------------------------------------------------------------

Eugene Buyanovsky
JHED ID: ebuyano1

Module Info
--------------------------------------------------------------------------------------------------------
Course: Modern Software Concepts in Python
Module: Module 2 – Web Scraping
Assignment: GradCafe Data Scraping and Cleaning
Due Date: February 1, 2026

Overview
--------------------------------------------------------------------------------------------------------
This project programmatically scrapes and collects publicly available graduate admissions data from website TheGradCafe (thegradcafe.com), 
puts it into JSON format, and standardizes program and university names using a locally hosted language model provided by my professor. 
The cleaned dataset is going to be used in later course modules as per the office hours. This assignment was challenging :)

Approach
Part 1 – Data Collection (scrape.py)
--------------------------------------------------------------------------------------------------------
Confirmed scraping permission and compliance by checking the site's robots.txt file (screenshot included - screenshot.jpg).
Used urllib.request to send HTTP requests and receive responses. 
(Confirmed during office hours that we need to use urllib not urllib3)
Parsed HTML using BeautifulSoup.
Extracted structured data using string methods and RegEx/regular expressions, including:

Program name
University
Applicant status and dates
Start term and degree
GPA and GRE scores (when available)
Domestic/International status

Implemented parallel page scraping with ThreadPoolExecutor to efficiently collect ~30,000 records. Thanks AI. 
Added deduplication, resume support, and atomic JSON writes for reliability. Also print progress to know if it is working.
Output saved to applicant_data.json.

Part 2 – Data Cleaning (clean.py)
--------------------------------------------------------------------------------------------------------
Preserved original scraped fields for traceability.
Used the local LLM standardizer in the llm_hosting/ folder that professor provided to download.
Ran the LLM as a local Flask API and processed rows in batches.
Added two standardized fields to each record:

llm-generated-program
llm-generated-university

Implemented caching to avoid repeated LLM calls for identical program strings! This was re-worked because originally ran for ~56 hours.
Output saved to llm_extend_applicant_data.json.

How to Run Scraping
--------------------------------------------------------------------------------------------------------
python scrape.py

How to do Cleaning (LLM API mode)
--------------------------------------------------------------------------------------------------------
python llm_hosting/app.py --serve
python clean.py

Performance Notes
--------------------------------------------------------------------------------------------------------
Scraping is parallelized and completes within the expected time window.
LLM cleaning is CPU dependant and may take several hours for ~30,000 records.
Caching significantly reduces runtime when duplicate program strings are present.
No external APIs or paid services are used.

Known Limitations
--------------------------------------------------------------------------------------------------------
Some rare program or university name variants may remain after standardization.
LLM inference speed depends on local hardware and available CPU resources. 
This is CPU bound and heavy - set to 6 Cores on mine.

Notes
--------------------------------------------------------------------------------------------------------
All data collected comes from publicly submitted user entries on TheGradCafe.
No authentication, restricted content, or prohibited scraping methods were used.

The TinyLlama model (.gguf) is not committed (Github) due to size and is automatically downloaded when running llm_hosting/app.py.
