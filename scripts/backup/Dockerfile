FROM postgres:16-alpine

COPY backup.sh /usr/local/bin/backup.sh
COPY restore.sh /usr/local/bin/restore.sh
RUN chmod +x /usr/local/bin/backup.sh /usr/local/bin/restore.sh

# Default: daily at 3 AM UTC
ENV BACKUP_CRON="0 3 * * *"

CMD echo "${BACKUP_CRON} /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1" > /etc/crontabs/root \
    && crond -f -l 2
