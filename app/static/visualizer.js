(function () {
    const MM_TO_PX_SCALE = 0.15;
    const MIN_WIDTH_PX = 40;
    const SVG_NS = 'http://www.w3.org/2000/svg';

    const cabinetTypeLabels = {
        base: 'Dolna zwykła',
        base_standard: 'Dolna zwykła',
        base_sink: 'Dolna pod zlew',
        base_oven: 'Dolna pod piekarnik',
        tall: 'Wysoka'
    };

    const backTypeLabels = {
        overlay: 'nakładane',
        groove: 'kanalik',
        between: 'między bokami'
    };

    function moduleClassByType(cabinetType) {
        if (cabinetType === 'base_sink') return 'visualizer-module--sink';
        if (cabinetType === 'base_oven') return 'visualizer-module--oven';
        if (cabinetType === 'tall') return 'visualizer-module--tall';
        return 'visualizer-module--base';
    }

    function moduleHeightPx(cabinetType) {
        if (cabinetType === 'tall') return 220;
        return 120;
    }

    function createLegendItem(label, cls) {
        const item = document.createElement('div');
        item.className = 'visualizer-legend-item';
        const swatch = document.createElement('span');
        swatch.className = `visualizer-legend-swatch ${cls}`;
        const text = document.createElement('span');
        text.textContent = label;
        item.appendChild(swatch);
        item.appendChild(text);
        return item;
    }

    function createSvg(width, height) {
        const svg = document.createElementNS(SVG_NS, 'svg');
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', String(height));
        svg.classList.add('module-preview-svg');
        return svg;
    }

    function svgRect(svg, x, y, width, height, className) {
        const el = document.createElementNS(SVG_NS, 'rect');
        el.setAttribute('x', String(x));
        el.setAttribute('y', String(y));
        el.setAttribute('width', String(width));
        el.setAttribute('height', String(height));
        if (className) el.setAttribute('class', className);
        svg.appendChild(el);
        return el;
    }

    function svgLine(svg, x1, y1, x2, y2, className) {
        const el = document.createElementNS(SVG_NS, 'line');
        el.setAttribute('x1', String(x1));
        el.setAttribute('y1', String(y1));
        el.setAttribute('x2', String(x2));
        el.setAttribute('y2', String(y2));
        if (className) el.setAttribute('class', className);
        svg.appendChild(el);
        return el;
    }

    function svgText(svg, x, y, text, className) {
        const el = document.createElementNS(SVG_NS, 'text');
        el.setAttribute('x', String(x));
        el.setAttribute('y', String(y));
        if (className) el.setAttribute('class', className);
        el.textContent = text;
        svg.appendChild(el);
        return el;
    }

    function getNumberValue(id, fallback) {
        const input = document.getElementById(id);
        if (!input) return fallback;
        const value = Number(input.value);
        return Number.isFinite(value) && value > 0 ? value : fallback;
    }

    function getSelectValue(id, fallback) {
        const input = document.getElementById(id);
        if (!input) return fallback;
        return input.value || fallback;
    }

    function getCurrentModuleConfig() {
        const sideToFloor = getSelectValue('manual_side_to_floor', 'none');
        const bottomRailMode = sideToFloor === 'both'
            ? 'bottom_between_sides'
            : getSelectValue('manual_bottom_rail_mode', 'sides_on_bottom');

        return {
            width: getNumberValue('manual_width', 300),
            cabinet_type: getSelectValue('manual_cabinet_type', 'base_standard'),
            base_height: getNumberValue('manual_base_height', 820),
            leg_height: getNumberValue('manual_leg_height', 100),
            depth: getNumberValue('depth', 600),
            board_thickness: getNumberValue('manual_board_thickness', 18),
            back_thickness: getNumberValue('manual_back_thickness', 3),
            back_type: getSelectValue('manual_back_type', 'overlay'),
            has_legs: getSelectValue('manual_has_legs', 'true') === 'true',
            side_to_floor: sideToFloor,
            bottom_rail_mode: bottomRailMode,
            top_mode: getSelectValue('manual_top_mode', 'full_top_on_sides'),
            content: getSelectValue('manual_content', 'shelves'),
            front_type: getSelectValue('manual_front_type', 'none'),
            front_count: Math.max(0, Math.floor(getNumberValue('manual_front_count', 0)))
        };
    }

    function drawFrontView(config) {
        const svg = createSvg(320, 220);
        const x = 36;
        const y = 20;
        const width = 248;
        const bodyHeight = 168;
        const legZone = config.has_legs ? 22 : 0;
        const t = Math.max(8, Math.min(16, Math.round(config.board_thickness * 0.5)));

        svgRect(svg, x, y, width, bodyHeight, 'mp-outline');

        const leftToFloor = config.side_to_floor === 'left' || config.side_to_floor === 'both';
        const rightToFloor = config.side_to_floor === 'right' || config.side_to_floor === 'both';
        const sideHeight = bodyHeight + legZone;

        svgRect(svg, x, y, t, leftToFloor ? sideHeight : bodyHeight, 'mp-board');
        svgRect(svg, x + width - t, y, t, rightToFloor ? sideHeight : bodyHeight, 'mp-board');

        const bottomY = config.bottom_rail_mode === 'bottom_between_sides' ? y + bodyHeight - t : y + bodyHeight;
        const bottomX = config.bottom_rail_mode === 'bottom_between_sides' ? x + t : x;
        const bottomW = config.bottom_rail_mode === 'bottom_between_sides' ? width - (2 * t) : width;
        svgRect(svg, bottomX, bottomY, bottomW, t, 'mp-board');

        if (config.top_mode === 'traverses') {
            svgRect(svg, x + t, y + 6, 42, 10, 'mp-inner');
            svgRect(svg, x + width - t - 42, y + 6, 42, 10, 'mp-inner');
        } else {
            const topX = config.top_mode === 'full_top_between_sides' ? x + t : x;
            const topW = config.top_mode === 'full_top_between_sides' ? width - (2 * t) : width;
            svgRect(svg, topX, y, topW, t, 'mp-board');
        }

        if (config.content === 'shelves') {
            const innerX = x + t;
            const innerW = width - (2 * t);
            svgRect(svg, innerX, y + 54, innerW, 8, 'mp-inner');
            svgRect(svg, innerX, y + 100, innerW, 8, 'mp-inner');
        }

        if (config.content === 'drawers') {
            const innerX = x + t;
            const innerW = width - (2 * t);
            svgLine(svg, innerX, y + 54, innerX + innerW, y + 54, 'mp-line');
            svgLine(svg, innerX, y + 95, innerX + innerW, y + 95, 'mp-line');
            svgLine(svg, innerX, y + 136, innerX + innerW, y + 136, 'mp-line');
        }

        if (config.front_type === 'doors' || config.front_type === 'drawers') {
            const frontCount = Math.max(1, config.front_count || 1);
            const frontX = x + 6;
            const frontY = y + 6;
            const frontW = width - 12;
            const frontH = bodyHeight - 12;
            if (config.front_type === 'doors') {
                for (let i = 1; i < frontCount; i += 1) {
                    const cx = frontX + (frontW / frontCount) * i;
                    svgLine(svg, cx, frontY, cx, frontY + frontH, 'mp-line');
                }
            } else {
                for (let i = 1; i < frontCount; i += 1) {
                    const cy = frontY + (frontH / frontCount) * i;
                    svgLine(svg, frontX, cy, frontX + frontW, cy, 'mp-line');
                }
            }
            svgRect(svg, frontX, frontY, frontW, frontH, 'mp-front');
        }

        if (config.has_legs) {
            const legY = y + bodyHeight;
            const legHeight = 18;
            const legW = 12;
            svgRect(svg, x + 14, legY, legW, legHeight, 'mp-legs');
            svgRect(svg, x + width - 14 - legW, legY, legW, legHeight, 'mp-legs');
        }

        return svg;
    }

    function drawTopView(config) {
        const svg = createSvg(320, 220);
        const x = 40;
        const y = 46;
        const width = 240;
        const depth = 120;
        const t = Math.max(7, Math.min(14, Math.round(config.board_thickness * 0.45)));
        const backT = Math.max(2, Math.min(8, Math.round(config.back_thickness * 0.45)));

        svgRect(svg, x, y, width, depth, 'mp-outline');
        svgRect(svg, x, y, t, depth, 'mp-board');
        svgRect(svg, x + width - t, y, t, depth, 'mp-board');

        if (config.back_type === 'overlay') {
            svgRect(svg, x, y + depth + 2, width, backT, 'mp-back');
            svgText(svg, x, y + depth + 24, 'plecy nakładane', 'mp-caption');
        } else if (config.back_type === 'groove') {
            const grooveOffset = 12;
            const grooveY = y + depth - grooveOffset;
            svgRect(svg, x + t - 2, grooveY - 4, 4, 10, 'mp-groove');
            svgRect(svg, x + width - t - 2, grooveY - 4, 4, 10, 'mp-groove');
            svgRect(svg, x + t, grooveY, width - (2 * t), 3, 'mp-back');
            svgText(svg, x, y + depth + 24, 'plecy w kanaliku', 'mp-caption');
        } else {
            svgRect(svg, x + t, y + depth - backT - 2, width - (2 * t), backT, 'mp-back');
            svgText(svg, x, y + depth + 24, 'plecy między bokami', 'mp-caption');
        }

        return svg;
    }

    function drawSideView(config) {
        const svg = createSvg(320, 220);
        const x = 50;
        const y = 20;
        const depth = 210;
        const bodyHeight = 168;
        const legZone = config.has_legs ? 22 : 0;
        const t = Math.max(8, Math.min(16, Math.round(config.board_thickness * 0.5)));
        const backT = Math.max(2, Math.min(8, Math.round(config.back_thickness * 0.45)));

        svgRect(svg, x, y, depth, bodyHeight + legZone, 'mp-outline');

        const sideHeight = config.side_to_floor === 'left' || config.side_to_floor === 'both'
            ? bodyHeight + legZone
            : bodyHeight;
        svgRect(svg, x, y, depth - (depth - t), sideHeight, 'mp-board');

        if (config.bottom_rail_mode === 'bottom_between_sides') {
            svgRect(svg, x + t, y + bodyHeight - t, depth - t - 6, t, 'mp-board');
        } else {
            svgRect(svg, x, y + bodyHeight, depth - 6, t, 'mp-board');
        }

        if (config.top_mode === 'traverses') {
            svgRect(svg, x + 16, y + 6, 38, 10, 'mp-inner');
            svgRect(svg, x + depth - 62, y + 6, 38, 10, 'mp-inner');
        } else if (config.top_mode === 'full_top_between_sides') {
            svgRect(svg, x + t, y, depth - t - 6, t, 'mp-board');
        } else {
            svgRect(svg, x, y, depth - 6, t, 'mp-board');
        }

        if (config.back_type === 'overlay') {
            svgRect(svg, x + depth - 4, y, backT, bodyHeight, 'mp-back');
        } else if (config.back_type === 'groove') {
            svgRect(svg, x + depth - 16, y + 2, 3, bodyHeight - 4, 'mp-back');
            svgRect(svg, x + depth - 20, y + 2, 4, bodyHeight - 4, 'mp-groove');
        } else {
            svgRect(svg, x + depth - backT - 8, y + 2, backT, bodyHeight - 4, 'mp-back');
        }

        if (config.has_legs) {
            svgRect(svg, x + 20, y + bodyHeight, 12, 18, 'mp-legs');
            svgRect(svg, x + depth - 34, y + bodyHeight, 12, 18, 'mp-legs');
        }

        return svg;
    }

    window.renderCurrentModulePreview = function renderCurrentModulePreview() {
        const container = document.getElementById('module-preview');
        const front = document.getElementById('module-front-view');
        const top = document.getElementById('module-top-view');
        const side = document.getElementById('module-side-view');
        if (!container || !front || !top || !side) return;

        const config = getCurrentModuleConfig();
        front.innerHTML = '';
        top.innerHTML = '';
        side.innerHTML = '';

        front.appendChild(drawFrontView(config));
        top.appendChild(drawTopView(config));
        side.appendChild(drawSideView(config));
    };

    window.renderCabinetPreview = function renderCabinetPreview(project) {
        const container = document.getElementById('cabinet-visualizer');
        if (!container) return;

        container.innerHTML = '';

        const modules = project?.project?.modules;
        if (!Array.isArray(modules) || modules.length === 0) {
            const empty = document.createElement('div');
            empty.className = 'visualizer-empty';
            empty.textContent = 'Brak danych do podglądu.';
            container.appendChild(empty);
            return;
        }

        const row = document.createElement('div');
        row.className = 'visualizer-row';

        modules.forEach((module, index) => {
            const cabinetType = module.cabinet_type || 'base_standard';
            const widthPx = Math.max(MIN_WIDTH_PX, Number(module.width || 0) * MM_TO_PX_SCALE);
            const box = document.createElement('div');
            box.className = `visualizer-module ${moduleClassByType(cabinetType)}`;
            box.style.width = `${widthPx}px`;
            box.style.height = `${moduleHeightPx(cabinetType)}px`;

            const moduleLabel = module.module_id || `M${index + 1}`;
            const typeLabel = cabinetTypeLabels[cabinetType] || cabinetType;
            const sizeText = `${module.width || '-'} x ${module.height || '-'}`;
            const frontsText = module.front_type && module.front_type !== 'none'
                ? `Fronty: ${module.front_type} (${module.front_count ?? 0})`
                : 'Fronty: brak';
            const backText = `Plecy: ${backTypeLabels[module.back_type] || 'brak'}`;

            box.innerHTML = `${moduleLabel}<br>${typeLabel}<br>${sizeText}<br>${frontsText}<br>${backText}`;
            row.appendChild(box);
        });

        const legend = document.createElement('div');
        legend.className = 'visualizer-legend';
        legend.appendChild(createLegendItem('Dolna zwykła', 'visualizer-module--base'));
        legend.appendChild(createLegendItem('Dolna pod zlew', 'visualizer-module--sink'));
        legend.appendChild(createLegendItem('Dolna pod piekarnik', 'visualizer-module--oven'));
        legend.appendChild(createLegendItem('Wysoka', 'visualizer-module--tall'));

        container.appendChild(row);
        container.appendChild(legend);
    };
})();
