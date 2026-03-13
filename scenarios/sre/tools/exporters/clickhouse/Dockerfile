FROM registry.access.redhat.com/ubi10/python-312-minimal:10.1-1772469338

USER 0

RUN microdnf update && \
    microdnf install -y tar

USER 1001

WORKDIR /app

COPY requirements.txt requirements.txt

RUN python3.12 -m pip install --no-cache-dir -r requirements.txt

COPY gather.py gather.py

CMD ["python3.12", "gather.py"]
