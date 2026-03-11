#!/bin/bash
# scenario: şüpheli SUID binary (backdoor benzeri ama zararsız) oluştur
set -e

if [[ -x /bin/sh ]]; then
  cp /bin/sh /usr/local/bin/suidsh-demo
  chmod 4755 /usr/local/bin/suidsh-demo
else
  echo "no /bin/sh found to clone" >&2
fi

echo "suid backdoor simulation scenario ready"

