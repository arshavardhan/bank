"""Extractor for CSV and Excel files."""

import io
import csv
from typing import List, Optional
import pandas as pd

from app.extraction.base import BaseExtractor, ExtractedData

CANDIDATE_HEADER_KEYWORDS = [
    "date", "txn", "trans", "description", "details", "narration", "particulars",
    "amount", "debit", "credit", "withdrawal", "deposit", "balance", "dr", "cr"
]


class CsvExcelExtractor(BaseExtractor):
    """Robust extractor for CSV and Excel bank statement files."""

    def extract(self, content: bytes, filename: str) -> ExtractedData:
        lower_name = filename.lower()
        if lower_name.endswith(".csv"):
            return self._extract_csv(content, filename)
        elif lower_name.endswith((".xlsx", ".xls")):
            return self._extract_excel(content, filename)
        else:
            raise ValueError(f"Unsupported file format for CsvExcelExtractor: {filename}")

    def _extract_csv(self, content: bytes, filename: str) -> ExtractedData:
        warnings: List[str] = []
        text = ""
        for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if not text:
            text = content.decode("utf-8", errors="replace")
            warnings.append("Used lossy encoding replacement to parse CSV.")

        # Detect header row index
        lines = [line for line in text.splitlines() if line.strip()]
        header_idx = self._find_header_line(lines)

        # Detect delimiter
        delimiter = self._detect_delimiter(lines[header_idx : header_idx + 5] if lines else [])

        csv_buffer = io.StringIO("\n".join(lines[header_idx:]))
        try:
            df = pd.read_csv(csv_buffer, sep=delimiter, skipinitialspace=True, dtype=str)
        except Exception as e:
            warnings.append(f"Standard CSV parse failed ({e}), attempting fallback parsing.")
            csv_buffer.seek(0)
            df = pd.read_csv(csv_buffer, sep=None, engine="python", dtype=str)

        # Drop entirely empty rows and columns
        df = df.dropna(how="all").dropna(axis=1, how="all")

        return ExtractedData(
            dataframes=[df],
            raw_text="\n".join(lines[:header_idx]) if header_idx > 0 else "",
            metadata={"filename": filename, "header_row_offset": header_idx, "delimiter": delimiter},
            warnings=warnings
        )

    def _extract_excel(self, content: bytes, filename: str) -> ExtractedData:
        warnings: List[str] = []
        excel_buffer = io.BytesIO(content)
        
        # Read all sheets or first active sheet
        engine = "openpyxl" if filename.lower().endswith(".xlsx") else None
        excel_file = pd.ExcelFile(excel_buffer, engine=engine)
        dfs: List[pd.DataFrame] = []
        raw_text_parts: List[str] = []

        for sheet_name in excel_file.sheet_names:
            try:
                # Read first 15 rows to locate header row
                sample_df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, nrows=20, dtype=str)
                header_idx = self._find_header_in_dataframe(sample_df)

                df = pd.read_excel(
                    excel_file,
                    sheet_name=sheet_name,
                    header=header_idx,
                    dtype=str
                )
                df = df.dropna(how="all").dropna(axis=1, how="all")
                if not df.empty and len(df.columns) >= 2:
                    dfs.append(df)
            except Exception as e:
                warnings.append(f"Failed to parse sheet '{sheet_name}': {e}")

        return ExtractedData(
            dataframes=dfs,
            raw_text="\n".join(raw_text_parts),
            metadata={"filename": filename, "sheet_count": len(dfs)},
            warnings=warnings
        )

    def _find_header_line(self, lines: List[str]) -> int:
        """Find the 0-indexed line that looks most like a table header."""
        best_idx = 0
        max_matches = 0

        for idx, line in enumerate(lines[:25]):
            lower_line = line.lower()
            matches = sum(1 for kw in CANDIDATE_HEADER_KEYWORDS if kw in lower_line)
            if matches > max_matches:
                max_matches = matches
                best_idx = idx

        return best_idx if max_matches >= 2 else 0

    def _find_header_in_dataframe(self, df: pd.DataFrame) -> int:
        """Find row index in DataFrame matching table header keywords."""
        for idx in range(min(len(df), 20)):
            row_str = " ".join([str(val).lower() for val in df.iloc[idx].values if pd.notna(val)])
            matches = sum(1 for kw in CANDIDATE_HEADER_KEYWORDS if kw in row_str)
            if matches >= 2:
                return idx
        return 0

    def _detect_delimiter(self, lines: List[str]) -> str:
        """Detect whether delimiter is comma, semicolon, tab, or pipe."""
        if not lines:
            return ","
        sample = "\n".join(lines[:5])
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            return dialect.delimiter
        except Exception:
            # Simple heuristic
            commas = sample.count(",")
            semicolons = sample.count(";")
            tabs = sample.count("\t")
            pipes = sample.count("|")
            counts = {",": commas, ";": semicolons, "\t": tabs, "|": pipes}
            return max(counts, key=counts.get) if max(counts.values()) > 0 else ","
