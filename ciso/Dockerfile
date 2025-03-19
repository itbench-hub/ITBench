FROM python:3.11.10-slim

RUN apt update -y && apt install -y curl gnupg2 unzip ssh
RUN mkdir /etc/agent-benchmark
RUN ln -sf /bin/bash /bin/sh

# install `ansible-playbook`
RUN pip install ansible-core jmespath kubernetes==31.0.0 --no-cache-dir passlib
RUN ansible-galaxy collection install kubernetes.core community.crypto
# install `helm`
RUN curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | tee /usr/share/keyrings/helm.gpg > /dev/null && \
    apt install apt-transport-https --yes && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | tee /etc/apt/sources.list.d/helm-stable-debian.list && \
    apt update && \
    apt install -y helm
# install `jq`
RUN apt install -y jq
# install `make`
RUN apt install -y make
# install `kubectl`
RUN curl -LO https://dl.k8s.io/release/v1.31.0/bin/linux/$(dpkg --print-architecture)/kubectl && \
    chmod +x ./kubectl && \
    mv ./kubectl /usr/local/bin/kubectl
# install `aws` (need this for using kubectl against AWS cluster)
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install
# install `opa`
RUN curl -L -o opa https://github.com/open-policy-agent/opa/releases/download/v1.0.0/opa_linux_$(dpkg --print-architecture)_static && \
    chmod +x ./opa && \
    mv ./opa /usr/local/bin/opa

WORKDIR /etc/ciso-task-scenarios
ENV FOREGROUND=true
ENV MAKEFLAGS=-s
ENV KUBECONFIG=/etc/ciso-task-scenarios/kubeconfig.yaml
ENV SHARED_WORKSPACE=/tmp/agent

RUN echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config

COPY 1.gen-cis-b-k8s-kyverno ./1.gen-cis-b-k8s-kyverno
COPY 2.gen-cis-b-k8s-kubectl-opa ./2.gen-cis-b-k8s-kubectl-opa
COPY 3.gen-cis-b-rhel9-ansible-opa ./3.gen-cis-b-rhel9-ansible-opa
COPY 4.upd-cis-b-k8s-kyverno ./4.upd-cis-b-k8s-kyverno
