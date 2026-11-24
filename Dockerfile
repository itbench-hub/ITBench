FROM registry.access.redhat.com/ubi10/python-314-minimal:10.3-1795234906@sha256:6a3ac934913b426ccf9a9d8406084e47044ef8da88a6722a3acc60ac990595c3

COPY --from=ghcr.io/jdx/mise:2026.11.13@sha256:06a4e5b507ac24d0279d6d2fc1f0849cb54fd0c1eb305a93db028398364b45f9 /usr/local/bin/mise /usr/local/bin/mise

USER 0

# Install system dependencies
RUN microdnf -y update && \
    microdnf -y install ca-certificates && \
    microdnf clean all

USER 1001

WORKDIR /itbench

# Install the pinned tools (uv, helm) with mise
COPY mise.toml mise.toml

RUN mise trust && \
    mise install

# Install Python dependencies using uv lockfile
COPY pyproject.toml uv.lock requirements.yaml ./

RUN mise exec -- uv sync --frozen --no-dev --no-install-project

# Copy project source and scenario data
COPY src/ ./src/
COPY inventory/ ./inventory/
COPY project/ ./project/
COPY scenarios/ ./scenarios/
COPY library/ ./library/

COPY README.md ./

# Install itbench package into environment
RUN mise exec -- uv sync --frozen --no-dev

# Activate virtual environment in PATH
ENV PATH="/itbench/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Install Ansible collections from requirements.yaml
RUN ansible-galaxy collection install -r requirements.yaml

# Run through mise so `mise` and the pinned helm are on PATH for Ansible
ENTRYPOINT ["mise", "exec", "--", "itbench"]
CMD ["--help"]
