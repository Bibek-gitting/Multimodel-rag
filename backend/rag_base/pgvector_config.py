import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path
from psycopg2.extras import execute_values
import numpy as np

load_dotenv()


class PGVectorDB:
    def __init__(self, table_name="documents", dim=384):
        self.conn = psycopg2.connect(
            os.getenv("DATABASE_URL")
        )
        self.cur = self.conn.cursor()
        self.table_name = table_name
        self.dim = dim
        base_dir = Path(__file__).resolve().parent.parent
        self.upload_dir = base_dir / "uploaded_media_files"

    def setup(self):
        # Enable extension
        self.cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # self.cur.execute(f"DROP TABLE IF EXISTS {self.table_name};")
        # self.conn.commit()

        # Create table
        self.cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id SERIAL PRIMARY KEY,
            content TEXT,
            embedding VECTOR({self.dim}),
            source_id TEXT,
            page INT,
            image_id TEXT[],
            tsv TSVECTOR,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)
        self.conn.commit()
        # Index for cosine similarity
        self.cur.execute(f"""
        CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx
        ON {self.table_name}
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
        """)

        self.cur.execute(f"""
        CREATE INDEX IF NOT EXISTS {self.table_name}_tsv_idx
        ON {self.table_name}
        USING GIN(tsv);
        """)

        self.conn.commit()

    def insert_batch(self, records: list, embeddings, file: str):
        """
        records = [
            {
                "content": "...",
                "embedding": [...],
                "source_id": "...",
                "page": 1,
                "image_id": None
            }
        ]
        """
        list_embeddings = np.array(embeddings).tolist()  # Convert to list of lists for JSON storage
        values = [
            (
                r.get("text", None),
                e,
                file,
                r.get("pageno", 0),
                r.get("figurenos", []),
                r.get("text", None),
            )
            for r, e in zip(records, list_embeddings)
        ]

        query = f"""
        INSERT INTO {self.table_name}
        (content, embedding, source_id, page, image_id, tsv)
        VALUES %s
        """

        execute_values(self.cur, query, values, template="""
        (%s, %s, %s, %s, %s, to_tsvector('english', %s))
        """)
        self.conn.commit()

    def search(self, query_embedding, query_text,top_k=10):
        # Convert numpy array to list for psycopg2 compatibility
        if isinstance(query_embedding, np.ndarray):
            query_embedding = query_embedding.tolist()
        
        self.cur.execute(f"""
        SELECT id, content, source_id, page, image_id,
               (0.7 * (embedding <=> %s::vector)) +
               (0.3 * (1 - ts_rank(tsv, plainto_tsquery(%s)))) AS score
        FROM {self.table_name}
        ORDER BY score ASC
        LIMIT %s;
        """, (query_embedding, query_text, top_k))  

        return self.cur.fetchall()  #[(id, content, source_id, page, image_id, score), ...]
    
    def delete_db(self):
        self.cur.execute(f"TRUNCATE TABLE {self.table_name} RESTART IDENTITY;")
        self.conn.commit()


    def close(self):
        self.cur.close()
        self.conn.close()


# Singleton instance for app-wide use
db = PGVectorDB()