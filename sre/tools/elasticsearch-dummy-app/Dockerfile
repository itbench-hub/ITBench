FROM registry.access.redhat.com/ubi9/python-312:9.5-1744198409

WORKDIR /app

COPY requirements-dev.txt requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY es_dummy_app.py es_dummy_app.py

CMD ["python", "es_dummy_app.py", "--size", "200"]
