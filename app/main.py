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


@app.get("/app", response_class=HTMLResponse)
def app_status_page() -> HTMLResponse:
    sample_manual_modules = """[
  {
    "width": 300,
    "cabinet_type": "base",
    "position": "end_left",
    "content": "drawers"
  },
  {
    "width": 300,
    "cabinet_type": "base",
    "position": "normal",
    "content": "shelves"
  },
  {
    "width": 800,
    "cabinet_type": "base",
    "position": "normal",
    "content": "empty"
  },
  {
    "width": 600,
    "cabinet_type": "tall",
    "position": "corner_left",
    "content": "shelves"
  },
  {
    "width": 600,
    "cabinet_type": "tall",
    "position": "end_right",
    "content": "empty"
  }
]"""
    html = f"""
    <!DOCTYPE html>
    <html lang="pl">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Aplikacja meblowa - panel testowy</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 24px;
                color: #1f2937;
            }}
            h1, h2 {{
                margin-bottom: 12px;
            }}
            .links {{
                display: flex;
                gap: 12px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }}
            .btn, button {{
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 8px 12px;
                background: #f9fafb;
                cursor: pointer;
                text-decoration: none;
                color: #111827;
                font-size: 14px;
            }}
            .btn:hover, button:hover {{
                background: #f3f4f6;
            }}
            form {{
                max-width: 720px;
                display: grid;
                gap: 10px;
                margin-bottom: 20px;
            }}
            label {{
                display: grid;
                gap: 6px;
                font-weight: 600;
            }}
            input, textarea {{
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                font-family: inherit;
            }}
            textarea {{
                min-height: 280px;
                font-family: "Courier New", monospace;
            }}
            .button-row {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                max-width: 960px;
                margin-top: 10px;
            }}
            th, td {{
                border: 1px solid #d1d5db;
                padding: 8px;
                text-align: left;
                font-size: 14px;
            }}
            th {{
                background: #f9fafb;
            }}
            #result-json {{
                background: #f8fafc;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 12px;
                white-space: pre-wrap;
                max-width: 960px;
            }}
            #error {{
                color: #b91c1c;
                font-weight: 700;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <h1>Aplikacja meblowa - panel testowy</h1>
        <div class="links">
            <a class="btn" href="/">Status systemu</a>
            <a class="btn" href="/docs">Dokumentacja API</a>
        </div>

        <h2>Formularz projektu</h2>
        <form id="project-form">
            <label>project_name
                <input id="project_name" name="project_name" value="Projekt testowy" required />
            </label>
            <label>width
                <input id="width" name="width" type="number" min="1" value="2600" required />
            </label>
            <label>height
                <input id="height" name="height" type="number" min="1" value="2400" required />
            </label>
            <label>depth
                <input id="depth" name="depth" type="number" min="1" value="600" required />
            </label>
            <label>manual_modules
                <textarea id="manual_modules" name="manual_modules">{sample_manual_modules}</textarea>
            </label>
            <div class="button-row">
                <button type="button" id="auto-btn">Utwórz projekt automatycznie</button>
                <button type="button" id="manual-btn">Utwórz projekt z modułami ręcznymi</button>
                <button type="button" id="clear-btn">Wyczyść formularz</button>
            </div>
        </form>

        <h2>Dostępne wartości</h2>
        <table>
            <thead>
                <tr>
                    <th>Pole</th>
                    <th>Wartość</th>
                    <th>Opis</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>cabinet_type</td><td>base</td><td>szafka niska pod blat</td></tr>
                <tr><td>cabinet_type</td><td>tall</td><td>szafka wysoka pod sufit</td></tr>
                <tr><td>position</td><td>normal</td><td>normalna</td></tr>
                <tr><td>position</td><td>end_left</td><td>końcowa lewa</td></tr>
                <tr><td>position</td><td>end_right</td><td>końcowa prawa</td></tr>
                <tr><td>position</td><td>corner_left</td><td>narożna lewa</td></tr>
                <tr><td>position</td><td>corner_right</td><td>narożna prawa</td></tr>
                <tr><td>content</td><td>shelves</td><td>półki</td></tr>
                <tr><td>content</td><td>drawers</td><td>szuflady</td></tr>
                <tr><td>content</td><td>empty</td><td>pusta</td></tr>
            </tbody>
        </table>

        <h2>Wynik JSON</h2>
        <div id="error"></div>
        <pre id="result-json"></pre>

        <h2>Moduły projektu</h2>
        <table>
            <thead>
                <tr>
                    <th>module_id</th>
                    <th>module_type</th>
                    <th>width</th>
                    <th>height</th>
                    <th>depth</th>
                    <th>position</th>
                    <th>content</th>
                </tr>
            </thead>
            <tbody id="modules-body"></tbody>
        </table>

        <script>
            const form = document.getElementById("project-form");
            const resultJson = document.getElementById("result-json");
            const errorBox = document.getElementById("error");
            const modulesBody = document.getElementById("modules-body");

            function clearResult() {{
                resultJson.textContent = "";
                errorBox.textContent = "";
                modulesBody.innerHTML = "";
            }}

            function basePayload() {{
                return {{
                    project_name: document.getElementById("project_name").value,
                    width: Number(document.getElementById("width").value),
                    height: Number(document.getElementById("height").value),
                    depth: Number(document.getElementById("depth").value)
                }};
            }}

            function renderModules(modules) {{
                modulesBody.innerHTML = "";
                for (const module of modules) {{
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${{module.module_id}}</td>
                        <td>${{module.module_type}}</td>
                        <td>${{module.width}}</td>
                        <td>${{module.height}}</td>
                        <td>${{module.depth}}</td>
                        <td>${{module.position}}</td>
                        <td>${{module.content}}</td>
                    `;
                    modulesBody.appendChild(row);
                }}
            }}

            async function sendProject(useManualModules) {{
                clearResult();
                try {{
                    const payload = basePayload();
                    if (useManualModules) {{
                        payload.manual_modules = JSON.parse(document.getElementById("manual_modules").value);
                    }}

                    const response = await fetch("/projects/from-manual", {{
                        method: "POST",
                        headers: {{"Content-Type": "application/json"}},
                        body: JSON.stringify(payload)
                    }});

                    const data = await response.json();
                    if (!response.ok) {{
                        throw new Error(data.detail || "Wystąpił błąd");
                    }}

                    resultJson.textContent = JSON.stringify(data, null, 2);
                    renderModules(data.project?.modules || []);
                }} catch (error) {{
                    errorBox.textContent = error.message;
                }}
            }}

            document.getElementById("auto-btn").addEventListener("click", () => sendProject(false));
            document.getElementById("manual-btn").addEventListener("click", () => sendProject(true));
            document.getElementById("clear-btn").addEventListener("click", () => {{
                form.reset();
                document.getElementById("manual_modules").value = `{sample_manual_modules}`;
                clearResult();
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


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
