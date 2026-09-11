"""Unattended visa-bulletin beat (C3): loads a captured DOS bulletin month
+ the matching USCIS chart-selection month, evaluates one seeded case's
priority date against it, and runs the result through the same shared
engine/gate/persistence/draft path as the discrepancy pack — proving the
"watch -> match -> evaluate -> ping" loop runs unattended, not just on a
user-triggered upload. See fixtures/bulletins/ for the real captured
source data and its provenance.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from strands import Agent

from agent.engine.engine import RuleOutcome, process_event
from agent.engine.schema import Alert, Clock, Event
from agent.engine.store import Store
from agent.llm.draft import DraftResult, build_attorney_draft
from agent.packs.immigration.rules import BulletinChart, CutoffResult, check_bulletin_cutoff

BULLETINS_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "bulletins"


class BulletinLoadError(Exception):
    """A bulletin/chart-selection source is missing or malformed — must
    produce a visible review/error state, never a crash (C3)."""


@dataclass
class SeededCase:
    case_name: str
    priority_date: str
    category: str
    chargeability: str


# The immediately preceding captured month, keyed by month. Lets a poll skip
# a same-chart-type retrogression comparison correctly (see
# fixtures/bulletins/README.md) without calendar arithmetic over a fixture
# set that does not cover every month.
PRIOR_CAPTURED_MONTH: dict[str, str] = {"2025-10": "2025-09"}


def load_seeded_case(bulletins_dir: Path = BULLETINS_DIR) -> SeededCase:
    data = json.loads((bulletins_dir / "seeded_case.json").read_text())
    return SeededCase(
        case_name=data["case_name"],
        priority_date=data["priority_date"],
        category=data["category"],
        chargeability=data["chargeability"],
    )


@dataclass
class BulletinMonth:
    chart: BulletinChart
    designated_chart_type: str | None


def load_bulletin_month(month: str, bulletins_dir: Path = BULLETINS_DIR) -> BulletinMonth:
    path = bulletins_dir / f"{month}.json"
    if not path.exists():
        raise BulletinLoadError(f"no captured bulletin + chart-selection source for month '{month}'")
    try:
        data = json.loads(path.read_text())
        dos = data["dos_bulletin"]
        uscis = data["uscis_chart_selection"]
        chart = BulletinChart(chart_type=dos["chart_type"], month=dos["month"], cutoffs=dos["cutoffs"])
        designated_chart_type = uscis["designated_chart_type"]
    except (KeyError, json.JSONDecodeError) as exc:
        raise BulletinLoadError(f"malformed bulletin fixture for month '{month}': {exc}") from exc
    return BulletinMonth(chart=chart, designated_chart_type=designated_chart_type)


@dataclass
class BulletinPollResult:
    alert: Alert | None
    draft: DraftResult | None
    cutoff: CutoffResult | None
    error: str | None


def run_bulletin_poll(
    store: Store,
    clock_id: str,
    month: str,
    case: SeededCase,
    agent: Agent | None = None,
    previous_month: str | None = None,
    bulletins_dir: Path = BULLETINS_DIR,
) -> BulletinPollResult:
    try:
        current = load_bulletin_month(month, bulletins_dir=bulletins_dir)
    except BulletinLoadError as exc:
        return BulletinPollResult(alert=None, draft=None, cutoff=None, error=str(exc))

    previous_chart = None
    if previous_month is not None:
        try:
            previous = load_bulletin_month(previous_month, bulletins_dir=bulletins_dir)
        except BulletinLoadError:
            previous = None
        # Only a same-chart-type comparison is a meaningful retrogression
        # check — DOS publishes Final Action Dates and Dates for Filing as
        # two separate series, so comparing across a month where USCIS
        # switched which one it designated would conflate two different
        # published series, not an actual backward move.
        if previous is not None and previous.chart.chart_type == current.chart.chart_type:
            previous_chart = previous.chart

    cutoff = check_bulletin_cutoff(
        priority_date=case.priority_date,
        category=case.category,
        uscis_designated_chart_type=current.designated_chart_type,
        current_chart=current.chart,
        previous_chart=previous_chart,
    )

    if cutoff.status == "needs_review":
        return BulletinPollResult(alert=None, draft=None, cutoff=cutoff, error=cutoff.message)

    # Only a status the case-holder can act on (newly current, or a
    # retrogression that costs them ground) is worth an attorney's
    # attention — "still not current, nothing changed" stays silent.
    material = cutoff.status in ("current", "retrogressed")
    outcome = RuleOutcome(material=material, actionable=material, window_open=material)

    clock = Clock(clock_id=clock_id, user_id="demo-user", module="immigration", rule_id="bulletin_cutoff", state="quiet")
    event = Event(
        event_id=f"bulletin-{month}-{case.category}",
        source="visa_bulletin",
        effective_date=month,
        rule_version="v1",
        payload={"month": month, "category": case.category, "priority_date": case.priority_date},
    )

    alert = process_event(store, clock, event, outcome)

    draft = None
    if alert.decision == "surfaced":
        draft = build_attorney_draft(rule_message=cutoff.message, subject_facts={"case_name": case.case_name}, agent=agent)
        store.save_draft(
            clock_id=clock.clock_id,
            event_id=event.event_id,
            rule_version=event.rule_version,
            status="ready",
            subject=draft.subject,
            body=draft.body,
            used_llm_personalization=draft.used_llm_personalization,
        )
    else:
        existing = store.get_draft(clock_id=clock.clock_id, event_id=event.event_id, rule_version=event.rule_version)
        if existing is not None and existing.status == "ready":
            draft = DraftResult(
                subject=existing.subject,
                body=existing.body,
                used_llm_personalization=bool(existing.used_llm_personalization),
            )

    return BulletinPollResult(alert=alert, draft=draft, cutoff=cutoff, error=None)
