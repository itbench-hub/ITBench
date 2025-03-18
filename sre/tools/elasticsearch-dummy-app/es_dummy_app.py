import time
import random
import string
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import argparse
import os


class ElasticsearchApp:
    def __init__(self, index_name="test_index", doc_count=1000):
        """Initialize the Elasticsearch connection and create the index if needed."""
        es_host = os.getenv("ES_HOST", "https://localhost:9200")
        es_user = os.getenv("ES_USER", "elastic")  
        es_pass = os.getenv("ES_PASS", "changeme")  

        self.index_name = index_name
        self.doc_count = doc_count
        self.es = Elasticsearch(
            [es_host],
            basic_auth=(es_user, es_pass),
            verify_certs=False,
            ssl_show_warn=False
        )

        self._initialize_index()

    def _initialize_index(self):
        """Create an index with mappings if it does not exist."""
        if not self.es.indices.exists(index=self.index_name):
            self.es.indices.create(
                index=self.index_name,
                body={
                    "mappings": {
                        "properties": {
                            "message": {"type": "text"},
                            "timestamp": {"type": "date"},
                        }
                    }
                },
            )
            print(f"Index '{self.index_name}' created.")
        else:
            print(f"Index '{self.index_name}' already exists.")

    def populate_index_sync(self, target_size_mb: int):
        """Synchronously populate the index to reach a target size in MB."""
        doc_size_bytes = 1024  # Approximate size of each document (1KB per document)
        doc_count_per_bulk = 10000  # Number of documents per bulk request
        total_docs_needed = (target_size_mb * 1024 * 1024) // doc_size_bytes

        actions = [
            {
                "_index": self.index_name,
                "_source": {
                    "message": "".join(
                        random.choices(string.ascii_letters + string.digits, k=doc_size_bytes)
                    ),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }
            for _ in range(doc_count_per_bulk)
        ]

        print(f"Starting bulk index to reach {target_size_mb}MB of data...")

        docs_indexed = 0
        while docs_indexed < total_docs_needed:
            bulk(self.es, actions)
            docs_indexed += doc_count_per_bulk
            print(f"Indexed {docs_indexed}/{total_docs_needed} documents.")

        print(f"Completed indexing approximately {target_size_mb}MB of data.")

    def query_index(self):
        """Periodically query the index and print the number of documents found."""
        while True:
            response = self.es.count(index=self.index_name)
            print(f"Queried: {response['count']} documents.")
            time.sleep(2)

    def delete_index(self):
        """Delete the Elasticsearch index."""
        if self.es.indices.exists(index=self.index_name):
            self.es.indices.delete(index=self.index_name)
            print(f"Index '{self.index_name}' deleted.")
        else:
            print(f"Index '{self.index_name}' does not exist.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Elasticsearch Dummy Data Generator")
    parser.add_argument("--size", type=int, default=200, help="Size of data to generate in MB")
    args = parser.parse_args()

    es_app = ElasticsearchApp()
    es_app.populate_index_sync(args.size)
