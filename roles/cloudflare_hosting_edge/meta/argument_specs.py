# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

DEFAULT_AUTHOR = "Collection maintainers"
from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec

# NEVER put literal Jinja delimiters in a description (Ansible templates the argspec).

# Every Cloudflare id below is a fact about one installation: required, no default, supplied by
# the caller. A role default for an account id would be right for exactly one account.
_COMMON = {
    "cloudflare_hosting_edge_tiers": OptionSpec(
        type="dict",
        required=True,
        description=[
            "Tier name to its settings: suffix (the wildcard is star.suffix), entrypoint_port (the",
            "Traefik port the tunnel route for that tier targets) and the 1Password item names that",
            "hold the tier's Access service token (cf_id_item, cf_secret_item).",
        ],
    ),
    "cloudflare_hosting_edge_zone_id": OptionSpec(
        type="str", required=True, description=["Zone id of the zone the wildcards live in."]
    ),
    "cloudflare_hosting_edge_api_token": OptionSpec(
        type="str",
        required=False,
        no_log=True,
        description=[
            "The Cloudflare API token itself, from whatever secret store the caller uses. When set",
            "it is used directly and cloudflare_hosting_edge_token_item is not read. One of the two",
            "is required.",
        ],
    ),
    "cloudflare_hosting_edge_token_item": OptionSpec(
        type="str",
        required=False,
        description=[
            "Alternative to cloudflare_hosting_edge_api_token: the 1Password item id (not title:",
            "titles with slashes read as empty) of the API token, read through",
            "richard_lynch.common.onepassword_cached (needs the op CLI).",
        ],
    ),
    "cloudflare_hosting_edge_token_field": OptionSpec(
        type="str",
        default="credential",
        description=[
            "Field of that item holding the token. API Credential items use credential, Password items use password."
        ],
    ),
    "cloudflare_hosting_edge_op_vault": OptionSpec(
        type="str",
        required=False,
        description=[
            "1Password vault holding cloudflare_hosting_edge_token_item and, on apply, the tier",
            "service tokens (created ones are stored there through richard_lynch.common.secrets_manager).",
            "Required with cloudflare_hosting_edge_token_item, and for an apply of main.",
        ],
    ),
    "cloudflare_hosting_edge_apply": OptionSpec(
        type="bool",
        default=False,
        description=[
            "Generate-don't-apply. False reads, gates and reports; true writes and reads back."
        ],
    ),
}

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Wildcard tunnel route, DNS record and Access app per hosting tier",
            description=[
                "For each tier: one wildcard ingress rule on the tunnel pointing at the origin's",
                "Traefik entrypoint port, one proxied wildcard CNAME, and one wildcard Access",
                "application (owner SSO allow plus a service-token non_identity policy).",
                "After this a new app needs no DNS, tunnel or Access step.",
                "Before any write it proves the wildcards cannot capture an existing hostname: no",
                "existing DNS name, ingress hostname or Access app domain falls under them, and the",
                "winning Access app for every existing hostname is identical before and after.",
            ],
            version_added="1.1",
            author=DEFAULT_AUTHOR,
            options={
                **_COMMON,
                "cloudflare_hosting_edge_account_id": OptionSpec(
                    type="str", required=True, description=["Cloudflare account id."]
                ),
                "cloudflare_hosting_edge_tunnel_id": OptionSpec(
                    type="str",
                    required=True,
                    description=["Id of the tunnel whose ingress receives the wildcard rules."],
                ),
                "cloudflare_hosting_edge_origin": OptionSpec(
                    type="str",
                    required=True,
                    description=[
                        "Host that runs Traefik; the tunnel service is http://origin:entrypoint_port."
                    ],
                ),
                "cloudflare_hosting_edge_sso_group_id": OptionSpec(
                    type="str",
                    required=True,
                    description=[
                        "Existing Access group the human allow policy reuses (never copied)."
                    ],
                ),
                "cloudflare_hosting_edge_zone_app_id": OptionSpec(
                    type="str",
                    required=True,
                    description=[
                        "Id of the zone-wide wildcard Access app (star.zone), read before and after and asserted unchanged by this role."
                    ],
                ),
                "cloudflare_hosting_edge_session_duration": OptionSpec(
                    type="str",
                    default="24h",
                    description=["Access session length for the new apps."],
                ),
            },
        ),
        "acm": ArgumentSpec(
            short_description="Order an Advanced Certificate Manager pack and read it back active",
            description=[
                "The Universal certificate covers one label below the zone only, so a two-level",
                "wildcard needs an ACM advanced pack. Reads the existing packs first and orders",
                "only what is not already active or in flight, then waits and ASSERTS each wildcard",
                "host is named by an active pack. Never reports an order as success.",
            ],
            version_added="1.1",
            author=DEFAULT_AUTHOR,
            options={
                **_COMMON,
                "cloudflare_hosting_edge_acm_ca": OptionSpec(
                    type="str",
                    default="lets_encrypt",
                    choices=["google", "lets_encrypt", "ssl_com"],
                    description=["Certificate authority for the pack."],
                ),
                "cloudflare_hosting_edge_acm_validity_days": OptionSpec(
                    type="int",
                    default=90,
                    choices=[14, 30, 90, 365],
                    description=["Pack validity in days."],
                ),
                "cloudflare_hosting_edge_acm_wait_s": OptionSpec(
                    type="int",
                    default=1800,
                    min_value=0,
                    max_value=7200,
                    description=[
                        "How long to wait for the pack to become active (DCV can take minutes)."
                    ],
                ),
            },
        ),
    }
)
