#!/bin/sh
set -e

echo "[kea-dhcp4] Resolving DDNS service hostname..."

# Use Docker's internal DNS to resolve the DDNS service IP
DDNS_IP=$(getent hosts kea_dhcp_ddns | awk '{ print $1 }')

if [ -z "$DDNS_IP" ]; then
	echo "[kea-dhcp4] ERROR: Could not resolve kea_dhcp_ddns"
	exit 1
fi

echo "[kea-dhcp4] Resolved kea_dhcp_ddns to $DDNS_IP"

# Replace placeholder in the config template
sed "s/__DDNS_IP__/$DDNS_IP/g" /etc/kea/kea-dhcp4.conf.template >/etc/kea/kea-dhcp4.conf

# Cleanup PID files
rm -f /var/run/kea/*.pid

# Launch Kea
# If arguments were passed to the script, run them as a command (like CMD in Dockerfile)
if [ "$#" -gt 0 ]; then
	echo "[kea-dhcp4] Executing custom command: $*"
	exec "$@"
else
	# Fallback to default if no CMD was passed
	echo "[kea-dhcp4] NO ARGS Starting kea-dhcp4..."
	exec /usr/sbin/kea-dhcp4 -c /etc/kea/kea-dhcp4.conf
fi
