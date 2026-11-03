<!--
Copyright: (c) 2026, Richard Lynch
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Changelog

All notable changes to this collection are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the collection
uses [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-11-03

### Added

- Role `service_bind9_dns`: BIND 9 authoritative zones and a recursive resolver, with TSIG-keyed dynamic updates and a validated reload.
- Roles `service_kea_dhcp` and `kea_reservations`: Kea DHCPv4 with one reservation file per host, merged and validated before the server is reloaded.
- Role `dns_service_registrar`: registers service names as DNS records through dynamic updates.
- Roles `service_pihole`, `service_headscale`, `service_tailscale` and `service_wireguard_peer`: Pi-hole, a Headscale control server and Tailscale clients, and WireGuard peers.
- Roles `unifi_network`, `unifi_network_dhcp` and `unifi_wlan`: UniFi networks, DHCP options and WLANs through the controller API, reported before they are applied.
- Role `config_vlan_probe`: a multi-homed probe with one interface per VLAN.
- Every installation-specific value is an option the caller sets: addresses, zones, domains, credentials and data paths.
