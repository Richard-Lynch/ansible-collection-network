<!--
Copyright: (c) 2026, Richard Lynch
SPDX-License-Identifier: GPL-3.0-or-later
-->

# richard_lynch.network

Network service roles: BIND 9 authoritative and recursive DNS with dynamic updates, Kea DHCP with per-host reservations, DNS service registration, Pi-hole, Headscale and Tailscale, WireGuard peers, UniFi networks, DHCP options and WLANs through the controller API, a multi-VLAN probe, and the edge: Traefik, Cloudflare Tunnel and Access (mTLS, wildcard hosting), published endpoints, an frp relay and the Hetzner Cloud firewall.

## Roles

| Role | Description |
| ---- | ----------- |
| `cloudflare_access_mtls` | Cloudflare Access mTLS CA and client-certificate lifecycle |
| `cloudflare_hosting_edge` | Wildcard tunnel route, DNS record and Access app per hosting tier |
| `config_vlan_probe` | Configure a multi-homed probe guest with one interface per VLAN, and prove each leg landed on the VLAN it was asked for, so layer-2 traffic such as Wake-on-LAN can be sent from the target's own segment. |
| `dns_service_registrar` | Reconcile a svc.* zone against the services a host runs |
| `hetzner_cloud_firewall` | Reconcile a Hetzner Cloud firewall to a declared rule set |
| `kea_reservations` | Merge and validate per-host Kea DHCP reservations |
| `service_bind9_dns` | Authoritative bind9 DNS (optionally forwarding) + record task interface |
| `service_cloudflared` | Deploy a Cloudflare Tunnel client (cloudflared) |
| `service_frp_relay` | Deploy an frps TCP relay on a public host (dashboard off or loopback-only) |
| `service_headscale` | Headscale control server + embedded DERP behind a TLS-terminating traefik |
| `service_kea_dhcp` | Deploys kea for DHCP and DDNS |
| `service_pihole` | Pi-hole ad-block/forwarding DNS |
| `service_public_endpoint` | Publish one service: internal DNS, traefik, optional Cloudflare |
| `service_tailscale` | Install Tailscale and join a node, optionally as subnet router/exit node |
| `service_traefik` | Deploy Traefik as a reverse proxy with Cloudflare DNS-01 certificates |
| `service_wireguard_peer` | Configure one end of a WireGuard site-to-site link |
| `unifi_network` | Create or update a network (VLAN) on the UniFi controller |
| `unifi_network_dhcp` | Reconcile per-network DHCP settings on a UniFi controller |
| `unifi_wlan` | Create or update a WLAN (SSID) on the UniFi controller |

## Install

```sh
ansible-galaxy collection install richard_lynch.network
```

or pin it in `requirements.yml`:

```yaml
collections:
  - name: richard_lynch.network
    version: "1.1.0"
```

Requires ansible-core >=2.19.0.

## Development

```sh
# from a checkout at ansible_collections/richard_lynch/network
ansible-test sanity --docker
ansible-test units --docker
ansible-galaxy collection build
devkit conform                  # the repository standard (ansible-devkit)
devkit check all                # the static checks, configured by devkit.toml
```

CI, the disclosure gate and releases are the shared workflows of
[ansible-devkit](https://github.com/Richard-Lynch/ansible-devkit), called from
`.github/workflows/` at tag `v0.2.3`. A release is a merged pull
request that bumps `version` in `galaxy.yml` and adds the matching
`CHANGELOG.md` section. `export.manifest` lists every tracked path; update it in
the same commit as any file added or removed.

## Licence

GPL-3.0-or-later. See [LICENSE](LICENSE).
