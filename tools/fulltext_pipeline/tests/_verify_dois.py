"""Extract DOI and title from first 2 pages for MDPI PDFs."""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import fitz

PDFS = {
    '6': 'C:/Users/mouadh/Downloads/electronics-14-04082.pdf',
    '11': 'C:/Users/mouadh/Downloads/robotics-15-00081-v2.pdf',
    '17': 'C:/Users/mouadh/Downloads/applsci-16-03745-v2.pdf',
    '39': 'C:/Users/mouadh/Downloads/remotesensing-16-04394-v2.pdf',
    '41': 'C:/Users/mouadh/Downloads/agriculture-16-00215-v2.pdf',
}
EXPECT_DOI = {
    '6': '10.3390/electronics14204082',
    '11': '10.3390/robotics15040081',
    '17': '10.3390/app16083745',
    '39': '10.3390/rs16234394',
    '41': '10.3390/agriculture16020215',
}
for rank, path in PDFS.items():
    doc = fitz.open(path)
    text = doc[0].get_text() + '\n' + (doc[1].get_text() if doc.page_count > 1 else '')
    doc.close()
    dois = re.findall(r'10\.\d{4,9}/[-._;()/:A-Z0-9a-z]+', text)
    title = text.split('\n')
    # heuristic: look for the article title between MDPI header and abstract
    head = text[:1200].replace('\n', ' | ')
    print(f'rank={rank} expected DOI={EXPECT_DOI[rank]}')
    print(f'  found DOIs: {sorted(set(dois))[:6]}')
    print(f'  head: {head[:250]}')
    print()
