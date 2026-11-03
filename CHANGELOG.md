<!--
Copyright: (c) 2026, Richard Lynch
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Changelog

All notable changes to this collection are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the collection
uses [Semantic Versioning](https://semver.org/).

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
