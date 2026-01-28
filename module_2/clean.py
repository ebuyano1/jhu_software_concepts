import json
import os
import sys
import time
import urllib.request
import urllib.error


class DataCleaner:
    """
    clean.py
    --------
    This script takes the raw scraper output (applicant_data.json) and "cleans" it by
    standardizing the program + university names using the professor provided local LLM tool.

    The professor tool produces the following output keys (and the assignment expects them):
      - llm-generated-program
      - llm-generated-university

    Default behavior / priority order:
      1) Preferred: call the local Flask API (llm_hosting/app.py --serve)
         Endpoint: http://localhost:8000/standardize
         Benefit: batching is faster and reduces overhead.
      2) Fallback: if the server is not running (or becomes unavailable mid-run),
         import llm_hosting.app and call _call_llm() directly.

    Notes on performance:
      - We batch requests when using the API.
      - We cache results keyed by the raw "program" string to avoid repeated LLM calls.
        (In GradCafe data, duplicates are extremely common.)
      - Output is saved atomically so long runs can be resumed safely.
    """

    def __init__(
        self,
        input_file: str = "applicant_data.json",
        output_file: str = "llm_extend_applicant_data.json",
        api_url: str = "http://localhost:8000/standardize",
        batch_size: int = 50,
        timeout_seconds: int = 60,
    ):
        # Input: output from scrape.py
        self.input_file = input_file

        # Output: same rows + the two LLM-generated fields appended
        self.output_file = output_file

        # Local LLM server endpoint (Option A in your workflow)
        self.api_url = api_url

        # Batch size for API mode (50 is a reasonable tradeoff for speed vs stability)
        self.batch_size = batch_size

        # Network timeout for the local API call
        self.timeout_seconds = timeout_seconds

        # Cache standardizations keyed by raw "program" field.
        # This is the biggest speed-up for large runs (30k rows).
        #
        # If you ever wanted to broaden the cache, you could include university too,
        # but program alone usually captures most duplicates.
        self.cache = {}

    def _load_input(self):
        """
        Load applicant_data.json and return the parsed JSON data.

        Expected format:
          - a JSON list of dict rows produced by scrape.py
        """
        if not os.path.exists(self.input_file):
            print(f"Error: {self.input_file} not found.")
            return None
        with open(self.input_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _atomic_save(self, data):
        """
        Save output safely.

        We write to a temp file first and then replace the real output file.
        This prevents partial/corrupt JSON if the program is interrupted mid-write.
        """
        tmp_path = self.output_file + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        os.replace(tmp_path, self.output_file)

    def _post_json(self, payload: dict):
        """
        POST JSON to the local standardizer API using urllib (lecture topics).

        The server expects:
          {"rows": [ { "program": "...", ... }, ... ]}

        And returns a dict with:
          {"rows": [ { ..., "llm-generated-program": "...", "llm-generated-university": "..." }, ... ]}
        """
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.api_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)

    def _can_use_api(self) -> bool:
        """
        Quick health check: try a single tiny request.

        If it works, we run in fast "API (batched)" mode.
        If it fails, we fall back to direct import mode.
        """
        try:
            test = self._post_json({"rows": [{"program": "Information Studies, McGill University"}]})
            return isinstance(test, dict) and isinstance(test.get("rows"), list)
        except Exception:
            return False

    def _direct_standardize_row(self, row: dict) -> dict:
        """
        Fallback mode (no server):
        Import llm_hosting.app and call _call_llm(program_text) directly.

        The professor function returns:
          { "standardized_program": "...", "standardized_university": "..." }

        We then map those outputs into the assignment-required keys:
          - llm-generated-program
          - llm-generated-university
        """
        try:
            # Expect llm_hosting/ to be a subfolder in module_2.
            # It must be importable (llm_hosting/__init__.py exists).
            from llm_hosting import app as llm_app  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "Could not import llm_hosting.app. "
                "Make sure the llm_hosting folder is present and importable."
            ) from e

        # The professor LLM tool takes the raw program text and returns standardized fields.
        program_text = (row or {}).get("program") or ""
        result = llm_app._call_llm(program_text)  # returns dict with standardized_program/university

        # Store the outputs using the assignment-required key names.
        row["llm-generated-program"] = result.get("standardized_program") or None
        row["llm-generated-university"] = result.get("standardized_university") or None
        return row

    def clean_data(self):
        """
        Main cleaning routine:
          - Load scraped rows
          - Standardize each row via LLM (batched API if possible)
          - Cache repeats
          - Save output periodically and at the end
        """
        data = self._load_input()
        if data is None:
            return None

        # Scraper output must be a list of rows.
        if not isinstance(data, list):
            print("Error: applicant_data.json must be a JSON list of rows.")
            return None

        total = len(data)
        if total == 0:
            print("No rows found in input.")
            self._atomic_save([])
            return []

        # Decide whether we can use the faster local API mode.
        use_api = self._can_use_api()
        mode = "API (batched)" if use_api else "Direct import"
        print(f"Starting LLM cleaning on {total} rows using: {mode}")

        cleaned = []
        start = time.time()
        cache_hits = 0

        # Process in batches so:
        #  - API mode can send many rows at once
        #  - We can periodically checkpoint progress
        i = 0
        while i < total:
            batch = data[i : i + self.batch_size]

            # Cache first:
            # Many program strings repeat; if we’ve already standardized this exact program
            # text, we can copy the cached LLM outputs without calling the model again.
            to_send = []
            send_map = []  # indices of rows in batch that were NOT cache hits

            for idx, row in enumerate(batch):
                program_key = ((row or {}).get("program") or "").strip().lower()

                # Cache hit: copy LLM-generated fields into this row immediately.
                if program_key and program_key in self.cache:
                    row["llm-generated-program"] = self.cache[program_key].get("llm-generated-program")
                    row["llm-generated-university"] = self.cache[program_key].get("llm-generated-university")
                    cache_hits += 1
                else:
                    # Cache miss: we need to standardize this row via LLM.
                    to_send.append(row)
                    send_map.append(idx)

            # Standardize only the non-cached rows.
            if to_send:
                if use_api:
                    try:
                        # Batched API call: fastest path when the server is running.
                        resp = self._post_json({"rows": to_send})
                        out_rows = resp.get("rows", [])

                        # Basic validation: response should contain one output row per input row.
                        if not isinstance(out_rows, list) or len(out_rows) != len(to_send):
                            raise ValueError("Unexpected API response shape.")

                        # Update cache with freshly standardized results.
                        for r in out_rows:
                            program_key = ((r or {}).get("program") or "").strip().lower()
                            if program_key:
                                self.cache[program_key] = {
                                    "llm-generated-program": r.get("llm-generated-program") or None,
                                    "llm-generated-university": r.get("llm-generated-university") or None,
                                }

                        # Merge standardized rows back into the original batch positions.
                        for k, original_batch_index in enumerate(send_map):
                            batch[original_batch_index] = out_rows[k]

                    except Exception:
                        # If the API fails mid-run (server crash, timeout, etc.),
                        # switch to direct import mode for the remainder of the job.
                        use_api = False

                        for original_batch_index in send_map:
                            row = batch[original_batch_index]
                            row = self._direct_standardize_row(row)

                            program_key = ((row or {}).get("program") or "").strip().lower()
                            if program_key:
                                self.cache[program_key] = {
                                    "llm-generated-program": row.get("llm-generated-program") or None,
                                    "llm-generated-university": row.get("llm-generated-university") or None,
                                }

                            batch[original_batch_index] = row

                else:
                    # Direct import mode: standardize one row at a time.
                    # Slower than API batching, but works even without the server.
                    for original_batch_index in send_map:
                        row = batch[original_batch_index]
                        row = self._direct_standardize_row(row)

                        # Cache results so duplicates are fast going forward.
                        program_key = ((row or {}).get("program") or "").strip().lower()
                        if program_key:
                            self.cache[program_key] = {
                                "llm-generated-program": row.get("llm-generated-program") or None,
                                "llm-generated-university": row.get("llm-generated-university") or None,
                            }

                        batch[original_batch_index] = row

            # Add the processed batch to our final list and advance the cursor.
            cleaned.extend(batch)
            i += len(batch)

            # Progress indicator (single updating line in terminal).
            elapsed = time.time() - start
            pct = (i / total) * 100
            sys.stdout.write(
                f"\rCleaning: {pct:6.2f}% | {i}/{total} | Cache hits: {cache_hits} | Elapsed: {elapsed:.1f}s"
            )
            sys.stdout.flush()

            # Periodic checkpoint so you don’t lose hours of work if interrupted.
            # Every 1000 rows is a good balance between overhead and safety.
            if i % 1000 == 0:
                self._atomic_save(cleaned)

        # Final save to ensure output is complete and up to date.
        self._atomic_save(cleaned)
        print(f"\nSaved cleaned output to {self.output_file}")
        return cleaned


if __name__ == "__main__":
    # Default run: read applicant_data.json and write llm_extend_applicant_data.json
    # If you want to customize behavior, adjust DataCleaner() parameters above.
    cleaner = DataCleaner()
    cleaner.clean_data()
