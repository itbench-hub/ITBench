FROM registry.access.redhat.com/ubi10/python-314-minimal:10.3-1793860470@sha256:464fc6c1ed22a1625fe8d9ebfe3cc90142fc77903647259e72883e8f30135176

COPY --from=ghcr.io/jdx/mise:2026.11.10@sha256:80aa2afb17ba760cabe74ac90771ca2d1470773d514cc2bb79c69c8d3f92f150 /usr/local/bin/mise /usr/local/bin/mise

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
