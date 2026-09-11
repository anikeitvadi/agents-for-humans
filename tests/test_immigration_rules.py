from agent.packs.immigration.rules import (
    BulletinChart,
    check_bulletin_cutoff,
    check_i94_i797_discrepancy,
)

# --- I-94 vs I-797 discrepancy: pure arithmetic, no legal conclusion ---


def test_i94_earlier_than_i797_is_flagged_with_correct_gap():
    result = check_i94_i797_discrepancy(i94_admit_until="2026-11-03", i797_valid_until="2026-12-28")
    assert result.discrepant is True
    assert result.gap_days == 55
    assert "attorney" in result.message.lower()
    # Must never state a legal conclusion about status/bars.
    for forbidden in ("unlawful presence", "bar", "you are not in status", "you must leave"):
        assert forbidden not in result.message.lower()


def test_matching_dates_are_not_discrepant():
    result = check_i94_i797_discrepancy(i94_admit_until="2026-12-28", i797_valid_until="2026-12-28")
    assert result.discrepant is False
    assert result.gap_days == 0


def test_i94_later_than_i797_is_also_flagged():
    result = check_i94_i797_discrepancy(i94_admit_until="2027-01-15", i797_valid_until="2026-12-28")
    assert result.discrepant is True
    assert result.gap_days == 18


# --- Bulletin cutoff: requires the USCIS-designated chart, never concludes filing eligibility ---


def _final_action_chart(month, cutoffs):
    return BulletinChart(chart_type="final_action", month=month, cutoffs=cutoffs)


def test_priority_date_before_cutoff_is_current():
    chart = _final_action_chart("2026-09", {"EB2-India": "2019-05-01"})
    result = check_bulletin_cutoff(
        priority_date="2019-04-01",
        category="EB2-India",
        uscis_designated_chart_type="final_action",
        current_chart=chart,
    )
    assert result.status == "current"
    assert "attorney" in result.message.lower()
    assert "file" not in result.message.lower().replace("filing", "")


def test_priority_date_equal_to_cutoff_is_not_current():
    # DOS instructions require a priority date STRICTLY earlier than the
    # cutoff; equality is not yet current.
    chart = _final_action_chart("2026-09", {"EB2-India": "2019-05-01"})
    result = check_bulletin_cutoff(
        priority_date="2019-05-01",
        category="EB2-India",
        uscis_designated_chart_type="final_action",
        current_chart=chart,
    )
    assert result.status == "not_current"


def test_priority_date_after_cutoff_is_not_current():
    chart = _final_action_chart("2026-09", {"EB2-India": "2019-05-01"})
    result = check_bulletin_cutoff(
        priority_date="2020-01-01",
        category="EB2-India",
        uscis_designated_chart_type="final_action",
        current_chart=chart,
    )
    assert result.status == "not_current"


def test_current_code_c_means_current():
    chart = _final_action_chart("2026-09", {"EB3-Worldwide": "C"})
    result = check_bulletin_cutoff(
        priority_date="2024-01-01",
        category="EB3-Worldwide",
        uscis_designated_chart_type="final_action",
        current_chart=chart,
    )
    assert result.status == "current"


def test_unavailable_code_u_means_not_current():
    chart = _final_action_chart("2026-09", {"EB1-China": "U"})
    result = check_bulletin_cutoff(
        priority_date="2018-01-01",
        category="EB1-China",
        uscis_designated_chart_type="final_action",
        current_chart=chart,
    )
    assert result.status == "not_current"


def test_retrogression_is_flagged_when_cutoff_moves_backward():
    previous = _final_action_chart("2026-08", {"EB2-India": "2019-06-01"})
    current = _final_action_chart("2026-09", {"EB2-India": "2019-05-01"})
    result = check_bulletin_cutoff(
        priority_date="2019-05-15",
        category="EB2-India",
        uscis_designated_chart_type="final_action",
        current_chart=current,
        previous_chart=previous,
    )
    assert result.status == "retrogressed"


def test_missing_uscis_chart_selection_needs_review():
    chart = _final_action_chart("2026-09", {"EB2-India": "2019-05-01"})
    result = check_bulletin_cutoff(
        priority_date="2019-04-01",
        category="EB2-India",
        uscis_designated_chart_type=None,
        current_chart=chart,
    )
    assert result.status == "needs_review"
    assert "attorney" in result.message.lower()


def test_chart_mismatch_needs_review():
    chart = _final_action_chart("2026-09", {"EB2-India": "2019-05-01"})
    result = check_bulletin_cutoff(
        priority_date="2019-04-01",
        category="EB2-India",
        uscis_designated_chart_type="dates_for_filing",
        current_chart=chart,  # this chart is final_action, mismatched with designation
    )
    assert result.status == "needs_review"


def test_missing_category_in_chart_needs_review():
    chart = _final_action_chart("2026-09", {"EB2-India": "2019-05-01"})
    result = check_bulletin_cutoff(
        priority_date="2019-04-01",
        category="EB3-China",
        uscis_designated_chart_type="final_action",
        current_chart=chart,
    )
    assert result.status == "needs_review"
