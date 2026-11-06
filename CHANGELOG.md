<!--
Copyright: (c) 2026, Richard Lynch
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Changelog

All notable changes to this collection are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the collection
uses [Semantic Versioning](https://semver.org/).

## [1.1.1] — 2026-11-06

### Changed

- The CI, release and disclose callers use ansible-devkit `v0.4.1`.

### Fixed

- `service_bind9_dns` renders `named.conf.keys` with `no_log` and `diff: false`, so neither TSIG secret is printed under `--diff` or in a failed task's result.
- `dns_service_registrar` writes its zone-transfer TSIG keyfile with `no_log` as well as `diff: false`.
- `service_kea_dhcp` renders its config through `richard_lynch.common.deployment_config` with `apply: {no_log: true, diff: false}`, so the DDNS TSIG secret in `kea-dhcp-ddns.conf` is not printed under `--diff`.
- Secret options are `no_log` in the argument specs: `ddns_tsig_key_secret` (`service_bind9_dns`), `svc_tsig_key_secret` (`dns_service_registrar`), `pihole_web_password` (`service_pihole`), and `unifi_network_api_key`, `unifi_network_dhcp_api_key` and `unifi_wlan_api_key`.
- `unifi_network`, `unifi_network_dhcp` and `unifi_wlan` send the API key, and read and write controller objects (a WLAN object carries its passphrase), in `no_log` tasks. Each request is followed by a check that reports only its HTTP status and message, the facts holding whole controller objects are `no_log`, and `unifi_network_dhcp`'s report and read-back loops carry only the fields they print.
- `service_pihole` sends and stores the API session id only in `no_log` tasks, reports the status and message of each request separately, and logs the session out in an `always:` block, so a failed task no longer leaves the session open.

## [1.1.0] — 2026-11-03

### Added

- Role `service_traefik`: Traefik v3 with Docker Compose, Let's Encrypt certificates over Cloudflare DNS-01, and file-provider routes supplied by the caller as a directory of files and templates. Entrypoints publish on loopback unless told otherwise.
- Role `service_cloudflared`: a Cloudflare Tunnel client run from a token.
- Role `service_public_endpoint`: publishes a service as an internal DNS record and, optionally, a Cloudflare Tunnel hostname behind Cloudflare Access, reported before it is applied.
- Role `service_frp_relay`: an frps relay for raw TCP passthrough, dashboard off by default.
- Roles `cloudflare_access_mtls` and `cloudflare_hosting_edge`: Cloudflare Access mutual-TLS client certificates, and wildcard hosting routes with checks that a wildcard cannot capture, shadow or re-authenticate an existing hostname.
- Role `hetzner_cloud_firewall`: reconciles a Hetzner Cloud firewall to a declared rule set, reported before it is applied.

## [1.0.0] — 2026-11-03

### Added

- Role `service_bind9_dns`: BIND 9 authoritative zones and a recursive resolver, with TSIG-keyed dynamic updates and a validated reload.
- Roles `service_kea_dhcp` and `kea_reservations`: Kea DHCPv4 with one reservation file per host, merged and validated before the server is reloaded.
- Role `dns_service_registrar`: registers service names as DNS records through dynamic updates.
- Roles `service_pihole`, `service_headscale`, `service_tailscale` and `service_wireguard_peer`: Pi-hole, a Headscale control server and Tailscale clients, and WireGuard peers.
- Roles `unifi_network`, `unifi_network_dhcp` and `unifi_wlan`: UniFi networks, DHCP options and WLANs through the controller API, reported before they are applied.
- Role `config_vlan_probe`: a multi-homed probe with one interface per VLAN.
- Every installation-specific value is an option the caller sets: addresses, zones, domains, credentials and data paths.
