# Protocol for working with free or smaller models

## Use models for judgment, not bookkeeping

Use Python for identifiers, joins, counts, hashes, deduplication, and schema validation. Use models for classification, interpretation, synthesis, and writing.

## Task contract

Every model task must specify:

- objective;
- exact input files/rows;
- permitted output file;
- required schema;
- evidence rules;
- stop conditions;
- maximum batch size.

## Recommended limits

- Full-text extraction: 1 paper.
- Title/abstract screening: 10-20 papers.
- Seed identity review: 1-5 seeds.
- Code repair: 1 bug plus tests.
- Synthesis: one matrix or one claim family.

## Verification

After every agent write:

1. inspect `git diff`;
2. run the relevant deterministic checker;
3. compare row counts and unique IDs;
4. manually inspect a sample;
5. update the session handoff.

## Privacy and provider choice

Free endpoints can change and may have different retention or model-improvement terms. Do not send unpublished confidential data, participant information, credentials, or proprietary datasets to a free hosted model. Public papers and public bibliographic metadata are lower risk, but still review the currently selected provider's terms. Keep model selection outside the committed project config so it can be changed without rewriting the workflow.
