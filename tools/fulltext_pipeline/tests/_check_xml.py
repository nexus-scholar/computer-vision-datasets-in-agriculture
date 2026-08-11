from pathlib import Path
pids = [
    'doi_10.1016_j.dib.2024.110821',
    'doi_10.1016_j.ophoto.2024.100078',
    'doi_10.1016_j.dib.2020.105833',
    'doi_10.1177_0278364917720510',
]
r = Path('.')
for pid in pids:
    xmls = list(r.glob(f'data/raw/fulltext/{pid}/**/publisher.xml'))
    if xmls:
        sz = xmls[0].stat().st_size
        print(f'{pid}: size={sz}')
        txt = xmls[0].read_text(encoding='utf-8')[:300]
        print(f'  {txt}')
    else:
        print(f'{pid}: NO publisher.xml')
