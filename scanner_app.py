# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import csv
import datetime
import re
from collections import Counter

try:
    import Tkinter as tk
    import tkFileDialog as filedialog
    import ttk
except ImportError:
    import tkinter as tk
    from tkinter import filedialog
    from tkinter import ttk


class ScannerApp(object):
    def __init__(self, root):
        self.root = root
        self.root.title('CNC QR Scanner')
        self.root.geometry('900x650')

        self.root_folder = ''
        self.csv_mode = tk.StringVar()
        self.csv_mode.set('group_list')

        self.csv_files = []
        self.merged_project_data = []
        self.merged_counter = Counter()
        self.cnc_records = []
        self.cnc_programs_by_compare_id = {}
        self.cnc_programs_by_name = {}
        self.scan_records = []
        self.report_rows = []
        self.csv_item_meta = {}

        self._build_ui()
        self.update_live_comparison()

    def _build_ui(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        main = ttk.Frame(self.root, padding=10)
        main.grid(row=0, column=0, sticky='nsew')
        main.grid_rowconfigure(4, weight=1)
        main.grid_columnconfigure(0, weight=1)

        sources_frame = ttk.LabelFrame(main, text='Źródła danych', padding=8)
        sources_frame.grid(row=0, column=0, sticky='ew', pady=4)
        sources_frame.grid_columnconfigure(6, weight=1)

        ttk.Button(sources_frame, text='Dodaj CSV projektu', command=self.on_add_csv).grid(row=0, column=0, sticky='w')
        ttk.Button(sources_frame, text='Usuń zaznaczony CSV', command=self.on_remove_selected_csv).grid(row=0, column=1, sticky='w', padx=4)
        ttk.Button(sources_frame, text='Wyczyść listy CSV', command=self.on_clear_csv_list).grid(row=0, column=2, sticky='w')
        ttk.Label(sources_frame, text='Tryb CSV').grid(row=0, column=3, sticky='e', padx=(8, 4))
        mode = ttk.Combobox(sources_frame, textvariable=self.csv_mode, state='readonly', width=18)
        mode['values'] = ('group_list', 'program_list')
        mode.grid(row=0, column=4, sticky='w')
        mode.bind('<<ComboboxSelected>>', lambda event: self.on_csv_mode_changed())
        ttk.Button(sources_frame, text='Wybierz folder główny projektu', command=self.on_select_root_folder).grid(row=0, column=5, sticky='w', padx=4)
        ttk.Button(sources_frame, text='Odśwież folder CNC', command=self.on_refresh_root_folder).grid(row=0, column=6, sticky='w', padx=4)

        self.csv_stats = ttk.Label(sources_frame, text='Pliki CSV: 0')
        self.csv_stats.grid(row=1, column=0, sticky='w', pady=(6, 0))
        self.csv_items_stats = ttk.Label(sources_frame, text='Pozycje CSV (scalone): 0')
        self.csv_items_stats.grid(row=1, column=1, columnspan=2, sticky='w', pady=(6, 0))
        self.root_label = ttk.Label(sources_frame, text='Folder główny: Brak folderu')
        self.root_label.grid(row=1, column=3, columnspan=2, sticky='w', pady=(6, 0))
        self.root_stats = ttk.Label(sources_frame, text='Pliki .TCN: 0 | Grupy A_: 0')
        self.root_stats.grid(row=1, column=5, columnspan=2, sticky='w', pady=(6, 0))

        csv_list_frame = ttk.LabelFrame(main, text='Lista plików CSV', padding=6)
        csv_list_frame.grid(row=1, column=0, sticky='ew', pady=4)
        csv_list_frame.grid_columnconfigure(0, weight=1)
        csv_list_frame.grid_rowconfigure(0, weight=1)
        self.csv_listbox = tk.Listbox(csv_list_frame, height=3)
        self.csv_listbox.grid(row=0, column=0, sticky='ew')
        csv_list_scroll = ttk.Scrollbar(csv_list_frame, orient='vertical', command=self.csv_listbox.yview)
        csv_list_scroll.grid(row=0, column=1, sticky='ns')
        self.csv_listbox.configure(yscrollcommand=csv_list_scroll.set)

        scan_frame = ttk.LabelFrame(main, text='Skanowanie', padding=8)
        scan_frame.grid(row=2, column=0, sticky='ew', pady=4)
        scan_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(scan_frame, text='Kod QR').grid(row=0, column=0, sticky='w')
        self.scan_entry = ttk.Entry(scan_frame)
        self.scan_entry.grid(row=0, column=1, sticky='ew', padx=6)
        ttk.Button(scan_frame, text='Dodaj skan', command=self.on_add_scan).grid(row=0, column=2, sticky='w')
        ttk.Button(scan_frame, text='Usuń zaznaczony skan', command=self.on_remove_selected_scan).grid(row=0, column=3, sticky='w', padx=4)
        ttk.Button(scan_frame, text='Wyczyść skany', command=self.on_clear_scans).grid(row=0, column=4, sticky='w')

        self.scan_preview = ttk.Label(scan_frame, text='Oryginalny kod: - | group_id: - | program_name: - | compare_id: -')
        self.scan_preview.grid(row=1, column=0, columnspan=5, sticky='w', pady=(6, 2))

        scan_list_frame = ttk.Frame(scan_frame)
        scan_list_frame.grid(row=2, column=0, columnspan=5, sticky='ew')
        scan_list_frame.grid_columnconfigure(0, weight=1)
        self.scan_list = tk.Listbox(scan_list_frame, height=4)
        self.scan_list.grid(row=0, column=0, sticky='ew')
        scan_scroll = ttk.Scrollbar(scan_list_frame, orient='vertical', command=self.scan_list.yview)
        scan_scroll.grid(row=0, column=1, sticky='ns')
        self.scan_list.configure(yscrollcommand=scan_scroll.set)

        summary = ttk.LabelFrame(main, text='Podsumowanie', padding=6)
        summary.grid(row=3, column=0, sticky='ew', pady=4)
        self.summary_label = ttk.Label(summary, text='CSV: 0 | CNC: 0 | Skany: 0 | OK: 0 | Problemy: 0')
        self.summary_label.grid(row=0, column=0, sticky='w')

        live_frame = ttk.LabelFrame(main, text='Bieżąca kontrola CNC', padding=8)
        live_frame.grid(row=4, column=0, sticky='nsew', pady=4)
        live_frame.grid_rowconfigure(0, weight=1)
        live_frame.grid_columnconfigure(0, weight=1)

        cols = ('nr', 'scan', 'cnc', 'csv', 'qty', 'csv_length', 'tcn_length', 'csv_width', 'tcn_width', 'csv_thickness', 'tcn_thickness', 'edge', 'dim_status', 'status', 'note')
        self.live_tree = ttk.Treeview(live_frame, columns=cols, show='headings', height=8)
        self.live_tree.heading('nr', text='Nr')
        self.live_tree.heading('scan', text='Skan')
        self.live_tree.heading('cnc', text='Program CNC')
        self.live_tree.heading('csv', text='Element z CSV')
        self.live_tree.heading('qty', text='Ilość z CSV')
        self.live_tree.heading('csv_length', text='CSV dł.')
        self.live_tree.heading('tcn_length', text='TCN dł.')
        self.live_tree.heading('csv_width', text='CSV szer.')
        self.live_tree.heading('tcn_width', text='TCN szer.')
        self.live_tree.heading('csv_thickness', text='CSV gr.')
        self.live_tree.heading('tcn_thickness', text='TCN gr.')
        self.live_tree.heading('edge', text='Obrzeże')
        self.live_tree.heading('dim_status', text='Kontrola wymiarów')
        self.live_tree.heading('status', text='Status')
        self.live_tree.heading('note', text='Uwagi')
        self.live_tree.column('nr', width=35, anchor='center', stretch=False)
        self.live_tree.column('scan', width=90, anchor='center', stretch=False)
        self.live_tree.column('cnc', width=70, anchor='center', stretch=False)
        self.live_tree.column('csv', width=70, anchor='center', stretch=False)
        self.live_tree.column('qty', width=50, anchor='center', stretch=False)
        self.live_tree.column('csv_length', width=55, anchor='center', stretch=False)
        self.live_tree.column('tcn_length', width=55, anchor='center', stretch=False)
        self.live_tree.column('csv_width', width=55, anchor='center', stretch=False)
        self.live_tree.column('tcn_width', width=55, anchor='center', stretch=False)
        self.live_tree.column('csv_thickness', width=50, anchor='center', stretch=False)
        self.live_tree.column('tcn_thickness', width=50, anchor='center', stretch=False)
        self.live_tree.column('edge', width=80, anchor='center', stretch=False)
        self.live_tree.column('dim_status', width=110, anchor='center', stretch=False)
        self.live_tree.column('status', width=90, anchor='center', stretch=False)
        self.live_tree.column('note', width=180, anchor='w', stretch=False)
        self.live_tree.grid(row=0, column=0, sticky='nsew')
        live_y = ttk.Scrollbar(live_frame, orient='vertical', command=self.live_tree.yview)
        live_y.grid(row=0, column=1, sticky='ns')
        live_x = ttk.Scrollbar(live_frame, orient='horizontal', command=self.live_tree.xview)
        live_x.grid(row=1, column=0, sticky='ew')
        self.live_tree.configure(yscrollcommand=live_y.set, xscrollcommand=live_x.set)

        self.live_tree.tag_configure('ok', background='#c9f7c9')
        self.live_tree.tag_configure('bad', background='#f7c9c9')
        self.live_tree.tag_configure('warn', background='#fff6b3')
        self.live_tree.tag_configure('missing', background='#ffd8a8')

        report_frame = ttk.LabelFrame(main, text='Raporty', padding=6)
        report_frame.grid(row=5, column=0, sticky='ew', pady=4)
        ttk.Button(report_frame, text='Odśwież porównanie', command=self.on_generate_report).grid(row=0, column=0, sticky='w')
        ttk.Button(report_frame, text='Eksportuj raport ręcznie', command=self.on_export_report_csv).grid(row=0, column=1, sticky='w', padx=6)
        self.report_text = tk.Text(report_frame, height=4)
        self.report_text.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(4, 0))
        report_scroll = ttk.Scrollbar(report_frame, orient='vertical', command=self.report_text.yview)
        report_scroll.grid(row=1, column=2, sticky='ns', pady=(4, 0))
        self.report_text.configure(yscrollcommand=report_scroll.set)

        csv_preview_frame = ttk.LabelFrame(main, text='Wczytana lista CSV', padding=6)
        csv_preview_frame.grid(row=6, column=0, sticky='ew', pady=4)
        csv_preview_frame.grid_columnconfigure(0, weight=1)
        csv_cols = ('nr', 'code', 'group', 'qty', 'length', 'width', 'thickness', 'edge')
        self.csv_tree = ttk.Treeview(csv_preview_frame, columns=csv_cols, show='headings', height=4)
        self.csv_tree.heading('nr', text='Nr')
        self.csv_tree.heading('code', text='Kod')
        self.csv_tree.heading('group', text='Grupa')
        self.csv_tree.heading('qty', text='Ilość')
        self.csv_tree.heading('length', text='Dł.')
        self.csv_tree.heading('width', text='Szer.')
        self.csv_tree.heading('thickness', text='Gr.')
        self.csv_tree.heading('edge', text='Obrzeże')
        self.csv_tree.column('nr', width=35, anchor='center', stretch=False)
        self.csv_tree.column('code', width=90, anchor='center', stretch=False)
        self.csv_tree.column('group', width=70, anchor='center', stretch=False)
        self.csv_tree.column('qty', width=50, anchor='center', stretch=False)
        self.csv_tree.column('length', width=55, anchor='center', stretch=False)
        self.csv_tree.column('width', width=55, anchor='center', stretch=False)
        self.csv_tree.column('thickness', width=50, anchor='center', stretch=False)
        self.csv_tree.column('edge', width=90, anchor='center', stretch=False)
        self.csv_tree.grid(row=0, column=0, sticky='ew')
        csv_preview_scroll = ttk.Scrollbar(csv_preview_frame, orient='vertical', command=self.csv_tree.yview)
        csv_preview_scroll.grid(row=0, column=1, sticky='ns')
        self.csv_tree.configure(yscrollcommand=csv_preview_scroll.set)

        self.scan_entry.bind('<Return>', lambda event: self.on_add_scan())
        self.root.after(200, lambda: self.focus_scan_entry(False))

    def focus_scan_entry(self, clear=False):
        if clear:
            self.scan_entry.delete(0, tk.END)
        self.scan_entry.focus_set()

    def normalize_path(self, value):
        if value is None:
            return ''
        return value.strip().strip('"').replace('/', '\\')

    def normalize_item_code(self, value):
        code = (value or '').strip().strip('\"').upper()
        if code.endswith('.TCN'):
            code = code[:-4]
        return code.strip()

    def build_csv_item_key(self, group_id, program_name):
        clean_group_id = (group_id or '').strip().upper()
        program_base_name = self.normalize_item_code(program_name)
        if not clean_group_id:
            return program_base_name
        prefix = clean_group_id + ' '
        if program_base_name.startswith(prefix):
            return program_base_name
        if program_base_name == clean_group_id:
            return clean_group_id
        if program_base_name:
            return clean_group_id + ' ' + program_base_name
        return clean_group_id

    def parse_int(self, value, default_value):
        try:
            return int((value or '').strip())
        except Exception:
            return default_value


    def parse_float(self, value):
        try:
            return float(str(value).strip().replace(',', '.'))
        except Exception:
            return None

    def round_mm(self, value):
        if value is None:
            return None
        return int(round(value))

    def format_number(self, value):
        if value in (None, ''):
            return ''
        try:
            return str(int(round(float(value))))
        except Exception:
            return ''

    def short_text(self, value, max_len):
        text = '' if value is None else str(value)
        if len(text) <= max_len:
            return text
        return text[:max_len - 3] + '...'

    def extract_tcn_dimensions(self, file_path):
        result = {
            'length': None,
            'width': None,
            'thickness': None,
            'source': '',
            'parse_status': 'NO_DIMENSIONS',
            'source_line': ''
        }
        lines = []
        for enc in ('utf-8', 'latin-1'):
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    for idx, line in enumerate(f):
                        if idx >= 200:
                            break
                        lines.append(line)
                break
            except Exception:
                lines = []
                continue

        if not lines:
            return result

        for line in lines:
            stripped = line.strip()
            if not stripped.startswith('::UNm'):
                continue
            result['source'] = 'UNm'
            result['source_line'] = stripped
            dl = re.search(r'DL=([0-9]+(?:\.[0-9]+)?)', stripped)
            dh = re.search(r'DH=([0-9]+(?:\.[0-9]+)?)', stripped)
            ds = re.search(r'DS=([0-9]+(?:\.[0-9]+)?)', stripped)
            if dl and dh and ds:
                result['length'] = int(round(float(dl.group(1))))
                result['width'] = int(round(float(dh.group(1))))
                result['thickness'] = int(round(float(ds.group(1))))
                result['parse_status'] = 'OK'
                return result
            result['parse_status'] = 'ERROR_UNM_PARSE'
            return result

        for line in lines:
            stripped = line.strip()
            if not stripped.startswith('::LF'):
                continue
            result['source'] = 'LF'
            result['source_line'] = stripped
            lf = re.search(r'LF=([0-9]+(?:\.[0-9]+)?)', stripped)
            hf = re.search(r'HF=([0-9]+(?:\.[0-9]+)?)', stripped)
            sf = re.search(r'SF=([0-9]+(?:\.[0-9]+)?)', stripped)
            if lf and hf and sf:
                result['length'] = int(round(float(lf.group(1))))
                result['width'] = int(round(float(hf.group(1))))
                result['thickness'] = int(round(float(sf.group(1))))
                result['parse_status'] = 'OK'
                return result

        return result

    def parse_scanned_path(self, original_code, root_folder):
        clean = self.normalize_path(original_code)
        tokens = [t for t in clean.split('\\') if t]
        program_name = tokens[-1] if tokens else ''
        program_base_name = self.normalize_item_code(program_name)
        group_id = ''
        for part in tokens:
            if part.upper().startswith('A_'):
                group_id = part
                break
        compare_id = group_id + '\\' + program_name if group_id else program_name
        csv_item_key = self.build_csv_item_key(group_id, program_name)
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'original_code': original_code,
            'group_id': group_id,
            'program_name': program_name,
            'program_base_name': program_base_name,
            'compare_id': compare_id,
            'csv_item_key': csv_item_key
        }

    def scan_cnc_folder(self):
        self.cnc_records = []
        self.cnc_programs_by_compare_id = {}
        self.cnc_programs_by_name = {}
        if not self.root_folder:
            self.root_stats.config(text='Pliki .TCN: 0 | Grupy A_: 0')
            return
        for base, _, files in os.walk(self.root_folder):
            for filename in files:
                if not filename.lower().endswith('.tcn'):
                    continue
                rel = os.path.relpath(os.path.join(base, filename), self.root_folder).replace('/', '\\')
                parts = [p for p in rel.split('\\') if p]
                group_id = ''
                for part in parts:
                    if part.upper().startswith('A_'):
                        group_id = part
                        break
                compare_id = group_id + '\\' + filename if group_id else filename
                file_path = os.path.join(base, filename)
                dims = self.extract_tcn_dimensions(file_path)
                program_base_name = self.normalize_item_code(filename)
                record = {
                    'full_path': file_path,
                    'relative_path': rel,
                    'group_id': group_id,
                    'program_name': filename,
                    'program_base_name': program_base_name,
                    'compare_id': compare_id,
                    'csv_item_key': self.build_csv_item_key(group_id, filename),
                    'tcn_length': self.round_mm(dims.get('length')),
                    'tcn_width': self.round_mm(dims.get('width')),
                    'tcn_thickness': self.round_mm(dims.get('thickness')),
                    'tcn_parse_status': dims.get('parse_status'),
                    'tcn_dimension_source_line': dims.get('source_line', '')
                }
                self.cnc_records.append(record)
                self.cnc_programs_by_compare_id[compare_id] = record
                if filename not in self.cnc_programs_by_name:
                    self.cnc_programs_by_name[filename] = []
                self.cnc_programs_by_name[filename].append(record)
        groups = sorted(set([r['group_id'] for r in self.cnc_records if r['group_id']]))
        self.root_stats.config(text='Pliki .TCN: {0} | Grupy A_: {1}'.format(len(self.cnc_records), len(groups)))

    def reload_all_csv(self):
        self.merged_counter = Counter()
        self.merged_project_data = []
        self.csv_item_meta = {}
        for item in self.csv_files:
            path = item['path']
            if not os.path.isfile(path):
                continue
            with open(path, 'r') as f:
                reader = csv.reader(f, delimiter=';')
                for row in reader:
                    if not row:
                        continue
                    if not ''.join(row).strip():
                        continue
                    group_id = self.normalize_item_code(row[1] if len(row) > 1 else '')
                    raw_item_code = row[0] if len(row) > 0 else ''
                    item_code = self.build_csv_item_key(group_id, raw_item_code)
                    if not item_code:
                        continue
                    quantity = self.parse_int(row[4] if len(row) > 4 else '', 1)
                    length = (row[5] if len(row) > 5 else '').strip()
                    width = (row[6] if len(row) > 6 else '').strip()
                    thickness = (row[7] if len(row) > 7 else '').strip()
                    edge_info = (row[8] if len(row) > 8 else '').strip()

                    self.merged_counter[('item', item_code)] += quantity
                    if item_code not in self.csv_item_meta:
                        self.csv_item_meta[item_code] = {
                            'item_code': item_code,
                            'group_id': group_id,
                            'length': length,
                            'width': width,
                            'thickness': thickness,
                            'edge_info': edge_info,
                            'note': ''
                        }
                    else:
                        meta = self.csv_item_meta[item_code]
                        if (meta.get('length', '') != length) or (meta.get('width', '') != width) or (meta.get('thickness', '') != thickness):
                            meta['note'] = 'Ten sam kod ma różne wymiary w CSV'
        for key, val in self.merged_counter.items():
            if key[0] == 'item':
                meta = self.csv_item_meta.get(key[1], {})
                self.merged_project_data.append({
                    'item_code': key[1],
                    'group_id': meta.get('group_id', ''),
                    'quantity': val,
                    'length': meta.get('length', ''),
                    'width': meta.get('width', ''),
                    'thickness': meta.get('thickness', ''),
                    'edge_info': meta.get('edge_info', ''),
                    'note': meta.get('note', '')
                })
        self.csv_stats.config(text='Pliki CSV: {0}'.format(len(self.csv_files)))
        self.csv_items_stats.config(text='Pozycje CSV (scalone): {0}'.format(len(self.merged_project_data)))
        for item in self.csv_tree.get_children():
            self.csv_tree.delete(item)
        for idx, row in enumerate(self.merged_project_data, 1):
            self.csv_tree.insert('', 'end', values=(
                idx,
                self.short_text(row.get('item_code', ''), 12),
                self.short_text(row.get('group_id', ''), 10),
                row.get('quantity', ''),
                self.format_number(row.get('length', '')),
                self.format_number(row.get('width', '')),
                self.format_number(row.get('thickness', '')),
                self.short_text(row.get('edge_info', ''), 12)
            ))

    def build_live_rows(self):
        rows = []
        scans_by_csv_item_key = Counter([s.get('csv_item_key', '') for s in self.scan_records if s.get('csv_item_key')])
        for rec in self.scan_records:
            cid = rec.get('compare_id', '')
            pname = rec.get('program_name', '')
            gid = rec.get('group_id', '')
            pbase = rec.get('program_base_name', '')
            csv_item_key = rec.get('csv_item_key', '')
            scan_label = csv_item_key or ((gid + ' ' + pbase).strip() if gid else pbase or pname)

            cnc_record = self.cnc_programs_by_compare_id.get(cid)
            cnc_lookup_status = 'COMPARE_ID'
            if not cnc_record:
                by_name = self.cnc_programs_by_name.get(pname, [])
                if len(by_name) == 1:
                    cnc_record = by_name[0]
                    cnc_lookup_status = 'PROGRAM_NAME_FALLBACK'
                elif len(by_name) > 1:
                    cnc_lookup_status = 'PROGRAM_NAME_AMBIGUOUS'
            exists_in_cnc = cnc_record is not None

            exists_in_csv = ('item', csv_item_key) in self.merged_counter
            expected = self.merged_counter.get(('item', csv_item_key), 0)
            scanned_count = scans_by_csv_item_key.get(csv_item_key, 0) if csv_item_key else 0
            meta = self.csv_item_meta.get(csv_item_key, {})

            status = 'OK'
            note = 'Skan istnieje w CNC i CSV'
            dim_status = 'BRAK WYMIARÓW TCN'
            dim_note = 'Brak wymiarów w TCN'
            tcn_length = cnc_record.get('tcn_length') if cnc_record else None
            tcn_width = cnc_record.get('tcn_width') if cnc_record else None
            tcn_thickness = cnc_record.get('tcn_thickness') if cnc_record else None
            tcn_parse_status = cnc_record.get('tcn_parse_status', 'ERROR') if cnc_record else 'ERROR'
            tcn_source_line = cnc_record.get('tcn_dimension_source_line', '') if cnc_record else ''
            tcn_path = cnc_record.get('full_path', '') if cnc_record else ''
            tol = 1

            csv_length = self.round_mm(self.parse_float(meta.get('length', '')))
            csv_width = self.round_mm(self.parse_float(meta.get('width', '')))
            csv_thickness = self.round_mm(self.parse_float(meta.get('thickness', '')))

            if tcn_parse_status == 'OK' and tcn_length is not None and tcn_width is not None and tcn_thickness is not None:
                length_bad = csv_length is None or abs(csv_length - tcn_length) > tol
                width_bad = csv_width is None or abs(csv_width - tcn_width) > tol
                thickness_bad = csv_thickness is None or csv_thickness != tcn_thickness
                if length_bad or width_bad:
                    dim_status = 'RÓŻNICA WYMIARÓW INFO'
                    if length_bad:
                        dim_note = 'Różnica długości > 1 mm'
                    else:
                        dim_note = 'Różnica szerokości > 1 mm'
                elif thickness_bad:
                    dim_status = 'UWAGA GRUBOŚĆ'
                    dim_note = 'Różnica grubości: CSV {0} / TCN {1}. UWAGA: grubość TCN różni się od CSV'.format(csv_thickness, tcn_thickness)
                else:
                    dim_status = 'WYMIARY OK'
                    dim_note = 'Długość/szerokość w tolerancji 1 mm'
            if not exists_in_cnc and not exists_in_csv:
                status = 'NIEZNANY'
                note = 'Skan nie występuje w CNC ani CSV'
            elif not exists_in_cnc:
                if cnc_lookup_status == 'PROGRAM_NAME_AMBIGUOUS':
                    status = 'NIEJEDNOZNACZNY PROGRAM CNC'
                    note = 'Program name występuje w wielu grupach, wymagany compare_id'
                else:
                    status = 'BRAK PROGRAMU CNC'
                    note = 'Skan nie ma programu w folderze CNC'
            elif not exists_in_csv:
                status = 'BRAK W CSV'
                note = 'Skan nie występuje w żadnym CSV'
            elif expected > 0 and scanned_count > expected:
                status = 'ZA DUŻO' if scanned_count > expected + 1 else 'DUPLIKAT'
                note = 'Zeskanowano więcej razy niż wymagane'

            rows.append({
                'timestamp': rec.get('timestamp', ''),
                'original_code': rec.get('original_code', ''),
                'group_id': gid,
                'program_name': pname,
                'compare_id': cid,
                'item_code': csv_item_key,
                'quantity': expected,
                'length': meta.get('length', ''),
                'width': meta.get('width', ''),
                'thickness': meta.get('thickness', ''),
                'csv_length': csv_length if csv_length is not None else '',
                'csv_width': csv_width if csv_width is not None else '',
                'csv_thickness': csv_thickness if csv_thickness is not None else '',
                'tcn_length': tcn_length,
                'tcn_width': tcn_width,
                'tcn_thickness': tcn_thickness,
                'tcn_parse_status': tcn_parse_status,
                'tcn_dimension_source_line': tcn_source_line,
                'dim_status': dim_status,
                'dimension_status': dim_status,
                'dimension_note': dim_note,
                'edge_info': meta.get('edge_info', ''),
                'exists_in_cnc': 'TAK' if exists_in_cnc else 'BRAK',
                'exists_in_csv': 'TAK' if exists_in_csv else 'BRAK',
                'scanned_count': scanned_count,
                'status': status,
                'note': (meta.get('note', '') + ' | ' + note + ' | ' + dim_note + ' | compare_id: {0} | TCN path: {1} | TCN line: {2} | CSV key: {3}'.format(cid, tcn_path, tcn_source_line, csv_item_key)).strip(' |'),
                'scan_label': scan_label
            })
        return rows

    def update_live_comparison(self):
        self.report_rows = self.build_live_rows()
        for item in self.live_tree.get_children():
            self.live_tree.delete(item)
        ok_count = 0
        for idx, row in enumerate(self.report_rows, 1):
            status = row['status']
            dim_status = row.get('dim_status', '')
            tag = 'ok'
            if dim_status == 'UWAGA GRUBOŚĆ':
                tag = 'warn'
            elif status in ('DUPLIKAT',):
                tag = 'warn'
            elif status in ('BRAKUJE',):
                tag = 'missing'
            elif status in ('BRAK PROGRAMU CNC', 'NIEJEDNOZNACZNY PROGRAM CNC', 'BRAK W CSV', 'NIEZNANY', 'ZA DUŻO'):
                tag = 'bad'
            else:
                ok_count += 1
            self.live_tree.insert('', 'end', values=(idx, self.short_text(row['scan_label'], 12), self.short_text(row.get('program_name', ''), 10), self.short_text(row.get('item_code', ''), 10), row.get('quantity', 0), self.format_number(row.get('csv_length', '')), self.format_number(row.get('tcn_length', '')), self.format_number(row.get('csv_width', '')), self.format_number(row.get('tcn_width', '')), self.format_number(row.get('csv_thickness', '')), self.format_number(row.get('tcn_thickness', '')), self.short_text(row.get('edge_info', ''), 12), row.get('dim_status', ''), self.short_text(row['status'], 14), self.short_text(row['note'], 40)), tags=(tag,))

        problem_count = len(self.report_rows) - ok_count
        self.summary_label.config(text='CSV: {0} | CNC: {1} | Skany: {2} | OK: {3} | Problemy: {4}'.format(len(self.merged_project_data), len(self.cnc_records), len(self.scan_records), ok_count, problem_count))

        missing_lines = []
        for item in self.merged_project_data:
            code = item.get('item_code', '')
            scanned = Counter([r.get('csv_item_key', '') for r in self.scan_records]).get(code, 0)
            if scanned < item.get('quantity', 0):
                missing_lines.append('{0}: BRAKUJE ({1}/{2})'.format(code, scanned, item.get('quantity', 0)))
        self.report_text.delete('1.0', 'end')
        self.report_text.insert('1.0', '\n'.join(missing_lines) if missing_lines else 'Brak pozycji BRAKUJE.')

    def sanitize_file_name(self, value):
        safe = value.replace(' ', '_')
        out = []
        for ch in safe:
            if ch.isalnum() or ch in ('_', '-'):
                out.append(ch)
        return ''.join(out) or 'raport_skanow'

    def auto_save_session_report(self):
        if not self.report_rows:
            self.update_live_comparison()
        now_txt = datetime.datetime.now().strftime('%Y%m%d_%H%M')
        if self.root_folder:
            base = self.sanitize_file_name(os.path.basename(self.root_folder))
            save_dir = self.root_folder
            name = '{0}_{1}.csv'.format(base, now_txt)
        else:
            save_dir = os.getcwd()
            name = 'raport_skanow_{0}.csv'.format(now_txt)
        path = os.path.join(save_dir, name)
        self.write_report_csv(path)
        self.report_text.delete('1.0', 'end')
        self.report_text.insert('1.0', 'Raport sesji zapisany: {0}'.format(path))

    def write_report_csv(self, save_path):
        fields = ['compare_id', 'program_name', 'item_code', 'group_id', 'quantity', 'csv_length', 'tcn_length', 'csv_width', 'tcn_width', 'csv_thickness', 'tcn_thickness', 'tcn_parse_status', 'dimension_status', 'dimension_note', 'edge_info', 'exists_in_cnc', 'scanned_count', 'status', 'note']
        with open(save_path, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in self.report_rows:
                writer.writerow({k: row.get(k, '') for k in fields})

    def on_add_csv(self):
        path = filedialog.askopenfilename(filetypes=[('CSV', '*.csv'), ('All files', '*.*')])
        if not path:
            self.focus_scan_entry(False)
            return
        if not any([x for x in self.csv_files if x['path'] == path]):
            self.csv_files.append({'name': os.path.basename(path), 'path': path})
            self.csv_listbox.insert('end', os.path.basename(path))
        self.reload_all_csv()
        self.update_live_comparison()
        self.focus_scan_entry(False)

    def on_remove_selected_csv(self):
        sel = self.csv_listbox.curselection()
        if not sel:
            self.focus_scan_entry(False)
            return
        idx = int(sel[0])
        self.csv_listbox.delete(idx)
        del self.csv_files[idx]
        self.reload_all_csv()
        self.update_live_comparison()
        self.focus_scan_entry(False)

    def on_clear_csv_list(self):
        self.csv_listbox.delete(0, 'end')
        self.csv_files = []
        self.reload_all_csv()
        self.update_live_comparison()
        self.focus_scan_entry(False)

    def on_csv_mode_changed(self):
        self.reload_all_csv()
        self.update_live_comparison()
        self.focus_scan_entry(False)

    def on_select_root_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.root_folder = path
            self.root_label.config(text='Folder główny: {0}'.format(path))
            self.scan_cnc_folder()
            self.update_live_comparison()
        self.focus_scan_entry(False)

    def on_refresh_root_folder(self):
        self.scan_cnc_folder()
        self.update_live_comparison()
        self.focus_scan_entry(False)

    def on_add_scan(self):
        code = self.scan_entry.get()
        if not code.strip():
            self.focus_scan_entry(True)
            return
        parsed = self.parse_scanned_path(code, self.root_folder)
        self.scan_records.append(parsed)
        scan_key = parsed.get('csv_item_key', '') or (((parsed.get('group_id', '') + ' ' + parsed.get('program_base_name', '')).strip()) if parsed.get('group_id', '') else parsed.get('program_base_name', ''))
        self.scan_list.insert('end', scan_key or '-')
        self.scan_preview.config(text='Oryginalny kod: {0} | group_id: {1} | program_name: {2} | compare_id: {3} | csv_item_key: {4}'.format(parsed.get('original_code', ''), parsed.get('group_id', ''), parsed.get('program_name', ''), parsed.get('compare_id', ''), parsed.get('csv_item_key', '')))
        self.update_live_comparison()
        self.focus_scan_entry(True)

    def on_remove_selected_scan(self):
        sel = self.scan_list.curselection()
        if sel:
            idx = int(sel[0])
            self.scan_list.delete(idx)
            del self.scan_records[idx]
            self.update_live_comparison()
        self.focus_scan_entry(False)

    def on_clear_scans(self):
        if self.scan_records:
            self.auto_save_session_report()
        self.scan_records = []
        self.scan_list.delete(0, 'end')
        self.update_live_comparison()
        self.focus_scan_entry(True)

    def on_generate_report(self):
        self.update_live_comparison()
        self.focus_scan_entry(False)

    def on_export_report_csv(self):
        self.update_live_comparison()
        save_path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV', '*.csv')])
        if save_path:
            self.write_report_csv(save_path)
        self.focus_scan_entry(False)


if __name__ == '__main__':
    root = tk.Tk()
    app = ScannerApp(root)
    root.mainloop()
