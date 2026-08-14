from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="SmartBiz MVP")

class Job(BaseModel):
    id: int
    title: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/jobs")
def create_job(job: Job):
    return {"ok": True, "job": job.model_dump()}
