FROM registry.access.redhat.com/ubi10/python-314-minimal:10.2-1790644442@sha256:f1e81dae0f0255961d1f091034e3a6da496786c06b40edf976dd1f09def524ea

WORKDIR /app

COPY pyproject.toml pyproject.toml

RUN python3.14 -m pip install --no-cache-dir .

COPY gather.py gather.py
COPY test_gather.py test_gather.py

ENTRYPOINT ["python3.14", "gather.py"]
