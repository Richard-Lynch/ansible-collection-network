# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright: (c) 2026, Richard Lynch
# GNU General Public License v3.0+ (see https://www.gnu.org/licenses/gpl-3.0.txt)
"""Pure functions behind cloudflare_hosting_edge's safety gates.

Everything that decides "is it safe to publish a wildcard" is here, rather than in Jinja, so it can
be unit-tested with fixtures that must FAIL and near-misses that must PASS.

The question these answer is the one a wildcard raises: could `*.dev.example.com` or
`*.apps.example.com` take over, shadow or re-authenticate a hostname that already exists?

  hosting_edge_matches(pattern, host)        does an Access/DNS/tunnel pattern cover this host?
  hosting_edge_captured(wildcards, hosts)    which EXISTING hosts fall under the new wildcards
  hosting_edge_winner(apps, host)            which Access app wins for a host (most specific)
  hosting_edge_winner_map(apps, hosts)       {host: winning app name or None}
  hosting_edge_winner_diff(before, after, hosts)  hosts whose winning app differs
  hosting_edge_existing_hosts(dns, ingress, apps, own)  every hostname that exists today
  hosting_edge_merge_ingress(before, wanted) the ingress list to PUT, or raise
  hosting_edge_cert_missing(packs, hosts)    wildcard hosts NOT covered by an ACTIVE pack
"""

from __future__ import annotations

try:  # pragma: no cover
    from ansible.errors import AnsibleFilterError
except Exception:  # pragma: no cover

    class AnsibleFilterError(Exception):  # type: ignore[no-redef]
        pass


def _hostpart(domain):
    """An Access app domain may carry a path ('app.example.com/mcp'); the host is before the slash."""
    return str(domain).split("/", 1)[0].lower()


def hosting_edge_matches(pattern, host):
    """True if `pattern` covers `host`. `*.x.y` covers any name BELOW x.y at any depth (Access and
    Cloudflare DNS both treat the wildcard that way) but not x.y itself."""
    pattern = _hostpart(pattern)
    host = host.lower()
    if pattern.startswith("*."):
        return host.endswith(pattern[1:]) and host != pattern[2:]
    return pattern == host


def hosting_edge_captured(wildcards, hosts):
    """Existing hostnames that fall under any of the new wildcards, excluding the wildcards
    themselves. A non-empty result means publishing the wildcard would change how a live name is
    routed or authenticated."""
    out = []
    for h in hosts:
        h = str(h)
        if h.startswith("*."):
            continue
        if any(hosting_edge_matches(w, h) for w in wildcards):
            out.append(h)
    return sorted(set(out))


def _domains(app):
    doms = list(app.get("self_hosted_domains") or [])
    if app.get("domain"):
        doms.append(app["domain"])
    return doms


def hosting_edge_winner(apps, host):
    """Name of the Access app that decides `host` for the ROOT path, or None.

    Most specific wins: an exact hostname beats any wildcard; among wildcards the longer (more
    specific) beats the shorter. Apps whose domain carries a path only decide that path, so they do
    not compete for '/'."""
    best = None
    for app in apps:
        for d in _domains(app):
            if "/" in str(d):
                continue
            if not hosting_edge_matches(d, host):
                continue
            exact = 0 if str(d).startswith("*.") else 1
            key = (exact, len(_hostpart(d)))
            if best is None or key > best[0]:
                best = (key, app.get("name"))
    return best[1] if best else None


def hosting_edge_winner_map(apps, hosts):
    return {h: hosting_edge_winner(apps, h) for h in sorted(set(hosts))}


def hosting_edge_winner_diff(apps_before, apps_after, hosts):
    """Hosts whose winning Access app differs between two app lists (empty = nothing re-decided)."""
    return [
        h
        for h in sorted(set(hosts))
        if hosting_edge_winner(apps_before, h) != hosting_edge_winner(apps_after, h)
    ]


def hosting_edge_existing_hosts(dns_records, ingress_hostnames, apps, own_app_names):
    """Every hostname that exists today: DNS names, tunnel ingress hostnames and Access app domains
    (minus the apps this role owns, and minus wildcard patterns, which are rules not names)."""
    out = [r["name"] for r in dns_records or []]
    out += list(ingress_hostnames or [])
    for app in apps or []:
        if app.get("name") in (own_app_names or []):
            continue
        out += [_hostpart(d) for d in _domains(app)]
    return sorted({h.lower() for h in out if h and not str(h).startswith("*.")})


def hosting_edge_merge_ingress(before, wanted):
    """The full ingress list to PUT. `PUT .../configurations` REPLACES the whole list, so this keeps
    every existing rule byte-identical, replaces/adds only the `wanted` hostnames, and keeps the
    catch-all last. Raises if anything pre-existing would be lost or altered."""
    wanted_names = {w["hostname"] for w in wanted}
    keep = [r for r in before if "hostname" in r and r["hostname"] not in wanted_names]
    catch = [r for r in before if "hostname" not in r]
    if len(catch) != 1:
        raise AnsibleFilterError(
            "the current ingress has %d catch-all rule(s), expected exactly 1; refusing to guess"
            % len(catch)
        )
    after = keep + list(wanted) + catch
    # Read-back style check on the RESULT, not on the construction above: every pre-existing rule
    # that is not ours must appear unchanged, and the catch-all must be last.
    for r in before:
        if "hostname" in r and r["hostname"] not in wanted_names and r not in after:
            raise AnsibleFilterError("pre-existing ingress rule would change: %s" % r["hostname"])
    if "hostname" in after[-1]:
        raise AnsibleFilterError("the catch-all is not last")
    for w in wanted:
        if not str(w["hostname"]).startswith("*."):
            raise AnsibleFilterError(
                "this role only owns wildcard routes; %r is not one" % w["hostname"]
            )
    return after


def hosting_edge_cert_missing(packs, hosts):
    """Hosts in `hosts` NOT named by any pack whose status is 'active'. Compared on the exact
    string, because the Universal certificate covers `*.example.com` only: it does not cover
    `x.dev.example.com`, and a pack that exists but is still `pending_validation` serves nothing."""
    covered = set()
    for p in packs or []:
        if p.get("status") == "active":
            covered.update(h.lower() for h in (p.get("hosts") or []))
    return [h for h in hosts if h.lower() not in covered]


class FilterModule(object):
    def filters(self):
        return {
            "hosting_edge_matches": hosting_edge_matches,
            "hosting_edge_captured": hosting_edge_captured,
            "hosting_edge_winner": hosting_edge_winner,
            "hosting_edge_winner_map": hosting_edge_winner_map,
            "hosting_edge_winner_diff": hosting_edge_winner_diff,
            "hosting_edge_existing_hosts": hosting_edge_existing_hosts,
            "hosting_edge_merge_ingress": hosting_edge_merge_ingress,
            "hosting_edge_cert_missing": hosting_edge_cert_missing,
        }
