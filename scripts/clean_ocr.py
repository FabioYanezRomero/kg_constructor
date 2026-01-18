#!/usr/bin/env python3
"""Clean OCR artifacts from JSONL input files.

Fixes common OCR issues like:
- Broken words with spurious spaces: "du ty" -> "duty"
- Mid-word line breaks preserved as spaces
"""

import json
import re
import sys
from pathlib import Path


def fix_broken_words(text: str) -> str:
    """Fix words that were broken by OCR with spurious spaces."""
    
    # Direct replacements for known broken patterns
    replacements = {
        # Common OCR breaks found in legal documents
        "Si gma": "Sigma",
        "Si gma's": "Sigma's",
        "financ ial": "financial",
        "financi al": "financial",
        "du ty": "duty",
        "dut y": "duty",
        "bind s": "binds",
        "proceed ings": "proceedings",
        "proceedin gs": "proceedings",
        "establish ed": "established",
        "invest ment": "investment",
        "stemmi ng": "stemming",
        "dur ing": "during",
        "du ring": "during",
        "whos e": "whose",
        "there fore": "therefore",
        "appell ant": "appellant",
        "circ uit": "circuit",
        "brou ght": "brought",
        "br ought": "brought",
        "serv ices": "services",
        "particu lar": "particular",
        "argu ments": "arguments",
        "applic ation": "application",
        "corr ect": "correct",
        "th e ": "the ",  # Be careful with word boundaries
        "tha t": "that",
        "Cour t": "Court",
        "Suprem e": "Supreme",
        "provi sions": "provisions",
        "provis ions": "provisions",
        "credit ors": "creditors",
        "realis ation": "realisation",
        "discre tion": "discretion",
        "circumst ances": "circumstances",
        "consider ation": "consideration",
        "Intellig ence": "Intelligence",
        "judg ment": "judgment",
        "para graph": "paragraph",
        "pro ceedings": "proceedings",
        "re spect": "respect",
        " gma": "gma",  # Fix orphaned fragments at word starts
    }
    
    for broken, fixed in replacements.items():
        text = text.replace(broken, fixed)
    
    return text


def clean_record(record: dict) -> dict:
    """Clean a single record's text field."""
    if "text" in record:
        record["text"] = fix_broken_words(record["text"])
    if "reasoning" in record:
        record["reasoning"] = fix_broken_words(record["reasoning"])
    if "title" in record:
        record["title"] = fix_broken_words(record["title"])
    return record


def clean_jsonl(input_path: Path, output_path: Path) -> None:
    """Clean all records in a JSONL file."""
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                records.append(clean_record(record))
    
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"Cleaned {len(records)} records: {input_path} -> {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python clean_ocr.py <input.jsonl> [output.jsonl]")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.with_suffix(".cleaned.jsonl")
    
    clean_jsonl(input_path, output_path)
