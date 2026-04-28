(function () {
    const MM_TO_PX_SCALE = 0.15;
    const MIN_WIDTH_PX = 40;

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
