FROM registry.access.redhat.com/ubi10/python-314-minimal:10.2-1787230952@sha256:b03ba8137469b97fa0997a5770d3dfc9b13a0448603eafa181818022b205cf1e

WORKDIR /app

COPY pyproject.toml pyproject.toml

RUN python3.14 -m pip install --no-cache-dir .

COPY gather.py gather.py
COPY test_gather.py test_gather.py

ENTRYPOINT ["python3.14", "gather.py"]
