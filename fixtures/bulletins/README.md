# Bulletin fixtures

`sample_month.json` seeds one visa-bulletin month for the unattended-beat demo and for `tests/test_immigration_rules.py`-style cutoff testing.

**Provenance requirement (do not skip):** before this fixture is used for anything beyond the placeholder values below, replace it with real, dated values captured from:
- DOS Visa Bulletin (both charts, Final Action Dates and Dates for Filing): https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html
- The matching-month USCIS "which chart to use for filing" page: https://www.uscis.gov/green-card/green-card-processes-and-procedures/visa-availability-and-priority-dates

Record the DOS bulletin's own publication/effective date and the USCIS chart-selection page's publication date in `source_provenance` — both are needed because they are two separate government publications, and the rules engine (`agent/packs/immigration/rules.py::check_bulletin_cutoff`) explicitly refuses to conclude anything if the two don't agree on which chart applies.
