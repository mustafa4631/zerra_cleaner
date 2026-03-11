#!/bin/bash
# scenario: unattended-upgrades paketi kurulu ama otomatik güncelleme kapalı
set -e

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends unattended-upgrades

mkdir -p /etc/apt/apt.conf.d
cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "0";
EOF

echo "unattended-upgrades disabled scenario ready"

