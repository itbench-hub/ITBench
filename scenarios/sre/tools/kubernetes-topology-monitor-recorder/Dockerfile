FROM registry.access.redhat.com/ubi10/python-314-minimal:10.2-1791290410@sha256:06f7f76a5a718f240534d62974d1708b2985ecddb245e8c9e69eac792e075293

WORKDIR /app

COPY pyproject.toml pyproject.toml

RUN python3.14 -m pip install --no-cache-dir .

COPY gather.py gather.py
COPY test_gather.py test_gather.py

ENTRYPOINT ["python3.14", "gather.py"]
