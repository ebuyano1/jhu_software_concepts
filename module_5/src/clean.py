"""
clean.py
--------
Standardizes program and university names using a local LLM tool via API or direct import.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

class DataCleaner:
    """
    Takes raw scraper output and standardizes fields using a local LLM.
    """

    def __init__(
        self,
        input_file: str = "applicant_data.json",
        output_file: str = "llm_extend_applicant_data.json",
        **kwargs
    ):
        """
        Initializes the cleaner with file paths and API settings.
        """
        self.input_file = input_file
        self.output_file = output_file
        self.api_url = kwargs.get("api_url", "http://localhost:8000/standardize")
        self.batch_size = kwargs.get("batch_size", 50)
        self.timeout_seconds = kwargs.get("timeout_seconds", 60)
        self.cache = {}
        self.start_time = 0.0

    def _load_input(self):
        """Load applicant_data.json and return the parsed JSON data."""
        if not os.path.exists(self.input_file):
            print(f"Error: {self.input_file} not found.")
            return None
        with open(self.input_file, "r", encoding="utf-8") as file:
            return json.load(file)

    def _atomic_save(self, data):
        """Save output safely using a temporary file."""
        tmp_path = self.output_file + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        os.replace(tmp_path, self.output_file)

    def _post_json(self, payload: dict):
        """POST JSON to the local standardizer API."""
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
        """Quick health check for the local API."""
        try:
            test_row = {"program": "Information Studies, McGill University"}
            test = self._post_json({"rows": [test_row]})
            return isinstance(test, dict) and isinstance(test.get("rows"), list)
        except (urllib.error.URLError, ValueError, TimeoutError):
            return False

    def _direct_standardize_row(self, row: dict) -> dict:
        """Fallback: Import llm_hosting and call _call_llm directly."""
        try:
            # pylint: disable=import-outside-toplevel, import-error
            from llm_hosting import app as llm_app
        except ImportError as err:
            raise RuntimeError("Could not import llm_hosting.app.") from err

        program_text = (row or {}).get("program") or ""
        # pylint: disable=protected-access
        result = llm_app._call_llm(program_text)

        row["llm-generated-program"] = result.get("standardized_program")
        row["llm-generated-university"] = result.get("standardized_university")
        return row

    def _update_cache_and_batch(self, rows, batch, send_map):
        """Updates the cache and merges API results into the current batch."""
        for r_data in rows:
            prog_key = ((r_data or {}).get("program") or "").strip().lower()
            if prog_key:
                self.cache[prog_key] = {
                    "llm-generated-program": r_data.get("llm-generated-program"),
                    "llm-generated-university": r_data.get("llm-generated-university"),
                }

        for k, original_idx in enumerate(send_map):
            batch[original_idx] = rows[k]

    def _process_batch_fallback(self, batch, send_map):
        """Handles row-by-row standardization when API is unavailable."""
        for original_idx in send_map:
            row = self._direct_standardize_row(batch[original_idx])
            prog_key = ((row or {}).get("program") or "").strip().lower()
            if prog_key:
                self.cache[prog_key] = {
                    "llm-generated-program": row.get("llm-generated-program"),
                    "llm-generated-university": row.get("llm-generated-university"),
                }
            batch[original_idx] = row

    def _print_progress(self, current, total, hits):
        """Prints a formatted progress bar. Reduces variables in clean_data."""
        elapsed = time.time() - self.start_time
        pct = (current / total) * 100
        msg = f"\rCleaning: {pct:6.2f}% | {current}/{total} | Hits: {hits} | Time: {elapsed:.1f}s"
        sys.stdout.write(msg)
        sys.stdout.flush()

    def clean_data(self):
        """Main cleaning routine. Optimized to minimize local variables."""
        data = self._load_input()
        if not isinstance(data, list) or not data:
            return data

        use_api = self._can_use_api()
        print(f"Starting LLM cleaning. API Mode: {use_api}")

        cleaned = []
        self.start_time = time.time()
        cache_hits, i = 0, 0

        while i < len(data):
            batch = data[i : i + self.batch_size]
            to_send, send_map = [], []

            for idx, row in enumerate(batch):
                prog_key = ((row or {}).get("program") or "").strip().lower()
                if prog_key in self.cache:
                    p_val = self.cache[prog_key]["llm-generated-program"]
                    u_val = self.cache[prog_key]["llm-generated-university"]
                    row["llm-generated-program"], row["llm-generated-university"] = p_val, u_val
                    cache_hits += 1
                else:
                    to_send.append(row)
                    send_map.append(idx)

            if to_send:
                if use_api:
                    try:
                        resp = self._post_json({"rows": to_send})
                        self._update_cache_and_batch(resp.get("rows", []), batch, send_map)
                    except (urllib.error.URLError, ValueError):
                        use_api = False
                        self._process_batch_fallback(batch, send_map)
                else:
                    self._process_batch_fallback(batch, send_map)

            cleaned.extend(batch)
            i += len(batch)
            self._print_progress(i, len(data), cache_hits)

            if i % 1000 == 0:
                self._atomic_save(cleaned)

        self._atomic_save(cleaned)
        return cleaned

    def run(self):
        """Public entry point to start the cleaning process."""
        self.clean_data()

if __name__ == "__main__":
    cleaner = DataCleaner()
    cleaner.run()
