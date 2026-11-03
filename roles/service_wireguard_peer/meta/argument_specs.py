# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from ansible_devkit.argspec.models import ArgumentSpec, ArgumentSpecs, OptionSpec
DEFAULT_AUTHOR = "Collection maintainers"

# CONSTRAINTS ARE DECLARED HERE AND ENFORCED FOR REAL.
#
# The argspec model carries the constraints that actually prevent a stranding. Two mechanisms, and the split matters:
#
#   ENFORCED BY ANSIBLE      type, required, choices, no_log — the role-argspec validator handles
#                            these itself, before any task runs.
#   ENFORCED BY GENERATED    min_value/max_value, min_length, pattern, forbidden_values,
#   GUARDS                   element_constraints — Ansible's validator has NO range/length/pattern
#                            checking, so the argspec generator renders these into
#                            tasks/_argspec_guards.yml as real asserts. The constraint keys are
#                            STRIPPED from argument_specs.yml so it never claims enforcement it
#                            does not have.
#
# Constraints too complex for a declaration (a peer routing its own endpoint; every peer having a
# public_key) stay as hand-written asserts in tasks/_guards.yml.

_COMMON = {
    "wireguard_interface": OptionSpec(
        type="str",
        required=False,
        default="wg0",
        description=["Interface name. One per peering; wg0 unless a host holds several."],
    ),
    "wireguard_address": OptionSpec(
        type="str",
        required=True,
        # Must carry a prefix: a bare address silently gives wg-quick a /32 and the far end
        # becomes unreachable for reasons that look like a routing problem.
        pattern=r"^[0-9a-fA-F:.]+/[0-9]{1,3}$",
        description=[
            "This end's address on the tunnel, WITH prefix, e.g. 198.18.254.1/30.",
            "Pick a small transfer subnet that is disjoint from every network either end",
            "already routes, so the tunnel never shadows a real route.",
        ],
    ),
    "wireguard_listen_port": OptionSpec(
        type="int",
        required=False,
        default=0,
        description=[
            "UDP port to listen on. 0 means DO NOT SET ListenPort — correct for a NATed",
            "initiator, which dials out and should let the port float. The fixed listener sets",
            "a port (WireGuard's conventional one is 51820) because it is the endpoint peers dial.",
        ],
    ),
    "wireguard_private_key_path": OptionSpec(
        type="str",
        required=False,
        default="/etc/wireguard/wg0.key",
        description=[
            "Where the private key file lives, 0600. The key is DELIBERATELY NOT written into",
            "wg0.conf: generate-don't-apply prints config diffs, and a key in the config forces a",
            "choice between no_log (kills the diff) and leaking the secret into transcripts and CI.",
            "The config loads it via PostUp instead, so it can diff freely forever.",
        ],
    ),
    "wireguard_private_key": OptionSpec(
        type="str",
        required=False,
        default="",
        no_log=True,  # ENFORCED by Ansible — a validation failure must never echo the key
        min_length=1,  # generated guard: `required` still permits an empty string
        description=[
            "The private key VALUE, from a secret lookup of your choice. Never hardcode it.",
            "Empty means the role refuses to configure rather than writing a broken peer.",
        ],
    ),
    "wireguard_public_key": OptionSpec(
        type="str",
        required=False,
        default="",
        description=[
            "This end's OWN public key. Not a secret. Used as a read-back assertion: after the key",
            "is installed the role compares `wg show <if> public-key` against this. That converts",
            "a pubkey/privkey desync — the cross-end failure that actually happens, and which is",
            "otherwise SILENT (the handshake simply never completes) — into a red assert.",
        ],
    ),
    # NO nested `options` here, deliberately. The argspec generator flattens sub-option DEFAULTS
    # into the parent's default, so declaring them turns `default=[]` into a bare dict
    # ({endpoint: '', persistent_keepalive: 0}) in the generated defaults file — which then fails
    # Ansible's own list validation at run time. Verified: that is exactly what it produced.
    # The shape is documented here and enforced by tasks/_guards.yml instead.
    "wireguard_peers": OptionSpec(
        type="list",
        required=False,
        default=[],
        elements="dict",
        description=[
            "The far end(s). Each entry is a dict:",
            "  public_key           (str, required)",
            "  allowed_ips          (list of str, required) — cryptokey routing: BOTH the route",
            "                       selector and the inbound source filter. A packet from this",
            "                       peer whose source is not listed is DROPPED SILENTLY.",
            "                       0.0.0.0/0 would hijack the default route — rejected in _guards.",
            "  endpoint             (str, optional) host:port. Omit for a passive listener.",
            "  persistent_keepalive (int, optional) 25 on a NAT'd initiator, 0 on a public peer.",
        ],
    ),
    "wireguard_mtu": OptionSpec(
        type="int",
        required=False,
        default=1420,
        min_value=1280,  # below this breaks IPv6's minimum MTU
        max_value=1420,  # above this risks an MTU blackhole on a real path
        description=[
            "1500 - 80 covers the worst common encapsulation. Too high gives an MTU BLACKHOLE:",
            "handshake and ping fine, large responses silently vanish. Range enforced in _guards.",
        ],
    ),
    # DEFAULT IS THE STRING "none", NOT "off". Bare `off` in YAML is the BOOLEAN false — the
    # generated defaults file would carry `wireguard_table__default: off`, which Ansible loads as
    # False and the template would render as `Table = False`. wg-quick accepts "off" and "auto";
    # this role normalises its own sentinel to "off" at render time so the YAML never holds a
    # boolean-looking bareword. Caught by yamllint's truthy rule, which was right.
    "wireguard_table": OptionSpec(
        type="str",
        required=False,
        default="none",
        # choices deliberately EXCLUDES the bareword "off": in YAML that is the BOOLEAN false, and
        # it would land in the generated argspec as such (the same trap the default hit). The
        # role's sentinel is "none"; the template maps it to wg-quick's "off" at render time.
        choices=["none", "auto"],  # ENFORCED by Ansible
        description=[
            "'none' (this role's sentinel, rendered as wg-quick's 'off') means wg-quick",
            "installs NO routes and the play adds only what it needs.",
            "Any other value lets AllowedIPs drive the routing table, which on a remote public",
            "host is one copy-paste away from replacing the default route and stranding you.",
        ],
    ),
    "wireguard_forward": OptionSpec(
        type="bool",
        required=False,
        default=False,
        description=[
            "Enable IPv4 forwarding, so this peer can ROUTE traffic between the tunnel and its",
            "local network rather than only terminating it.",
            "",
            "Required on a peer that acts as a gateway for other hosts on its side of the link.",
            "Without it the packets ARRIVE and are silently discarded: the tunnel is healthy, AllowedIPs is right, the",
            "route is right, and nothing crosses. Defaults FALSE because a peer that only",
            "terminates traffic should not be a router.",
        ],
    ),
    "wireguard_manage_nftables": OptionSpec(
        type="bool",
        required=False,
        default=False,
        description=[
            "Whether to install the nftables policy. FALSE by default so that 'zero firewall",
            "changes on this host' is structural rather than remembered — set it true only on",
            "the end whose firewall this role should own.",
        ],
    ),
    # Same generator constraint as wireguard_peers above — no nested options.
    "wireguard_inbound_allow": OptionSpec(
        type="list",
        required=False,
        default=[],
        elements="dict",
        description=[
            "Flows the FAR end may INITIATE into this side. Empty means established/related only.",
            "Each entry: daddr (str), dport (int), proto (str, default tcp), comment (str).",
            "Needed whenever the far end PUSHES to this side (a metrics or log shipper, say) —",
            "without it the firewall would block the very traffic the link exists for.",
        ],
    ),
    "wireguard_apply": OptionSpec(
        type="bool",
        required=False,
        default=False,
        description=["Generate-don't-apply. When false, reports the diff and writes nothing."],
    ),
    "wireguard_render_dir": OptionSpec(
        type="str",
        required=False,
        default="",
        description=[
            "TESTABILITY SEAM, unset in production: render config to this directory instead of",
            "/etc so molecule can call the REAL role and assert on real output rather than",
            "re-deriving the role's own expressions over a stub (the tautology trap).",
        ],
    ),
}

argument_specs = ArgumentSpecs(
    argument_specs={
        "main": ArgumentSpec(
            short_description="Configure one end of a WireGuard site-to-site link",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options=_COMMON,
        ),
        "verify": ArgumentSpec(
            short_description="Read-only checks on a configured WireGuard peer",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                **_COMMON,
                "wireguard_verify_transport": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=[
                        "When false, LOCAL checks only (interface exists, pubkey matches, unit active,",
                        "default route unchanged) — these must pass with the far end ABSENT, which",
                        "is exactly the state after configuring one side.",
                        "When true, also assert handshake age and an rx counter delta. Only meaningful",
                        "once both ends exist. The knob exists so nobody reaches for",
                        "failed_when:false when a one-sided verify legitimately cannot handshake.",
                    ],
                ),
            },
        ),
        "teardown": ArgumentSpec(
            short_description="Remove a WireGuard peer configuration",
            version_added="1.0",
            author=DEFAULT_AUTHOR,
            options={
                **_COMMON,
                "wireguard_teardown_confirm": OptionSpec(
                    type="bool",
                    required=False,
                    default=False,
                    description=[
                        "Separate confirm var — deliberately NOT wireguard_apply. Destruction",
                        "should never ride on the same flag as configuration.",
                    ],
                ),
            },
        ),
    }
)
