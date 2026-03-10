#!/bin/bash
# critical failure scenario: locked dpkg, permission mess, deep dirs
set -e

chmod 000 /etc/passwd /etc/group || true
mkdir -p /var/lib/dpkg
touch /var/lib/dpkg/lock-frontend

mkdir -p /var/tmp/chain
for i in $(seq 1 2500); do
    mkdir -p /var/tmp/chain/$(printf '%04d' $i)
done
ln -s ../chain /var/tmp/chain/0001/loop
ln -s /var/nowhere /etc/broken

echo "critical failure scenario ready"