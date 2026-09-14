"""Text-based PDF extractor using PyMuPDF (fitz) and pdfplumber."""

import io
from typing import List
import pandas as pd

from app.extraction.base import BaseExtractor, ExtractedData

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


class PdfExtractor(BaseExtractor):
    """Extracts tables and text blocks from digital/text-based PDF bank statements."""

    def extract(self, content: bytes, filename: str) -> ExtractedData:
        warnings: List[str] = []
        dfs: List[pd.DataFrame] = []
        raw_text_parts: List[str] = []

        # 1. Extract text using PyMuPDF if available
        if fitz is not None:
            try:
                doc = fitz.open(stream=content, filetype="pdf")
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text("text")
                    if text.strip():
                        raw_text_parts.append(f"--- Page {page_num + 1} ---\n{text}")
                doc.close()
            except Exception as e:
                warnings.append(f"PyMuPDF text extraction warning: {e}")

        # 2. Extract structured tables using pdfplumber
        if pdfplumber is not None:
            try:
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    for page_idx, page in enumerate(pdf.pages):
                        # Extract table lines (standard line-based, then text-aligned fallback)
                        tables = page.extract_tables()
                        if not tables:
                            try:
                                tables = page.extract_tables(table_settings={
                                    "vertical_strategy": "text",
                                    "horizontal_strategy": "text",
                                    "snap_tolerance": 5
                                })
                            except Exception:
                                tables = []

                        for table in tables:
                            if not table or len(table) < 2:
                                continue
                            
                            # Search top 15 rows for candidate header
                            header_idx = 0
                            for r_idx, row in enumerate(table[:15]):
                                row_str = " ".join([str(c).lower() for c in row if c])
                                matches = sum(1 for kw in ["date", "desc", "amount", "debit", "credit", "balance"] if kw in row_str)
                                if matches >= 2:
                                    header_idx = r_idx
                                    break
                            
                            headers = [str(c).strip() if c else f"col_{i}" for i, c in enumerate(table[header_idx])]
                            rows = table[header_idx + 1:]
                            if rows:
                                df = pd.DataFrame(rows, columns=headers)
                                df = df.dropna(how="all").dropna(axis=1, how="all")
                                if not df.empty and len(df.columns) >= 2:
                                    dfs.append(df)
                        
                        # Fallback text if PyMuPDF wasn't used
                        if not raw_text_parts:
                            page_text = page.extract_text()
                            if page_text:
                                raw_text_parts.append(f"--- Page {page_idx + 1} ---\n{page_text}")
            except Exception as e:
                warnings.append(f"pdfplumber table extraction warning: {e}")

        if not dfs and raw_text_parts:
            # Fallback: attempt to parse lines of text looking like transactions
            parsed_df = self._parse_text_lines_to_df(raw_text_parts)
            if parsed_df is not None and not parsed_df.empty:
                dfs.append(parsed_df)
                warnings.append("Parsed tabular transactions from PDF text stream directly.")

        return ExtractedData(
            dataframes=dfs,
            raw_text="\n\n".join(raw_text_parts),
            metadata={"filename": filename, "page_count": len(raw_text_parts), "tables_found": len(dfs)},
            warnings=warnings
        )

    def _parse_text_lines_to_df(self, text_pages: List[str]) -> Optional[pd.DataFrame]:
        """Robust parser for text-based statements without bordered tables."""
        import re
        date_pattern = re.compile(r"^(\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4})\s+(.+?)\s+([+-]?\$?[\d,]+\.\d{2})(?:\s+([+-]?\$?[\d,]+\.\d{2}))?$")
        num_pattern = re.compile(r"^[+-]?\$?[\d,]+\.\d{2}$")
        simple_date_pattern = re.compile(r"^(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})$")

        rows = []

        for page in text_pages:
            lines = [l.strip() for l in page.splitlines() if l.strip()]
            
            # First check single-line regex matches
            for line in lines:
                match = date_pattern.match(line)
                if match:
                    d, desc, amt, bal = match.groups()
                    rows.append({
                        "Date": d,
                        "Description": desc.strip(),
                        "Amount": amt,
                        "Balance": bal if bal else ""
                    })

            # If no single-line matches, parse multi-line sequential tokens: Date -> Desc -> Amount(s)
            if not rows:
                i = 0
                while i < len(lines):
                    if simple_date_pattern.match(lines[i]):
                        d = lines[i]
                        desc = lines[i + 1] if i + 1 < len(lines) and not simple_date_pattern.match(lines[i + 1]) else "Transaction"
                        # Next 1 or 2 items might be amounts
                        amt = ""
                        bal = ""
                        curr = i + 2
                        while curr < min(i + 5, len(lines)) and num_pattern.match(lines[curr]):
                            if not amt:
                                amt = lines[curr]
                            elif not bal:
                                bal = lines[curr]
                            curr += 1
                        
                        if amt:
                            rows.append({
                                "Date": d,
                                "Description": desc,
                                "Amount": amt,
                                "Balance": bal
                            })
                            i = curr
                            continue
                    i += 1

        if rows:
            return pd.DataFrame(rows)
        return None
