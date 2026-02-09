import urllib.request
import urllib.error
from urllib.parse import urlencode
from bs4 import BeautifulSoup
import re
import json
import time
import sys
import random
import os
import threading
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

# ---------------- Regex Patterns ----------------
# Each GradCafe result has a stable URL like /result/992350.
# We use this as our primary key so we can de-dupe cleanly across pages / runs.
RESULT_HREF_RE = re.compile(r"^/result/(\d+)$")

# The “term” usually appears in the detail/badge text as something like “Fall 2026”.
TERM_RE = re.compile(r"\b(Fall|Spring|Summer)\s+\d{4}\b", re.I)

# These fields (GPA / GRE) often show up in the detail rows as short strings,
# so we extract them using small, targeted regex patterns.
GPA_RE = re.compile(r"\bGPA\s*([0-4]\.\d{1,2}|[0-4])\b", re.I)
GRE_V_RE = re.compile(r"\bV\s*[:\-]?\s*(\d{2,3})\b", re.I)
GRE_Q_RE = re.compile(r"\bQ\s*[:\-]?\s*(\d{2,3})\b", re.I)
GRE_AW_RE = re.compile(r"\bAW\s*[:\-]?\s*([\d.]+)\b", re.I)


class GradCafeScraper:
    """
    Uses urllib.request + BeautifulSoup (lecture topics only).

    IMPORTANT FIX (from debug HTML):
      - Pagination uses `page=<n>` not `p=<n>`
      - The links show p=52 constant, and page=2,3,4... for pagination
        Example: /survey/index.php?q=&t=a&pp=50&p=52&page=2

    This scraper:
      - fetches pages in parallel (modest workers)
      - groups multi-<tr> records (main row + detail rows + optional comment row)
      - dedupes by result_id
      - saves atomically + can resume
    """

    def __init__(self):
        # Base admissions “survey” page (this is the big results listing)
        self.base_url = "https://www.thegradcafe.com/survey/index.php"

        # We write all collected results here (also used for resume)
        self.output_file = "applicant_data.json"

        # Per-page requested. The site may return fewer, but we request 50 for efficiency.
        self.per_page = 50

        # Key detail from debugging: GradCafe expects p=52 to be present as a constant.
        # The actual page number is controlled by `page=<n>`.
        self.fixed_p = "52"

        # Parallelism + timeouts are configurable via env vars, so you can tune
        # based on how fast/slow the site is responding for you.
        self.max_workers = int(os.getenv("SCRAPE_WORKERS", "4"))
        self.timeout = float(os.getenv("SCRAPE_TIMEOUT", "12"))
        self.max_retries = int(os.getenv("SCRAPE_RETRIES", "4"))
        self.save_every_pages = int(os.getenv("SAVE_EVERY_PAGES", "10"))

        # Small random delay per request helps avoid hammering the site and reduces
        # the chance of rate-limits or temporary blocks.
        self.jitter_min = float(os.getenv("JITTER_MIN", "0.10"))
        self.jitter_max = float(os.getenv("JITTER_MAX", "0.35"))

        # Basic headers so we look like a normal browser request.
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JHU-Software-Concepts-Scraper/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Results collection + a set for fast de-duplication by result_id.
        self.results = []
        self._seen_ids = set()

        # Lock is only needed when multiple threads append to shared structures.
        self._lock = threading.Lock()

        # If there is no prior data, we start at page 1.
        self.start_page = 1

        # Resume support:
        # If applicant_data.json exists, load it and continue scraping where we left off.
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, "r", encoding="utf-8") as f:
                    self.results = json.load(f) or []
                for r in self.results:
                    rid = (r or {}).get("result_id")
                    if rid:
                        self._seen_ids.add(str(rid))

                # The site tends to return ~20 “main records” per page.
                # This is a rough estimate, but good enough for resuming without starting over.
                self.start_page = (len(self.results) // 20) + 1
                print(f"Resuming at page {self.start_page} ({len(self.results)} records)")
            except Exception:
                # If the JSON is corrupted or unreadable for any reason, start fresh.
                self.results = []
                self._seen_ids = set()
                self.start_page = 1

    def _build_url(self, page_num: int) -> str:
        # IMPORTANT:
        #  - `page` is the real page number.
        #  - `p` remains constant (as seen in GradCafe’s own pagination links).
        params = {
            "q": "",
            "t": "a",
            "pp": self.per_page,
            "p": self.fixed_p,
            "page": page_num,
            "sort": "newest",  # makes pagination stable and predictable
        }
        return f"{self.base_url}?{urlencode(params)}"

    def _fetch_html(self, page_num: int) -> bytes | None:
        # Build request for a specific survey results page
        url = self._build_url(page_num)
        req = urllib.request.Request(url, headers=self.headers)

        # Polite jitter to avoid bursts (helps with stability in long runs)
        time.sleep(random.uniform(self.jitter_min, self.jitter_max))

        # Retry loop: handle transient errors like 429 / 5xx / network hiccups.
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return resp.read()

            except urllib.error.HTTPError as e:
                # Common “temporary” errors: backoff and try again.
                if e.code in (429, 500, 502, 503, 504):
                    backoff = (2 ** attempt) * 0.6 + random.uniform(0.0, 0.4)
                    time.sleep(backoff)
                    continue
                # For other HTTP errors, treat as non-recoverable for this page.
                return None

            except urllib.error.URLError:
                # Network/DNS/etc. temporary failure — backoff and retry.
                backoff = (2 ** attempt) * 0.6 + random.uniform(0.0, 0.4)
                time.sleep(backoff)
                continue

            except Exception:
                # Catch-all safety: we don’t want a single weird error to kill the run.
                backoff = (2 ** attempt) * 0.6 + random.uniform(0.0, 0.4)
                time.sleep(backoff)
                continue

        # If we exhausted retries, mark the page as failed.
        return None

    def _parse_page(self, page_num: int):
        """
        Fetch and parse one survey page.

        Returns:
          (page_num, entries, status)

        status values:
          - "ok": parsed successfully (entries may still be empty)
          - "empty": HTML parsed, but expected table/rows not found
          - "error": request failed or parsing raised an exception
        """
        html = self._fetch_html(page_num)
        if not html:
            return page_num, None, "error"

        try:
            # Parse the HTML into a BeautifulSoup DOM tree
            soup = BeautifulSoup(html, "html.parser")

            # The survey results are inside a <tbody> with a series of <tr> rows.
            tbody = soup.find("tbody")
            if not tbody:
                return page_num, [], "empty"

            # IMPORTANT:
            # GradCafe uses multiple <tr> rows per application record:
            #   - a “main” row with key columns (school/program/status/etc.)
            #   - one or more “detail” rows with badges (term, GPA, American/International, etc.)
            #   - sometimes a comment row with a <p> element
            rows = tbody.find_all("tr", recursive=False)
            if not rows:
                return page_num, [], "empty"

            entries = []
            i = 0
            while i < len(rows):
                tr = rows[i]
                tds = tr.find_all("td", recursive=False)

                # If the row does not look like a “main” row, skip it.
                # Main rows have at least 4 direct <td> cells.
                if len(tds) < 4:
                    i += 1
                    continue

                # The presence of a /result/<id> link is what really identifies a main row.
                a = tr.find("a", href=RESULT_HREF_RE)
                if not a:
                    i += 1
                    continue

                # Extract the stable record identifier from the URL
                m = RESULT_HREF_RE.match(a.get("href", ""))
                result_id = m.group(1) if m else None
                url = f"https://www.thegradcafe.com{a['href']}"

                # Column 0: Institution name
                school = tds[0].get_text(" ", strip=True)

                # Column 1: Program cell often includes multiple spans:
                #   - span[0] is the major/program name
                #   - span[1] is the degree type (e.g., PhD, Masters)
                prog_cell = tds[1]
                spans = prog_cell.find_all("span")
                program = spans[0].get_text(" ", strip=True) if len(spans) >= 1 else prog_cell.get_text(" ", strip=True)
                degree = spans[1].get_text(" ", strip=True) if len(spans) >= 2 else None

                # Column 2: Date added to the GradCafe survey listing
                date_added = tds[2].get_text(" ", strip=True) if len(tds) >= 3 else None

                # Column 3: Status/decision text (e.g., “Rejected on 27 Jan”)
                status = tds[3].get_text(" ", strip=True) if len(tds) >= 4 else None

                # Now gather the “detail rows” that belong to this record.
                # We keep consuming rows until we reach the next main record row.
                j = i + 1
                detail_text_chunks = []
                comment = ""

                while j < len(rows):
                    nxt = rows[j]
                    nxt_tds = nxt.find_all("td", recursive=False)

                    # A new main record begins when:
                    #   - it has >= 4 direct td cells, AND
                    #   - it contains another /result/<id> link
                    if len(nxt_tds) >= 4 and nxt.find("a", href=RESULT_HREF_RE):
                        break

                    # The badge/detail rows usually contain the term, GPA, GRE, etc.
                    txt = nxt.get_text(" ", strip=True)
                    if txt:
                        detail_text_chunks.append(txt)

                    # The optional “comment” row includes a <p> tag (if the user left notes).
                    p = nxt.find("p")
                    if p and p.get_text(strip=True):
                        comment = p.get_text(strip=True)

                    j += 1

                # This is the combined text for all detail rows,
                # which we then mine with regex for specific values.
                detail_blob = " ".join(detail_text_chunks)

                # Term (Fall/Spring/Summer + year)
                term = None
                term_m = TERM_RE.search(detail_blob)
                if term_m:
                    term = term_m.group(0)

                # Degree’s country of origin (American vs International)
                us_intl = None
                if re.search(r"\bInternational\b", detail_blob, re.I):
                    us_intl = "International"
                elif re.search(r"\bAmerican\b", detail_blob, re.I):
                    us_intl = "American"

                # GPA (if present in badge text)
                gpa = None
                gpa_m = GPA_RE.search(detail_blob)
                if gpa_m:
                    gpa = gpa_m.group(1)

                # GRE scores (if present). Many records omit these entirely.
                v = GRE_V_RE.search(detail_blob)
                q = GRE_Q_RE.search(detail_blob)
                aw = GRE_AW_RE.search(detail_blob)

                # Create the normalized dictionary for this record.
                # Note: result_id is our stable de-dupe key.
                entries.append(
                    {
                        "result_id": result_id,
                        "url": url,
                        "university": school,
                        "program": program,
                        "Degree": degree,
                        "date_added": date_added,
                        "status": status,
                        "term": term,
                        "US/International": us_intl,
                        "GPA": gpa,
                        "GRE V Score": v.group(1) if v else None,
                        "GRE Score": q.group(1) if q else None,
                        "GRE AW": aw.group(1) if aw else None,
                        "comments": comment or "",
                    }
                )

                # Move i to the next main record row
                i = j

            return page_num, entries, "ok"
        except Exception:
            # If anything unexpected happens (HTML change, parse error, etc.),
            # mark this page as an error so the caller can keep going.
            return page_num, None, "error"

    def scrape_data(self, target: int = 30000):
        # Counters used for progress reporting and for detecting long runs of failures.
        pages_done = 0
        consecutive_bad = 0

        # If we hit too many pages in a row that are empty/error, assume we’re done or blocked.
        max_consecutive_bad = max(12, self.max_workers * 4)

        # Start where we left off (or page 1 if no prior output exists).
        next_page = self.start_page

        # ThreadPoolExecutor lets us overlap network requests (I/O-bound),
        # which makes scraping MUCH faster than strictly sequential fetching.
        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            in_flight = set()

            # Prime the pipeline: launch the first N page fetch/parse tasks.
            for _ in range(self.max_workers):
                in_flight.add(ex.submit(self._parse_page, next_page))
                next_page += 1

            # Main loop: keep going until we hit the target number of records,
            # or until we decide the site is no longer giving useful pages.
            while in_flight and len(self.results) < target:
                done, in_flight = wait(
                    in_flight,
                    timeout=max(5.0, self.timeout + 2.0),
                    return_when=FIRST_COMPLETED,
                )

                # If nothing finished within the wait timeout, pause briefly and try again.
                if not done:
                    time.sleep(0.2)
                    continue

                for fut in done:
                    try:
                        page_num, entries, status = fut.result()
                    except Exception:
                        page_num, entries, status = None, None, "error"

                    pages_done += 1

                    # If we got good entries, append only the new ones.
                    # The lock protects self.results / self._seen_ids from race conditions.
                    if status == "ok" and entries:
                        consecutive_bad = 0
                        with self._lock:
                            for e in entries:
                                rid = str((e or {}).get("result_id") or "")
                                if not rid or rid in self._seen_ids:
                                    continue
                                self._seen_ids.add(rid)
                                self.results.append(e)
                    else:
                        # Empty/error pages count toward the “bad streak” detector.
                        consecutive_bad += 1

                    # Progress bar-style output (single updating line in the terminal).
                    pct = (len(self.results) / target) * 100
                    sys.stdout.write(
                        f"\rProgress: {len(self.results)}/{target} ({pct:.2f}%) | "
                        f"Pages done: {pages_done} | Bad streak: {consecutive_bad}"
                    )
                    sys.stdout.flush()

                    # Periodic saving so we can resume if anything interrupts the run.
                    if pages_done % self.save_every_pages == 0:
                        self.save_data()

                    # If we hit too many bad pages in a row, stop gracefully.
                    if consecutive_bad >= max_consecutive_bad:
                        print("\nStopping early: too many consecutive empty/error pages (end or blocked).")
                        in_flight.clear()
                        break

                    # Keep the pipeline full by submitting the next page task.
                    if len(self.results) < target:
                        in_flight.add(ex.submit(self._parse_page, next_page))
                        next_page += 1

        # Final save at the end (ensures output_file is up to date)
        self.save_data()
        print("\nDone.")

    def save_data(self):
        # Write to a temp file first, then atomically replace the real output.
        # This helps prevent partial/corrupted JSON files if the program is interrupted.
        tmp = self.output_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.output_file)


if __name__ == "__main__":
    # Allow overriding the target from the environment, but default to 30,000.
    target = int(os.getenv("TARGET", "30000"))

    # Kick off the scraping run.
    GradCafeScraper().scrape_data(target)
