# Configuration supplied by this package

`seed_corrections.csv` contains manually verified corrections for P004 and P013.
The installer copies it to `config/seed_corrections.csv` in the target repository.

Rules:

- Keep a correction only when its identity is verified against a primary paper record or the local PDF.
- Never place API keys in this directory.
- Review the dry-run output of `apply_seed_corrections.py` before applying changes.
