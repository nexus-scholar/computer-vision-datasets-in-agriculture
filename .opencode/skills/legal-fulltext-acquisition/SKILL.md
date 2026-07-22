---
name: legal-fulltext-acquisition
description: Resolve, acquire, validate, hash, and audit legal scholarly full-text artifacts without bypassing access controls or confusing free-to-read access with reuse rights.
compatibility: opencode
metadata:
  project: agri-cv
  workflow: fulltext
---

Use exact identifiers before URLs: PMCID, arXiv ID, DOI, OpenAlex ID, Semantic Scholar ID.

Allowed automated source classes:

1. exact known PDF/XML URL;
2. PubMed Central OAI-PMH and Europe PMC;
3. arXiv;
4. Unpaywall OA locations;
5. Crossref full-text links;
6. OpenAlex OA locations;
7. Semantic Scholar `openAccessPdf`;
8. explicitly enabled OpenAlex content.

Never:

- use shadow libraries;
- bypass a login, CAPTCHA, paywall, or anti-bot control;
- scrape publisher search pages as a fallback;
- resolve by fuzzy title and silently accept the result;
- store API keys in manifests or URLs;
- call “free to read” content openly licensed without evidence.

For each attempt preserve source, candidate URL with secrets redacted, status, HTTP status, final URL, content type, size, hash, license, version, rights status, timestamps, and error.

Manual institutional copies must be imported as `local_research_only` or `restricted` unless a reusable license is verified.
