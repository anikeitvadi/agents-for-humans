"""Demo configuration.

No frozen "as of" date is needed: the discrepancy check
(check_i94_i797_discrepancy) is pure document-to-document date arithmetic
("these two dates disagree by N days"), not a days-remaining-from-today
calculation, so its output cannot drift with wall-clock time. If a future
rule needs "today" (e.g. a real window-open check against the current
date), reintroduce a frozen as-of value here rather than calling
date.today() directly, so demo runs stay reproducible.
"""

RULE_VERSION = "v1"

# The Strands/Bedrock default model id varies by SDK version — always set
# this explicitly and confirm access to it in the Bedrock console before
# relying on it (see docs/architecture-spec.md "open uncertainties").
BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"  # UNVERIFIED — confirm before Day 1 build
