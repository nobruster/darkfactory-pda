FROM alpine:3.22@sha256:14358309a308569c32bdc37e2e0e9694be33a9d99e68afb0f5ff33cc1f695dce

RUN apk add --no-cache openssh-server

COPY sshd_config /etc/ssh/sshd_config
COPY entrypoint.sh /usr/local/bin/sftp-entrypoint
RUN chmod 0755 /usr/local/bin/sftp-entrypoint

EXPOSE 22

ENTRYPOINT ["/usr/local/bin/sftp-entrypoint"]
