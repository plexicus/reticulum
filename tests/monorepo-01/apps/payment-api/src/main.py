from fastapi import FastAPI
import requests

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "exposed"}
