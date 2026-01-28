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
RESULT_HREF_RE = re.compile(r"^/result/(\d+)$")
TERM_RE = re.compile(r"\b(Fall|Spring|Summer)\s+\d{4}\b", re.I)

GPA_RE = re.compile(r"\bGPA\s*([0-4]\.\d{1,2}|[0-4])\b", re.I)
GRE_V_RE = re.compile(r"\bV\s*[:\-]?\s*(\d{2,3})\b", re.I)
GRE_Q_RE = re.compile(r"\bQ\s*[:\-]?\s*(\d{2,3})\b", re.I)
GRE_AW_RE = re.compile(r"\bAW\s*[:\-]?\s*([\d.]+)\b", re.I)


class GradCafeScraper:
    """
    Uses urllib.request + BeautifulSoup (lecture topics only).

    IMPORTANT FIX (from your debug HTML):
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
        self.base_url = "https://www.thegradcafe.com/survey/index.php"
        self.output_file = "applicant_data.json"

        self.per_page = 50

        # Key: p=52 is required by site pagination structure (from debug HTML)
        self.fixed_p = "52"

        self.max_workers = int(os.getenv("SCRAPE_WORKERS", "4"))
        self.timeout = float(os.getenv("SCRAPE_TIMEOUT", "12"))
        self.max_retries = int(os.getenv("SCRAPE_RETRIES", "4"))
        self.save_every_pages = int(os.getenv("SAVE_EVERY_PAGES", "10"))

        self.jitter_min = float(os.getenv("JITTER_MIN", "0.10"))
        self.jitter_max = float(os.getenv("JITTER_MAX", "0.35"))

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JHU-Software-Concepts-Scraper/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        self.results = []
        self._seen_ids = set()
        self._lock = threading.Lock()
        self.start_page = 1

        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, "r", encoding="utf-8") as f:
                    self.results = json.load(f) or []
                for r in self.results:
                    rid = (r or {}).get("result_id")
                    if rid:
                        self._seen_ids.add(str(rid))
                # resume by assuming roughly 20 main records per page
                self.start_page = (len(self.results) // 20) + 1
                print(f"Resuming at page {self.start_page} ({len(self.results)} records)")
            except Exception:
                self.results = []
                self._seen_ids = set()
                self.start_page = 1

    def _build_url(self, page_num: int) -> str:
        # IMPORTANT: use page=<n> for pagination, keep p=52 fixed (matches site)
        params = {
            "q": "",
            "t": "a",
            "pp": self.per_page,
            "p": self.fixed_p,
            "page": page_num,
            "sort": "newest",
        }
        return f"{self.base_url}?{urlencode(params)}"

    def _fetch_html(self, page_num: int) -> bytes | None:
        url = self._build_url(page_num)
        req = urllib.request.Request(url, headers=self.headers)

        time.sleep(random.uniform(self.jitter_min, self.jitter_max))

        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return resp.read()

            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504):
                    backoff = (2 ** attempt) * 0.6 + random.uniform(0.0, 0.4)
                    time.sleep(backoff)
                    continue
                return None

            except urllib.error.URLError:
                backoff = (2 ** attempt) * 0.6 + random.uniform(0.0, 0.4)
                time.sleep(backoff)
                continue

            except Exception:
                backoff = (2 ** attempt) * 0.6 + random.uniform(0.0, 0.4)
                time.sleep(backoff)
                continue

        return None

    def _parse_page(self, page_num: int):
        html = self._fetch_html(page_num)
        if not html:
            return page_num, None, "error"

        try:
            soup = BeautifulSoup(html, "html.parser")
            tbody = soup.find("tbody")
            if not tbody:
                return page_num, [], "empty"

            rows = tbody.find_all("tr", recursive=False)
            if not rows:
                return page_num, [], "empty"

            entries = []
            i = 0
            while i < len(rows):
                tr = rows[i]
                tds = tr.find_all("td", recursive=False)
                if len(tds) < 4:
                    i += 1
                    continue

                a = tr.find("a", href=RESULT_HREF_RE)
                if not a:
                    i += 1
                    continue

                m = RESULT_HREF_RE.match(a.get("href", ""))
                result_id = m.group(1) if m else None
                url = f"https://www.thegradcafe.com{a['href']}"

                school = tds[0].get_text(" ", strip=True)

                prog_cell = tds[1]
                spans = prog_cell.find_all("span")
                program = spans[0].get_text(" ", strip=True) if len(spans) >= 1 else prog_cell.get_text(" ", strip=True)
                degree = spans[1].get_text(" ", strip=True) if len(spans) >= 2 else None

                date_added = tds[2].get_text(" ", strip=True) if len(tds) >= 3 else None
                status = tds[3].get_text(" ", strip=True) if len(tds) >= 4 else None

                j = i + 1
                detail_text_chunks = []
                comment = ""

                while j < len(rows):
                    nxt = rows[j]
                    nxt_tds = nxt.find_all("td", recursive=False)
                    if len(nxt_tds) >= 4 and nxt.find("a", href=RESULT_HREF_RE):
                        break

                    txt = nxt.get_text(" ", strip=True)
                    if txt:
                        detail_text_chunks.append(txt)

                    p = nxt.find("p")
                    if p and p.get_text(strip=True):
                        comment = p.get_text(strip=True)

                    j += 1

                detail_blob = " ".join(detail_text_chunks)

                term = None
                term_m = TERM_RE.search(detail_blob)
                if term_m:
                    term = term_m.group(0)

                us_intl = None
                if re.search(r"\bInternational\b", detail_blob, re.I):
                    us_intl = "International"
                elif re.search(r"\bAmerican\b", detail_blob, re.I):
                    us_intl = "American"

                gpa = None
                gpa_m = GPA_RE.search(detail_blob)
                if gpa_m:
                    gpa = gpa_m.group(1)

                v = GRE_V_RE.search(detail_blob)
                q = GRE_Q_RE.search(detail_blob)
                aw = GRE_AW_RE.search(detail_blob)

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

                i = j

            return page_num, entries, "ok"
        except Exception:
            return page_num, None, "error"

    def scrape_data(self, target: int = 30000):
        pages_done = 0
        consecutive_bad = 0
        max_consecutive_bad = max(12, self.max_workers * 4)

        next_page = self.start_page

        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            in_flight = set()

            for _ in range(self.max_workers):
                in_flight.add(ex.submit(self._parse_page, next_page))
                next_page += 1

            while in_flight and len(self.results) < target:
                done, in_flight = wait(
                    in_flight,
                    timeout=max(5.0, self.timeout + 2.0),
                    return_when=FIRST_COMPLETED,
                )
                if not done:
                    time.sleep(0.2)
                    continue

                for fut in done:
                    try:
                        page_num, entries, status = fut.result()
                    except Exception:
                        page_num, entries, status = None, None, "error"

                    pages_done += 1

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
                        consecutive_bad += 1

                    pct = (len(self.results) / target) * 100
                    sys.stdout.write(
                        f"\rProgress: {len(self.results)}/{target} ({pct:.2f}%) | "
                        f"Pages done: {pages_done} | Bad streak: {consecutive_bad}"
                    )
                    sys.stdout.flush()

                    if pages_done % self.save_every_pages == 0:
                        self.save_data()

                    if consecutive_bad >= max_consecutive_bad:
                        print("\nStopping early: too many consecutive empty/error pages (end or blocked).")
                        in_flight.clear()
                        break

                    if len(self.results) < target:
                        in_flight.add(ex.submit(self._parse_page, next_page))
                        next_page += 1

        self.save_data()
        print("\nDone.")

    def save_data(self):
        tmp = self.output_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.output_file)


if __name__ == "__main__":
    target = int(os.getenv("TARGET", "30000"))
    GradCafeScraper().scrape_data(target)
