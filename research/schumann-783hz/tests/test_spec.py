"""Spec Kit artefacts: template conformance, IDs, checklist, contracts vs results."""
from __future__ import annotations

import re

SPEC_DIR = "specs/001-sr783-tro-ly-dong-bo"
TEMPLATE_HEADINGS = [
    "## User Scenarios & Testing *(mandatory)*", "### Edge Cases", "## Requirements *(mandatory)*",
    "### Functional Requirements", "### Key Entities *(include if feature involves data)*",
    "## Success Criteria *(mandatory)*", "### Measurable Outcomes", "## Assumptions",
]


def read(root, rel):
    return (root / rel).read_text(encoding="utf-8")


def test_spec_follows_template(root):
    spec = read(root, f"{SPEC_DIR}/spec.md")
    assert spec.startswith("# Feature Specification: ")
    pos = [spec.index(h) for h in TEMPLATE_HEADINGS]
    assert pos == sorted(pos)
    assert "[NEEDS CLARIFICATION" not in spec
    for field in ("**Feature Branch**", "**Created**", "**Status**", "**Input**"):
        assert field in spec


def test_user_stories(root):
    spec = read(root, f"{SPEC_DIR}/spec.md")
    stories = re.findall(r"^### User Story (\d+) - .+ \(Priority: P(\d)\)$", spec, flags=re.M)
    assert [int(n) for n, _ in stories] == list(range(1, 8))
    for block in spec.split("### User Story ")[1:]:
        block = block.split("### Edge Cases")[0]
        assert "**Why this priority**" in block and "**Independent Test**" in block and "**Acceptance Scenarios**" in block
        assert re.search(r"\*\*Given\*\*.+\*\*When\*\*", block, flags=re.S)


def test_requirement_and_success_ids(root):
    spec = read(root, f"{SPEC_DIR}/spec.md")
    fr = [int(x) for x in re.findall(r"\*\*FR-(\d{3})\*\*", spec)]
    sc = [int(x) for x in re.findall(r"\*\*SC-(\d{3})\*\*", spec)]
    assert fr == list(range(1, 31)) and sc == list(range(1, 13))


def test_checklist_complete(root):
    cl = read(root, f"{SPEC_DIR}/checklists/requirements.md")
    assert "- [ ]" not in cl and cl.count("- [x]") == 16


def test_plan_and_constitution(root):
    plan = read(root, f"{SPEC_DIR}/plan.md")
    for h in ("## Summary", "## Technical Context", "## Constitution Check", "## Project Structure", "## Complexity Tracking"):
        assert h in plan
    const = read(root, ".specify/memory/constitution.md")
    assert len(re.findall(r"^### [IVX]+\. ", const, flags=re.M)) == 7


def test_tasks_reference_existing_files(root):
    tasks = read(root, f"{SPEC_DIR}/tasks.md")
    done = [ln for ln in tasks.splitlines() if ln.startswith("- [X]")]
    todo = [ln for ln in tasks.splitlines() if ln.startswith("- [ ]")]
    ids = [int(x) for x in re.findall(r"^- \[[X ]\] T(\d{3})", tasks, flags=re.M)]
    assert ids == list(range(1, 33)) and len(done) == 28
    assert len(todo) == 4 and all("[US7]" in ln for ln in todo)   # only the future hardware bridge is open
    for line in done:
        for path in re.findall(r"`([^`\s]+\.(?:py|json|html|md|cjs))`", line):
            assert (root / path).exists() or (root / SPEC_DIR / path).exists(), path


def test_contract_vectors_match_results(root, results):
    sync = read(root, f"{SPEC_DIR}/contracts/sync-code.md")
    assert results["synth"]["sync_code_example"]["code"] in sync
    for v in results["synth"]["phase_vectors"]:
        assert f"| {v['phase_num']} |" in sync and v["phase_deg"] in sync
    sett = read(root, f"{SPEC_DIR}/contracts/settings-secded.md")
    rec = results["settings_record"]
    for token in rec["codewords"] + [rec["tag"], rec["word0_hex"], rec["word1_hex"]]:
        assert token in sett
