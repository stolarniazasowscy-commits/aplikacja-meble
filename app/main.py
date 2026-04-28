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
    base_height: int = Field(default=820, gt=0)
    leg_height: int = Field(default=100, ge=0)
    board_thickness: int = Field(default=18, gt=0)
    back_thickness: int = Field(default=3, gt=0)
    back_type: BackType = "overlay"
    back_groove_offset: int = Field(default=10, ge=0)
    back_groove_insert: int = Field(default=10, ge=0)


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
    base_height: int = Field(gt=0)
    leg_height: int = Field(ge=0)
    board_thickness: int = Field(gt=0)
    back_thickness: int = Field(gt=0)
    back_type: BackType
    back_groove_offset: int = Field(ge=0)
    back_groove_insert: int = Field(ge=0)


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


def generate_modules(
    width: int,
    height: int,
    depth: int,
    base_height: int,
    leg_height: int,
    board_thickness: int,
    back_thickness: int,
    back_type: BackType,
    back_groove_offset: int,
    back_groove_insert: int,
) -> list[ModuleResponse]:
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
                base_height=base_height,
                leg_height=leg_height,
                board_thickness=board_thickness,
                back_thickness=back_thickness,
                back_type=back_type,
                back_groove_offset=back_groove_offset,
                back_groove_insert=back_groove_insert,
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


def _resolve_back_part_dimensions(
    module: ModuleResponse,
    board_thickness: int,
    back_thickness: int,
    back_type: BackType,
    back_groove_insert: int,
) -> tuple[int, int, int]:
    resolved_back_thickness = back_thickness

    if back_type == "overlay":
        back_width = module.width - 6
        back_length = module.height - 6
    elif back_type == "groove":
        resolved_back_thickness = 3
        back_width = module.width - (2 * board_thickness) + (2 * back_groove_insert)
        back_length = module.height - 6
    else:
        back_width = module.width - (2 * board_thickness)
        back_length = module.height

    if back_width <= 0 or back_length <= 0:
        raise HTTPException(status_code=400, detail="Invalid back dimensions after clearances")

    return back_length, back_width, resolved_back_thickness


def generate_base_parts(
    module: ModuleResponse,
    board_thickness: int,
    back_thickness: int,
    back_type: BackType,
    back_groove_offset: int,
    back_groove_insert: int,
    base_height: int,
    leg_height: int,
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

    back_length, back_width, resolved_back_thickness = _resolve_back_part_dimensions(
        module=module,
        board_thickness=board_thickness,
        back_thickness=back_thickness,
        back_type=back_type,
        back_groove_insert=back_groove_insert,
    )
    _append_part(
        parts,
        module.module_id,
        "back",
        length=back_length,
        width=back_width,
        thickness=resolved_back_thickness,
    )

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


def _effective_module_technology(module: ManualModuleInput, module_id: str, warnings: list[str]) -> dict[str, int | str]:
    effective_back_thickness = module.back_thickness
    if module.back_type == "groove" and module.back_thickness != 3:
        effective_back_thickness = 3
        warnings.append(f"Back thickness forced to 3 mm for groove back type in module {module_id}")

    return {
        "base_height": module.base_height,
        "leg_height": module.leg_height,
        "board_thickness": module.board_thickness,
        "back_thickness": effective_back_thickness,
        "back_type": module.back_type,
        "back_groove_offset": module.back_groove_offset,
        "back_groove_insert": module.back_groove_insert,
    }


def generate_parts_for_module(module: ModuleResponse) -> list[PartResponse]:
    if module.module_type == "base_cabinet":
        return generate_base_parts(
            module=module,
            board_thickness=module.board_thickness,
            back_thickness=module.back_thickness,
            back_type=module.back_type,
            back_groove_offset=module.back_groove_offset,
            back_groove_insert=module.back_groove_insert,
            base_height=module.base_height,
            leg_height=module.leg_height,
        )

    parts: list[PartResponse] = []
    _append_part(parts, module.module_id, "side_left", module.height, module.depth, module.board_thickness)
    _append_part(parts, module.module_id, "side_right", module.height, module.depth, module.board_thickness)
    _append_part(parts, module.module_id, "bottom", module.width, module.depth, module.board_thickness)
    _append_part(parts, module.module_id, "top", module.width, module.depth, module.board_thickness)
    back_length, back_width, resolved_back_thickness = _resolve_back_part_dimensions(
        module=module,
        board_thickness=module.board_thickness,
        back_thickness=module.back_thickness,
        back_type=module.back_type,
        back_groove_insert=module.back_groove_insert,
    )
    _append_part(parts, module.module_id, "back", back_length, back_width, resolved_back_thickness)
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
                    <h3>Dane ogólne projektu</h3>
                    <div class="form-grid">
                        <label>Nazwa projektu<input id="project_name" name="project_name" value="Projekt testowy" required /></label>
                        <label>Szerokość całkowita [mm]<input id="width" name="width" type="number" min="1" value="2600" required /></label>
                        <label>Wysokość całkowita [mm]<input id="height" name="height" type="number" min="1" value="2400" required /></label>
                        <label>Głębokość całkowita [mm]<input id="depth" name="depth" type="number" min="1" value="600" required /></label>
                        <label>Kształt zabudowy
                            <select id="layout_shape" name="layout_shape">
                                <option value="straight">Prosta</option>
                                <option value="l_shape">L-kształt</option>
                                <option value="u_shape">U-kształt</option>
                            </select>
                        </label>
                    </div>

                    <h3 style="margin-top:16px;">Parametry technologiczne</h3>
                    <div class="form-grid">
                        <label>Grubość płyty [mm]<input id="board_thickness" name="board_thickness" type="number" min="1" value="18" required /></label>
                        <label>Grubość pleców [mm]<input id="back_thickness" name="back_thickness" type="number" min="1" value="3" required /></label>
                        <label>Rodzaj pleców
                            <select id="back_type" name="back_type">
                                <option value="overlay">Nakładane</option>
                                <option value="groove">Wpuszczane w kanalik</option>
                                <option value="between">Między bokami</option>
                            </select>
                        </label>
                        <label>Cofnięcie kanalika od tyłu [mm]<input id="back_groove_offset" name="back_groove_offset" type="number" min="0" value="10" required /></label>
                        <label>Wpuszczenie pleców w kanalik [mm]<input id="back_groove_insert" name="back_groove_insert" type="number" min="0" value="10" required /></label>
                        <label>Wysokość szafki dolnej [mm]<input id="base_height" name="base_height" type="number" min="1" value="720" required /></label>
                        <label>Wysokość nóg [mm]<input id="leg_height" name="leg_height" type="number" min="0" value="100" required /></label>
                    </div>
                    <div id="back-type-description" class="hint" style="display:block;background:#eef2ff;border-color:#a5b4fc;color:#3730a3;"></div>
                    <div class="button-row">
                        <button class="btn-primary" type="button" id="auto-btn">Utwórz projekt automatycznie</button>
                        <button class="btn-secondary" type="button" id="manual-btn">Utwórz projekt ręcznie</button>
                    </div>
                </form>
            </section>

            <section class="card">
                <h2>Moduły ręczne</h2>
                <div class="form-grid">
                    <label>Szerokość modułu [mm]<input id="manual_width" type="number" min="1" value="300" /></label>
                    <label>Typ szafki
                        <select id="manual_cabinet_type">
                            <option value="base">Szafka dolna</option>
                            <option value="tall">Szafka wysoka</option>
                        </select>
                    </label>
                    <label>Pozycja
                        <select id="manual_position">
                            <option value="normal">Normalna</option>
                            <option value="end_left">Końcowa lewa</option>
                            <option value="end_right">Końcowa prawa</option>
                            <option value="corner_left">Narożna lewa</option>
                            <option value="corner_right">Narożna prawa</option>
                        </select>
                    </label>
                    <label>Zawartość
                        <select id="manual_content">
                            <option value="shelves">Półki</option>
                            <option value="drawers">Szuflady</option>
                            <option value="empty">Pusta</option>
                        </select>
                    </label>
                    <label>Nogi
                        <select id="manual_has_legs">
                            <option value="true">Tak</option>
                            <option value="false">Nie</option>
                        </select>
                    </label>
                    <label>Bok do podłogi
                        <select id="manual_side_to_floor">
                            <option value="none">Brak</option>
                            <option value="left">Lewy</option>
                            <option value="right">Prawy</option>
                            <option value="both">Oba</option>
                        </select>
                    </label>
                    <label>Wieniec dolny
                        <select id="manual_bottom_rail_mode">
                            <option value="sides_on_bottom">Boki stoją na wieńcu</option>
                            <option value="bottom_between_sides">Wieniec między bokami</option>
                        </select>
                    </label>
                    <label>Wieniec górny
                        <select id="manual_top_mode">
                            <option value="full_top_on_sides">Na bokach</option>
                            <option value="full_top_between_sides">Między bokami</option>
                            <option value="traverses">Trawersy</option>
                        </select>
                    </label>
                    <label>Front
                        <select id="manual_front_type">
                            <option value="none">Brak</option>
                            <option value="doors">Drzwiczki</option>
                            <option value="drawers">Szuflady</option>
                        </select>
                    </label>
                    <label>Ilość frontów<input id="manual_front_count" type="number" min="0" value="0" /></label>
                    <label>Wysokość szafki dolnej [mm]<input id="manual_base_height" type="number" min="1" value="820" /></label>
                    <label>Wysokość nóg [mm]<input id="manual_leg_height" type="number" min="0" value="100" /></label>
                    <label>Grubość płyty [mm]<input id="manual_board_thickness" type="number" min="1" value="18" /></label>
                    <label>Grubość pleców [mm]<input id="manual_back_thickness" type="number" min="1" value="3" /></label>
                    <label>Rodzaj pleców
                        <select id="manual_back_type">
                            <option value="overlay">Nakładane</option>
                            <option value="groove">Wpuszczane w kanalik</option>
                            <option value="between">Między bokami</option>
                        </select>
                    </label>
                    <label>Cofnięcie kanalika od tyłu [mm]<input id="manual_back_groove_offset" type="number" min="0" value="10" /></label>
                    <label>Wpuszczenie pleców w kanalik [mm]<input id="manual_back_groove_insert" type="number" min="0" value="10" /></label>
                </div>
                <div id="side-floor-hint" class="hint">Wieniec dolny jest wymuszony między bokami tylko wtedy, gdy oba boki schodzą do podłogi.</div>
                <div id="edit-mode-info" class="hint" style="display:none;background:#eff6ff;border-color:#93c5fd;color:#1d4ed8;"></div>
                <div class="button-row">
                    <button class="btn-primary" type="button" id="add-module-btn">Dodaj moduł</button>
                    <button class="btn-danger" type="button" id="clear-modules-btn">Wyczyść moduły</button>
                </div>
            </section>

            <section class="card">
                <h2>Podsumowanie szerokości</h2>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Numer</th><th>Typ</th><th>Szerokość</th><th>Wysokość</th><th>Wysokość nóg</th><th>Pozycja</th><th>Zawartość</th><th>Fronty</th><th>Nogi</th><th>Bok do podłogi</th><th>Wieniec dolny</th><th>Wieniec górny</th><th>Grubość płyty</th><th>Plecy</th><th>Akcje</th>
                            </tr>
                        </thead>
                        <tbody id="manual-modules-body"></tbody>
                    </table>
                </div>
                <div class="summary">
                    <div id="manual-width-sum">Suma modułów: 0 mm</div>
                    <div id="project-width-info">Szerokość projektu: 0 mm</div>
                    <div id="manual-width-diff">Różnica: 0 mm</div>
                    <div id="manual-width-status" class="status-error">Suma modułów NIE zgadza się z szerokością projektu</div>
                </div>
            </section>

            <section class="card">
                <h2>Wynik obliczeń (JSON)</h2>
                <div id="error"></div>
                <pre id="result-json"></pre>
            </section>

            <section class="card">
                <h2>Moduły projektu</h2>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Numer</th><th>Typ</th><th>Szerokość</th><th>Wysokość</th><th>Wysokość nóg</th><th>Pozycja</th><th>Zawartość</th><th>Fronty</th><th>Plecy</th>
                            </tr>
                        </thead>
                        <tbody id="modules-body"></tbody>
                    </table>
                </div>
            </section>

            <section class="card">
                <h2>Tabela elementów</h2>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr><th>Moduł</th><th>Element</th><th>Długość</th><th>Szerokość</th><th>Grubość</th></tr>
                        </thead>
                        <tbody id="parts-body"></tbody>
                    </table>
                </div>
            </section>
        </div>

        <script>
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
            const manualCabinetType = document.getElementById("manual_cabinet_type");
            const addModuleBtn = document.getElementById("add-module-btn");
            const editModeInfo = document.getElementById("edit-mode-info");
            const sideFloorHint = document.getElementById("side-floor-hint");
            const backTypeSelect = document.getElementById("back_type");
            const backTypeDescription = document.getElementById("back-type-description");
            const backThicknessInput = document.getElementById("back_thickness");
            const manualBackTypeSelect = document.getElementById("manual_back_type");
            const manualBackThicknessInput = document.getElementById("manual_back_thickness");
            const manualModules = [];
            let editingModuleIndex = null;
            const cabinetTypeLabels = { base: "Dolna", tall: "Wysoka" };
            const positionLabels = {
                normal: "Normalna",
                end_left: "Końcowa lewa",
                end_right: "Końcowa prawa",
                corner_left: "Narożna lewa",
                corner_right: "Narożna prawa"
            };
            const contentLabels = { shelves: "Półki", drawers: "Szuflady", empty: "Pusta" };
            const sideToFloorLabels = { none: "Brak", left: "Lewy", right: "Prawy", both: "Oba" };
            const bottomRailLabels = { sides_on_bottom: "Boki stoją na wieńcu", bottom_between_sides: "Wieniec między bokami" };
            const topModeLabels = { full_top_on_sides: "Na bokach", full_top_between_sides: "Między bokami", traverses: "Trawersy" };
            const frontTypeLabels = { none: "Brak", doors: "Drzwiczki", drawers: "Szuflady" };
            const backTypeLabels = { overlay: "Nakładane", groove: "Wpuszczane w kanalik", between: "Między bokami" };
            const partTypeLabels = {
                side_left: "Bok lewy",
                side_right: "Bok prawy",
                bottom: "Wieniec dolny",
                top: "Wieniec górny",
                traverse_front: "Trawers przedni",
                traverse_back: "Trawers tylny",
                back: "Plecy",
                door_front: "Front drzwiowy",
                drawer_front: "Front szuflady"
            };

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
                    layout_shape: document.getElementById("layout_shape").value,
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
                    overlay: "Plecy nakładane – wymiar pleców pomniejszony o 6 mm z szerokości i 6 mm z wysokości.",
                    groove: "Plecy wpuszczane w kanalik – grubość wymuszona 3 mm, szerokość według wpuszczenia w kanalik, wysokość pomniejszona o 6 mm.",
                    between: "Plecy między bokami – liczone między bokami."
                };
                backTypeDescription.textContent = descriptions[backTypeSelect.value] || "";
                if (backTypeSelect.value === "groove") {
                    backThicknessInput.value = "3";
                    backThicknessInput.disabled = true;
                } else {
                    backThicknessInput.disabled = false;
                }
            }

            function updateManualBackTypeState() {
                if (manualBackTypeSelect.value === "groove") {
                    manualBackThicknessInput.value = "3";
                    manualBackThicknessInput.disabled = true;
                } else {
                    manualBackThicknessInput.disabled = false;
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
                    manualWidthStatus.textContent = "Suma modułów NIE zgadza się z szerokością projektu";
                    manualWidthStatus.classList.add("status-error");
                    manualWidthStatus.classList.remove("status-ok");
                }
            }

            function renderManualModules() {
                manualModulesBody.innerHTML = "";
                manualModules.forEach((module, index) => {
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${index + 1}</td>
                        <td>${cabinetTypeLabels[module.cabinet_type] || module.cabinet_type}</td>
                        <td>${module.width}</td>
                        <td>${module.base_height}</td>
                        <td>${module.leg_height}</td>
                        <td>${positionLabels[module.position] || module.position}</td>
                        <td>${contentLabels[module.content] || module.content}</td>
                        <td>${frontTypeLabels[module.front_type] || module.front_type} (${module.front_count})</td>
                        <td>${module.has_legs ? "Tak" : "Nie"}</td>
                        <td>${sideToFloorLabels[module.side_to_floor] || module.side_to_floor}</td>
                        <td>${bottomRailLabels[module.bottom_rail_mode] || module.bottom_rail_mode}</td>
                        <td>${topModeLabels[module.top_mode] || module.top_mode}</td>
                        <td>${module.board_thickness}</td>
                        <td>${backTypeLabels[module.back_type] || module.back_type} (${module.back_thickness} mm)</td>
                        <td>
                            <button class="btn-secondary" type="button" data-action="edit" data-index="${index}">Edytuj</button>
                            <button class="btn-primary" type="button" data-action="copy" data-index="${index}">Kopiuj</button>
                            <button class="btn-danger" type="button" data-action="delete" data-index="${index}">Usuń</button>
                        </td>
                    `;
                    row.querySelectorAll("button").forEach((button) => {
                        button.addEventListener("click", () => {
                            const action = button.dataset.action;
                            if (action === "edit") {
                                loadModuleIntoForm(index);
                                return;
                            }
                            if (action === "copy") {
                                manualModules.push({ ...module });
                                renderManualModules();
                                updateManualSummary();
                                return;
                            }
                            if (editingModuleIndex === index) {
                                resetEditMode();
                            } else if (editingModuleIndex !== null && index < editingModuleIndex) {
                                editingModuleIndex -= 1;
                                updateEditModeInfo();
                            }
                            manualModules.splice(index, 1);
                            renderManualModules();
                            updateManualSummary();
                        });
                    });
                    manualModulesBody.appendChild(row);
                });
            }

            function renderParts(parts) {
                partsBody.innerHTML = "";
                for (const part of parts) {
                    const row = document.createElement("tr");
                    row.innerHTML = `<td>${part.module_id}</td><td>${partTypeLabels[part.part_type] || part.part_type}</td><td>${part.length}</td><td>${part.width}</td><td>${part.thickness}</td>`;
                    partsBody.appendChild(row);
                }
            }

            function renderModules(modules) {
                modulesBody.innerHTML = "";
                for (const module of modules) {
                    const moduleTypeLabel = module.module_type === "base_cabinet"
                        ? cabinetTypeLabels.base
                        : module.module_type === "tall_cabinet"
                            ? cabinetTypeLabels.tall
                            : module.module_type;
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${module.module_id}</td>
                        <td>${moduleTypeLabel}</td>
                        <td>${module.width}</td>
                        <td>${module.height}</td>
                        <td>${module.leg_height}</td>
                        <td>${positionLabels[module.position] || module.position}</td>
                        <td>${contentLabels[module.content] || module.content}</td>
                        <td>${frontTypeLabels[module.front_type] || module.front_type} (${module.front_count})</td>
                        <td>${backTypeLabels[module.back_type] || module.back_type} (${module.back_thickness} mm)</td>
                    `;
                    modulesBody.appendChild(row);
                }
            }

            async function sendProject(useManualModules) {
                clearResult();
                try {
                    const payload = useManualModules
                        ? {
                            project_name: document.getElementById("project_name").value,
                            width: Number(document.getElementById("width").value),
                            height: Number(document.getElementById("height").value),
                            depth: Number(document.getElementById("depth").value),
                            layout_shape: document.getElementById("layout_shape").value,
                            manual_modules: manualModules
                        }
                        : basePayload();
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

            function getManualModuleFromForm() {
                const width = Number(document.getElementById("manual_width").value);
                if (!Number.isInteger(width) || width <= 0) {
                    errorBox.textContent = "Szerokość modułu musi być dodatnią liczbą całkowitą";
                    return null;
                }
                const frontCount = Number(document.getElementById("manual_front_count").value);
                if (!Number.isInteger(frontCount) || frontCount < 0) {
                    errorBox.textContent = "Ilość frontów musi być liczbą całkowitą >= 0";
                    return null;
                }
                const baseHeight = Number(document.getElementById("manual_base_height").value);
                const legHeight = Number(document.getElementById("manual_leg_height").value);
                const boardThickness = Number(document.getElementById("manual_board_thickness").value);
                const backThickness = Number(manualBackThicknessInput.value);
                const backGrooveOffset = Number(document.getElementById("manual_back_groove_offset").value);
                const backGrooveInsert = Number(document.getElementById("manual_back_groove_insert").value);
                if (!Number.isInteger(baseHeight) || baseHeight <= 0) {
                    errorBox.textContent = "Wysokość szafki dolnej musi być liczbą całkowitą > 0";
                    return null;
                }
                if (!Number.isInteger(legHeight) || legHeight < 0) {
                    errorBox.textContent = "Wysokość nóg musi być liczbą całkowitą >= 0";
                    return null;
                }
                if (!Number.isInteger(boardThickness) || boardThickness <= 0) {
                    errorBox.textContent = "Grubość płyty musi być liczbą całkowitą > 0";
                    return null;
                }
                if (!Number.isInteger(backThickness) || backThickness <= 0) {
                    errorBox.textContent = "Grubość pleców musi być liczbą całkowitą > 0";
                    return null;
                }
                if (!Number.isInteger(backGrooveOffset) || backGrooveOffset < 0) {
                    errorBox.textContent = "Cofnięcie kanalika musi być liczbą całkowitą >= 0";
                    return null;
                }
                if (!Number.isInteger(backGrooveInsert) || backGrooveInsert < 0) {
                    errorBox.textContent = "Wpuszczenie pleców musi być liczbą całkowitą >= 0";
                    return null;
                }

                const sideToFloor = manualSideToFloor.value;
                const bottomRailMode = sideToFloor === "both" ? "bottom_between_sides" : manualBottomRailMode.value;

                errorBox.textContent = "";
                return {
                    width,
                    cabinet_type: manualCabinetType.value,
                    position: document.getElementById("manual_position").value,
                    content: document.getElementById("manual_content").value,
                    has_legs: document.getElementById("manual_has_legs").value === "true",
                    side_to_floor: sideToFloor,
                    bottom_rail_mode: bottomRailMode,
                    top_mode: document.getElementById("manual_top_mode").value,
                    front_type: document.getElementById("manual_front_type").value,
                    front_count: frontCount,
                    base_height: baseHeight,
                    leg_height: legHeight,
                    board_thickness: boardThickness,
                    back_thickness: backThickness,
                    back_type: manualBackTypeSelect.value,
                    back_groove_offset: backGrooveOffset,
                    back_groove_insert: backGrooveInsert
                };
            }

            function fillManualForm(module) {
                document.getElementById("manual_width").value = module.width;
                manualCabinetType.value = module.cabinet_type;
                document.getElementById("manual_position").value = module.position;
                document.getElementById("manual_content").value = module.content;
                document.getElementById("manual_has_legs").value = String(module.has_legs);
                manualSideToFloor.value = module.side_to_floor;
                manualBottomRailMode.value = module.bottom_rail_mode;
                document.getElementById("manual_top_mode").value = module.top_mode;
                document.getElementById("manual_front_type").value = module.front_type;
                document.getElementById("manual_front_count").value = module.front_count;
                document.getElementById("manual_base_height").value = module.base_height;
                document.getElementById("manual_leg_height").value = module.leg_height;
                document.getElementById("manual_board_thickness").value = module.board_thickness;
                manualBackThicknessInput.value = module.back_thickness;
                manualBackTypeSelect.value = module.back_type;
                document.getElementById("manual_back_groove_offset").value = module.back_groove_offset;
                document.getElementById("manual_back_groove_insert").value = module.back_groove_insert;
                updateFloorHint();
                updateManualBackTypeState();
            }

            function updateEditModeInfo() {
                if (editingModuleIndex === null) {
                    editModeInfo.style.display = "none";
                    editModeInfo.textContent = "";
                    addModuleBtn.textContent = "Dodaj moduł";
                    manualCabinetType.disabled = false;
                    return;
                }
                addModuleBtn.textContent = "Zapisz zmiany";
                manualCabinetType.disabled = true;
                editModeInfo.style.display = "block";
                editModeInfo.textContent = `Edytujesz moduł nr ${editingModuleIndex + 1}`;
            }

            function loadModuleIntoForm(index) {
                editingModuleIndex = index;
                fillManualForm(manualModules[index]);
                updateEditModeInfo();
            }

            function resetEditMode() {
                editingModuleIndex = null;
                updateEditModeInfo();
            }

            function addOrUpdateManualModule() {
                const moduleData = getManualModuleFromForm();
                if (!moduleData) {
                    return;
                }
                if (editingModuleIndex !== null) {
                    moduleData.cabinet_type = manualModules[editingModuleIndex].cabinet_type;
                    manualModules[editingModuleIndex] = moduleData;
                    resetEditMode();
                } else {
                    manualModules.push(moduleData);
                }
                renderManualModules();
                updateManualSummary();
            }

            document.getElementById("auto-btn").addEventListener("click", () => sendProject(false));
            document.getElementById("manual-btn").addEventListener("click", () => sendProject(true));
            addModuleBtn.addEventListener("click", addOrUpdateManualModule);
            document.getElementById("clear-modules-btn").addEventListener("click", () => {
                manualModules.length = 0;
                resetEditMode();
                renderManualModules();
                updateManualSummary();
            });
            projectWidthInput.addEventListener("input", updateManualSummary);
            manualSideToFloor.addEventListener("change", updateFloorHint);
            backTypeSelect.addEventListener("change", updateBackTypeDescription);
            manualBackTypeSelect.addEventListener("change", updateManualBackTypeState);
            updateManualSummary();
            updateFloorHint();
            updateBackTypeDescription();
            updateManualBackTypeState();
            updateEditModeInfo();
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
        modules = generate_modules(
            payload.width,
            payload.height,
            payload.depth,
            payload.base_height,
            payload.leg_height,
            payload.board_thickness,
            effective_back_thickness,
            payload.back_type,
            payload.back_groove_offset,
            payload.back_groove_insert,
        )
        parts: list[PartResponse] = []
    else:
        if sum(module.width for module in payload.manual_modules) != payload.width:
            raise HTTPException(status_code=400, detail=MANUAL_WIDTH_SUM_ERROR)

        module_source = "manual"
        modules = []
        parts = []
        for idx, module in enumerate(payload.manual_modules, start=1):
            module_id = f"M{idx}"
            effective_tech = _effective_module_technology(module, module_id, warnings)
            has_legs, side_to_floor, bottom_rail_mode, legacy_base_construction = _normalize_module_config(module)
            module_type = "base_cabinet" if module.cabinet_type == "base" else "tall_cabinet"
            module_height = int(effective_tech["base_height"]) if module.cabinet_type == "base" else payload.height
            response_module = ModuleResponse(
                module_id=module_id,
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
                base_height=int(effective_tech["base_height"]),
                leg_height=int(effective_tech["leg_height"]),
                board_thickness=int(effective_tech["board_thickness"]),
                back_thickness=int(effective_tech["back_thickness"]),
                back_type=effective_tech["back_type"],
                back_groove_offset=int(effective_tech["back_groove_offset"]),
                back_groove_insert=int(effective_tech["back_groove_insert"]),
            )
            modules.append(response_module)
            parts.extend(generate_parts_for_module(response_module))

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
