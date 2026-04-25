from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

@app.get("/health")

def health():
    return {"status": "ok", "service": "knowledge-module"}

def get_conn():
    return psycopg2.connect(
        host="platform-postgres",
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=int(os.getenv("POSTGRES_PORT", 5432))
    )

@app.get("/db-test")

def db_test():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    result = cur.fetchone()
    conn.close()

    return {"db": "ok", "result": result}