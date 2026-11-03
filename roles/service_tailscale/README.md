# service_tailscale

Installs a pinned `tailscale` from pkgs.tailscale.com and joins the node to a
control server (Headscale). It can also make the node a **subnet router** and/or
**exit node**.

A typical use is a subnet router: one node on a site's networks advertises
them to the tailnet.

## Join once, then converge

- **Not joined to `tailscale_login_server`:** `tailscale up` with
  `tailscale_auth_key`. If no key is given, the role fails.
- **Already joined:** `tailscale set` runs, and only when the prefs tailscaled
  **reports** (`tailscale debug prefs`) differ from the declaration. A re-run
  needs no key and reports `changed` only for a real change.
- **Every run:** the role finishes by reading prefs and status back and
  asserting `Running` on the declared server, with exactly the declared routes.

Tags come from the pre-auth key, not from this role.

## Requirements

- **`/dev/net/tun`.** This is checked first, before anything is installed. On an
  unprivileged LXC the hypervisor has to pass it through (a device entry in the
  container's config); the role does not do that for you.
- **Debian or Ubuntu.** The apt repo is built from `ansible_distribution` /
  `_release`, so facts must be gathered.
- **IP forwarding** is enabled by the role (`/etc/sysctl.d/99-tailscale.conf`)
  whenever routes or an exit node are advertised.

## Defaults worth knowing

- **`tailscale_accept_dns: false`.** A server should not let the tailnet rewrite
  its resolver, and a DNS server must not.
- **`tailscale_accept_routes: false`.** A subnet router already sits on the
  networks it advertises.

## Testing

`molecule test` calls the real role with a TUN path that does not exist. It
asserts that the TUN gate is what stopped the run, and that no apt repository
was written.
