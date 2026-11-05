from examples.feature_demos.cron_reporting.contract import CATALOG, SCHEDULE
from myworkflow.generation.schedules import render_schedules
from myworkflow.generation.workflows import workflow_documents


def test_schedule_document_and_workflow_details_reference_the_same_entry_point():
    text = render_schedules((SCHEDULE,), CATALOG)
    assert "0 6 * * *" in text and "Asia/Tokyo" in text
    assert "(workflows/w.daily_report.md)" in text
    assert "| b.daily_report | t.daily_cron | [システム]" in text
    assert text == render_schedules((SCHEDULE,), CATALOG)
    page = workflow_documents(CATALOG, schedules=(SCHEDULE,))[
        "workflows/w.daily_report.md"
    ]
    assert "cron.daily_report" in page and "Asia/Tokyo" in page
    assert "(../schedules.md)" in page
