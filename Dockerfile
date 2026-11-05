FROM ghcr.io/astral-sh/uv:python3.14-alpine3.23

# Install system dependencies
RUN apk update && \
    apk add --no-cache ca-certificates

WORKDIR /itbench

# Install Python dependencies using uv lockfile
COPY pyproject.toml uv.lock requirements.yaml ./

RUN uv sync --frozen --no-dev --no-install-project

# Copy project source and scenario data
COPY src/ ./src/
COPY scenarios/ ./scenarios/
COPY library/ ./library/

COPY README.md ./

# Install itbench package into environment
RUN uv sync --frozen --no-dev

# Activate virtual environment in PATH
ENV PATH="/itbench/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Install Ansible collections from requirements.yaml
RUN ansible-galaxy collection install -r requirements.yaml

ENTRYPOINT ["itbench"]
CMD ["--help"]
