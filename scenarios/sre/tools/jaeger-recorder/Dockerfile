FROM registry.access.redhat.com/ubi10/python-314-minimal:10.2-1787002610@sha256:b6cc4d6c56a139b763af6cb9cd6b838d0f8ed5a67caadfa3418e68dec6ab755f

WORKDIR /app

COPY pyproject.toml pyproject.toml

RUN python3.14 -m pip install --no-cache-dir .

COPY gather.py gather.py
COPY test_gather.py test_gather.py

ENTRYPOINT ["python3.14", "gather.py"]
