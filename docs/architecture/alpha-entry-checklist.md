# VOS-Workbench — Alpha Entry Checklist

*Nothing gets coded until every item on this list is frozen.*

**Current status:** 12 / 12 frozen (alpha foundation + runtime services merged)

---

## Checklist

### Config layer

- [x] **1. `workbench.yaml` schema** — `src/vos_workbench/config/models.py`
- [x] **2. `module.yaml` schema** — `src/vos_workbench/config/models.py`
- [x] **3. URI grammar spec** — `src/vos_workbench/uri/parser.py`
- [x] **4. Ontology: module vs resource vs node** — everything is a module
- [x] **5. Settings merge semantics** — `src/vos_workbench/config/merge.py`
- [x] **6. Config validation lifecycle** — `src/vos_workbench/config/loader.py`

### Runtime layer

- [x] **7. Module type registry contract** — `src/vos_workbench/registry/registry.py`
- [x] **8. Bootstrap / startup contract** — `src/vos_workbench/runtime/startup.py`
- [x] **9. Event bus contract** — `src/vos_workbench/events/bus.py`
- [x] **10. Frontend API contract** — `src/vos_workbench/api/`
- [x] **11. Runtime storage contract** — `src/vos_workbench/storage/`
- [x] **12. Error and supervision contract** — `src/vos_workbench/errors.py`

---

## What's next: Explorer Alpha Exit Criteria

See `docs/architecture/explorer-alpha-roadmap.md`
