FROM registry.access.redhat.com/ubi9/python-312:9.5-1743509868

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY es_dummy_app.py es_dummy_app.py

CMD ["python", "es_dummy_app.py", "--size", "200"]
