"""Deterministic immigration rules.

Scope boundary (see docs/architecture-spec.md §7, HANDOFF.md): this module
computes date arithmetic and bulletin-cutoff comparisons ONLY. It never
concludes lawful-status length, unlawful-presence bars, or filing
eligibility. Every non-trivial result is framed as a flag for attorney
review, never advice. F-1/OPT timelines and unlawful-presence-bar
computation are explicitly out of scope for this iteration.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal


def _parse(d: str) -> date:
    return date.fromisoformat(d)


@dataclass
class DiscrepancyResult:
    discrepant: bool
    gap_days: int
    message: str


def check_i94_i797_discrepancy(i94_admit_until: str, i797_valid_until: str) -> DiscrepancyResult:
    """Compare two document dates. Pure arithmetic — no status determination."""
    i94 = _parse(i94_admit_until)
    i797 = _parse(i797_valid_until)
    gap_days = abs((i797 - i94).days)
    discrepant = i94 != i797

    if not discrepant:
        message = "I-94 admit-until date matches the I-797 validity end date. No discrepancy found."
    else:
        earlier, later = ("I-94", "I-797") if i94 < i797 else ("I-797", "I-94")
        message = (
            f"Your I-94 admit-until date and I-797 validity end date disagree by {gap_days} day(s) "
            f"({earlier} is earlier). These documents disagree — this is a flag to review with your "
            f"attorney, not a status determination."
        )

    return DiscrepancyResult(discrepant=discrepant, gap_days=gap_days, message=message)


ChartType = Literal["final_action", "dates_for_filing"]
CutoffStatus = Literal["current", "not_current", "retrogressed", "needs_review"]


@dataclass
class BulletinChart:
    chart_type: ChartType
    month: str
    cutoffs: dict[str, str]  # category -> "YYYY-MM-DD" | "C" | "U"


@dataclass
class CutoffResult:
    status: CutoffStatus
    message: str


_ATTORNEY_SUFFIX = "Flag for attorney review of filing options — this is not a filing determination."


def check_bulletin_cutoff(
    priority_date: str,
    category: str,
    uscis_designated_chart_type: ChartType | None,
    current_chart: BulletinChart,
    previous_chart: BulletinChart | None = None,
) -> CutoffResult:
    """Compare a priority date to the visa bulletin cutoff for the chart
    USCIS designated for this month. DOS publishes both charts every month;
    USCIS separately announces which one applies to adjustment-of-status
    filing. Never concludes eligibility — flags for attorney review only.
    """
    if uscis_designated_chart_type is None:
        return CutoffResult(
            "needs_review",
            "USCIS has not published which chart applies this month. " + _ATTORNEY_SUFFIX,
        )

    if current_chart.chart_type != uscis_designated_chart_type:
        return CutoffResult(
            "needs_review",
            f"The bulletin chart provided ({current_chart.chart_type}) does not match the "
            f"USCIS-designated chart ({uscis_designated_chart_type}) for this month. " + _ATTORNEY_SUFFIX,
        )

    cutoff = current_chart.cutoffs.get(category)
    if cutoff is None:
        return CutoffResult(
            "needs_review",
            f"No cutoff is published for category {category} this month. " + _ATTORNEY_SUFFIX,
        )

    retrogressed = _is_retrogressed(category, cutoff, previous_chart)

    if cutoff == "U":
        status: CutoffStatus = "retrogressed" if retrogressed else "not_current"
        return CutoffResult(status, "Category is Unavailable this month. " + _ATTORNEY_SUFFIX)

    if cutoff == "C":
        return CutoffResult("current", "Category is listed as Current this month. " + _ATTORNEY_SUFFIX)

    is_current = _parse(priority_date) < _parse(cutoff)
    if is_current:
        status = "retrogressed" if retrogressed else "current"
        return CutoffResult(
            status, "Priority date is before this month's cutoff. " + _ATTORNEY_SUFFIX
        )

    status = "retrogressed" if retrogressed else "not_current"
    return CutoffResult(
        status,
        "Priority date is after this month's cutoff — not yet current. " + _ATTORNEY_SUFFIX,
    )


def _is_retrogressed(category: str, current_cutoff: str, previous_chart: BulletinChart | None) -> bool:
    if previous_chart is None:
        return False
    previous_cutoff = previous_chart.cutoffs.get(category)
    if previous_cutoff is None:
        return False
    if previous_cutoff == "C" and current_cutoff != "C":
        return True
    if previous_cutoff in ("C", "U") or current_cutoff in ("C", "U"):
        return False
    return _parse(current_cutoff) < _parse(previous_cutoff)
