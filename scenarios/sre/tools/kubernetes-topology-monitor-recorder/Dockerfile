FROM registry.access.redhat.com/ubi10/python-314-minimal:10.2-1789951202@sha256:39659b2e2f54adcdbe66315e10edae56e9a7c79ac6e798edebba340535c9c4a3

WORKDIR /app

COPY pyproject.toml pyproject.toml

RUN python3.14 -m pip install --no-cache-dir .

COPY gather.py gather.py
COPY test_gather.py test_gather.py

ENTRYPOINT ["python3.14", "gather.py"]
