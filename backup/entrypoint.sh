#!/bin/bash

printenv | sed 's/^\(.*\)$/export \1/g' > /app/env.sh

echo "0 3 */2 * * . /app/env.sh && /app/backup.sh >> /var/log/backup.log 2>&1" > /etc/crontabs/root

crond -f -l 2
