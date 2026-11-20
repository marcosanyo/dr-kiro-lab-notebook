"""How the lab works, `how.html` (Requirement 18). Task 14.1.

The page has four parts:

- the two levels of spec: the builder's specs, which built the lab, and Dr. Kiro's lab spec (18.1);
- what Dr. Kiro can and cannot touch: its lab folder's spec and experiment files, the four bench tools, no
  shell, no other folder (18.2);
- the two applications side by side, from the declaration in each record: knobs and ranges, measurements,
  budget, picture kind and goal. Records of one application with different declarations get one column per
  distinct declaration, each with its session ids (18.3);
- per session, the count of refusals by action and each refusal's message as recorded (18.4).

The commentary comes from `text.py`, quotes no builder spec and names or links no file or folder outside a lab
(18.5, design N24). Declared values are the bench's (pencil); declared numbers are shown as recorded, in full.
"""

from notebook import addresses, html, numbers, refusals
from notebook.choices import App
from notebook.errors import NotebookError
from notebook.ink import Segment, pencil
from notebook.pages import parts
from notebook.pages.parts import link, say_text
from notebook.records import REFUSAL_GIVEN, Declaration, RecordModel, Refusal

# The bench's refused actions, in the order of its four tools (register, run, verdict, end).
ACTIONS = tuple(REFUSAL_GIVEN)


def _start(record: RecordModel) -> str:
    return f"{record.name}/log.jsonl line 1"


def _value(text: str, source: str) -> list[Segment]:
    return html.text(pencil(text, source))


def declaration_key(declaration: Declaration) -> tuple:
    """The parts of a declaration this page shows (18.3: knobs and ranges, measurements, budget, picture
    kind, goal), without where they were read. Two records with equal keys get one column. Parts the page
    does not show (the knob descriptions, how the measurements are made) are left out, so two columns never
    look the same."""
    return (
        tuple((k.name, k.kind, k.low, k.high) for k in declaration.knobs),
        tuple((m.name, m.unit, m.kind) for m in declaration.measurements),
        declaration.picture.text,
        declaration.budget,
        declaration.goal.text,
    )


def declarations(records: list[RecordModel]) -> list[tuple[str, list[RecordModel]]]:
    """(application, records) per distinct declaration: applications in code-point order, and within one
    application the declarations in the order of their first session (records are in session order)."""
    groups: dict[tuple[str, tuple], list[RecordModel]] = {}
    for record in sorted(records, key=lambda r: (r.application, r.session)):
        groups.setdefault((record.application, declaration_key(record.declaration)), []).append(record)
    return [(application, group) for (application, _), group in groups.items()]


def _items(items: list[list[Segment]]) -> list[Segment]:
    return [s for item in items for s in html.element("li", None, item)]


def _application(application: str, group: list[RecordModel]) -> list[Segment]:
    first = group[0]
    source = _start(first)
    declared = first.declaration
    sessions: list[Segment] = []
    for i, record in enumerate(group):
        if i:
            sessions += say_text("LIST_SEPARATOR")
        start = _start(record)
        page = addresses.session(record.application, record.session, start)
        sessions += link(page, _value(record.session, start))
    knobs = [
        [
            *_value(k.name, source),
            *say_text("HOW_KNOB_KIND"),
            *_value(k.kind, source),
            *say_text("HOW_KNOB_RANGE"),
            *say_text("HOW_RANGE_OPEN"),
            *_value(numbers.full(k.low, source), source),
            *say_text("LIST_SEPARATOR"),
            *_value(numbers.full(k.high, source), source),
            *say_text("HOW_RANGE_CLOSE"),
        ]
        for k in declared.knobs
    ]
    measurements = [
        [
            *_value(m.name, source),
            *say_text("HOW_MEASUREMENT_UNIT"),
            *_value(m.unit, source),
            *say_text("HOW_MEASUREMENT_KIND"),
            *_value(m.kind, source),
        ]
        for m in declared.measurements
    ]
    return html.element(
        "section",
        {"class": "how-app"},
        [
            *html.element("h3", None, _value(application, source)),
            *html.element("p", None, [*say_text("HOW_APP_SESSIONS"), *sessions]),
            *html.element("p", None, [*say_text("HOW_GOAL"), *html.text(declared.goal.segment())]),
            *html.element("p", None, say_text("HOW_KNOBS")),
            *html.element("ul", {"class": "how-list"}, _items(knobs)),
            *html.element("p", None, say_text("HOW_MEASUREMENTS")),
            *html.element("ul", {"class": "how-list"}, _items(measurements)),
            *html.element("p", None, [*say_text("HOW_BUDGET"), *_value(str(declared.budget), source)]),
            *html.element("p", None, [*say_text("HOW_PICTURE"), *html.text(declared.picture.segment())]),
        ],
    )


def refusal_counts(record: RecordModel) -> list[tuple[str, int]]:
    """(action, number of refusal entries) for each of the bench's refused actions, in tool order."""
    unknown = [r.action for r in record.refusals if r.action not in ACTIONS]
    if unknown:
        raise NotebookError(record.name, f"refusals of unknown actions {unknown}")
    return [(action, sum(1 for r in record.refusals if r.action == action)) for action in ACTIONS]


def _refusal(record: RecordModel, refusal: Refusal) -> list[Segment]:
    source = f"{record.name}/log.jsonl line {refusal.seq}"
    shown = refusals.message(refusal)
    body = html.element(
        "p",
        None,
        [
            *say_text("REFUSAL_ACTION"),
            *_value(refusal.action, source),
            *say_text("VERDICT_COLON"),
            *(s for part in shown.parts for s in html.text(part)),
        ],
    )
    if shown.note is not None:
        body += html.element("p", {"class": "quote-note"}, html.text(shown.note))
    return html.element("li", {"class": "refusal"}, body)


def _session_refusals(record: RecordModel) -> list[Segment]:
    start = _start(record)
    seal = f"{record.name}/log.jsonl line {record.seal.seq}"
    page = addresses.session(record.application, record.session, start)
    counts: list[Segment] = []
    for i, (action, count) in enumerate(refusal_counts(record)):
        if i:
            counts += say_text("LIST_SEPARATOR")
        counts += [*_value(action, seal), *say_text("VALUE_SEPARATOR"), *_value(str(count), seal)]
    heading = link(
        page,
        [*_value(record.application, start), *say_text("HOW_SESSION_OF"), *_value(record.session, start)],
    )
    content = [
        *html.element("h3", None, heading),
        *html.element("p", None, [*say_text("HOW_REFUSALS_BY_ACTION"), *counts]),
    ]
    if record.refusals:
        content += html.element(
            "ul", {"class": "refusals"}, [s for r in record.refusals for s in _refusal(record, r)]
        )
    else:
        content += html.element("p", None, say_text("REFUSALS_NONE"))
    return html.element("section", {"class": "how-refusals"}, content)


def page(records: list[RecordModel], app: App) -> list[Segment]:
    """`how.html` of one application from its records, in code-point order of session."""
    if not records:
        raise NotebookError("how.html", "the page needs at least one record")
    ordered = sorted(records, key=lambda r: (r.application, r.session))
    tools = [
        say_text(name) for name in ("HOW_TOOL_REGISTER", "HOW_TOOL_RUN", "HOW_TOOL_VERDICT", "HOW_TOOL_END")
    ]
    apps = [s for application, group in declarations(ordered) for s in _application(application, group)]
    body = [
        *html.element("p", None, link(addresses.COVER, say_text("BACK_TO_COVER"))),
        *html.element("h1", None, say_text("HOW_TITLE")),
        *html.element("p", None, say_text("HOW_INTRO")),
        *html.element(
            "section",
            {"class": "how-levels", "id": "levels"},
            [
                *html.element("h2", None, say_text("HOW_LEVELS_HEADING")),
                *html.element("p", None, say_text("HOW_LEVEL_BUILDER")),
                *html.element("p", None, say_text("HOW_LEVEL_DRKIRO")),
            ],
        ),
        *html.element(
            "section",
            {"class": "how-touch", "id": "touch"},
            [
                *html.element("h2", None, say_text("HOW_TOUCH_HEADING")),
                *html.element("p", None, say_text("HOW_CAN")),
                *html.element("ul", {"class": "how-list"}, _items(tools)),
                *html.element("p", None, say_text("HOW_CANNOT")),
                *html.element("p", None, say_text("HOW_WORDING")),
            ],
        ),
        *html.element(
            "section",
            {"class": "how-apps", "id": "applications"},
            [
                *html.element("h2", None, say_text("HOW_APPS_HEADING")),
                *html.element("p", None, say_text("HOW_APPS_INTRO")),
                *html.element("section", {"class": "side-by-side"}, apps),
            ],
        ),
        *html.element(
            "section",
            {"class": "how-refusal-list", "id": "refusals"},
            [
                *html.element("h2", None, say_text("HOW_REFUSALS_HEADING")),
                *html.element("p", None, say_text("HOW_REFUSALS_INTRO")),
                *(s for r in ordered for s in _session_refusals(r)),
            ],
        ),
    ]
    return parts.page("HOW_TITLE", body, app=app)
