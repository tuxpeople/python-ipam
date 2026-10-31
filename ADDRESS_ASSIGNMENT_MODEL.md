# Address assignment, leases and observations

Date: 2026-10-31. Status: phase 1 implemented in this repository (see
"Implementation status" at the end); collector changes and scoped
retirement are still open.

## Purpose

Extend Python IPAM so it can represent DHCP reservations, dynamic leases,
host-configured static addresses and device observations without conflating them
in the existing `status` field. This proposal is intended for implementation in
this repository; the UDM collector lives in
`~/development/github/tuxpeople/homelab-automation/scripts/ipam/`.

## Current integration and model

The collector has successfully upserted eight networks, eight DHCP ranges and
13 active reservations from the UDM. A subsequent preview reported zero changes.
Terraform configures the UDM; the independent collector reads its applied state.
The collector currently creates reservation hosts with `status=reserved`,
`is_assigned=true` and `discovery_source=udm-reservations`. It preserves existing
names and observed health from other collectors, and does not set `last_seen`
merely because a reservation exists. Dynamic leases are not collected yet.
No automatic deletion, stale-entry retirement or recurring run is configured.

The current Host model has `status`, `is_assigned`, `last_seen` and
`discovery_source`, with a unique IPv4 address. It cannot independently express
assignment, lease validity and observed presence. For example, a device can have
a reservation and a valid DHCP lease while also being currently online.

## Recommendation

Do not solve this by adding more mutually exclusive `status` values. Track three
independent aspects, initially with additive nullable fields:

| Field | Proposed values | Meaning |
|-------|-----------------|---------|
| `assignment_type` | `reservation`, `static`, `dynamic`, `unknown` | How the address is assigned |
| `lease_expires_at` | UTC timestamp or null | Expiry of an explicitly observed DHCP lease |
| `last_seen` | UTC timestamp or null | Latest actual observation of the device |

`assignment_type=reservation` can coexist with a non-null `lease_expires_at`.
Do not change it to `dynamic` merely because a reserved client acquires a lease.
`static` means configured on the host or explicitly declared as static; it is
different from a DHCP reservation. `unknown` means the allocation mechanism has
not been established, not that the IP is free. Null lease expiry means unknown
or not supplied, not infinite validity or absence of every lease.

Keep `status` for backward compatibility initially. Define its purpose before
using it as a health indicator; do not silently reinterpret existing rows.
New assignment information should be authoritative for allocation displays.
Keep observed health separate from assignment and lease validity.

## Sources, timestamps and identity

Record provenance and freshness for each aspect, not just for the whole row.
Proposed names, subject to final API design:

- `assignment_source` and `assignment_last_confirmed_at`.
- `lease_source` and `lease_observed_at`.
- Existing `last_seen`, plus a source for that observation.

A device observation does not refresh reservation confirmation. Reading a
reservation does not refresh device `last_seen`. Collector execution time is not
device presence. Do not overwrite a newer observation with an older timestamp.
Use timezone-aware UTC timestamps consistently in the API and database contract.

An external identifier and source scope are also needed for reliable retirement:
e.g. UDM site + network identity + client MAC for a reservation, and UDM network
identity for a subnet. `discovery_source` alone is neither complete field ownership
nor an authorization mechanism. Network and DHCP-range models need provenance
too if their disappeared entries are ever to be retired automatically.

The minimal flat-field model supports a single effective assignment and lease.
If multiple collectors need independent claims for the same aspect, prefer child
records keyed by source/external identity rather than adding more flat source
columns or letting the last writer win. Define precedence and conflict handling
before enabling that case. Conflicting MAC claims must remain visible.

## Derived display and availability

| Facts | Derived allocation display |
|-------|----------------------------|
| Reservation, no valid lease, not recently observed | Reserved |
| Reservation and valid lease | Reserved; lease active |
| No persistent assignment, valid lease | Dynamically allocated |
| Static assignment, device offline | Statically allocated |
| Expired lease, no persistent assignment | No confirmed current allocation |
| Observation only | Observed; assignment unknown |

Do not persist these combinations as additional independent status values.
Derive them from the underlying facts so contradictions cannot accumulate.
An expired lease or missed ping is not proof that an address is safe to allocate.

Existing active DHCP pools must continue to be excluded from static allocation
suggestions even if individual leases expire. A reserved or statically assigned
IP remains unavailable irrespective of `last_seen` or lease expiry. Distinguish
an address with no recorded allocation from a positively confirmed free address.

## Reconciliation and retirement rules

- A valid DHCP lease does not replace or remove a reservation/static assignment.
- Repeated reservation imports must not overwrite lease data or observed health.
- An absent or expired lease may remove a dynamic allocation claim, but not a
  persistent assignment or its history.
- Removing a reservation on the UDM must not immediately free an address if a
  valid lease, static declaration or conflicting claim still exists.
- Only a complete successful snapshot of the owning source/scope can establish
  that an assignment disappeared. Failed API access, partial collection and
  unreachable devices must not trigger retirement.
- Preserve manually curated CNAMEs, descriptions, names and other collectors'
  observations according to explicit field ownership rules.
- IP reuse and MAC changes require a deliberate transition; a MAC mismatch must
  not silently transfer an old reservation or history to another device.

## API and migration

1. Add nullable fields through an Alembic migration; preserve all existing data.
2. Document new fields in GET/list/create/update/upsert contracts and UI forms.
3. Preserve partial upsert behavior: omitted fields stay unchanged. Explicit null
   clears only fields that allow it. Reject invalid enums/timestamps and document
   clearing of persistent assignments explicitly.
4. Do not infer an assignment type solely from `is_assigned=true` or `status=active`.
   Existing records without evidence should become `unknown` or remain unset.
5. Rows with `discovery_source=udm-reservations`, `is_assigned=true` and
   `status=reserved` are candidates for reservation backfill. Confirm the migration
   rule or refresh from the UDM; never infer static assignments from these values.
6. Keep old clients working while the collector transitions to the new fields.
   Define how legacy `is_assigned` relates to derived occupancy; do not maintain
   two writable, conflicting sources of truth indefinitely.
7. Update available-IP queries and counters to use the same allocation semantics.
8. After deployment, update the collector in homelab-automation: reservation
   provenance first, then lease collection, then static-address sources. Scoped
   retirement comes after ownership and complete-snapshot rules are in place.

An IPAM deployment failure must not block Terraform plan/apply or UDM operation.
No Terraform provider coupling is proposed.

## Acceptance cases

- Reservation + active lease + online observation can coexist.
- Reservation survives lease expiry and device offline periods.
- Static assignment survives missed observations.
- Expired dynamic leases do not release persistent assignments.
- Failed/partial source collection does not retire anything.
- Existing manual metadata survives reservation/lease upserts.
- Older source timestamps cannot replace newer observations.
- Clearing one aspect does not accidentally clear the other two.
- DHCP pool exclusion and address availability remain consistent.
- IP reuse/MAC mismatch produces a visible conflict or explicit transition.
- Legacy API clients and populated databases remain usable after migration.
- Repeated identical imports do not create duplicates or allocation drift.

This was written as a design handoff. The implementation decisions taken
are recorded below.

## Implementation status

Implemented (migration `e5a8c1d4f2b3`):

- Host fields `assignment_type`, `assignment_source`,
  `assignment_last_confirmed_at`, `lease_expires_at`, `lease_source`,
  `lease_observed_at`, `last_seen_source`; all nullable, no inference from
  `is_assigned` or `status`.
- Migration backfill: rows with `discovery_source=udm-reservations`,
  `is_assigned=1` and `status=reserved` become `assignment_type=reservation`
  with `assignment_source=udm-reservations`; `assignment_last_confirmed_at`
  stays NULL until the collector confirms it again.
- Timestamps are stored as naive UTC and returned with `+00:00`. New
  timestamp fields reject input without an offset; legacy `last_seen` still
  accepts naive input as UTC.
- Derived `allocation_state` / `allocation_label` / `lease_active`
  (`ipam/allocation.py`), never persisted.
- Upsert reconciliation per aspect: omitted fields unchanged, explicit null
  clears, stale freshness timestamps ignore the aspect, persistent
  assignments are not replaced by `dynamic`/`unknown`, ignored aspects are
  reported in `X-IPAM-Ignored-Aspects`. A MAC change on a reservation/static
  host returns 409 unless `confirm_mac_change=true`, which then clears the
  previous device's lease and observation data.
- `PUT` changes the new fields only when present and applies no guards
  (manual update).
- Availability: any host record and any active DHCP range excludes an
  address from next-ip, available-ips and `available_hosts`. The IP query
  endpoint reports `allocation_state=no_record` and `confirmed_free=false`
  for unrecorded addresses.
- Legacy `status` unchanged; `is_assigned` documented as a curation flag
  that is not authoritative for allocation.
- Web UI, JSON/CSV export and import support the new fields.

Not implemented yet:

- External identifiers and source scopes (hosts, networks, DHCP ranges),
  complete-snapshot bookkeeping and scoped retirement.
- Child records for multiple concurrent claims per aspect.
- Collector changes in homelab-automation.
