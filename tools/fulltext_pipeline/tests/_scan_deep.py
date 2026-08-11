from __future__ import annotations

import re
import sys

import fitz

sys.stdout.reconfigure(encoding="utf-8")

FILES = [
    r"C:\Users\mouadh\Downloads\cicba2017a.pdf",
    r"C:\Users\mouadh\Downloads\Estimating_the_LAI_IROS2017.pdf",
    r"C:\Users\mouadh\Downloads\Overview_of_the_radiometric_and_biophysi.pdf",
    r"C:\Users\mouadh\Downloads\2310.11516v2.pdf",
    r"C:\Users\mouadh\Downloads\chong2023ral.pdf",
    r"C:\Users\mouadh\Downloads\marks2022icra.pdf",
    r"C:\Users\mouadh\Downloads\ECPA23.pdf",
    r"C:\Users\mouadh\Downloads\s41597-026-07074-w.pdf",
    r"C:\Users\mouadh\Downloads\s41597-026-06926-9_reference.pdf",
]

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"',;\)\]]+")
ARX_RE = re.compile(r"arXiv:?\s*(\d{4}\.\d{4,5})")

for f in FILES:
    doc = fitz.open(f)
    text_all = ""
    for i in range(min(doc.page_count, 3)):
        text_all += doc[i].get_text()
    text_all = re.sub(r"\s+", " ", text_all)
    dois = [d for d in DOI_RE.findall(text_all)]
    arx = ARX_RE.findall(text_all)
    # candidate title: longest capitalized line near start
    lines = [re.sub(r"\s+", " ", doc[0].get_text().split("\n")[i]) for i in range(min(6, doc[0].page_count))] if False else None
    print("=" * 90)
    print("FILE:", f.split("\\")[-1])
    print("pages:", doc.page_count)
    print("DOIs:", dois[:4])
    print("arXiv:", arx[:2])
    head = doc[0].get_text().split("\n")
    head = [h.strip() for h in head if h.strip()][:8]
    print("HEAD:", " / ".join(head)[:220])
    doc.close()
