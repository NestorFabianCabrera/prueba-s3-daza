FROM ubuntu:24.04

ARG DEPLOYER_PUBKEY
ARG MONITOR_PUBKEY=""

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
      openssh-server \
      ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /var/run/sshd && \
    ssh-keygen -A

# Usuarios
RUN useradd -m -s /bin/bash deployer && \
    useradd -M -s /sbin/nologin -r monitor && \
    usermod -p '*' deployer && \
    usermod -p '*' monitor

# deployer: authorized_keys
RUN mkdir -p /home/deployer/.ssh && \
    echo "${DEPLOYER_PUBKEY}" > /home/deployer/.ssh/authorized_keys && \
    chmod 700 /home/deployer/.ssh && \
    chmod 600 /home/deployer/.ssh/authorized_keys && \
    chown -R deployer:deployer /home/deployer/.ssh

# sshd hardened
COPY infra/dockerfiles/jumphost/sshd_config /etc/ssh/sshd_config
COPY infra/dockerfiles/jumphost/banner.txt   /etc/ssh/banner.txt

EXPOSE 2222

CMD ["/usr/sbin/sshd", "-D", "-e"]
