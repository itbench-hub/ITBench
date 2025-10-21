FROM registry.access.redhat.com/ubi10/python-312-minimal:10.0-1758744656

ENV DATA_DIRECTORY=/app/topology_data

WORKDIR /app

COPY requirements.txt requirements.txt

RUN python3.12 -m pip install --no-cache-dir -r requirements.txt

COPY __init__.py __init__.py
COPY app.py app.py
COPY event_manager.py event_manager.py
COPY main.py main.py
COPY path_finder.py path_finder.py
COPY resource_watcher.py resource_watcher.py
COPY taxonomy_creator.py taxonomy_creator.py
COPY topology_analyzer.py topology_analyzer.py
COPY topology_manager.py topology_manager.py

USER 0

RUN mkdir ${DATA_DIRECTORY} && \
    chown -R 1001 ${DATA_DIRECTORY}

USER 1001

CMD ["python3.12", "main.py"]
