"""Try to download PDF for rank 83 from PMC."""
from pathlib import Path
import urllib.request

url = "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11381999/pdf/main.pdf"
dest = Path("data/raw/fulltext/doi_10.1016_j.dib.2024.110821/pmc_article.pdf")

try:
    urllib.request.urlretrieve(url, dest)
    print(f"Downloaded {dest.stat().st_size} bytes")
except Exception as e:
    print(f"Failed: {e}")
    
# Also try ScienceDirect PDF for rank 85
url2 = "https://www.sciencedirect.com/science/article/pii/S266739322400022X/pdfft"
dest2 = Path("data/raw/fulltext/doi_10.1016_j.ophoto.2024.100078/sciencedirect.pdf")
try:
    req = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        with open(dest2, "wb") as f:
            f.write(r.read())
    print(f"Downloaded {dest2.stat().st_size} bytes for rank 85")
except Exception as e:
    print(f"Rank 85 failed: {e}")
