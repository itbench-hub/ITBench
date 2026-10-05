FROM registry.access.redhat.com/ubi10/python-314-minimal:10.2-1791160361@sha256:1ef40558aa44913478db2b564b4daf9ae67e5ecf72f5b46a433bd21f916ba4d1

WORKDIR /app

COPY pyproject.toml pyproject.toml

RUN python3.14 -m pip install --no-cache-dir .

COPY gather.py gather.py
COPY test_gather.py test_gather.py

ENTRYPOINT ["python3.14", "gather.py"]
