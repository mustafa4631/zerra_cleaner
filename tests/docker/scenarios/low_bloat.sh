#!/bin/bash
# populate a container with low‑severity bloat for GK-Healter to detect
set -e

# large log file
dd if=/dev/zero of=/var/log/dummy.log bs=1M count=500
mkdir -p /tmp/empty/{a,b}/{c,d}
touch /tmp/empty/a/c/{1,2,3}
ln -s /nonexistent /tmp/broken-link

echo "low bloat scenario ready"