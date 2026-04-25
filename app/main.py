from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()


class ManualProjectRequest(BaseModel):
    project_name: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    depth: int = Field(gt=0)


class ModuleResponse(BaseModel):
    module_id: str
    module_type: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    depth: int = Field(gt=0)


class ProjectResponse(BaseModel):
    project_name: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    depth: int = Field(gt=0)
    modules: list[ModuleResponse]


class ManualProjectResponse(BaseModel):
    status: str
    project: ProjectResponse


def generate_modules(width: int, height: int, depth: int) -> list[ModuleResponse]:
    max_module_width = 600
    module_count = (width + max_module_width - 1) // max_module_width

    base_width = width // module_count
    remainder = width % module_count

    modules: list[ModuleResponse] = []
    for idx in range(module_count):
        module_width = base_width + (1 if idx < remainder else 0)
        modules.append(
            ModuleResponse(
                module_id=f"M{idx + 1}",
                module_type="wardrobe_cabinet",
                width=module_width,
                height=height,
                depth=depth,
            )
        )

    return modules


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/projects/from-manual", response_model=ManualProjectResponse)
def create_project_from_manual(payload: ManualProjectRequest) -> ManualProjectResponse:
    modules = generate_modules(payload.width, payload.height, payload.depth)
    project = ProjectResponse(
        project_name=payload.project_name,
        width=payload.width,
        height=payload.height,
        depth=payload.depth,
        modules=modules,
    )
    return ManualProjectResponse(status="ok", project=project)
