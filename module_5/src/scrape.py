"""
scrape.py
---------
A multi-threaded scraper for GradCafe survey results.
"""
import json
import os
import random
import re
import sys
import threading
import time
import urllib.request
import urllib.error
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from bs4 import BeautifulSoup

# ---------------- Regex Patterns ----------------
RESULT_HREF_RE = re.compile(r"^/result/(\d+)$")
TERM_RE = re.compile(r"\b(Fall|Spring|Summer)\s+\d{4}\b", re.I)
GPA_RE = re.compile(r"\bGPA\s*([0-4]\.\d{1,2}|[0-4])\b", re.I)
GRE_V_RE = re.compile(r"\bV\s*[:\-]?\s*(\d{2,3})\b", re.I)
GRE_Q_RE = re.compile(r"\bQ\s*[:\-]?\s*(\d{2,3})\b", re.I)
GRE_AW_RE = re.compile(r"\bAW\s*[:\-]?\s*([\d.]+)\b", re.I)


class GradCafeScraper:
    """
    Scrapes admission results from GradCafe with thread-safe management.
    """

    def __init__(self):
        # Grouped configuration to solve R0902 (Attributes)
        self.config = {
            "base_url": "https://www.thegradcafe.com/survey/index.php",
            "per_page": 50,
            "fixed_p": "52",
            "workers": int(os.getenv("SCRAPE_WORKERS", "4")),
            "timeout": float(os.getenv("SCRAPE_TIMEOUT", "12")),
            "retries": int(os.getenv("SCRAPE_RETRIES", "4")),
            "save_interval": int(os.getenv("SAVE_EVERY_PAGES", "10")),
            "jitter_min": float(os.getenv("JITTER_MIN", "0.10")),
            "jitter_max": float(os.getenv("JITTER_MAX", "0.35")),
            "start_page": 1
        }

        self.output_file = "applicant_data.json"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows) JHU-Scraper/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        # State attributes
        self.results = []
        self._seen_ids = set()
        self._lock = threading.Lock()

        self._load_existing_data()

    def _load_existing_data(self):
        """Loads existing JSON data to resume scraping."""
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, "r", encoding="utf-8") as file:
                    self.results = json.load(file) or []
                for row in self.results:
                    rid = (row or {}).get("result_id")
                    if rid:
                        self._seen_ids.add(str(rid))
                self.config["start_page"] = (len(self.results) // 20) + 1
            except (json.JSONDecodeError, OSError):
                self.results = []
                self._seen_ids = set()

    def _build_url(self, page_num: int) -> str:
        """Constructs the query URL."""
        params = {
            "pp": self.config["per_page"],
            "p": self.config["fixed_p"],
            "page": page_num,
            "sort": "newest",
        }
        return f"{self.config['base_url']}?{urlencode(params)}"

    def _fetch_html(self, page_num: int) -> bytes | None:
        """Fetches raw HTML with retries and jitter."""
        url = self._build_url(page_num)
        req = urllib.request.Request(url, headers=self.headers)
        time.sleep(random.uniform(self.config["jitter_min"], self.config["jitter_max"]))

        for attempt in range(self.config["retries"] + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.config["timeout"]) as resp:
                    return resp.read()
            except (urllib.error.URLError, TimeoutError, Exception):  # pylint: disable=broad-exception-caught
                sleep_time = (2 ** attempt) * 0.6 + random.uniform(0.0, 0.4)
                time.sleep(sleep_time)
        return None

    def _parse_scores(self, detail_blob: str) -> dict:
        """Helper to extract scores from text using regex. Reduces local vars."""
        term_m = TERM_RE.search(detail_blob)
        gpa_m = GPA_RE.search(detail_blob)
        gre_v = GRE_V_RE.search(detail_blob)
        gre_q = GRE_Q_RE.search(detail_blob)
        gre_aw = GRE_AW_RE.search(detail_blob)

        us_intl = None
        if re.search(r"\bInternational\b", detail_blob, re.I):
            us_intl = "International"
        elif re.search(r"\bAmerican\b", detail_blob, re.I):
            us_intl = "American"

        return {
            "term": term_m.group(0) if term_m else None,
            "US/International": us_intl,
            "GPA": gpa_m.group(1) if gpa_m else None,
            "GRE V Score": gre_v.group(1) if gre_v else None,
            "GRE Score": gre_q.group(1) if gre_q else None,
            "GRE AW": gre_aw.group(1) if gre_aw else None,
        }

    def _get_metadata(self, tds):
        """Extracts program and degree information from table cells."""
        spans = tds[1].find_all("span")
        prog = spans[0].get_text(" ", strip=True) if spans else tds[1].get_text(" ", strip=True)
        deg = spans[1].get_text(" ", strip=True) if len(spans) >= 2 else None
        return prog, deg

    def _get_detail_blob(self, rows, start_index):
        """Gathers detail rows and comments until the next main record starts."""
        idx_j = start_index + 1
        chunks, comment = [], ""
        while idx_j < len(rows):
            nxt = rows[idx_j]
            # If the next row is a main record row, we stop
            if len(nxt.find_all("td", recursive=False)) >= 4 and nxt.find("a", href=RESULT_HREF_RE):
                break
            if nxt.get_text(strip=True):
                chunks.append(nxt.get_text(" ", strip=True))
            if nxt.find("p"):
                comment = nxt.find("p").get_text(strip=True)
            idx_j += 1
        return " ".join(chunks), comment, idx_j

    def _extract_single_record(self, rows, start_index):
        """
        Parses a single applicant record. 
        Helper methods used to satisfy R0914 (Local Variables).
        """
        tr_main = rows[start_index]
        tds = tr_main.find_all("td", recursive=False)
        link = tr_main.find("a", href=RESULT_HREF_RE)

        if len(tds) < 4 or not link:
            return None, start_index + 1

        # Base entry info
        match = RESULT_HREF_RE.match(link.get("href", ""))

        # Delegate metadata and comment parsing to reduce local variable count
        prog, deg = self._get_metadata(tds)
        blob, comment, next_idx = self._get_detail_blob(rows, start_index)

        entry = {
            "result_id": match.group(1) if match else None,
            "url": f"https://www.thegradcafe.com{link['href']}",
            "university": tds[0].get_text(" ", strip=True),
            "program": prog,
            "Degree": deg,
            "date_added": tds[2].get_text(" ", strip=True),
            "status": tds[3].get_text(" ", strip=True),
            "comments": comment,
            **self._parse_scores(blob)
        }
        return entry, next_idx

    def _parse_page(self, page_num: int):
        """Fetch and parse one survey page."""
        html = self._fetch_html(page_num)
        if not html:
            return page_num, None, "error"
        try:
            soup = BeautifulSoup(html, "html.parser")
            tbody = soup.find("tbody")
            if not tbody:
                return page_num, [], "empty"
            rows = tbody.find_all("tr", recursive=False)
            entries, idx = [], 0
            while idx < len(rows):
                entry, next_idx = self._extract_single_record(rows, idx)
                if entry:
                    entries.append(entry)
                idx = next_idx
            return page_num, entries, "ok"
        except Exception:  # pylint: disable=broad-exception-caught
            return page_num, None, "error"

    def scrape_data(self, target_count: int = 30000):
        """Main multi-threaded execution method."""
        pages_done, consecutive_bad = 0, 0
        next_page = self.config["start_page"]

        with ThreadPoolExecutor(max_workers=self.config["workers"]) as ex:
            in_flight = {ex.submit(self._parse_page, p): p
                         for p in range(next_page, next_page + self.config["workers"])}
            next_page += self.config["workers"]

            while in_flight and len(self.results) < target_count:
                done, in_flight = wait(in_flight, timeout=14.0, return_when=FIRST_COMPLETED)
                for fut in done:
                    pages_done += 1
                    _, entries, status = fut.result()
                    if status == "ok" and entries:
                        consecutive_bad = 0
                        with self._lock:
                            for item in entries:
                                rid = str(item.get("result_id", ""))
                                if rid and rid not in self._seen_ids:
                                    self._seen_ids.add(rid)
                                    self.results.append(item)
                    else:
                        consecutive_bad += 1

                    self._print_progress(len(self.results), target_count, pages_done)
                    if pages_done % self.config["save_interval"] == 0:
                        self.save_data()

                    if consecutive_bad < 20 and len(self.results) < target_count:
                        in_flight.add(ex.submit(self._parse_page, next_page))
                        next_page += 1
        self.save_data()

    def _print_progress(self, current, total, pages):
        """Prints progress bar."""
        pct = (current / total) * 100
        sys.stdout.write(f"\rProgress: {current}/{total} ({pct:.2f}%) | Pages: {pages}")
        sys.stdout.flush()

    def save_data(self):
        """Atomically saves the collected results."""
        tmp = self.output_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as file:
            json.dump(self.results, file, ensure_ascii=False, indent=2)
        os.replace(tmp, self.output_file)


if __name__ == "__main__":
    TARGET = int(os.getenv("TARGET", "5000"))
    GradCafeScraper().scrape_data(TARGET)
