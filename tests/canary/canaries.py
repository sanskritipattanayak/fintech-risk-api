"""Planted fake sensitive values, assembled at runtime.

They are built from fragments so no complete PAN/SSN/key literal exists in the
repository source (which would trip our own commit scan and GitHub secret scanning).
All are public test values or obviously fake.
"""

PAN = "4111" + "1111" + "1111" + "1111"  # public Visa test number
PAN_SPACED = "4111 1111 1111 1111"[:0] + " ".join(["4111", "1111", "1111", "1111"])
SSN = "078-05-" + "1120"
AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLE"  # AWS documentation example
PRIVATE_KEY = "-----BEGIN " + "RSA PRIVATE KEY-----"
EMAIL = "jane.doe" + "@" + "realbank.io"

ALL = {
    "pan": PAN,
    "ssn": SSN,
    "aws_access_key": AWS_KEY,
    "private_key": PRIVATE_KEY,
    "email": EMAIL,
}

# The same canaries embedded in the four places data can leak from.
PRD_TEXT = f"## Example\nCustomer Jane paid with card {PAN} and SSN {SSN}.\n"
LOG_LINE = f'{{"event":"DECLINED_VELOCITY","note":"retry for {EMAIL}","card":"{PAN}"}}'
FIXTURE_ROW = f"txn_999999,{PAN},2026-03-01T12:00:00+00:00,25.50,USD"
DIFF_ADDED = f'+API_KEY = "{AWS_KEY}"\n+ssn = "{SSN}"'
