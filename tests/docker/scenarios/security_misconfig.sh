#!/bin/bash
# security misconfiguration scenario: create findings for SecurityScanner
set -e

# world-writable file under /etc
echo "insecure" > /etc/world-writable-demo.conf
chmod 666 /etc/world-writable-demo.conf

# risky sudoers drop-in
mkdir -p /etc/sudoers.d
cat >/etc/sudoers.d/99-gk-healter-insecure <<'EOF'
ALL ALL=(ALL) NOPASSWD: ALL
EOF
chmod 440 /etc/sudoers.d/99-gk-healter-insecure

# sshd_config with risky settings (create if missing)
mkdir -p /etc/ssh
cat >/etc/ssh/sshd_config <<'EOF'
Port 22
Protocol 2
PermitRootLogin yes
PermitEmptyPasswords yes
PasswordAuthentication yes
X11Forwarding yes
EOF

echo "security misconfig scenario ready"

