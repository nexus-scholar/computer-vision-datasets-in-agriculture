import csv
import io
import sys

from agri_fulltext.schema import FULLTEXT_DECISION_FIELDS

REPAIRS = {
    "outputs/fulltext/reviews/review_0139_20260803T012216Z/decision_template.csv": {
        "prefix": 12,
        "join_field": "source_page",
        "join_range": slice(12, 15),
    },
    "outputs/fulltext/reviews/review_0212_20260803T012235Z/decision_template.csv": {
        "prefix": 19,
        "join_field": "notes",
        "join_range": slice(19, 27),
    },
}


def main() -> int:
    for path, spec in REPAIRS.items():
        with open(path, encoding="utf-8", newline="") as fh:
            rows = list(csv.reader(fh))
        header, body = rows[0], rows[1]
        if header != FULLTEXT_DECISION_FIELDS:
            raise ValueError(f"Unexpected header in {path}: {header}")
        if len(body) == len(FULLTEXT_DECISION_FIELDS):
            print(f"OK (already 20 fields): {path}")
            continue
        prefix = body[: spec["prefix"]]
        joined = ",".join(body[spec["join_range"]])
        tail = body[spec["join_range"].stop :]
        rebuilt = prefix + [joined] + tail
        if len(rebuilt) != len(FULLTEXT_DECISION_FIELDS):
            raise ValueError(
                f"Rebuilt row has {len(rebuilt)} fields, expected {len(FULLTEXT_DECISION_FIELDS)}: {path}"
            )
        buf = io.StringIO()
        csv.writer(buf, lineterminator="\n").writerow(FULLTEXT_DECISION_FIELDS)
        csv.writer(buf, lineterminator="\n").writerow(rebuilt)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(buf.getvalue())
        print(f"REPAIRED {path}: {len(body)} -> {len(rebuilt)} fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())
