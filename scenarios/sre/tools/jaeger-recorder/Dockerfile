FROM registry.access.redhat.com/ubi10/python-314-minimal:10.2-1789361905@sha256:a7f537598b1a6737c56f463421f490cbc12a0f60ca64d87f0b91944b34ee03db

WORKDIR /app

COPY pyproject.toml pyproject.toml

RUN python3.14 -m pip install --no-cache-dir .

COPY gather.py gather.py
COPY test_gather.py test_gather.py

ENTRYPOINT ["python3.14", "gather.py"]
