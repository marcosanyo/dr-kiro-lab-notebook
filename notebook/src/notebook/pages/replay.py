"""The replay pages: one static page per step of a session (Requirement 16, design N10). Task 18.1.

A step's page is the session page of `views.step_view(record, step)`, rendered by the same code
(`pages/session.py`, `page`) with the step's controls. Its address is `<app>-<session>-replay-<n>.html`
(`addresses.replay`). The pages carry no text of their own beyond the controls and the labels of `text.py`.
"""

from notebook import addresses, views
from notebook.choices import Choices
from notebook.ink import Segment
from notebook.layouts import Layout
from notebook.pages import session
from notebook.pages.photo import PictureFile, Pins
from notebook.records import RecordModel

PageOut = tuple[list[Segment], tuple[PictureFile, ...]]


def step_pages(record: RecordModel, layout: Layout, choices: Choices) -> dict[str, PageOut]:
    """Every replay page of `record`, keyed by its site path, in step order (Requirement 16.8)."""
    steps = views.steps(record)
    out: dict[str, PageOut] = {}
    session_page = addresses.session(record.application, record.session, f"{record.name}/log.jsonl line 1")
    for step in steps:
        here = addresses.replay(record.application, record.session, step.number, f"{record.name}/log.jsonl")
        back = (
            session_page
            if step.number == 1
            else addresses.replay(record.application, record.session, step.number - 1, record.name)
        )
        forward = (
            addresses.replay(record.application, record.session, step.number + 1, record.name)
            if step.number < len(steps)
            else None
        )
        nav = session.Nav(
            number=step.number,
            total=len(steps),
            end=step.end,
            back=back,
            forward=forward,
            session=session_page,
        )
        view = views.step_view(record, step)
        out[here] = session.page(view, choices, Pins(record, layout), nav)
    return out
