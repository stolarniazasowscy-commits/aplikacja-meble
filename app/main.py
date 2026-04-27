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
    base_construction: Literal["legs", "side_to_floor_left", "side_to_floor_right", "side_to_floor_both"] = "legs"
    bottom_rail_mode: Literal["sides_on_bottom", "bottom_between_sides"] = "sides_on_bottom"
    top_mode: Literal["full_top_on_sides", "full_top_between_sides", "traverses"] = "full_top_on_sides"
    front_type: Literal["none", "doors", "drawers"] = "none"
    front_count: int = Field(default=0, ge=0)


class ManualProjectRequest(BaseModel):
    project_name: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    depth: int = Field(gt=0)
    base_height: int = Field(default=720, gt=0)
    board_thickness: int = Field(default=18, gt=0)
    back_thickness: int = Field(default=3, gt=0)
    manual_modules: list[ManualModuleInput] | None = None


class ModuleResponse(BaseModel):
    module_id: str
    module_type: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    depth: int = Field(gt=0)
    position: Literal["normal", "end_left", "end_right", "corner_left", "corner_right"]
    content: Literal["shelves", "drawers", "empty"]
    base_construction: Literal["legs", "side_to_floor_left", "side_to_floor_right", "side_to_floor_both"] = "legs"
    bottom_rail_mode: Literal["sides_on_bottom", "bottom_between_sides"] = "sides_on_bottom"
    top_mode: Literal["full_top_on_sides", "full_top_between_sides", "traverses"] = "full_top_on_sides"
    front_type: Literal["none", "doors", "drawers"] = "none"
    front_count: int = Field(default=0, ge=0)


class PartResponse(BaseModel):
    module_id: str
    part_type: str
    width: int = Field(gt=0)
    height: int | None = Field(default=None, gt=0)
    depth: int | None = Field(default=None, gt=0)
    thickness: int = Field(gt=0)


class ProjectResponse(BaseModel):
    project_name: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    depth: int = Field(gt=0)
    board_thickness: int = Field(gt=0)
    back_thickness: int = Field(gt=0)
    module_source: ModuleSource
    modules: list[ModuleResponse]
    parts: list[PartResponse]


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
                base_construction="legs",
                bottom_rail_mode="sides_on_bottom",
                top_mode="full_top_on_sides",
                front_type="none",
                front_count=0,
            )
        )

    return modules


def generate_base_parts(module: ModuleResponse, board_thickness: int, back_thickness: int, base_height: int) -> list[PartResponse]:
    parts: list[PartResponse] = []
    side_left_to_floor = module.base_construction in {"side_to_floor_left", "side_to_floor_both"}
    side_right_to_floor = module.base_construction in {"side_to_floor_right", "side_to_floor_both"}

    if module.position != "end_left":
        parts.append(
            PartResponse(
                module_id=module.module_id,
                part_type="side_left",
                width=module.depth,
                height=base_height + 100 if side_left_to_floor else base_height,
                depth=module.depth,
                thickness=board_thickness,
            )
        )

    if module.position != "end_right":
        parts.append(
            PartResponse(
                module_id=module.module_id,
                part_type="side_right",
                width=module.depth,
                height=base_height + 100 if side_right_to_floor else base_height,
                depth=module.depth,
                thickness=board_thickness,
            )
        )

    if module.bottom_rail_mode == "sides_on_bottom":
        if module.base_construction == "legs":
            bottom_width = module.width
        elif module.base_construction in {"side_to_floor_left", "side_to_floor_right"}:
            bottom_width = module.width - board_thickness
        else:
            bottom_width = module.width - (2 * board_thickness)
    else:
        bottom_width = module.width - (2 * board_thickness)

    if bottom_width <= 0:
        raise HTTPException(status_code=400, detail="Invalid bottom width - check board thickness and module width")

    parts.append(
        PartResponse(
            module_id=module.module_id,
            part_type="bottom",
            width=bottom_width,
            depth=module.depth,
            thickness=board_thickness,
        )
    )

    if module.top_mode == "full_top_on_sides":
        parts.append(
            PartResponse(
                module_id=module.module_id,
                part_type="top",
                width=module.width,
                depth=module.depth,
                thickness=board_thickness,
            )
        )
    elif module.top_mode == "full_top_between_sides":
        parts.append(
            PartResponse(
                module_id=module.module_id,
                part_type="top",
                width=module.width - (2 * board_thickness),
                depth=module.depth,
                thickness=board_thickness,
            )
        )
    else:
        traverse_width = module.width - (2 * board_thickness)
        parts.append(
            PartResponse(
                module_id=module.module_id,
                part_type="traverse_front",
                width=traverse_width,
                depth=100,
                thickness=board_thickness,
            )
        )
        parts.append(
            PartResponse(
                module_id=module.module_id,
                part_type="traverse_back",
                width=traverse_width,
                depth=100,
                thickness=board_thickness,
            )
        )

    parts.append(
        PartResponse(
            module_id=module.module_id,
            part_type="back",
            width=module.width,
            height=module.height,
            thickness=back_thickness,
        )
    )

    if module.front_type == "doors":
        front_count = module.front_count if module.front_count > 0 else 1
        for _ in range(front_count):
            parts.append(
                PartResponse(
                    module_id=module.module_id,
                    part_type="door_front",
                    width=module.width // front_count,
                    height=module.height,
                    thickness=board_thickness,
                )
            )
    elif module.front_type == "drawers":
        front_count = module.front_count if module.front_count > 0 else 3
        for _ in range(front_count):
            parts.append(
                PartResponse(
                    module_id=module.module_id,
                    part_type="drawer_front",
                    width=module.width,
                    height=module.height // front_count,
                    thickness=board_thickness,
                )
            )

    return parts


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/app", response_class=HTMLResponse)
def app_status_page() -> HTMLResponse:
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
            select {{
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                font-family: inherit;
            }}
            .button-row {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }}
            .manual-module-box {{
                max-width: 720px;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 14px;
                margin-bottom: 16px;
            }}
            .grid-2 {{
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 10px;
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
            .summary {{
                margin-top: 12px;
                max-width: 960px;
                display: grid;
                gap: 4px;
                font-weight: 600;
            }}
            #manual-width-status {{
                margin-top: 8px;
                font-weight: 700;
            }}
            .status-ok {{
                color: #15803d;
            }}
            .status-error {{
                color: #b91c1c;
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
            <label>base_height
                <input id="base_height" name="base_height" type="number" min="1" value="720" required />
            </label>
            <label>board_thickness
                <input id="board_thickness" name="board_thickness" type="number" min="1" value="18" required />
            </label>
            <label>back_thickness
                <input id="back_thickness" name="back_thickness" type="number" min="1" value="3" required />
            </label>
            <div class="button-row">
                <button type="button" id="auto-btn">Utwórz projekt automatycznie</button>
                <button type="button" id="manual-btn">Utwórz projekt z modułami ręcznymi</button>
                <button type="button" id="clear-btn">Wyczyść formularz</button>
            </div>
        </form>

        <h2>Moduły ręczne</h2>
        <div class="manual-module-box">
            <div class="grid-2">
                <label>width
                    <input id="manual_width" type="number" min="1" value="300" />
                </label>
                <label>cabinet_type
                    <select id="manual_cabinet_type">
                        <option value="base">base = szafka niska pod blat</option>
                        <option value="tall">tall = szafka wysoka pod sufit</option>
                    </select>
                </label>
                <label>position
                    <select id="manual_position">
                        <option value="normal">normal = normalna</option>
                        <option value="end_left">end_left = końcowa lewa</option>
                        <option value="end_right">end_right = końcowa prawa</option>
                        <option value="corner_left">corner_left = narożna lewa</option>
                        <option value="corner_right">corner_right = narożna prawa</option>
                    </select>
                </label>
                <label>content
                    <select id="manual_content">
                        <option value="shelves">shelves = półki</option>
                        <option value="drawers">drawers = szuflady</option>
                        <option value="empty">empty = pusta</option>
                    </select>
                </label>
                <label>base_construction
                    <select id="manual_base_construction">
                        <option value="legs">legs = na nogach</option>
                        <option value="side_to_floor_left">side_to_floor_left = lewy bok do podłogi</option>
                        <option value="side_to_floor_right">side_to_floor_right = prawy bok do podłogi</option>
                        <option value="side_to_floor_both">side_to_floor_both = oba boki do podłogi</option>
                    </select>
                </label>
                <label>bottom_rail_mode
                    <select id="manual_bottom_rail_mode">
                        <option value="sides_on_bottom">sides_on_bottom = boki stoją na wieńcu dolnym</option>
                        <option value="bottom_between_sides">bottom_between_sides = wieniec między bokami</option>
                    </select>
                </label>
                <label>top_mode
                    <select id="manual_top_mode">
                        <option value="full_top_on_sides">full_top_on_sides = pełny na bokach</option>
                        <option value="full_top_between_sides">full_top_between_sides = pełny między bokami</option>
                        <option value="traverses">traverses = listwy/trawersy</option>
                    </select>
                </label>
                <label>front_type
                    <select id="manual_front_type">
                        <option value="none">none = brak frontów</option>
                        <option value="doors">doors = fronty drzwiowe</option>
                        <option value="drawers">drawers = fronty szuflad</option>
                    </select>
                </label>
                <label>front_count
                    <input id="manual_front_count" type="number" min="0" value="0" />
                </label>
            </div>
            <div class="button-row" style="margin-top: 10px;">
                <button type="button" id="add-module-btn">Dodaj moduł</button>
                <button type="button" id="clear-modules-btn">Wyczyść moduły ręczne</button>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>nr</th>
                    <th>width</th>
                    <th>cabinet_type</th>
                    <th>position</th>
                    <th>content</th>
                    <th>base_construction</th>
                    <th>bottom_rail_mode</th>
                    <th>top_mode</th>
                    <th>front_type</th>
                    <th>front_count</th>
                    <th>akcja</th>
                </tr>
            </thead>
            <tbody id="manual-modules-body"></tbody>
        </table>
        <div class="summary">
            <div id="manual-width-sum">Suma modułów: 0 mm</div>
            <div id="project-width-info">Szerokość projektu: 0 mm</div>
            <div id="manual-width-diff">Różnica: 0 mm</div>
            <div id="manual-width-status" class="status-error">Suma modułów nie zgadza się z szerokością projektu</div>
        </div>

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
        <h2>Parts projektu</h2>
        <table>
            <thead>
                <tr>
                    <th>module_id</th>
                    <th>part_type</th>
                    <th>width</th>
                    <th>height</th>
                    <th>depth</th>
                    <th>thickness</th>
                </tr>
            </thead>
            <tbody id="parts-body"></tbody>
        </table>

        <script>
            const form = document.getElementById("project-form");
            const resultJson = document.getElementById("result-json");
            const errorBox = document.getElementById("error");
            const modulesBody = document.getElementById("modules-body");
            const manualModulesBody = document.getElementById("manual-modules-body");
            const manualWidthSum = document.getElementById("manual-width-sum");
            const projectWidthInfo = document.getElementById("project-width-info");
            const manualWidthDiff = document.getElementById("manual-width-diff");
            const manualWidthStatus = document.getElementById("manual-width-status");
            const projectWidthInput = document.getElementById("width");
            const partsBody = document.getElementById("parts-body");
            const manualModules = [];

            function clearResult() {{
                resultJson.textContent = "";
                errorBox.textContent = "";
                modulesBody.innerHTML = "";
                partsBody.innerHTML = "";
            }}

            function basePayload() {{
                return {{
                    project_name: document.getElementById("project_name").value,
                    width: Number(document.getElementById("width").value),
                    height: Number(document.getElementById("height").value),
                    depth: Number(document.getElementById("depth").value),
                    base_height: Number(document.getElementById("base_height").value),
                    board_thickness: Number(document.getElementById("board_thickness").value),
                    back_thickness: Number(document.getElementById("back_thickness").value)
                }};
            }}

            function updateManualSummary() {{
                const projectWidth = Number(projectWidthInput.value) || 0;
                const totalManualWidth = manualModules.reduce((acc, module) => acc + module.width, 0);
                const diff = projectWidth - totalManualWidth;

                manualWidthSum.textContent = `Suma modułów: ${{totalManualWidth}} mm`;
                projectWidthInfo.textContent = `Szerokość projektu: ${{projectWidth}} mm`;
                manualWidthDiff.textContent = `Różnica: ${{diff}} mm`;

                if (totalManualWidth === projectWidth) {{
                    manualWidthStatus.textContent = "Suma modułów zgadza się z szerokością projektu";
                    manualWidthStatus.classList.add("status-ok");
                    manualWidthStatus.classList.remove("status-error");
                }} else {{
                    manualWidthStatus.textContent = "Suma modułów nie zgadza się z szerokością projektu";
                    manualWidthStatus.classList.add("status-error");
                    manualWidthStatus.classList.remove("status-ok");
                }}
            }}

            function renderManualModules() {{
                manualModulesBody.innerHTML = "";
                manualModules.forEach((module, index) => {{
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${{index + 1}}</td>
                        <td>${{module.width}}</td>
                        <td>${{module.cabinet_type}}</td>
                        <td>${{module.position}}</td>
                        <td>${{module.content}}</td>
                        <td>${{module.base_construction}}</td>
                        <td>${{module.bottom_rail_mode}}</td>
                        <td>${{module.top_mode}}</td>
                        <td>${{module.front_type}}</td>
                        <td>${{module.front_count}}</td>
                        <td><button type="button" data-index="${{index}}">Usuń</button></td>
                    `;
                    const deleteBtn = row.querySelector("button");
                    deleteBtn.addEventListener("click", () => {{
                        manualModules.splice(index, 1);
                        renderManualModules();
                        updateManualSummary();
                    }});
                    manualModulesBody.appendChild(row);
                }});
            }}

            function renderParts(parts) {{
                partsBody.innerHTML = "";
                for (const part of parts) {{
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${{part.module_id}}</td>
                        <td>${{part.part_type}}</td>
                        <td>${{part.width}}</td>
                        <td>${{part.height ?? ""}}</td>
                        <td>${{part.depth ?? ""}}</td>
                        <td>${{part.thickness}}</td>
                    `;
                    partsBody.appendChild(row);
                }}
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
                        payload.manual_modules = manualModules;
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
                    renderParts(data.project?.parts || []);
                }} catch (error) {{
                    errorBox.textContent = error.message;
                }}
            }}

            function addManualModule() {{
                const width = Number(document.getElementById("manual_width").value);
                if (!Number.isInteger(width) || width <= 0) {{
                    errorBox.textContent = "Szerokość modułu musi być dodatnią liczbą całkowitą";
                    return;
                }}
                const frontCount = Number(document.getElementById("manual_front_count").value);
                if (!Number.isInteger(frontCount) || frontCount < 0) {{
                    errorBox.textContent = "front_count musi być liczbą całkowitą >= 0";
                    return;
                }}
                errorBox.textContent = "";
                manualModules.push({{
                    width,
                    cabinet_type: document.getElementById("manual_cabinet_type").value,
                    position: document.getElementById("manual_position").value,
                    content: document.getElementById("manual_content").value,
                    base_construction: document.getElementById("manual_base_construction").value,
                    bottom_rail_mode: document.getElementById("manual_bottom_rail_mode").value,
                    top_mode: document.getElementById("manual_top_mode").value,
                    front_type: document.getElementById("manual_front_type").value,
                    front_count: frontCount
                }});
                renderManualModules();
                updateManualSummary();
            }}

            document.getElementById("auto-btn").addEventListener("click", () => sendProject(false));
            document.getElementById("manual-btn").addEventListener("click", () => sendProject(true));
            document.getElementById("add-module-btn").addEventListener("click", addManualModule);
            document.getElementById("clear-modules-btn").addEventListener("click", () => {{
                manualModules.length = 0;
                renderManualModules();
                updateManualSummary();
            }});
            projectWidthInput.addEventListener("input", updateManualSummary);
            document.getElementById("clear-btn").addEventListener("click", () => {{
                form.reset();
                manualModules.length = 0;
                renderManualModules();
                updateManualSummary();
                clearResult();
            }});
            updateManualSummary();
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
        parts: list[PartResponse] = []
    else:
        if sum(module.width for module in payload.manual_modules) != payload.width:
            raise HTTPException(status_code=400, detail=MANUAL_WIDTH_SUM_ERROR)

        module_source = "manual"
        modules = []
        parts = []
        for idx, module in enumerate(payload.manual_modules, start=1):
            module_type = "base_cabinet" if module.cabinet_type == "base" else "tall_cabinet"
            module_height = payload.base_height if module.cabinet_type == "base" else payload.height
            response_module = ModuleResponse(
                module_id=f"M{idx}",
                module_type=module_type,
                width=module.width,
                height=module_height,
                depth=payload.depth,
                position=module.position,
                content=module.content,
                base_construction=module.base_construction,
                bottom_rail_mode=module.bottom_rail_mode,
                top_mode=module.top_mode,
                front_type=module.front_type,
                front_count=module.front_count,
            )
            modules.append(response_module)
            if module.cabinet_type == "base":
                parts.extend(
                    generate_base_parts(
                        module=response_module,
                        board_thickness=payload.board_thickness,
                        back_thickness=payload.back_thickness,
                        base_height=payload.base_height,
                    )
                )
            else:
                parts.extend(
                    [
                        PartResponse(
                            module_id=response_module.module_id,
                            part_type="side_left",
                            width=response_module.depth,
                            height=response_module.height,
                            depth=response_module.depth,
                            thickness=payload.board_thickness,
                        ),
                        PartResponse(
                            module_id=response_module.module_id,
                            part_type="side_right",
                            width=response_module.depth,
                            height=response_module.height,
                            depth=response_module.depth,
                            thickness=payload.board_thickness,
                        ),
                        PartResponse(
                            module_id=response_module.module_id,
                            part_type="bottom",
                            width=response_module.width,
                            depth=response_module.depth,
                            thickness=payload.board_thickness,
                        ),
                        PartResponse(
                            module_id=response_module.module_id,
                            part_type="top",
                            width=response_module.width,
                            depth=response_module.depth,
                            thickness=payload.board_thickness,
                        ),
                        PartResponse(
                            module_id=response_module.module_id,
                            part_type="back",
                            width=response_module.width,
                            height=response_module.height,
                            thickness=payload.back_thickness,
                        ),
                    ]
                )

    project = ProjectResponse(
        project_name=payload.project_name,
        width=payload.width,
        height=payload.height,
        depth=payload.depth,
        board_thickness=payload.board_thickness,
        back_thickness=payload.back_thickness,
        module_source=module_source,
        modules=modules,
        parts=parts,
    )
    return ManualProjectResponse(status="ok", project=project)
