# kea_reservations

Merges one-file-per-host DHCP reservations into the validated list `service_kea_dhcp` renders, and
gates provisioning on a reservation being **declared and live**.

Pure helper: it writes nothing to managed hosts and never touches Kea. It produces a variable.

## Why a directory instead of a list

A single long reservation list in inventory is readable, but:

- a host's reservation lived nowhere near the play that provisions that host, so the two drifted;
- the rationale for each address — the part that cannot be reconstructed later — sat in a comment
  block a merge conflict could silently reorder;
- and the flat list had **no duplicate detection at all**. Two entries claiming one address, or one
  MAC claiming two, rendered happily into the config; Kea picked one and nothing said so.

One file per owner suits exactly this shape: a consumer that globs a directory, where one caller's
mistake must not corrupt everyone else's entry.

## Entrypoints

| `tasks_from` | Does |
|---|---|
| *(main)* | Glob `reservations.d/*.yml`, validate the set, publish `kea_reservations`. |
| `assert_reserved` | Two-stage gate: declared locally **and** live in the running Kea. |
| `declare` | Scaffold one validated declaration. Writes a file; deploys nothing. |

### main

```yaml
- ansible.builtin.include_role: { name: kea_reservations }
  vars:
    kea_reservations_dir: "{{ playbook_dir }}/vars/reservations.d"
- ansible.builtin.include_role: { name: service_kea_dhcp }   # consumes kea_reservations
```

Publishes `kea_reservations` (the name the kea role already takes),
`_kea_reservations_all` (same list, unambiguous name) and `_kea_reservations_annotated` (retains
`why` and `_source_file` for reporting). Validation metadata is **stripped** from what reaches the
role — `service_kea_dhcp`'s argspec declares the element options, so an undeclared extra key would
be rejected by `validate_argument_spec`.

### assert_reserved — the provisioning gate

```yaml
- ansible.builtin.include_role:
    name: richard_lynch.network.kea_reservations
    tasks_from: assert_reserved
  vars:
    reservation_host: nas
```

**Stage 1 (declared)** — a well-formed `<host>.yml` exists.
**Stage 2 (live)** — the running Kea holds that exact **MAC + IP pair**, read from the **control
socket**.

Both halves are load-bearing. Stage 1 alone proves someone wrote a file; it says nothing about
whether Kea would honour it, and the two diverge routinely because `service_kea_dhcp` restarts only
`when: deployment_config_changed` — a re-render after a failed run leaves the process serving stale
config from memory while every file on disk looks right.

Stage 2 has **no on-disk fallback**, deliberately. The rendered file does not prove what the
process loaded; for a report a labelled fallback beats nothing, but for a gate it renders the
stale-memory case as a pass.

The live read is a `config-get` sent to the Kea control agent's HTTP API through `python3` inside
the container, because the official Kea image ships neither `socat`, `kea-shell` nor `curl`. It
needs the `control-socket` stanza `service_kea_dhcp` renders into the dhcp4 config.

Matched as a **pair**, because either half alone passes a real defect: MAC-only passes a reservation
pointing at the wrong address; IP-only passes one bound to a different machine's NIC. MACs are
lowercased on both sides — Kea emits lowercase regardless of how the file is written.

Opt out with `reservation_expected=false` (bootstrap: the host that runs Kea cannot gate on the Kea
it is about to run) or `reservation_check_live=false` (no path to Kea). Both are *declared* exceptions
and say so in the output.

### declare

```
ansible-playbook declare_reservation.yml \
  -e reservation_host=media-pc -e reservation_subnet=100 \
  -e reservation_mac=02:00:5E:10:00:01 -e reservation_ip=192.0.2.2 \
  -e 'reservation_why="Streaming host; clients pin the address"' \
  -e reservation_declare_apply=true
```

Validates before writing, so a file the merge would reject cannot be scaffolded. **Refuses to
overwrite** a file declaring a different subnet/MAC/address — compared on parsed content, so a
comment edit is not a conflict but a re-addressing is.

It does **not** deploy. The sequence is `declare` → review → **commit** → deploy → and only then
does `assert_reserved` pass. An untracked file that never reaches Kea is the original failure in
miniature.

## Declaration format

```yaml
---
subnet_id: 200                     # must be a VLAN Kea serves (no `dns:` key in its VLAN entry)
hw_address: "02:00:5E:10:00:02"    # colon-separated; Kea matches on MAC alone
ip_address: "198.51.100.3"         # inside the subnet's reserved band (.2-.10)
hostname: "nas"                    # SHORT — Kea appends the ddns suffix; must match the filename
why: >-
  Storage target address, configured by IP on the hosts that mount it. If it moves the
  target disappears and every consumer loses its data volume.
```

`why` is required (`kea_reservations_require_why`, default true) and min-length'd so it cannot be
satisfied with "n/a". An address alone does not tell you that it is hardcoded in a dozen
configs, or that it sits behind router port forwards — so without it the next person either keeps a
reservation nobody can justify or moves one that silently breaks things.

## What is validated where

| Check | Where | Why there |
|---|---|---|
| required fields, `why`, filename/hostname match, short hostname, MAC format, valid IPv4, duplicate IP (subnet-scoped), duplicate MAC (global, case-insensitive), subnet is served, address in subnet | **this role** | Properties of the declaration *set* — only visible when all files are merged. |
| reservation inside the reserved band; DDNS zone matches bind9; resolver sane | `service_kea_dhcp` | Properties of the *deployment* — depend on `kea_pool_offset` and the VLAN map the role owns. |

Verified end-to-end: the merge accepts a structurally-valid `198.51.100.50`, and the kea role's band
guard then rejects it as in-pool. No gap between the two.

## Testing

`molecule test` is offline. `converge` merges good fixtures and asserts the result; `verify` points
the role at eight fixture directories each containing exactly **one** fault and asserts it **fails**
— duplicate IP, duplicate MAC (written in the other case), malformed MAC, missing rationale,
hostname/filename mismatch, FQDN hostname, unknown subnet — plus a check that
`require_why=false` really does disable that guard, and a **control case** that good input still
merges. Without the control, a role that failed unconditionally would pass every negative test.

> The scenario calls the role **twice** on purpose: `set_fact` persists for the whole play, so an
> accumulator built with `default([]) + [...]` would append the second invocation to the first's
> list and trip the duplicate guard with a message blaming the files. The role resets the
> accumulator explicitly, and the double call proves it.
