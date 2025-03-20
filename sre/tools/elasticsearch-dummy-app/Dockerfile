FROM registry.access.redhat.com/ubi9/python-312

WORKDIR /app

RUN pip install elasticsearch

COPY es_dummy_app.py es_dummy_app.py

CMD ["python", "es_dummy_app.py", "--size", "200"]
