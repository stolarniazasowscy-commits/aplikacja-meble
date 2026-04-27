from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI()

ModuleSource = Literal["manual", "auto"]
MANUAL_WIDTH_SUM_ERROR = "Sum of manual module widths must equal total project width"

LegacyBaseConstruction = Literal["legs", "side_to_floor_left", "side_to_floor_right", "side_to_floor_both"]
SideToFloor = Literal["none", "left", "right", "both"]
BottomRailMode = Literal["sides_on_bottom", "bottom_between_sides"]
BackType = Literal["overlay", "groove", "between"]


class ManualModuleInput(BaseModel):
    width: int = Field(gt=0)
    cabinet_type: Literal["base", "tall"]
    position: Literal["normal", "end_left", "end_right", "corner_left", "corner_right"]
    content: Literal["shelves", "drawers", "empty"]
    has_legs: bool = True
    side_to_floor: SideToFloor = "none"
    base_construction: LegacyBaseConstruction | None = None
    bottom_rail_mode: BottomRailMode = "sides_on_bottom"
    top_mode: Literal["full_top_on_sides", "full_top_between_sides", "traverses"] = "full_top_on_sides"
    front_type: Literal["none", "doors", "drawers"] = "none"
    front_count: int = Field(default=0, ge=0)


class ManualProjectRequest(BaseModel):
    project_name: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    depth: int = Field(gt=0)
    base_height: int = Field(default=720, gt=0)
    leg_height: int = Field(default=100, ge=0)
    board_thickness: int = Field(default=18, gt=0)
    back_thickness: int = Field(default=3, gt=0)
    back_type: BackType = "overlay"
    back_groove_offset: int = Field(default=10, ge=0)
    back_groove_insert: int = Field(default=10, ge=0)
    manual_modules: list[ManualModuleInput] | None = None


class ModuleResponse(BaseModel):
    module_id: str
    module_type: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    depth: int = Field(gt=0)
    position: Literal["normal", "end_left", "end_right", "corner_left", "corner_right"]
    content: Literal["shelves", "drawers", "empty"]
    has_legs: bool = True
    side_to_floor: SideToFloor = "none"
    base_construction: LegacyBaseConstruction | None = None
    bottom_rail_mode: BottomRailMode = "sides_on_bottom"
    top_mode: Literal["full_top_on_sides", "full_top_between_sides", "traverses"] = "full_top_on_sides"
    front_type: Literal["none", "doors", "drawers"] = "none"
    front_count: int = Field(default=0, ge=0)


class PartResponse(BaseModel):
    module_id: str
    part_type: str
    length: int | float = Field(gt=0)
    width: int | float = Field(gt=0)
    thickness: int | float = Field(gt=0)


class ProjectResponse(BaseModel):
    project_name: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    depth: int = Field(gt=0)
    base_height: int = Field(gt=0)
    leg_height: int = Field(ge=0)
    board_thickness: int = Field(gt=0)
    back_thickness: int = Field(gt=0)
    back_type: BackType
    back_groove_offset: int = Field(ge=0)
    back_groove_insert: int = Field(ge=0)
    module_source: ModuleSource
    warnings: list[str]
    modules: list[ModuleResponse]
    parts: list[PartResponse]


class ManualProjectResponse(BaseModel):
    status: Literal["ok"]
    project: ProjectResponse


def _map_legacy_base_construction(base_construction: LegacyBaseConstruction | None) -> tuple[bool, SideToFloor]:
    if base_construction == "side_to_floor_left":
        return True, "left"
    if base_construction == "side_to_floor_right":
        return True, "right"
    if base_construction == "side_to_floor_both":
        return True, "both"
    return True, "none"


def _normalize_module_config(module: ManualModuleInput) -> tuple[bool, SideToFloor, BottomRailMode, LegacyBaseConstruction | None]:
    has_legs = module.has_legs
    side_to_floor = module.side_to_floor

    if module.base_construction is not None:
        legacy_has_legs, legacy_side_to_floor = _map_legacy_base_construction(module.base_construction)
        has_legs = legacy_has_legs if module.has_legs is True else module.has_legs
        if module.side_to_floor == "none":
            side_to_floor = legacy_side_to_floor

    bottom_rail_mode = module.bottom_rail_mode
    if side_to_floor == "both":
        bottom_rail_mode = "bottom_between_sides"

    return has_legs, side_to_floor, bottom_rail_mode, module.base_construction


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
                has_legs=True,
                side_to_floor="none",
                base_construction="legs",
                bottom_rail_mode="sides_on_bottom",
                top_mode="full_top_on_sides",
                front_type="none",
                front_count=0,
            )
        )

    return modules


def _base_side_height(module: ModuleResponse, base_height: int, leg_height: int, board_thickness: int) -> int:
    side_height = base_height - leg_height if module.has_legs else base_height

    if module.bottom_rail_mode == "sides_on_bottom":
        side_height -= board_thickness

    if module.top_mode == "full_top_on_sides":
        side_height -= board_thickness

    return side_height


def _validate_part_dimensions(part_type: str, length: int | float, width: int | float) -> None:
    if length <= 0 or width <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid dimensions for part '{part_type}': length={length}, width={width}. Both must be > 0",
        )


def _append_part(
    parts: list[PartResponse],
    module_id: str,
    part_type: str,
    length: int | float,
    width: int | float,
    thickness: int | float,
) -> None:
    _validate_part_dimensions(part_type, length, width)
    parts.append(
        PartResponse(
            module_id=module_id,
            part_type=part_type,
            length=length,
            width=width,
            thickness=thickness,
        )
    )


def generate_base_parts(
    module: ModuleResponse,
    board_thickness: int,
    back_thickness: int,
    back_type: BackType,
    back_groove_offset: int,
    back_groove_insert: int,
    base_height: int,
    leg_height: int,
    warnings: list[str],
) -> list[PartResponse]:
    parts: list[PartResponse] = []
    effective_depth = module.depth - back_thickness if back_type == "overlay" else module.depth
    if effective_depth <= 0:
        raise HTTPException(status_code=400, detail="Invalid depth after subtracting back thickness")

    side_depth = effective_depth
    bottom_depth = effective_depth
    top_depth = effective_depth

    if back_type == "groove":
        side_depth = module.depth
        rail_depth = module.depth - back_thickness - back_groove_offset
        if rail_depth <= 0:
            raise HTTPException(status_code=400, detail="Invalid rail depth after back groove offset")
        bottom_depth = rail_depth
        top_depth = rail_depth
    elif back_type == "between":
        side_depth = module.depth
        bottom_depth = module.depth
        top_depth = module.depth

    effective_bottom_rail_mode: BottomRailMode = (
        "bottom_between_sides" if module.side_to_floor == "both" else module.bottom_rail_mode
    )

    normal_side_height = _base_side_height(module, base_height, leg_height, board_thickness)
    if normal_side_height <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid side height - check base height, leg height and board thickness",
        )

    left_height = base_height if module.side_to_floor in {"left", "both"} else normal_side_height
    right_height = base_height if module.side_to_floor in {"right", "both"} else normal_side_height

    if module.position != "end_left":
        _append_part(
            parts,
            module.module_id,
            "side_left",
            length=left_height,
            width=side_depth,
            thickness=board_thickness,
        )

    if module.position != "end_right":
        _append_part(
            parts,
            module.module_id,
            "side_right",
            length=right_height,
            width=side_depth,
            thickness=board_thickness,
        )

    if effective_bottom_rail_mode == "bottom_between_sides":
        bottom_length = module.width - (2 * board_thickness)
    elif module.side_to_floor == "none":
        bottom_length = module.width
    elif module.side_to_floor in {"left", "right"}:
        bottom_length = module.width - board_thickness
    else:
        bottom_length = module.width - (2 * board_thickness)

    _append_part(
        parts,
        module.module_id,
        "bottom",
        length=bottom_length,
        width=bottom_depth,
        thickness=board_thickness,
    )

    if module.top_mode == "full_top_on_sides":
        top_length = module.width
        _append_part(parts, module.module_id, "top", length=top_length, width=top_depth, thickness=board_thickness)
    elif module.top_mode == "full_top_between_sides":
        top_length = module.width - (2 * board_thickness)
        _append_part(parts, module.module_id, "top", length=top_length, width=top_depth, thickness=board_thickness)
    else:
        traverse_length = module.width - (2 * board_thickness)
        _append_part(
            parts,
            module.module_id,
            "traverse_front",
            length=traverse_length,
            width=100,
            thickness=board_thickness,
        )
        _append_part(
            parts,
            module.module_id,
            "traverse_back",
            length=traverse_length,
            width=100,
            thickness=board_thickness,
        )

    if back_type == "between" and (module.width - (2 * board_thickness)) <= 0:
        raise HTTPException(status_code=400, detail="Invalid back width between sides")

    back_width = module.width if back_type != "between" else module.width - (2 * board_thickness)
    if back_type == "groove":
        back_width = module.width - (2 * board_thickness) + (2 * back_groove_insert)
        if back_width <= 0:
            raise HTTPException(status_code=400, detail="Invalid groove back width")

    _append_part(parts, module.module_id, "back", length=module.height, width=back_width, thickness=back_thickness)

    if module.front_type == "doors":
        front_count = module.front_count if module.front_count > 0 else 1
        for _ in range(front_count):
            _append_part(
                parts,
                module.module_id,
                "door_front",
                length=module.height,
                width=module.width / front_count,
                thickness=board_thickness,
            )
    elif module.front_type == "drawers":
        front_count = module.front_count if module.front_count > 0 else 3
        for _ in range(front_count):
            _append_part(
                parts,
                module.module_id,
                "drawer_front",
                length=module.height / front_count,
                width=module.width,
                thickness=board_thickness,
            )

    return parts


@app.get("/")
def read_root() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/app", response_class=HTMLResponse)
def app_status_page() -> HTMLResponse:
    html = """
    <!DOCTYPE html>
    <html lang="pl">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Aplikacja meblowa - panel testowy</title>
        <style>
            :root {
                --bg: #f3f4f6;
                --card: #ffffff;
                --text: #1f2937;
                --muted: #6b7280;
                --border: #d1d5db;
                --primary: #2563eb;
                --secondary: #f3f4f6;
                --danger: #dc2626;
                --success: #15803d;
                --error: #b91c1c;
            }
            * { box-sizing: border-box; }
            body {
                margin: 0;
                padding: 24px;
                background: var(--bg);
                color: var(--text);
                font-family: Arial, sans-serif;
                line-height: 1.4;
            }
            h1, h2 { margin: 0 0 12px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card {
                background: var(--card);
                border: 1px solid var(--border);
                border-radius: 10px;
                padding: 18px;
                margin-bottom: 16px;
            }
            .links { display: flex; gap: 12px; flex-wrap: wrap; }
            .btn, button {
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 10px 16px;
                cursor: pointer;
                text-decoration: none;
                font-size: 14px;
                font-weight: 600;
                transition: filter 0.2s ease;
            }
            .btn:hover, button:hover { filter: brightness(0.96); }
            .btn-primary { background: var(--primary); color: #fff; }
            .btn-secondary { background: var(--secondary); color: var(--text); border-color: var(--border); }
            .btn-danger { background: var(--danger); color: #fff; }
            .button-row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
            .form-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 12px;
            }
            label { display: grid; gap: 6px; font-weight: 600; }
            input, textarea, select {
                border: 1px solid var(--border);
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-family: inherit;
                width: 100%;
                background: #fff;
            }
            .hint {
                margin-top: 10px;
                padding: 10px 12px;
                border-radius: 8px;
                background: #fff7ed;
                border: 1px solid #fdba74;
                color: #9a3412;
                font-weight: 600;
                display: none;
            }
            .table-wrap { overflow-x: auto; }
            table { border-collapse: collapse; width: 100%; min-width: 880px; }
            th, td { border: 1px solid var(--border); padding: 8px 10px; text-align: left; font-size: 14px; }
            th { background: #e5e7eb; }
            .summary { display: grid; gap: 4px; font-weight: 600; margin-top: 12px; }
            #manual-width-status { margin-top: 8px; font-weight: 700; }
            .status-ok { color: var(--success); }
            .status-error { color: var(--error); }
            #error { color: var(--error); font-weight: 700; margin-bottom: 10px; }
            #result-json {
                margin: 0;
                background: #111827;
                color: #f9fafb;
                border: 1px solid #1f2937;
                border-radius: 8px;
                padding: 12px;
                white-space: pre-wrap;
                overflow-wrap: anywhere;
                word-break: break-word;
            }
            @media (max-width: 960px) {
                .form-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            }
            @media (max-width: 640px) {
                body { padding: 14px; }
                .form-grid { grid-template-columns: 1fr; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <section class="card">
                <h1>Aplikacja meblowa - panel testowy</h1>
            </section>

            <section class="card">
                <h2>Status systemu</h2>
                <div class="links">
                    <a class="btn btn-secondary" href="/">Status systemu</a>
                    <a class="btn btn-secondary" href="/docs">Dokumentacja API</a>
                </div>
            </section>

            <section class="card">
                <h2>Formularz projektu</h2>
                <form id="project-form">
                    <div class="form-grid">
                        <label>project_name<input id="project_name" name="project_name" value="Projekt testowy" required /></label>
                        <label>width<input id="width" name="width" type="number" min="1" value="2600" required /></label>
                        <label>height<input id="height" name="height" type="number" min="1" value="2400" required /></label>
                        <label>depth<input id="depth" name="depth" type="number" min="1" value="600" required /></label>
                        <label>base_height<input id="base_height" name="base_height" type="number" min="1" value="720" required /></label>
                        <label>leg_height<input id="leg_height" name="leg_height" type="number" min="0" value="100" required /></label>
                        <label>board_thickness<input id="board_thickness" name="board_thickness" type="number" min="1" value="18" required /></label>
                        <label>back_thickness<input id="back_thickness" name="back_thickness" type="number" min="1" value="3" required /></label>
                        <label>back_type
                            <select id="back_type" name="back_type">
                                <option value="overlay">overlay = plecy nakładane</option>
                                <option value="groove">groove = plecy wpuszczane w kanalik</option>
                                <option value="between">between = plecy między bokami</option>
                            </select>
                        </label>
                        <label>back_groove_offset<input id="back_groove_offset" name="back_groove_offset" type="number" min="0" value="10" required /></label>
                        <label>back_groove_insert<input id="back_groove_insert" name="back_groove_insert" type="number" min="0" value="10" required /></label>
                    </div>
                    <div id="back-type-description" class="hint" style="display:block;background:#eef2ff;border-color:#a5b4fc;color:#3730a3;"></div>
                    <div class="button-row">
                        <button class="btn-primary" type="button" id="auto-btn">Utwórz projekt automatycznie</button>
                        <button class="btn-secondary" type="button" id="manual-btn">Utwórz projekt z modułami ręcznymi</button>
                        <button class="btn-danger" type="button" id="clear-btn">Wyczyść formularz</button>
                    </div>
                </form>
            </section>

            <section class="card">
                <h2>Moduły ręczne</h2>
                <div class="form-grid">
                    <label>width<input id="manual_width" type="number" min="1" value="300" /></label>
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
                    <label>has_legs
                        <select id="manual_has_legs">
                            <option value="true">Tak</option>
                            <option value="false">Nie</option>
                        </select>
                    </label>
                    <label>side_to_floor
                        <select id="manual_side_to_floor">
                            <option value="none">none = żaden bok do podłogi</option>
                            <option value="left">left = lewy bok do podłogi</option>
                            <option value="right">right = prawy bok do podłogi</option>
                            <option value="both">both = oba boki do podłogi</option>
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
                    <label>front_count<input id="manual_front_count" type="number" min="0" value="0" /></label>
                </div>
                <div id="side-floor-hint" class="hint">Wieniec dolny jest wymuszony między bokami tylko wtedy, gdy oba boki schodzą do podłogi.</div>
                <div class="button-row">
                    <button class="btn-primary" type="button" id="add-module-btn">Dodaj moduł</button>
                    <button class="btn-danger" type="button" id="clear-modules-btn">Wyczyść moduły ręczne</button>
                </div>
            </section>

            <section class="card">
                <h2>Podsumowanie szerokości</h2>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>nr</th><th>width</th><th>cabinet_type</th><th>position</th><th>content</th>
                                <th>has_legs</th><th>side_to_floor</th><th>bottom_rail_mode</th><th>top_mode</th><th>front_type</th><th>front_count</th><th>akcja</th>
                            </tr>
                        </thead>
                        <tbody id="manual-modules-body"></tbody>
                    </table>
                </div>
                <div class="summary">
                    <div id="manual-width-sum">Suma modułów: 0 mm</div>
                    <div id="project-width-info">Szerokość projektu: 0 mm</div>
                    <div id="manual-width-diff">Różnica: 0 mm</div>
                    <div id="manual-width-status" class="status-error">Suma modułów nie zgadza się z szerokością projektu</div>
                </div>
            </section>

            <section class="card">
                <h2>Wynik JSON</h2>
                <div id="error"></div>
                <pre id="result-json"></pre>
            </section>

            <section class="card">
                <h2>Moduły projektu</h2>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>module_id</th><th>module_type</th><th>width</th><th>height</th><th>depth</th><th>position</th><th>content</th>
                                <th>has_legs</th><th>side_to_floor</th><th>bottom_rail_mode</th><th>top_mode</th><th>front_type</th><th>front_count</th>
                            </tr>
                        </thead>
                        <tbody id="modules-body"></tbody>
                    </table>
                </div>
            </section>

            <section class="card">
                <h2>Parts projektu</h2>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr><th>module_id</th><th>part_type</th><th>length</th><th>width</th><th>thickness</th></tr>
                        </thead>
                        <tbody id="parts-body"></tbody>
                    </table>
                </div>
            </section>
        </div>

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
            const manualSideToFloor = document.getElementById("manual_side_to_floor");
            const manualBottomRailMode = document.getElementById("manual_bottom_rail_mode");
            const sideFloorHint = document.getElementById("side-floor-hint");
            const backTypeSelect = document.getElementById("back_type");
            const backTypeDescription = document.getElementById("back-type-description");
            const backThicknessInput = document.getElementById("back_thickness");
            const manualModules = [];

            function clearResult() {
                resultJson.textContent = "";
                errorBox.textContent = "";
                modulesBody.innerHTML = "";
                partsBody.innerHTML = "";
            }

            function basePayload() {
                return {
                    project_name: document.getElementById("project_name").value,
                    width: Number(document.getElementById("width").value),
                    height: Number(document.getElementById("height").value),
                    depth: Number(document.getElementById("depth").value),
                    base_height: Number(document.getElementById("base_height").value),
                    leg_height: Number(document.getElementById("leg_height").value),
                    board_thickness: Number(document.getElementById("board_thickness").value),
                    back_thickness: Number(backThicknessInput.value),
                    back_type: backTypeSelect.value,
                    back_groove_offset: Number(document.getElementById("back_groove_offset").value),
                    back_groove_insert: Number(document.getElementById("back_groove_insert").value)
                };
            }

            function updateBackTypeDescription() {
                const descriptions = {
                    overlay: "Plecy nakładane – korpus zostanie pomniejszony o grubość pleców, żeby całkowita głębokość nie wzrosła.",
                    groove: "Plecy wpuszczane w kanalik wymuszają grubość 3 mm. Boki zostają pełnej głębokości, a wieńce są cofnięte o grubość pleców + cofnięcie kanalika.",
                    between: "Plecy między bokami – plecy są liczone między bokami, bez zwiększania głębokości."
                };
                backTypeDescription.textContent = descriptions[backTypeSelect.value] || "";
                if (backTypeSelect.value === "groove") {
                    backThicknessInput.value = "3";
                    backThicknessInput.disabled = true;
                } else {
                    backThicknessInput.disabled = false;
                }
            }

            function updateFloorHint() {
                const sideToFloor = manualSideToFloor.value;
                const forceBottomBetweenSides = sideToFloor === "both";
                sideFloorHint.style.display = forceBottomBetweenSides ? "block" : "none";
                if (forceBottomBetweenSides) {
                    manualBottomRailMode.value = "bottom_between_sides";
                    manualBottomRailMode.disabled = true;
                } else {
                    manualBottomRailMode.disabled = false;
                }
            }

            function updateManualSummary() {
                const projectWidth = Number(projectWidthInput.value) || 0;
                const totalManualWidth = manualModules.reduce((acc, module) => acc + module.width, 0);
                const diff = projectWidth - totalManualWidth;
                manualWidthSum.textContent = `Suma modułów: ${totalManualWidth} mm`;
                projectWidthInfo.textContent = `Szerokość projektu: ${projectWidth} mm`;
                manualWidthDiff.textContent = `Różnica: ${diff} mm`;
                if (totalManualWidth === projectWidth) {
                    manualWidthStatus.textContent = "Suma modułów zgadza się z szerokością projektu";
                    manualWidthStatus.classList.add("status-ok");
                    manualWidthStatus.classList.remove("status-error");
                } else {
                    manualWidthStatus.textContent = "Suma modułów nie zgadza się z szerokością projektu";
                    manualWidthStatus.classList.add("status-error");
                    manualWidthStatus.classList.remove("status-ok");
                }
            }

            function renderManualModules() {
                manualModulesBody.innerHTML = "";
                manualModules.forEach((module, index) => {
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${index + 1}</td><td>${module.width}</td><td>${module.cabinet_type}</td><td>${module.position}</td><td>${module.content}</td>
                        <td>${module.has_legs ? "Tak" : "Nie"}</td><td>${module.side_to_floor}</td><td>${module.bottom_rail_mode}</td><td>${module.top_mode}</td><td>${module.front_type}</td><td>${module.front_count}</td>
                        <td><button class="btn-danger" type="button" data-index="${index}">Usuń</button></td>
                    `;
                    row.querySelector("button").addEventListener("click", () => {
                        manualModules.splice(index, 1);
                        renderManualModules();
                        updateManualSummary();
                    });
                    manualModulesBody.appendChild(row);
                });
            }

            function renderParts(parts) {
                partsBody.innerHTML = "";
                for (const part of parts) {
                    const row = document.createElement("tr");
                    row.innerHTML = `<td>${part.module_id}</td><td>${part.part_type}</td><td>${part.length}</td><td>${part.width}</td><td>${part.thickness}</td>`;
                    partsBody.appendChild(row);
                }
            }

            function renderModules(modules) {
                modulesBody.innerHTML = "";
                for (const module of modules) {
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${module.module_id}</td><td>${module.module_type}</td><td>${module.width}</td><td>${module.height}</td><td>${module.depth}</td><td>${module.position}</td><td>${module.content}</td>
                        <td>${module.has_legs ? "Tak" : "Nie"}</td><td>${module.side_to_floor}</td><td>${module.bottom_rail_mode}</td><td>${module.top_mode}</td><td>${module.front_type}</td><td>${module.front_count}</td>
                    `;
                    modulesBody.appendChild(row);
                }
            }

            async function sendProject(useManualModules) {
                clearResult();
                try {
                    const payload = basePayload();
                    if (useManualModules) payload.manual_modules = manualModules;
                    const response = await fetch("/projects/from-manual", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify(payload)
                    });
                    const data = await response.json();
                    if (!response.ok) throw new Error(data.detail || "Wystąpił błąd");
                    resultJson.textContent = JSON.stringify(data, null, 2);
                    renderModules(data.project?.modules || []);
                    renderParts(data.project?.parts || []);
                } catch (error) {
                    errorBox.textContent = error.message;
                }
            }

            function addManualModule() {
                const width = Number(document.getElementById("manual_width").value);
                if (!Number.isInteger(width) || width <= 0) {
                    errorBox.textContent = "Szerokość modułu musi być dodatnią liczbą całkowitą";
                    return;
                }
                const frontCount = Number(document.getElementById("manual_front_count").value);
                if (!Number.isInteger(frontCount) || frontCount < 0) {
                    errorBox.textContent = "front_count musi być liczbą całkowitą >= 0";
                    return;
                }

                const sideToFloor = manualSideToFloor.value;
                const bottomRailMode = sideToFloor === "both" ? "bottom_between_sides" : manualBottomRailMode.value;

                errorBox.textContent = "";
                manualModules.push({
                    width,
                    cabinet_type: document.getElementById("manual_cabinet_type").value,
                    position: document.getElementById("manual_position").value,
                    content: document.getElementById("manual_content").value,
                    has_legs: document.getElementById("manual_has_legs").value === "true",
                    side_to_floor: sideToFloor,
                    bottom_rail_mode: bottomRailMode,
                    top_mode: document.getElementById("manual_top_mode").value,
                    front_type: document.getElementById("manual_front_type").value,
                    front_count: frontCount
                });
                renderManualModules();
                updateManualSummary();
            }

            document.getElementById("auto-btn").addEventListener("click", () => sendProject(false));
            document.getElementById("manual-btn").addEventListener("click", () => sendProject(true));
            document.getElementById("add-module-btn").addEventListener("click", addManualModule);
            document.getElementById("clear-modules-btn").addEventListener("click", () => {
                manualModules.length = 0;
                renderManualModules();
                updateManualSummary();
            });
            projectWidthInput.addEventListener("input", updateManualSummary);
            manualSideToFloor.addEventListener("change", updateFloorHint);
            backTypeSelect.addEventListener("change", updateBackTypeDescription);
            document.getElementById("clear-btn").addEventListener("click", () => {
                form.reset();
                manualModules.length = 0;
                renderManualModules();
                updateManualSummary();
                clearResult();
                updateFloorHint();
                updateBackTypeDescription();
            });
            updateManualSummary();
            updateFloorHint();
            updateBackTypeDescription();
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
            body {{ font-family: Arial, sans-serif; margin: 24px; }}
            .canvas {{ display: flex; align-items: flex-end; gap: 8px; border: 1px solid #ddd; padding: 12px; overflow-x: auto; }}
            .module {{ display: flex; flex-direction: column; justify-content: center; align-items: center; border: 1px solid #333; box-sizing: border-box; color: #111; font-size: 14px; flex: 0 0 auto; }}
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
    warnings: list[str] = []
    effective_back_thickness = payload.back_thickness
    if payload.back_type == "groove" and payload.back_thickness != 3:
        effective_back_thickness = 3
        warnings.append("Back thickness forced to 3 mm for groove back type")

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
            has_legs, side_to_floor, bottom_rail_mode, legacy_base_construction = _normalize_module_config(module)
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
                has_legs=has_legs,
                side_to_floor=side_to_floor,
                base_construction=legacy_base_construction,
                bottom_rail_mode=bottom_rail_mode,
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
                        back_thickness=effective_back_thickness,
                        back_type=payload.back_type,
                        back_groove_offset=payload.back_groove_offset,
                        back_groove_insert=payload.back_groove_insert,
                        base_height=payload.base_height,
                        leg_height=payload.leg_height,
                        warnings=warnings,
                    )
                )
            else:
                _append_part(
                    parts,
                    response_module.module_id,
                    "side_left",
                    response_module.height,
                    response_module.depth,
                    payload.board_thickness,
                )
                _append_part(
                    parts,
                    response_module.module_id,
                    "side_right",
                    response_module.height,
                    response_module.depth,
                    payload.board_thickness,
                )
                _append_part(
                    parts,
                    response_module.module_id,
                    "bottom",
                    response_module.width,
                    response_module.depth,
                    payload.board_thickness,
                )
                _append_part(
                    parts,
                    response_module.module_id,
                    "top",
                    response_module.width,
                    response_module.depth,
                    payload.board_thickness,
                )
                if payload.back_type == "groove":
                    groove_back_width = response_module.width - (2 * payload.board_thickness) + (2 * payload.back_groove_insert)
                    if groove_back_width <= 0:
                        raise HTTPException(status_code=400, detail="Invalid groove back width")
                    _append_part(
                        parts,
                        response_module.module_id,
                        "back",
                        response_module.height,
                        groove_back_width,
                        effective_back_thickness,
                    )
                else:
                    _append_part(
                        parts,
                        response_module.module_id,
                        "back",
                        response_module.height,
                        response_module.width,
                        effective_back_thickness,
                    )

    project = ProjectResponse(
        project_name=payload.project_name,
        width=payload.width,
        height=payload.height,
        depth=payload.depth,
        base_height=payload.base_height,
        leg_height=payload.leg_height,
        board_thickness=payload.board_thickness,
        back_thickness=effective_back_thickness,
        back_type=payload.back_type,
        back_groove_offset=payload.back_groove_offset,
        back_groove_insert=payload.back_groove_insert,
        module_source=module_source,
        warnings=warnings,
        modules=modules,
        parts=parts,
    )
    return ManualProjectResponse(status="ok", project=project)
