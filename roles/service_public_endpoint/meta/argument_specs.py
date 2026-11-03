# SPDX-License-Identifier: GPL-3.0-or-later
from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Publish one service: internal DNS, traefik, optional Cloudflare",
            description=[
                "Reconciles a single service's public-facing surface: an internal record in the",
                "human-authored zone, a check for an existing traefik route, and — only when",
                "endpoint_public is true — a proxied Cloudflare DNS record plus an entry on the",
                "tunnel's ingress list.",
                "Human-authored names ONLY: it refuses to write into a zone the caller marks as",
                "machine-owned (endpoint_machine_zone_labels), which is reserved for",
                "machine-registered names (DHCP-driven DNS updates and service registration).",
            ],
            author=DEFAULT_AUTHOR,
            version_added="1.1",
            options={
                "endpoint_name": OptionSpec(
                    type="str",
                    required=True,
                    description="Bare label, no dots. 'grafana' -> grafana.<endpoint_zone>.",
                ),
                "endpoint_upstream": OptionSpec(
                    type="str",
                    required=True,
                    description="Where traefik sends the request, e.g. http://monitoring.example.com:3000.",
                ),
                "endpoint_zone": OptionSpec(
                    type="str",
                    required=True,
                    description=(
                        "The human-authored zone, e.g. example.com. A zone carrying any label in "
                        "endpoint_machine_zone_labels is refused by a hard gate."
                    ),
                ),
                "endpoint_record_type": OptionSpec(
                    type="str",
                    default="CNAME",
                    choices=["A", "CNAME"],
                    description=(
                        "CNAME (to traefik) or A. A name cannot hold both — the role reads the "
                        "live record first and refuses a collision, because bind9 responds to one "
                        "by refusing to load the ENTIRE zone."
                    ),
                ),
                "endpoint_cname_target": OptionSpec(
                    type="str",
                    required=False,
                    description=(
                        "Target FQDN when endpoint_record_type is CNAME (normally the reverse "
                        "proxy's own name, e.g. traefik.example.com). Required for a CNAME."
                    ),
                ),
                "endpoint_a_value": OptionSpec(
                    type="str",
                    required=False,
                    description="IP when endpoint_record_type is A.",
                ),
                "endpoint_public": OptionSpec(
                    type="bool",
                    default=False,
                    description=(
                        "Publish through Cloudflare. Defaults FALSE: an unpublished service is a "
                        "nuisance, an accidentally-published machine interface is not."
                    ),
                ),
                "endpoint_tunnel": OptionSpec(
                    type="str",
                    default="",
                    description=(
                        "Which tunnel publishes it: a key of endpoint_tunnel_ids. Required (and "
                        "checked against that map) when endpoint_public."
                    ),
                ),
                "endpoint_tunnel_ids": OptionSpec(
                    type="dict",
                    default={},
                    description=(
                        "Cloudflare Tunnel ids by name, {name: uuid}. The caller names a tunnel, "
                        "never pastes an id per service: a typo in a name fails the gate, a typo "
                        "in an id could publish onto the wrong tunnel."
                    ),
                ),
                "endpoint_tunnel_service": OptionSpec(
                    type="str",
                    required=False,
                    description=(
                        "The tunnel-side target — what cloudflared forwards to, NOT the traefik "
                        "upstream (e.g. https://traefik.example.com). Required when endpoint_public."
                    ),
                ),
                "endpoint_apply": OptionSpec(
                    type="bool",
                    default=False,
                    description="Generate-don't-apply. Reports the diff and changes nothing unless true.",
                ),
                "endpoint_bind9_addr": OptionSpec(
                    type="str",
                    required=True,
                    description="Address of the authoritative server to read records back from.",
                ),
                "endpoint_traefik_dynamic_dir": OptionSpec(
                    type="str",
                    required=True,
                    description=(
                        "Absolute path, on the controller, of the traefik file-provider route "
                        "directory. Scanned for an existing router of this name, which is never "
                        "overwritten. It must exist: a scan of a missing directory finds nothing, "
                        "which would read as 'no router' and defeat that protection."
                    ),
                ),
                "endpoint_cf_account": OptionSpec(
                    type="str",
                    required=False,
                    description="Cloudflare account id. Required when endpoint_public.",
                ),
                "endpoint_cf_zone": OptionSpec(
                    type="str",
                    required=False,
                    description="Cloudflare zone id of endpoint_zone. Required when endpoint_public.",
                ),
                "endpoint_cf_api_token": OptionSpec(
                    type="str",
                    required=False,
                    no_log=True,
                    description=(
                        "The Cloudflare API token itself, from whatever secret store the caller "
                        "uses. When set it is used directly and endpoint_cf_token_item / "
                        "endpoint_op_vault are ignored. Use a token scoped to DNS, tunnel and "
                        "Access reads/edits, never one that can mint tokens. When endpoint_public, "
                        "this or endpoint_cf_token_item plus endpoint_op_vault is required."
                    ),
                ),
                "endpoint_cf_token_item": OptionSpec(
                    type="str",
                    required=False,
                    description=(
                        "Alternative to endpoint_cf_api_token: the 1Password item holding the "
                        "Cloudflare API token (field 'credential'), read through "
                        "richard_lynch.common.onepassword_cached (needs the op CLI)."
                    ),
                ),
                "endpoint_op_vault": OptionSpec(
                    type="str",
                    required=False,
                    description="1Password vault of endpoint_cf_token_item.",
                ),
                "endpoint_machine_zone_labels": OptionSpec(
                    type="list",
                    elements="str",
                    default=[],
                    description=(
                        "DNS labels that mark a zone as machine-owned (written by DHCP-driven "
                        "updates or service registration, never by hand). endpoint_zone may not "
                        "contain any of them as a label: with ['dyn'], dyn.example.com and "
                        "a.dyn.example.com are refused. Empty (the default) refuses nothing."
                    ),
                ),
                "endpoint_origin_request": OptionSpec(
                    type="dict",
                    default={"noTLSVerify": False},
                    description=(
                        "cloudflared originRequest options for a NEW ingress entry. Defaults to "
                        "noTLSVerify: false — the tunnel talks HTTPS to traefik, which presents a "
                        "real certificate. An existing entry is carried through unchanged."
                    ),
                ),
                "endpoint_do": OptionSpec(
                    type="str",
                    default="both",
                    choices=["both", "internal", "public"],
                    description=(
                        "Which half to reconcile. The halves can run on different hosts — the "
                        "internal record edits zone files and must run ON the DNS server, while the "
                        "Cloudflare half is pure API from the controller — so a caller split "
                        "across two plays selects one at a time."
                    ),
                ),
                "endpoint_dns_probe_host": OptionSpec(
                    type="str",
                    required=False,
                    description="Optional host to run dig from, when the controller cannot reach bind9 directly.",
                ),
            },
        )
    }
)
