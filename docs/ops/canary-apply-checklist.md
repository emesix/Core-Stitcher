# Canary Apply Checklist — ix0 on OPNsense

**When:** After work hours (post 16:30) or weekend. Can't afford internet outage during work.

**Target:** ix0 (10G SFP+, MAC 20:7c:14:f4:78:76) → opt1 (FRONTEND trunk to ONTi-FE)

---

## Pre-flight

- [ ] 1. **Capture fresh snapshot**
  ```
  stitch_snapshot_capture(label="pre-canary")
  ```

- [ ] 2. **SSH sanity check**
  ```bash
  sshpass -p 'NikonD90' ssh root@172.16.0.1 "uname -a && cat /conf/config.xml | grep '<opt1>'" 
  ```
  Expected: no `<opt1>` in config.

- [ ] 3. **Dry run**
  ```
  stitch_interface_assign(device_id="opnsense", physical_interface="ix0", assign_as="opt1", description="FRONTEND trunk to ONTi-FE", dry_run=true)
  ```
  Verify: ok=true, before=unassigned, after=opt1.

## Apply

- [ ] 4. **Real apply (ONE interface only)**
  ```
  stitch_interface_assign(device_id="opnsense", physical_interface="ix0", assign_as="opt1", description="FRONTEND trunk to ONTi-FE", dry_run=false)
  ```
  Verify: ok=true, applied=true, verification.match=true.

## Verify

- [ ] 5. **Read-back verify**
  ```bash
  sshpass -p 'NikonD90' ssh root@172.16.0.1 "cat /conf/config.xml | grep -A 5 '<opt1>'"
  ```
  Expected: `<if>ix0</if>`, `<descr>FRONTEND trunk to ONTi-FE</descr>`, `<enable>1</enable>`

- [ ] 6. **Preflight + diagnostics**
  ```
  stitch_preflight_run(detail="standard")
  stitch_topology_diagnostics()
  ```

- [ ] 7. **Post snapshot + diff**
  ```
  stitch_snapshot_capture(label="post-canary")
  stitch_snapshot_diff(before_file="...-pre-canary.json", after_file="...-post-canary.json")
  ```

## Review

- [ ] 8. **Check audit log**
  ```bash
  cat ~/.stitch/audit.jsonl | tail -5
  ```

## Rollback (if needed)

```bash
sshpass -p 'NikonD90' ssh root@172.16.0.1 "cp /conf/config.xml.bak /conf/config.xml && configctl interface reconfigure"
```

## Hard stop

**Do NOT proceed to ix1 until ix0 is verified and stable.** Review everything, take a break, then decide.
