"""Show extraction registry rows for newly processed ranks."""
import csv
rows = list(csv.DictReader(open('data/curated/fulltext/extraction_registry.csv', encoding='utf-8')))
for r in rows:
    if r['rank'] in ('6', '11', '14', '17', '28', '31', '35', '38', '39', '41'):
        print(f"rank={r['rank']:>3s} docling={r['docling_status']:<10} xml={r['publisher_xml_status']:<10} qa={r['qa_status']}")
        print(f"      out={r['output_dir']}")
