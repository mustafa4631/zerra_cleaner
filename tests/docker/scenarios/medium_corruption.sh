#!/bin/bash
# medium corruption scenario: apt cache mess and circular links
set -e

mkdir -p /var/cache/apt/archives/partial
touch /var/cache/apt/archives/lock
dd if=/dev/urandom of=/var/cache/apt/archives/partial/ghost bs=1M count=100

ln -s /usr/bin/loop1 /usr/bin/loop2
ln -s /usr/bin/loop2 /usr/bin/loop1

echo 'echo hi' > /usr/bin/stray && chmod +x /usr/bin/stray

echo "medium corruption scenario ready"