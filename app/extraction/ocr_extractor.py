"""OCR extractor for scanned PDFs and image bank statements."""

import io
from typing import List
import pandas as pd
from PIL import Image

from app.extraction.base import BaseExtractor, ExtractedData

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None


class OcrExtractor(BaseExtractor):
    """Extracts text and tabular content from scanned documents and images using OCR."""

    def extract(self, content: bytes, filename: str) -> ExtractedData:
        warnings: List[str] = []
        raw_text_parts: List[str] = []
        dfs: List[pd.DataFrame] = []

        lower_name = filename.lower()

        if lower_name.endswith(".pdf"):
            images = self._convert_pdf_to_images(content)
        else:
            try:
                images = [Image.open(io.BytesIO(content))]
            except Exception as e:
                warnings.append(f"Failed to open image: {e}")
                images = []

        if not images:
            warnings.append("No readable images extracted from document.")
            return ExtractedData(warnings=warnings)

        if pytesseract is None:
            warnings.append("pytesseract is not installed; OCR extraction unavailable.")
            return ExtractedData(warnings=warnings)

        for idx, img in enumerate(images):
            try:
                text = pytesseract.image_to_string(img)
                if text.strip():
                    raw_text_parts.append(f"--- OCR Image {idx + 1} ---\n{text}")
            except Exception as e:
                warnings.append(f"Tesseract OCR failed on image {idx + 1}: {e}. (Ensure Tesseract-OCR binary is installed)")

        if raw_text_parts:
            # Attempt to parse table rows from OCR text
            from app.extraction.pdf_extractor import PdfExtractor
            parsed_df = PdfExtractor()._parse_text_lines_to_df(raw_text_parts)
            if parsed_df is not None and not parsed_df.empty:
                dfs.append(parsed_df)

        return ExtractedData(
            dataframes=dfs,
            raw_text="\n\n".join(raw_text_parts),
            metadata={"filename": filename, "images_processed": len(images)},
            warnings=warnings
        )

    def _convert_pdf_to_images(self, content: bytes) -> List[Image.Image]:
        images: List[Image.Image] = []
        if fitz is None:
            return images

        try:
            doc = fitz.open(stream=content, filetype="pdf")
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                images.append(img)
            doc.close()
        except Exception:
            pass
        return images
