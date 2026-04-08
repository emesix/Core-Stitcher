"""preflight — Preflight workflow application.

Orchestrates the full preflight check: collect topology from all resource
modules, merge into a snapshot, verify against contracts, and expose results
via interfacekit's HTTP API and MCP tools.
"""

from vos.apps.preflight.workflow import PreflightWorkflow

__all__ = ["PreflightWorkflow"]
