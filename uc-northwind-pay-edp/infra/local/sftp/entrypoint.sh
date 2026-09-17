#!/bin/sh
set -eu

: "${SFTP_RAW_PUBLISHER_PASSWORD:?SFTP_RAW_PUBLISHER_PASSWORD is required}"
: "${SFTP_PROCESSOR_PASSWORD:?SFTP_PROCESSOR_PASSWORD is required}"
: "${SFTP_LOADER_PASSWORD:?SFTP_LOADER_PASSWORD is required}"
: "${SFTP_OPERATOR_PASSWORD:?SFTP_OPERATOR_PASSWORD is required}"

for group in \
    sftpusers \
    rawincoming \
    rawprocessing \
    csvoutgoing \
    csvprocessing \
    operator
do
    addgroup -S "$group"
done

adduser -S -D -H -h /shared -s /sbin/nologin -G sftpusers raw-publisher
adduser -S -D -H -h /shared -s /sbin/nologin -G sftpusers processor
adduser -S -D -H -h /shared -s /sbin/nologin -G sftpusers loader
adduser -S -D -H -h /shared -s /sbin/nologin -G sftpusers operator

addgroup raw-publisher rawincoming
addgroup processor rawincoming
addgroup processor rawprocessing
addgroup processor csvoutgoing
addgroup loader csvoutgoing
addgroup loader csvprocessing
addgroup operator rawincoming
addgroup operator rawprocessing
addgroup operator csvoutgoing
addgroup operator csvprocessing
addgroup operator operator

printf '%s:%s\n' raw-publisher "$SFTP_RAW_PUBLISHER_PASSWORD" | chpasswd
printf '%s:%s\n' processor "$SFTP_PROCESSOR_PASSWORD" | chpasswd
printf '%s:%s\n' loader "$SFTP_LOADER_PASSWORD" | chpasswd
printf '%s:%s\n' operator "$SFTP_OPERATOR_PASSWORD" | chpasswd

mkdir -p \
    /sftp/shared/raw/incoming \
    /sftp/shared/raw/processing \
    /sftp/shared/raw/quarantine \
    /sftp/shared/raw/archive \
    /sftp/shared/csv/outgoing \
    /sftp/shared/csv/processing \
    /sftp/shared/csv/quarantine \
    /sftp/shared/csv/archive

chown root:root /sftp /sftp/shared /sftp/shared/raw /sftp/shared/csv
chmod 0755 /sftp /sftp/shared /sftp/shared/raw /sftp/shared/csv

chown root:rawincoming /sftp/shared/raw/incoming
chown root:rawprocessing \
    /sftp/shared/raw/processing \
    /sftp/shared/raw/quarantine
chown root:operator /sftp/shared/raw/archive
chown root:csvoutgoing /sftp/shared/csv/outgoing
chown root:csvprocessing \
    /sftp/shared/csv/processing \
    /sftp/shared/csv/quarantine
chown root:operator /sftp/shared/csv/archive

chmod 2770 \
    /sftp/shared/raw/incoming \
    /sftp/shared/raw/processing \
    /sftp/shared/raw/quarantine \
    /sftp/shared/raw/archive \
    /sftp/shared/csv/outgoing \
    /sftp/shared/csv/processing \
    /sftp/shared/csv/quarantine \
    /sftp/shared/csv/archive

ssh-keygen -A
exec /usr/sbin/sshd -D -e
