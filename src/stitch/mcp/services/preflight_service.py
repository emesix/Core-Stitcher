"""PreflightService — collect, merge, verify topology against live observations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from stitch.collectkit.merger import merge_observations
from stitch.mcp.schemas import DetailLevel, ErrorCode, ToolResponse
from stitch.verifykit.engine import verify_topology

if TYPE_CHECKING:
    from stitch.mcp.engine import StitchEngine
    from stitch.modelkit.observation import Observation


class PreflightService:
    def __init__(self, engine: StitchEngine) -> None:
        self._engine = engine

    async def run(
        self,
        *,
        topology_path: str | None = None,
        adapters: list[Any] | None = None,
        detail: DetailLevel = DetailLevel.STANDARD,
    ) -> ToolResponse:
        # 1. Load declared topology
        try:
            declared = self._engine.get_topology(override_path=topology_path)
        except FileNotFoundError:
            path = topology_path or self._engine.topology_path
            return ToolResponse.failure(
                ErrorCode.TOPOLOGY_NOT_FOUND,
                f"Topology file not found: {path}",
                summary="Topology file not found.",
                topology_path=path,
            )
        except Exception as exc:
            path = topology_path or self._engine.topology_path
            return ToolResponse.failure(
                ErrorCode.TOPOLOGY_INVALID,
                f"Failed to load topology: {exc}",
                summary="Topology file is invalid.",
                topology_path=path,
            )

        path = topology_path or self._engine.topology_path

        # 2. Collect observations from adapters
        all_observations: list[Observation] = []
        adapter_list = adapters if adapters is not None else []
        for adapter in adapter_list:
            try:
                obs = await adapter.collect()
                all_observations.extend(obs)
            except Exception:
                pass  # adapter failures are non-fatal

        # 3. Merge observations into observed topology
        observed, _conflicts = merge_observations(all_observations)

        # 4. Verify declared vs observed
        report = verify_topology(declared, observed)

        # 5. Determine verdict
        summary = report.summary
        fail_count = summary.get("fail", 0)
        warn_count = summary.get("warning", 0)

        if fail_count > 0:
            verdict = "fail"
        elif warn_count > 0:
            verdict = "warning"
        else:
            verdict = "pass"

        # 6. Build findings based on detail level
        findings: list[dict[str, Any]] = []
        if detail != DetailLevel.SUMMARY:
            for link_result in report.results:
                if detail == DetailLevel.STANDARD and link_result.status == "pass":
                    continue
                finding: dict[str, Any] = {
                    "link": link_result.link,
                    "link_type": link_result.link_type,
                    "status": link_result.status,
                    "highest_severity": str(link_result.highest_severity),
                }
                if detail == DetailLevel.FULL:
                    finding["checks"] = [c.model_dump(mode="json") for c in link_result.checks]
                else:
                    # STANDARD: only include failing/warning checks
                    failing = [c for c in link_result.checks if c.flag not in ("ok",)]
                    finding["checks"] = [c.model_dump(mode="json") for c in failing]
                findings.append(finding)

        result: dict[str, Any] = {
            "verdict": verdict,
            "observations_collected": len(all_observations),
            "links_total": summary.get("total", 0),
            "links_pass": summary.get("pass", 0),
            "links_fail": fail_count,
            "links_warning": warn_count,
            "highlights": summary.get("highlights", []),
            "findings": findings,
        }

        return ToolResponse.success(
            result,
            summary=f"Preflight {verdict}: {fail_count} fail, {warn_count} warn, "
            f"{summary.get('pass', 0)} pass ({len(all_observations)} observations)",
            topology_path=path,
        )
