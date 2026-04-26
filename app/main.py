from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI()

ModuleSource = Literal["manual", "auto"]
MANUAL_WIDTH_SUM_ERROR = "Sum of manual module widths must equal total project width"


class ManualModuleInput(BaseModel):
    width: int = Field(gt=0)
    cabinet_type: Literal["base", "tall"]
    position: Literal["normal", "end_left", "end_right", "corner_left", "corner_right"]
    content: Literal["shelves", "drawers", "empty"]


class ManualProjectRequest(BaseModel):
    project_name: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    depth: int = Field(gt=0)
    manual_modules: list[ManualModuleInput] | None = None


class ModuleResponse(BaseModel):
    module_id: str
    module_type: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    depth: int = Field(gt=0)
    position: Literal["normal", "end_left", "end_right", "corner_left", "corner_right"]
    content: Literal["shelves", "drawers", "empty"]


class ProjectResponse(BaseModel):
    project_name: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    depth: int = Field(gt=0)
    module_source: ModuleSource
    modules: list[ModuleResponse]


class ManualProjectResponse(BaseModel):
    status: Literal["ok"]
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
                position="normal",
                content="empty",
            )
        )

    return modules


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/view", response_class=HTMLResponse)
def view_modules() -> HTMLResponse:
    modules = [
        {"width": 300, "module_type": "base_cabinet"},
        {"width": 300, "module_type": "base_cabinet"},
        {"width": 800, "module_type": "base_cabinet"},
        {"width": 600, "module_type": "tall_cabinet"},
        {"width": 600, "module_type": "tall_cabinet"},
    ]

    module_boxes: list[str] = []
    for module in modules:
        is_tall = module["module_type"] == "tall_cabinet"
        module_height = 200 if is_tall else 100
        module_color = "lightgreen" if is_tall else "lightblue"
        module_label = "tall" if is_tall else "base"
        module_boxes.append(
            f"""
            <div class="module" style="width: {module['width']}px; height: {module_height}px; background: {module_color};">
                <div>{module['width']}</div>
                <div>{module_label}</div>
            </div>
            """
        )

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <title>Module View</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 24px;
            }}
            .canvas {{
                display: flex;
                align-items: flex-end;
                gap: 8px;
                border: 1px solid #ddd;
                padding: 12px;
                overflow-x: auto;
            }}
            .module {{
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                border: 1px solid #333;
                box-sizing: border-box;
                color: #111;
                font-size: 14px;
                flex: 0 0 auto;
            }}
        </style>
    </head>
    <body>
        <h1>2D Module Visualization</h1>
        <div class="canvas">
            {''.join(module_boxes)}
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/projects/from-manual", response_model=ManualProjectResponse)
def create_project_from_manual(payload: ManualProjectRequest) -> ManualProjectResponse:
    if payload.manual_modules is None:
        module_source: ModuleSource = "auto"
        modules = generate_modules(payload.width, payload.height, payload.depth)
    else:
        if sum(module.width for module in payload.manual_modules) != payload.width:
            raise HTTPException(status_code=400, detail=MANUAL_WIDTH_SUM_ERROR)

        module_source = "manual"
        modules = []
        for idx, module in enumerate(payload.manual_modules, start=1):
            module_type = "base_cabinet" if module.cabinet_type == "base" else "tall_cabinet"
            module_height = 720 if module.cabinet_type == "base" else payload.height
            modules.append(
                ModuleResponse(
                    module_id=f"M{idx}",
                    module_type=module_type,
                    width=module.width,
                    height=module_height,
                    depth=payload.depth,
                    position=module.position,
                    content=module.content,
                )
            )

    project = ProjectResponse(
        project_name=payload.project_name,
        width=payload.width,
        height=payload.height,
        depth=payload.depth,
        module_source=module_source,
        modules=modules,
    )
    return ManualProjectResponse(status="ok", project=project)
