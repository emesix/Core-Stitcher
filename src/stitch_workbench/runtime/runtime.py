from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

import structlog
from sqlalchemy import text
from sqlmodel import Session, select

from stitch_workbench.config.loader import load_module_configs, load_workbench_config
from stitch_workbench.events.bus import EventBus
from stitch_workbench.registry.registry import ModuleTypeRegistry
from stitch_workbench.runtime.resolver import RuntimeCapabilityResolver
from stitch_workbench.runtime.startup import StartupPlan, compute_startup_order
from stitch_workbench.sdk.context import ModuleContext
from stitch_workbench.storage.database import create_db_engine, run_migrations
from stitch_workbench.storage.models import EventRecord, ModuleHealthRecord

if TYPE_CHECKING:
    from pathlib import Path
    from uuid import UUID

    from sqlalchemy import Engine

    from stitch_workbench.config.models import ModuleConfig, WorkbenchConfig
    from stitch_workbench.events.models import VosEvent

logger = structlog.get_logger()


def _glob_to_like(pattern: str) -> str:
    """Convert a shell glob pattern to SQL LIKE, escaping literal metacharacters."""
    result = pattern.replace("\\", "\\\\")
    result = result.replace("%", "\\%")
    result = result.replace("_", "\\_")
    result = result.replace("*", "%")
    result = result.replace("?", "_")
    return result


class Runtime:
    """Core runtime that wires config, registry, event bus, storage, and startup."""

    def __init__(
        self,
        project_root: Path,
        db_url: str = "sqlite:///stitch_workbench.db",
        migration_policy: Literal["auto", "strict"] = "auto",
    ) -> None:
        self._project_root = project_root
        self._db_url = db_url
        self._migration_policy: Literal["auto", "strict"] = migration_policy
        self._workbench_config: WorkbenchConfig | None = None
        self._module_configs: list[ModuleConfig] = []
        self._modules_by_name: dict[str, ModuleConfig] = {}
        self._modules_by_uuid: dict[str, ModuleConfig] = {}
        self._startup_plan: StartupPlan | None = None
        self._booted = False

        self._module_instances: dict[str, object] = {}  # name → started instance

        self.event_bus = EventBus()
        self.registry = ModuleTypeRegistry()
        self._engine: Engine | None = None
        self._resolver = RuntimeCapabilityResolver()

    def load(self) -> None:
        """Load config, initialize DB, discover types, compute startup."""
        # 1. Load config
        self._workbench_config = load_workbench_config(self._project_root)
        self._module_configs = load_module_configs(self._project_root)
        self._modules_by_name = {m.name: m for m in self._module_configs}
        self._modules_by_uuid = {str(m.uuid): m for m in self._module_configs}

        # 2. Initialize database
        self._engine = create_db_engine(self._db_url)
        run_migrations(self._engine, self._migration_policy)

        # 3. Wire event persistence callback
        self.event_bus.on_publish = self._persist_event

        # 4. Discover module types from entry points
        discovered = self.registry.discover_entry_points()

        # 5. Compute startup plan
        self._startup_plan = compute_startup_order(self._module_configs)

        self._booted = True

        logger.info(
            "runtime_booted",
            project_id=self._workbench_config.project.id,
            module_count=len(self._module_configs),
            types_discovered=discovered,
            startup_groups=len(self._startup_plan.order),
            failed_modules=list(self._startup_plan.failed.keys()),
        )

        # Emit system.loaded — MUST be after on_publish is wired (step 3)
        from stitch_workbench.events.models import VosEvent as _VosEvent

        boot_event = _VosEvent(
            type="system.loaded",
            source="system://runtime",
            project_id=self._workbench_config.project.id,
            data={
                "module_count": len(self._module_configs),
                "types_discovered": discovered,
                "startup_groups": len(self._startup_plan.order),
                "failed_modules": list(self._startup_plan.failed.keys()),
            },
        )
        # load() is sync, event_bus.publish is async — use sync persistence directly
        self._persist_event(boot_event)
        self.event_bus._history.append(boot_event)

    @property
    def workbench_config(self) -> WorkbenchConfig:
        if self._workbench_config is None:
            raise RuntimeError("Runtime not loaded. Call load() first.")
        return self._workbench_config

    @property
    def module_configs(self) -> list[ModuleConfig]:
        return list(self._module_configs)

    @property
    def startup_plan(self) -> StartupPlan | None:
        return self._startup_plan

    @property
    def is_booted(self) -> bool:
        return self._booted

    def get_module(self, name: str) -> ModuleConfig | None:
        return self._modules_by_name.get(name)

    def get_module_by_uuid(self, uuid: str) -> ModuleConfig | None:
        return self._modules_by_uuid.get(uuid)

    def compute_startup(self) -> StartupPlan:
        return compute_startup_order(self._module_configs)

    def is_ready(self) -> dict:
        """Check readiness: boot complete, no hard failures, DB reachable."""
        failed_modules: list[str] = []
        startup_plan_complete = True

        if self._startup_plan:
            failed_modules = list(self._startup_plan.failed.keys())
            if failed_modules:
                startup_plan_complete = False

        # Fresh DB ping — not cached state from boot
        db_reachable = False
        if self._engine is not None:
            try:
                with self._engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                db_reachable = True
            except Exception:
                pass

        ready = self._booted and startup_plan_complete and db_reachable

        return {
            "status": "ready" if ready else "not_ready",
            "booted": self._booted,
            "startup_plan_complete": startup_plan_complete,
            "db_reachable": db_reachable,
            "failed_modules": failed_modules,
        }

    def get_health(self) -> dict:
        """Get system + per-module health status."""
        modules_health = []
        for mod in self._module_configs:
            status = "enabled" if mod.enabled else "disabled"
            if self._startup_plan and mod.name in self._startup_plan.failed:
                status = "failed"
            modules_health.append(
                {
                    "uuid": str(mod.uuid),
                    "name": mod.name,
                    "type": mod.type,
                    "status": status,
                    "failure_reason": (
                        self._startup_plan.failed.get(mod.name) if self._startup_plan else None
                    ),
                }
            )

        failed_count = len(self._startup_plan.failed) if self._startup_plan else 0
        system_status = "ok" if failed_count == 0 else "degraded"

        return {
            "system_status": system_status,
            "booted": self._booted,
            "project_id": self.workbench_config.project.id,
            "module_count": len(self._module_configs),
            "failed_count": failed_count,
            "startup_groups": len(self._startup_plan.order) if self._startup_plan else 0,
            "modules": modules_health,
        }

    def query_events(
        self,
        event_type: str | None = None,
        source: str | None = None,
        severity: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict], int, bool]:
        """Query persisted events. Returns (events, count, has_more)."""
        if self._engine is None:
            return [], 0, False

        with Session(self._engine) as session:
            stmt = select(EventRecord).order_by(
                EventRecord.time,  # pyright: ignore[reportArgumentType]
                EventRecord.id,  # pyright: ignore[reportArgumentType]
            )
            if event_type:
                stmt = stmt.where(EventRecord.type == event_type)
            if source:
                like_pattern = _glob_to_like(source)
                stmt = stmt.where(
                    EventRecord.source.like(like_pattern, escape="\\")  # pyright: ignore[reportAttributeAccessIssue]
                )
            if severity:
                stmt = stmt.where(EventRecord.severity == severity)
            if since:
                stmt = stmt.where(EventRecord.time >= since)  # pyright: ignore[reportArgumentType]
            if until:
                stmt = stmt.where(EventRecord.time <= until)  # pyright: ignore[reportArgumentType]

            stmt = stmt.offset(offset).limit(limit + 1)
            records = list(session.exec(stmt).all())

            has_more = len(records) > limit
            records = records[:limit]

            events = [
                {
                    "id": str(r.id),
                    "type": r.type,
                    "source": r.source,
                    "time": r.time.isoformat() if r.time else None,
                    "project_id": r.project_id,
                    "severity": r.severity,
                    "data": r.data,
                }
                for r in records
            ]
            return events, len(events), has_more

    def record_module_health(
        self,
        module_uuid: UUID,
        status: str,
        details: dict | None = None,
    ) -> None:
        """Persist a module health snapshot."""
        if self._engine is None:
            return
        with Session(self._engine) as session:
            record = ModuleHealthRecord(
                module_uuid=module_uuid,
                status=status,
                checked_at=datetime.now(UTC),
                details=details,
            )
            session.add(record)
            session.commit()

    async def boot_modules(self) -> dict[str, str]:
        """Instantiate and start all enabled modules per the startup plan.

        Returns a dict of {module_name: status} where status is 'started' or
        an error message. Modules are started in startup plan order.
        """
        if not self._booted:
            raise RuntimeError("Runtime not loaded. Call load() first.")
        if self._startup_plan is None:
            raise RuntimeError("No startup plan. Call load() first.")

        results: dict[str, str] = {}

        # Mark disabled and failed modules
        for config in self._module_configs:
            if not config.enabled:
                results[config.name] = "disabled"
        for name, reason in self._startup_plan.failed.items():
            results[name] = f"failed: {reason}"

        # Start in dependency order: each group can run in parallel,
        # groups are sequential
        for group in self._startup_plan.order:
            for name in group:
                config = self._modules_by_name.get(name)
                if config is None:
                    continue

                module_cls = self.registry.get(config.type)
                if module_cls is None:
                    results[name] = f"type '{config.type}' not found in registry"
                    logger.warning("module_type_not_found", name=name, type=config.type)
                    continue

                try:
                    instance = module_cls()
                    typed_config = instance.config_model(**config.config)

                    context = ModuleContext(
                        module_name=name,
                        module_uuid=str(config.uuid),
                        publisher=self.event_bus,
                        config=typed_config,
                        capabilities=self._resolver,
                    )

                    await instance.start(context)
                    self._module_instances[name] = instance
                    self._resolver.register(
                        instance,
                        instance_id=str(config.uuid),
                        name=name,
                    )
                    results[name] = "started"
                    logger.info("module_started", name=name, type=config.type)
                except Exception as exc:
                    results[name] = str(exc)
                    logger.error(
                        "module_start_failed",
                        name=name,
                        type=config.type,
                        error=str(exc),
                    )

        return results

    async def shutdown_modules(self) -> None:
        """Stop all started modules in reverse order."""
        for name in reversed(list(self._module_instances)):
            instance = self._module_instances[name]
            try:
                await instance.stop()
            except Exception:
                logger.error("module_stop_failed", name=name)
        self._module_instances.clear()
        if self._resolver:
            self._resolver = RuntimeCapabilityResolver()

    def collect_routers(self) -> list:
        """Return FastAPI routers from started modules that expose them."""
        routers = []
        for _name, instance in self._module_instances.items():
            router = getattr(instance, "router", None)
            if router is not None:
                routers.append(router)
        return routers

    def register_capability(
        self,
        instance: object,
        *,
        instance_id: str,
        name: str | None = None,
    ) -> None:
        """Register an external capability (e.g. app shell workflow) with the resolver.

        Use this to make app-level objects like PreflightWorkflow available
        for module capability resolution before boot_modules() is called.
        """
        self._resolver.register(instance, instance_id=instance_id, name=name)

    def get_instance(self, name: str) -> object | None:
        return self._module_instances.get(name)

    async def get_module_health(self) -> dict:
        """Get aggregated health from all started module instances.

        Calls each module's async health() method and collects results.
        Returns system-level summary plus per-module detail.
        """
        modules: list[dict] = []
        ok_count = 0
        degraded_count = 0
        error_count = 0

        for name, instance in self._module_instances.items():
            config = self._modules_by_name.get(name)
            module_type = config.type if config else "unknown"

            try:
                health = await instance.health()
                status = health.get("status", "unknown")
            except Exception as exc:
                health = {"status": "error", "message": str(exc)}
                status = "error"

            if status == "ok":
                ok_count += 1
            elif status == "degraded":
                degraded_count += 1
            else:
                error_count += 1

            modules.append(
                {
                    "name": name,
                    "type": module_type,
                    "health": health,
                }
            )

        total = len(modules)
        if error_count > 0:
            system_status = "error"
        elif degraded_count > 0:
            system_status = "degraded"
        elif total == 0:
            system_status = "idle"
        else:
            system_status = "ok"

        return {
            "status": system_status,
            "modules_total": total,
            "modules_ok": ok_count,
            "modules_degraded": degraded_count,
            "modules_error": error_count,
            "modules": modules,
        }

    @property
    def resolver(self) -> RuntimeCapabilityResolver:
        return self._resolver

    def _persist_event(self, event: VosEvent) -> None:
        """Callback to persist events with severity >= info to SQLite."""
        if self._engine is None or event.severity == "debug":
            return

        with Session(self._engine) as session:
            record = EventRecord(
                id=event.id,
                type=event.type,
                source=event.source,
                project_id=event.project_id,
                time=event.time,
                correlation_id=event.correlation_id,
                causation_id=event.causation_id,
                severity=event.severity,
                data=event.data,
            )
            session.add(record)
            session.commit()
