FROM registry.access.redhat.com/ubi10-minimal:10.2-1786960640@sha256:61f820b7893b6226e499e928db99c59a0a9135aa17e4e056fdaf1015908cca14 AS downloader

RUN microdnf install -y --nodocs \
      curl tar \
    && microdnf clean all

# Download Helm
RUN ARCH=$(uname -m) && \
    case "$ARCH" in \
      x86_64)  HELM_ARCH=amd64 ;; \
      aarch64) HELM_ARCH=arm64 ;; \
    esac && \
    curl -fsSL "https://get.helm.sh/helm-v4.2.4-linux-${HELM_ARCH}.tar.gz" \
      -o /tmp/helm.tar.gz && \
    tar -zxvf /tmp/helm.tar.gz -C /tmp && \
    mv /tmp/linux-${HELM_ARCH}/helm /usr/local/bin/helm && \
    rm -rf /tmp/helm.tar.gz /tmp/linux-${HELM_ARCH}

FROM registry.access.redhat.com/ubi10/python-314-minimal:10.2-1787002610@sha256:b6cc4d6c56a139b763af6cb9cd6b838d0f8ed5a67caadfa3418e68dec6ab755f

RUN cat <<EOF > /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.36.0/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.36.0/rpm/repodata/repomd.xml.key
EOF

RUN microdnf upgrade -y \
    && microdnf install -y --nodocs \
      tar \
      kubectl \
    && microdnf clean all

COPY --from=downloader /usr/local/bin/helm /usr/local/bin/helm

COPY pyproject.toml pyproject.toml
COPY requirements.yaml requirements.yaml

RUN python3.14 -m pip install --no-cache-dir .

RUN ansible-galaxy collection install -r requirements.yaml

WORKDIR /runner

COPY library/specs/ library/specs/
COPY scenarios/ scenarios/
