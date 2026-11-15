FROM registry.access.redhat.com/ubi10/python-314-minimal:10.2-1791928506@sha256:3754d6dacac3177e62637420cadf7dcf438e390f664c527b0457a79653a47488

COPY --from=ghcr.io/jdx/mise:2026.11.8@sha256:5c6e71a86c8c997c32d30a169b4269bec9d4681a804e29078bac8f44109f2edc /usr/local/bin/mise /usr/local/bin/mise

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
