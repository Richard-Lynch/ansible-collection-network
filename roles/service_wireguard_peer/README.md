# service_wireguard_peer

Configures **one end** of a WireGuard site-to-site link. Both ends use this same role; they differ
only in variables.

The shape it was built for is a site behind NAT linked to a remote public host: the site end dials
out, the public end listens on a fixed port, and the link carries a narrow set of flows (for
example metrics and logs) rather than whole networks.

## Entrypoints

| `tasks_from` | Does |
|---|---|
| `main` (default) | Renders config, validates it with `wg-quick strip`, shows the diff. Installs only with `wireguard_apply=true`, then runs `verify` as its own postcondition. |
| `verify` | **Read-only.** Local checks always; transport checks with `wireguard_verify_transport=true`. |
| `teardown` | Removes the peer. Own confirm var — `wireguard_teardown_confirm=true`. |

There is deliberately **no action-dispatch variable**. An action var that typos into no branch is a
green no-op, which is the silent-guard shape this repo audits against.

## The design invariant

> **Each end's configuration must be safe with the other end absent.**

`Table = off` means no routes are installed from `AllowedIPs`, so a half-applied link is a healthy
host with an inert interface — not a degraded network. That is why the two ends can be configured in
either order, and why `verify`'s local checks must pass before the far end exists.

## Usage

```yaml
# site end — NAT'd initiator
- role: richard_lynch.network.service_wireguard_peer
  vars:
    wireguard_address: "198.18.254.1/30"
    wireguard_private_key: "{{ site_wireguard_private_key }}"   # from your secrets manager
    wireguard_public_key: "<the matching pubkey — not a secret>"
    wireguard_manage_nftables: true
    wireguard_peers:
      - public_key: "<listener peer pubkey>"
        allowed_ips: ["198.18.254.2/32"]
        endpoint: "203.0.113.64:51820"
        persistent_keepalive: 25
```

Apply with `-e wireguard_apply=true`; without it the role only reports what it would change.

## Safety properties, and why each exists

- **The private key is never written into `wg0.conf`.** It goes to its own `0600` file, loaded via
  `PostUp`. Generate-don't-apply means printing diffs, and a key in the config forces a choice
  between `no_log` (which kills the diff) and leaking the secret into transcripts and CI.
- **`Table = off`** — otherwise `AllowedIPs` drives the routing table, and one wide entry replaces
  the host's default route. On a remote host that takes down SSH and every public service in one
  packet, with no way back but the provider console.
- **`wireguard_manage_nftables` defaults false** so "zero firewall changes on this host" is
  structural, not remembered. On a host whose firewall belongs to something else (Docker, or a
  host-networked service), an INPUT rule from this role would sit in front of traffic it knows
  nothing about.
- **`wireguard_inbound_allow`** exists because the default policy is "the far end may only reply".
  A shipper that *pushes* metrics or logs is far-end-initiated — without this list the firewall
  would block the very thing the link exists for.
- **The pubkey read-back** turns a private/public key desync into a red assert. Otherwise the
  handshake simply never completes, silently, with nothing naming the cause.

## Guards are runtime asserts, not argspec constraints

`OptionSpec` (`ansible_devkit.argspec.models`, from the pinned ansible-devkit package) exposes only
`description/version_added/type/required/default/choices/elements/options`, with `extra="forbid"` —
**no ranges, no custom validators, no `no_log`**. So "reject `0.0.0.0/0`", "MTU 1280–1420" and
"keepalive 0–120" cannot live there. They are asserts in `tasks/_guards.yml`, and molecule proves
each one *fires* on illegal input.

Related generator constraint: declaring nested `options` on a `list`/`elements: dict` variable makes
the generator flatten the sub-defaults into the parent's default, producing a **dict where a list
belongs**. `wireguard_peers` and `wireguard_inbound_allow` therefore document their shape in the
description and enforce it in `_guards.yml`.

## Test coverage — honestly

**Covered:** the real role is invoked with `wireguard_apply=false` into a render dir, and the
rendered artifacts are asserted on — `Table = off`, no `PrivateKey`, MTU, keepalive on the initiator
only, `ListenPort` on the listener only, `AllowedIPs` correct. Plus four negative tests proving every
guard fires.

**NOT covered, and not coverable in a container:** kernel module availability, interface creation,
handshakes, cryptokey-routing drop behaviour, NAT keepalive, MTU blackholes, systemd unit behaviour.
Those are answered by `verify` against a real host, and by a live probe of the target platform
(for a container guest: is the module loaded on the host, can the guest create the interface).

`wg-quick strip` and `nft -c` validation run only where those binaries exist; their absence is
reported **loudly** rather than skipped silently.

## Prerequisite the role does NOT handle

On an unprivileged container guest, the `wireguard` kernel module must be loaded **on the
hypervisor** and persisted (`/etc/modules-load.d/`); the guest cannot load it itself. A module that
is present but not persisted works until the next host reboot, and then presents as "the tunnel
randomly stopped".
