from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()


class ManualProjectRequest(BaseModel):
    project_name: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    depth: int = Field(gt=0)


class ManualProjectResponse(BaseModel):
    status: str
    project: ManualProjectRequest


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/projects/from-manual", response_model=ManualProjectResponse)
def create_project_from_manual(payload: ManualProjectRequest) -> ManualProjectResponse:
    return ManualProjectResponse(status="ok", project=payload)
