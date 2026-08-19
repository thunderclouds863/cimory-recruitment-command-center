from __future__ import annotations
import io, re
from pypdf import PdfReader

def extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join((p.extract_text() or "") for p in reader.pages)

def parse_candidate_text(text: str) -> dict:
    t = text or ""
    email = re.search(r"[\w.+'-]+@[\w.-]+\.[A-Za-z]{2,}", t)
    phone = re.search(r"(?:\+?62|0)[\s-]?8\d(?:[\s-]?\d){7,12}", t)
    gpa = re.search(r"(?:IPK|GPA)\s*[:\-]?\s*(\d[\.,]\d{1,2})", t, re.I)
    lines = [re.sub(r"\s+", " ", x).strip() for x in t.splitlines() if x.strip()]
    name = lines[0][:120] if lines else ""
    return {
        "name": name,
        "email": email.group(0) if email else "",
        "phone": re.sub(r"[\s-]", "", phone.group(0)) if phone else "",
        "gpa": float(gpa.group(1).replace(",", ".")) if gpa else None,
        "raw_text": t,
    }
