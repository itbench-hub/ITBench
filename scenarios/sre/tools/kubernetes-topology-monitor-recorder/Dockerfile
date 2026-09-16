FROM registry.access.redhat.com/ubi10/python-314-minimal:10.2-1789550684@sha256:b95480fb2015d616797995e3c4874bf7ee3842e2373855e0e841d1e24d615e20

WORKDIR /app

COPY pyproject.toml pyproject.toml

RUN python3.14 -m pip install --no-cache-dir .

COPY gather.py gather.py
COPY test_gather.py test_gather.py

ENTRYPOINT ["python3.14", "gather.py"]
