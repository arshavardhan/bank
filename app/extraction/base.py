"""Base extraction interfaces and data structures."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import pandas as pd


@dataclass
class ExtractedData:
    """Raw data extracted from a bank statement document."""
    dataframes: List[pd.DataFrame] = field(default_factory=list)
    raw_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class BaseExtractor(ABC):
    """Abstract base class for all document extractors."""

    @abstractmethod
    def extract(self, content: bytes, filename: str) -> ExtractedData:
        """Extract structured dataframes and unstructured text from raw file content."""
        pass
