"""Diff engine — compare two VerificationReports.

Pure function. No I/O, no spine dependency. Produces a deterministic
VerificationDiff summarizing added/removed/changed link verifications.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vos.modelkit.diff import CheckDiff, DiffSummary, LinkDiff, VerificationDiff

if TYPE_CHECKING:
    from vos.modelkit.verification import CheckResult, VerificationReport


def diff_reports(before: VerificationReport, after: VerificationReport) -> VerificationDiff:
    before_map = {lv.link: lv for lv in before.results}
    after_map = {lv.link: lv for lv in after.results}

    all_links = sorted(set(before_map) | set(after_map))
    links: list[LinkDiff] = []

    for link_id in all_links:
        b = before_map.get(link_id)
        a = after_map.get(link_id)

        if b is None:
            links.append(LinkDiff(link=link_id, change="added"))
        elif a is None:
            links.append(LinkDiff(link=link_id, change="removed"))
        else:
            check_diffs = _diff_checks(b.checks, a.checks)
            change = "changed" if check_diffs else "unchanged"
            links.append(LinkDiff(link=link_id, change=change, check_diffs=check_diffs))

    summary = DiffSummary(
        added=sum(1 for ld in links if ld.change == "added"),
        removed=sum(1 for ld in links if ld.change == "removed"),
        changed=sum(1 for ld in links if ld.change == "changed"),
        unchanged=sum(1 for ld in links if ld.change == "unchanged"),
    )

    return VerificationDiff(
        before_timestamp=before.timestamp,
        after_timestamp=after.timestamp,
        links=links,
        summary=summary,
    )


def _diff_checks(before: list[CheckResult], after: list[CheckResult]) -> list[CheckDiff]:
    def key(c: CheckResult) -> tuple[str, str]:
        return (c.check, c.port)

    before_map = {key(c): c for c in before}
    after_map = {key(c): c for c in after}

    diffs: list[CheckDiff] = []
    all_keys = sorted(set(before_map) | set(after_map))

    for k in all_keys:
        b = before_map.get(k)
        a = after_map.get(k)

        if b is None and a is not None:
            diffs.append(
                CheckDiff(check=a.check, port=a.port, change="added", after_flag=a.flag)
            )
        elif a is None and b is not None:
            diffs.append(
                CheckDiff(check=b.check, port=b.port, change="removed", before_flag=b.flag)
            )
        elif b is not None and a is not None and b.flag != a.flag:
            diffs.append(
                CheckDiff(
                    check=b.check,
                    port=b.port,
                    change="changed",
                    before_flag=b.flag,
                    after_flag=a.flag,
                )
            )

    return diffs
