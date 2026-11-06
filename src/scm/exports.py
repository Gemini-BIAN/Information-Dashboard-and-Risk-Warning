import csv
import io


def safe_csv(rows):
    """Prevent spreadsheet formula execution from external titles/notes."""
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        sanitized = {}
        for key, value in row.items():
            text = "" if value is None else str(value)
            sanitized[key] = (
                "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text
            )
        writer.writerow(sanitized)
    return "\ufeff" + output.getvalue()
