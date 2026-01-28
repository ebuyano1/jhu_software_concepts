import json
import os
import sys
import time
import urllib.request
import urllib.error


class DataCleaner:
    """
    Cleans GradCafe scraped rows by running the professor-provided tiny local LLM standardizer.
    Output keys match the professor tool:
      - llm-generated-program
      - llm-generated-university

    Default behavior:
      1) Try to call the local Flask API (app.py --serve) at http://localhost:8000/standardize in batches.
      2) If the server is not running, fall back to importing llm_hosting.app and calling _call_llm() directly.
    """

    def __init__(
        self,
        input_file: str = "applicant_data.json",
        output_file: str = "llm_extend_applicant_data.json",
        api_url: str = "http://localhost:8000/standardize",
        batch_size: int = 50,
        timeout_seconds: int = 60,
    ):
        self.input_file = input_file
        self.output_file = output_file
        self.api_url = api_url
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds

        # Cache standardizations keyed by raw "program" field (most common duplicate)
        # You can broaden this to include university if your scraper separates them cleanly.
        self.cache = {}

    def _load_input(self):
        if not os.path.exists(self.input_file):
            print(f"Error: {self.input_file} not found.")
            return None
        with open(self.input_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _atomic_save(self, data):
        tmp_path = self.output_file + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        os.replace(tmp_path, self.output_file)

    def _post_json(self, payload: dict):
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
        # Cheap check: try a single small request; if it fails, fall back to direct import.
        try:
            test = self._post_json({"rows": [{"program": "Information Studies, McGill University"}]})
            return isinstance(test, dict) and isinstance(test.get("rows"), list)
        except Exception:
            return False

    def _direct_standardize_row(self, row: dict) -> dict:
        """
        Fallback: call llm_hosting.app._call_llm(program_text) directly.
        This produces standardized_program / standardized_university, which we map to the required keys.
        """
        try:
            # Expect llm_hosting/ to be a subfolder in module_2. It must be importable.
            # If it's not, ensure module_2 is your working directory and llm_hosting has __init__.py
            from llm_hosting import app as llm_app  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "Could not import llm_hosting.app. "
                "Make sure the llm_hosting folder is present and importable."
            ) from e

        program_text = (row or {}).get("program") or ""
        result = llm_app._call_llm(program_text)  # returns dict with standardized_program/university

        row["llm-generated-program"] = result.get("standardized_program") or None
        row["llm-generated-university"] = result.get("standardized_university") or None
        return row

    def clean_data(self):
        data = self._load_input()
        if data is None:
            return None
        if not isinstance(data, list):
            print("Error: applicant_data.json must be a JSON list of rows.")
            return None

        total = len(data)
        if total == 0:
            print("No rows found in input.")
            self._atomic_save([])
            return []

        use_api = self._can_use_api()
        mode = "API (batched)" if use_api else "Direct import"
        print(f"Starting LLM cleaning on {total} rows using: {mode}")

        cleaned = []
        start = time.time()
        cache_hits = 0

        i = 0
        while i < total:
            batch = data[i : i + self.batch_size]

            # Apply cache first
            to_send = []
            send_map = []  # indices of rows in batch that were not cache hits

            for idx, row in enumerate(batch):
                program_key = ((row or {}).get("program") or "").strip().lower()
                if program_key and program_key in self.cache:
                    row["llm-generated-program"] = self.cache[program_key].get("llm-generated-program")
                    row["llm-generated-university"] = self.cache[program_key].get("llm-generated-university")
                    cache_hits += 1
                else:
                    to_send.append(row)
                    send_map.append(idx)

            # Standardize non-cached rows
            if to_send:
                if use_api:
                    try:
                        resp = self._post_json({"rows": to_send})
                        out_rows = resp.get("rows", [])
                        if not isinstance(out_rows, list) or len(out_rows) != len(to_send):
                            raise ValueError("Unexpected API response shape.")
                        for r in out_rows:
                            program_key = ((r or {}).get("program") or "").strip().lower()
                            if program_key:
                                self.cache[program_key] = {
                                    "llm-generated-program": r.get("llm-generated-program") or None,
                                    "llm-generated-university": r.get("llm-generated-university") or None,
                                }
                        # Merge back into batch
                        for k, original_batch_index in enumerate(send_map):
                            batch[original_batch_index] = out_rows[k]
                    except Exception:
                        # If API flakes mid-run, fall back for the rest
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

            cleaned.extend(batch)
            i += len(batch)

            # Progress
            elapsed = time.time() - start
            pct = (i / total) * 100
            sys.stdout.write(
                f"\rCleaning: {pct:6.2f}% | {i}/{total} | Cache hits: {cache_hits} | Elapsed: {elapsed:.1f}s"
            )
            sys.stdout.flush()

            # Periodic checkpoint (every ~1000 rows)
            if i % 1000 == 0:
                self._atomic_save(cleaned)

        self._atomic_save(cleaned)
        print(f"\nSaved cleaned output to {self.output_file}")
        return cleaned


if __name__ == "__main__":
    cleaner = DataCleaner()
    cleaner.clean_data()
