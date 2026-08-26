FROM registry.access.redhat.com/ubi10/python-314-minimal:10.2-1787722346@sha256:b7243a5f6ac9616eff0475c1a3caa4e71118d6d00151a82e019fd6f2260acc19

WORKDIR /app

COPY pyproject.toml pyproject.toml

RUN python3.14 -m pip install --no-cache-dir .

COPY gather.py gather.py
COPY test_gather.py test_gather.py

ENTRYPOINT ["python3.14", "gather.py"]
