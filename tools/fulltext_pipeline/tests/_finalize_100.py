"""Fix and finalize rank 100 decision."""
import sys; sys.path.insert(0, 'tools/fulltext_pipeline/src')
from pathlib import Path
from agri_fulltext.io_utils import read_csv, append_csv
from agri_fulltext.config import Settings
from agri_fulltext.reviewing import finalize_review

csv_path = Path('outputs/fulltext/reviews/review_0100_20260730T190114Z/decision_template.csv')

# Check for trailing comma / None key
fields, rows = read_csv(csv_path)
print(f"Fields: {fields}")
print(f"Has None key: {None in fields}")
if None in fields:
    # Fix by rewriting without trailing comma
    text = csv_path.read_text(encoding='utf-8-sig')
    text = text.rstrip('\n\r')
    # Remove trailing comma from header and data lines
    lines = text.split('\n')
    lines = [l.rstrip(',') for l in lines]
    csv_path.write_text('\n'.join(lines), encoding='utf-8-sig')
    print("Fixed trailing comma")
    
# Try finalize
settings = Settings(repo=Path('.'))
try:
    result = finalize_review(settings, csv_path)
    print(f"Finalized: {result}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
