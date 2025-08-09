#!/usr/bin/env python3
"""
pdf_processing.py

Extracts NCO-2015 occupation records from Vol-II A & B PDFs into JSON.

Output JSON schema (per record):
{
  "nco_code": "7212.0100",
  "title": "Welder, Gas",
  "description": "Full paragraph...",
  "synonyms": [],
  "examples": [],
  "source": "NCO-2015 Vol-II-A.pdf"
}

Usage:
  python backend/data/pdf_processing.py \
    --pdf backend/data/pdfs/NCO_Vol_II_A.pdf backend/data/pdfs/NCO_Vol_II_B.pdf \
    --out-json backend/nco_data.json \
    --save-clean backend/data/clean

Requirements:
  pip install pdfplumber pdfminer.six tqdm
"""

import re
import os
import json
import argparse
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Optional: fast progress bars
try:
    from tqdm import tqdm
except Exception:
    def tqdm(x, **kwargs): return x  # no-op fallback

# Text extractors: prefer pdfplumber, fallback to pdfminer.six
def extract_text_pdfplumber(pdf_path: Path) -> str:
    import pdfplumber  # type: ignore
    texts = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in tqdm(pdf.pages, desc=f"Reading {pdf_path.name} (pdfplumber)"):
            t = page.extract_text(x_tolerance=1, y_tolerance=1) or ""
            texts.append(t)
    # Mark page breaks explicitly (useful if we want to estimate page indices later)
    return "\n[[PAGE_BREAK]]\n".join(texts)

def extract_text_pdfminer(pdf_path: Path) -> str:
    from pdfminer.high_level import extract_text  # type: ignore
    return extract_text(str(pdf_path))

def extract_text(pdf_path: Path) -> str:
    try:
        return extract_text_pdfplumber(pdf_path)
    except Exception as e:
        logging.warning(f"pdfplumber failed for {pdf_path.name}: {e}. Falling back to pdfminer.six.")
        try:
            return extract_text_pdfminer(pdf_path)
        except Exception as e2:
            logging.error(f"pdfminer also failed for {pdf_path.name}: {e2}")
            raise

HEADER_PATTERNS = [
    r'(?im)^\s*VOLUME\s*II\s*[-–]?\s*[AB]\s+\d+\s*$',          # e.g., "VOLUME II A   123"
    r'(?im)^\s*National\s+Classification\s+of\s+Occupations.*$',  # title headers
    r'(?im)^\s*Government\s+of\s+India.*$',                      # misc headers
    r'(?im)^\s*Ministry\s+of\s+Labour.*$',                       # misc headers
    r'(?im)^\s*Division\s+\d+\s+.*$',                             # "Division 1 ..." lines
    r'(?im)^\s*Sub[\-\s]*Division\s+\d+\s+.*$',
    r'(?im)^\s*Page\s+\d+\s*$',
    r'(?im)^\s*\d+\s*$',                                          # lone page numbers
]

# Generic code pattern: 4 digits . 3 digits + optional alnum (e.g. 3432.0A00)
CODE_PATTERN = r'(?P<code>\d{4}\.\d{3}[0-9A-Z])'

# Allow optional leading bullets/whitespace before the code
CODE_LINE_ONLY = re.compile(r'^[^\d\n]*' + CODE_PATTERN + r'\s*$', re.M)
CODE_WITH_TITLE = re.compile(r'^[^\d\n]*' + CODE_PATTERN + r'\s+(?P<title>.+?)\s*$', re.M)
CODE_ANCHOR = re.compile(r'^[^\d\n]*' + CODE_PATTERN + r'\b', re.M)

def remove_headers_footers(text: str) -> str:
    cleaned = text
    for pat in HEADER_PATTERNS:
        cleaned = re.sub(pat, "", cleaned)
    # Insert a newline in case multiple records coalesced onto one line
    cleaned = re.sub(CODE_PATTERN, "\n\\g<code>", cleaned)
    # Normalize line endings and collapse excessive blank lines
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned

def normalize_whitespace(s: str) -> str:
    # Collapse internal whitespace but keep codes intact (no hyphen fixes).
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\s{2,}', ' ', s)
    return s.strip()

def segment_records(clean_text: str, source_label: str) -> List[Dict]:
    """
    Segments cleaned text into records. Handles both formats:
      1) "1111.0100 Title" on the same line, or
      2) "1111.0100" followed by a title on the next non-empty line.
    Everything after title until next code line is part of description.
    """
    lines = [ln.rstrip() for ln in clean_text.splitlines()]
    records = []
    i = 0
    n = len(lines)

    def is_code_line(ln: str) -> Optional[str]:
        m = re.match(r'^\s*(\d{4}\.\d{4})\s*(.*)$', ln)
        if m:
            code = m.group(1)
            trailing = m.group(2).strip()
            return code if code else None
        return None

    while i < n:
        line = lines[i].strip()
        code = None
        title = None

        # Try "code + title" on same line
        m_same = CODE_WITH_TITLE.match(line)
        if m_same:
            code = m_same.group("code")
            title = m_same.group("title").strip()
            i += 1
        else:
            # Try "code" alone on this line and title on next non-empty line
            m_code_only = CODE_LINE_ONLY.match(line)
            if m_code_only:
                code = m_code_only.group("code")
                i += 1
                # find the next suitable line as title
                # Peek ahead for title but do not skip if it's another code.
                j = i
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and CODE_ANCHOR.match(lines[j].strip()):
                    # Consecutive code lines -> current code has no title, likely header; skip.
                    i = j  # continue processing from next code line
                    code = None  # invalidate this code
                elif j < n:
                    title = lines[j].strip()
                    i = j + 1
                else:
                    code = None  # no title found at EOF
            else:
                i += 1
                continue  # not a code line

        if not code or not title:
            continue

        # Accumulate description lines until next code anchor or EOF
        desc_lines = []
        while i < n:
            if CODE_ANCHOR.match(lines[i].strip()):
                break
            # skip overly noisy blank lines; we will re-space later
            desc_lines.append(lines[i])
            i += 1

        description = " ".join(ln.strip() for ln in desc_lines if ln.strip())
        description = normalize_whitespace(description)

        record = {
            "nco_code": code,
            "title": normalize_whitespace(title),
            "description": description,
            "synonyms": [],
            "examples": [],
            "source": source_label,
        }
        records.append(record)

    return records

def quality_checks(records: List[Dict]) -> Dict:
    seen = {}
    dups = []
    too_short = []
    for r in records:
        c = r["nco_code"]
        if c in seen:
            dups.append(c)
        else:
            seen[c] = 1
        if len(r.get("description", "")) < 50:
            too_short.append(c)
    return {
        "total": len(records),
        "unique": len(seen),
        "duplicates": sorted(list(set(dups))),
        "short_descriptions": sorted(too_short)[:50],  # preview first 50
    }

def cleanup_clean_directory(clean_dir: Path) -> None:
    """
    Clean up the clean directory after processing is complete.
    Removes all files and the directory itself.
    """
    if clean_dir and clean_dir.exists():
        try:
            shutil.rmtree(clean_dir)
            logging.info(f"Cleaned up temporary directory: {clean_dir}")
        except Exception as e:
            logging.warning(f"Failed to clean up {clean_dir}: {e}")

def load_and_process(pdf_paths: List[Path], save_clean_dir: Optional[Path] = None) -> List[Dict]:
    all_records: List[Dict] = []
    for p in pdf_paths:
        logging.info(f"Extracting text from {p}")
        raw = extract_text(p)
        cleaned = remove_headers_footers(raw)
        if save_clean_dir:
            save_clean_dir.mkdir(parents=True, exist_ok=True)
            out_clean = save_clean_dir / f"{p.stem}.clean.txt"
            out_clean.write_text(cleaned, encoding="utf-8")
            logging.info(f"Saved cleaned text: {out_clean}")

        # Use a friendly source label for traceability
        source_label = p.name
        recs = segment_records(cleaned, source_label=source_label)
        logging.info(f"Parsed {len(recs)} records from {p.name}")
        all_records.extend(recs)

    # Deduplicate by nco_code, keep the first occurrence
    dedup: Dict[str, Dict] = {}
    for r in all_records:
        code = r["nco_code"]
        if code not in dedup:
            dedup[code] = r
    merged = list(dedup.values())

    stats = quality_checks(merged)
    logging.info(f"Quality: {json.dumps(stats, indent=2)}")
    return merged

def main():
    parser = argparse.ArgumentParser(description="Extract NCO-2015 occupations from PDF/CSV files and append to a consolidated JSON database.")
    parser.add_argument("--pdf", nargs="*", default=[], help="Path(s) to PDF files. If omitted, script processes all PDFs in its data directory.")
    parser.add_argument("--csv", nargs="*", default=[], help="Optional CSV file(s) to ingest. (CSV must contain columns nco_code,title,description)")
    parser.add_argument("--out-json", default=None, help="Output JSON path (default: backend/nco_data.json).")
    parser.add_argument("--save-clean", default=None, help="Optional dir to save cleaned text dumps.")
    parser.add_argument("--min-desc", type=int, default=0, help="Optional minimum description length filter (0=off).")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    backend_root = Path(__file__).resolve().parents[1]  # points to backend/
    data_dir = Path(__file__).resolve().parent  # backend/data

    # Collect PDFs: explicit list or auto-detect all in data_dir
    pdf_paths: List[Path] = []
    if args.pdf:
        pdf_paths = [Path(p).resolve() for p in args.pdf]
    else:
        pdf_paths = sorted(data_dir.glob('*.pdf'))
        logging.info(f"Auto-detected {len(pdf_paths)} PDF(s) in {data_dir}")
    for p in pdf_paths:
        if not p.exists():
            raise FileNotFoundError(f"PDF not found: {p}")

    # Default output JSON path
    out_json = Path(args.out_json) if args.out_json else (backend_root / "nco_data_full.json")

    save_clean_dir = Path(args.save_clean) if args.save_clean else None

    # Process PDFs
    records = load_and_process(pdf_paths, save_clean_dir)

    # TODO: support CSV ingestion
    if args.csv:
        try:
            import pandas as pd  # type: ignore
            for cpath in args.csv:
                df = pd.read_csv(cpath)
                for _, row in df.iterrows():
                    if {'nco_code','title','description'}.issubset(row.index):
                        records.append({
                            'nco_code': str(row['nco_code']),
                            'title': str(row['title']),
                            'description': str(row['description']),
                            'synonyms': [],
                            'examples': [],
                            'source': Path(cpath).name,
                        })
        except ImportError:
            logging.warning("pandas not installed; CSV ingestion skipped.")
    if args.min_desc > 0:
        before = len(records)
        records = [r for r in records if len(r.get("description", "")) >= args.min_desc]
        logging.info(f"Filtered by min description length {args.min_desc}: {before} -> {len(records)}")

    # Merge with existing database if present
    if out_json.exists():
        existing = json.loads(out_json.read_text(encoding='utf-8'))
        existing_map = {r['nco_code']: r for r in existing}
        for r in records:
            existing_map[r['nco_code']] = r  # overwrite / append
        records = list(existing_map.values())

    # Sort by nco_code for consistency
    records.sort(key=lambda r: r["nco_code"])

    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    logging.info(f"Database now contains {len(records)} unique records → {out_json}")
    
    # Clean up the clean directory after processing is complete
    cleanup_clean_directory(save_clean_dir)

if __name__ == "__main__":
    main()
