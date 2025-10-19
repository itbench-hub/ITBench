FROM registry.access.redhat.com/ubi9/python-311:9.6-1760420762

USER 0
RUN dnf update -y && dnf install -y gnupg2 unzip openssh
RUN mkdir /etc/agent-benchmark
RUN ln -sf /bin/bash /bin/sh

# install `ansible-playbook`
RUN pip install --upgrade setuptools==70.0.0
RUN pip install ansible-core jmespath kubernetes==31.0.0 --no-cache-dir passlib
# install `helm`
RUN curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
# install `jq`
RUN dnf install -y jq
# install `make`
RUN dnf install -y make

# identify architecture
ENV ARCH=unknown
RUN ARCH=$(uname -m) && \
    case "$ARCH" in \
      x86_64) ARCH=amd64 ;; \
      aarch64) ARCH=arm64 ;; \
      *) echo "unsupported architecture: $ARCH" && exit 1 ;; \
    esac && \
    echo "ARCH=$ARCH" >> /etc/environment

# install `kubectl`
RUN source /etc/environment && \
    curl -LO https://dl.k8s.io/release/v1.31.0/bin/linux/${ARCH}/kubectl && \
    chmod +x ./kubectl && \
    mv ./kubectl /usr/local/bin/kubectl
# install `aws` (need this for using kubectl against AWS cluster)
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install
# install `opa`
RUN source /etc/environment && \
    curl -L -o opa https://github.com/open-policy-agent/opa/releases/download/v1.0.0/opa_linux_${ARCH}_static && \
    chmod +x ./opa && \
    mv ./opa /usr/local/bin/opa

RUN echo "StrictHostKeyChecking no" >> /etc/ssh/ssh_config

USER 1001
RUN ansible-galaxy collection install kubernetes.core community.crypto

WORKDIR /etc/ciso-task-scenarios
ENV FOREGROUND=true
ENV MAKEFLAGS=-s
ENV KUBECONFIG=/etc/ciso-task-scenarios/kubeconfig.yaml
ENV SHARED_WORKSPACE=/tmp/agent

COPY 1.gen-cis-b-k8s-kyverno ./1.gen-cis-b-k8s-kyverno
COPY 2.gen-cis-b-k8s-kubectl-opa ./2.gen-cis-b-k8s-kubectl-opa
COPY 3.gen-cis-b-rhel9-ansible-opa ./3.gen-cis-b-rhel9-ansible-opa
COPY 4.upd-cis-b-k8s-kyverno ./4.upd-cis-b-k8s-kyverno
