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

        self.root_folder = ''
        self.csv_mode = tk.StringVar()
        self.csv_mode.set('group_list')

        self.csv_files = []
        self.merged_project_data = []
        self.merged_counter = Counter()
        self.cnc_records = []
        self.cnc_dimensions_by_base = {}
        self.scan_records = []
        self.report_rows = []
        self.csv_item_meta = {}

        self._build_ui()
        self.update_live_comparison()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill='both', expand=True)

        csv_frame = ttk.LabelFrame(main, text='CSV projektu', padding=8)
        csv_frame.pack(fill='x', pady=4)

        ttk.Button(csv_frame, text='Dodaj CSV projektu', command=self.on_add_csv).grid(row=0, column=0, sticky='w')
        ttk.Button(csv_frame, text='Usuń zaznaczony CSV', command=self.on_remove_selected_csv).grid(row=0, column=1, sticky='w', padx=6)
        ttk.Button(csv_frame, text='Wyczyść listy CSV', command=self.on_clear_csv_list).grid(row=0, column=2, sticky='w')

        self.csv_listbox = tk.Listbox(csv_frame, height=4)
        self.csv_listbox.grid(row=1, column=0, columnspan=3, sticky='we', pady=4)

        ttk.Label(csv_frame, text='Tryb CSV').grid(row=2, column=0, sticky='w', pady=4)
        mode = ttk.Combobox(csv_frame, textvariable=self.csv_mode, state='readonly', width=24)
        mode['values'] = ('group_list', 'program_list')
        mode.grid(row=2, column=1, sticky='w')
        mode.bind('<<ComboboxSelected>>', lambda event: self.on_csv_mode_changed())

        self.csv_stats = ttk.Label(csv_frame, text='Pliki CSV: 0 | Pozycje CSV (scalone): 0')
        self.csv_stats.grid(row=3, column=0, columnspan=3, sticky='w', pady=4)

        root_frame = ttk.LabelFrame(main, text='Folder główny projektu', padding=8)
        root_frame.pack(fill='x', pady=4)

        ttk.Button(root_frame, text='Wybierz folder główny projektu', command=self.on_select_root_folder).grid(row=0, column=0, sticky='w')
        self.root_label = ttk.Label(root_frame, text='Brak folderu')
        self.root_label.grid(row=0, column=1, sticky='w', padx=8)

        self.root_stats = ttk.Label(root_frame, text='Pliki .TCN: 0 | Grupy A_: 0 | Lista: -')
        self.root_stats.grid(row=1, column=0, columnspan=2, sticky='w', pady=4)

        scan_frame = ttk.LabelFrame(main, text='Skanowanie', padding=8)
        scan_frame.pack(fill='both', pady=4)

        ttk.Label(scan_frame, text='Kod QR').grid(row=0, column=0, sticky='w')
        self.scan_entry = ttk.Entry(scan_frame, width=80)
        self.scan_entry.grid(row=0, column=1, sticky='we', padx=6)
        ttk.Button(scan_frame, text='Dodaj skan', command=self.on_add_scan).grid(row=0, column=2, sticky='w')
        ttk.Button(scan_frame, text='Usuń zaznaczony skan', command=self.on_remove_selected_scan).grid(row=1, column=2, sticky='w')
        ttk.Button(scan_frame, text='Wyczyść skany', command=self.on_clear_scans).grid(row=2, column=2, sticky='w', pady=4)

        self.scan_preview = ttk.Label(scan_frame, text='Oryginalny kod: - | group_id: - | program_name: - | compare_id: -')
        self.scan_preview.grid(row=1, column=0, columnspan=2, sticky='w', pady=4)

        self.auto_info = ttk.Label(scan_frame, text='Program porównuje skany automatycznie po każdym skanie.')
        self.auto_info.grid(row=2, column=0, columnspan=2, sticky='w')

        self.scan_list = tk.Listbox(scan_frame, height=6)
        self.scan_list.grid(row=3, column=0, columnspan=3, sticky='nsew', pady=4)

        summary = ttk.LabelFrame(main, text='Podsumowanie', padding=8)
        summary.pack(fill='x', pady=4)
        self.summary_label = ttk.Label(summary, text='CSV: 0 | CNC: 0 | Skany: 0 | OK: 0 | Problemy: 0')
        self.summary_label.pack(anchor='w')

        live_frame = ttk.LabelFrame(main, text='Bieżąca kontrola CNC', padding=8)
        live_frame.pack(fill='both', expand=True, pady=4)

        cols = ('scan', 'cnc', 'csv', 'qty', 'csv_length', 'tcn_length', 'csv_width', 'tcn_width', 'csv_thickness', 'tcn_thickness', 'edge', 'dim_status', 'status', 'note')
        self.live_tree = ttk.Treeview(live_frame, columns=cols, show='headings', height=10)
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
        self.live_tree.column('scan', width=240)
        self.live_tree.column('cnc', width=90, anchor='center')
        self.live_tree.column('csv', width=130, anchor='center')
        self.live_tree.column('qty', width=90, anchor='center')
        self.live_tree.column('csv_length', width=70, anchor='center')
        self.live_tree.column('tcn_length', width=70, anchor='center')
        self.live_tree.column('csv_width', width=70, anchor='center')
        self.live_tree.column('tcn_width', width=70, anchor='center')
        self.live_tree.column('csv_thickness', width=70, anchor='center')
        self.live_tree.column('tcn_thickness', width=70, anchor='center')
        self.live_tree.column('edge', width=120)
        self.live_tree.column('dim_status', width=180)
        self.live_tree.column('status', width=150)
        self.live_tree.column('note', width=260)
        self.live_tree.pack(fill='both', expand=True)

        self.live_tree.tag_configure('ok', background='#c9f7c9')
        self.live_tree.tag_configure('bad', background='#f7c9c9')
        self.live_tree.tag_configure('warn', background='#fff6b3')
        self.live_tree.tag_configure('missing', background='#ffd8a8')

        report_frame = ttk.LabelFrame(main, text='Raporty', padding=8)
        report_frame.pack(fill='both', expand=True, pady=4)

        btn_row = ttk.Frame(report_frame)
        btn_row.pack(fill='x')
        ttk.Button(btn_row, text='Odśwież porównanie', command=self.on_generate_report).pack(side='left')
        ttk.Button(btn_row, text='Eksportuj raport ręcznie', command=self.on_export_report_csv).pack(side='left', padx=8)

        self.report_text = tk.Text(report_frame, height=10)
        self.report_text.pack(fill='both', expand=True, pady=4)

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
        self.cnc_dimensions_by_base = {}
        if not self.root_folder:
            self.root_stats.config(text='Pliki .TCN: 0 | Grupy A_: 0 | Lista: -')
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
                self.cnc_dimensions_by_base[program_base_name] = dims
                self.cnc_records.append({'group_id': group_id, 'program_name': filename, 'program_base_name': program_base_name, 'compare_id': compare_id, 'tcn_length': self.round_mm(dims.get('length')), 'tcn_width': self.round_mm(dims.get('width')), 'tcn_thickness': self.round_mm(dims.get('thickness')), 'tcn_parse_status': dims.get('parse_status'), 'tcn_dimension_source_line': dims.get('source_line', '')})
        groups = sorted(set([r['group_id'] for r in self.cnc_records if r['group_id']]))
        self.root_stats.config(text='Pliki .TCN: {0} | Grupy A_: {1} | Lista: {2}'.format(len(self.cnc_records), len(groups), ', '.join(groups) if groups else '-'))

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
        self.csv_stats.config(text='Pliki CSV: {0} | Pozycje CSV (scalone): {1}'.format(len(self.csv_files), len(self.merged_project_data)))

    def build_live_rows(self):
        rows = []
        scans_by_csv_item_key = Counter([s.get('csv_item_key', '') for s in self.scan_records if s.get('csv_item_key')])
        for rec in self.scan_records:
            cid = rec.get('compare_id', '')
            pname = rec.get('program_name', '')
            gid = rec.get('group_id', '')
            pbase = rec.get('program_base_name', '')
            csv_item_key = rec.get('csv_item_key', '')
            scan_label = pbase or cid or gid or pname

            exists_in_cnc = False
            if pbase:
                exists_in_cnc = any([x for x in self.cnc_records if x.get('program_base_name', '') == pbase])

            exists_in_csv = ('item', csv_item_key) in self.merged_counter
            expected = self.merged_counter.get(('item', csv_item_key), 0)
            scanned_count = scans_by_csv_item_key.get(csv_item_key, 0) if csv_item_key else 0
            meta = self.csv_item_meta.get(csv_item_key, {})

            status = 'OK'
            note = 'Skan istnieje w CNC i CSV'
            dim_status = 'BRAK WYMIARÓW TCN'
            dim_note = 'Brak wymiarów w TCN'
            tcn_data = self.cnc_dimensions_by_base.get(pbase, {})
            tcn_length_raw = tcn_data.get('length')
            tcn_width_raw = tcn_data.get('width')
            tcn_thickness_raw = tcn_data.get('thickness')
            tcn_length = self.round_mm(tcn_length_raw)
            tcn_width = self.round_mm(tcn_width_raw)
            tcn_thickness = self.round_mm(tcn_thickness_raw)
            tcn_parse_status = tcn_data.get('parse_status', 'ERROR')
            tcn_source_line = tcn_data.get('source_line', '')
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
                'note': (meta.get('note', '') + ' | ' + note + ' | ' + dim_note + ' | TCN line: {0} | CSV key: {1}'.format(tcn_source_line, csv_item_key)).strip(' |'),
                'scan_label': scan_label
            })
        return rows

    def update_live_comparison(self):
        self.report_rows = self.build_live_rows()
        for item in self.live_tree.get_children():
            self.live_tree.delete(item)
        ok_count = 0
        for row in self.report_rows:
            status = row['status']
            dim_status = row.get('dim_status', '')
            tag = 'ok'
            if dim_status == 'UWAGA GRUBOŚĆ':
                tag = 'warn'
            elif status in ('DUPLIKAT',):
                tag = 'warn'
            elif status in ('BRAKUJE',):
                tag = 'missing'
            elif status in ('BRAK PROGRAMU CNC', 'BRAK W CSV', 'NIEZNANY', 'ZA DUŻO'):
                tag = 'bad'
            else:
                ok_count += 1
            self.live_tree.insert('', 'end', values=(row['scan_label'], row.get('program_name', ''), row.get('item_code', ''), row.get('quantity', 0), row.get('csv_length', ''), row.get('tcn_length', ''), row.get('csv_width', ''), row.get('tcn_width', ''), row.get('csv_thickness', ''), row.get('tcn_thickness', ''), row.get('edge_info', ''), row.get('dim_status', ''), row['status'], row['note']), tags=(tag,))

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
        fields = ['item_code', 'group_id', 'quantity', 'csv_length', 'tcn_length', 'csv_width', 'tcn_width', 'csv_thickness', 'tcn_thickness', 'tcn_parse_status', 'dimension_status', 'dimension_note', 'edge_info', 'exists_in_cnc', 'scanned_count', 'status', 'note']
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
            self.csv_listbox.insert('end', path)
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
            self.root_label.config(text=path)
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
        self.scan_list.insert('end', '{0} | {1}'.format(parsed.get('group_id', '-') or '-', parsed.get('program_name', '-') or '-'))
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
