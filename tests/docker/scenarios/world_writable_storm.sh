#!/bin/bash
# scenario: sistemde geniş kapsamlı world-writable izin fırtınası yarat
set -e

mkdir -p /opt/demo-app/logs
touch /opt/demo-app/logs/app.log

chmod 777 /opt/demo-app /opt/demo-app/logs /opt/demo-app/logs/app.log

echo "world-writable storm scenario ready"

