#!/bin/bash
# scenario: Pardus APT depolarını yanlış sürüme işaret eden şekilde boz
set -e

mkdir -p /etc/apt/sources.list.d

cat >/etc/apt/sources.list.d/pardus-broken.list <<'EOF'
deb http://depo.pardus.org.tr/pardus ondokuz main contrib non-free
deb http://depo.pardus.org.tr/pardus guvenlik main contrib non-free
EOF

echo "pardus repo breakage scenario ready"

