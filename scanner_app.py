# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import csv
import datetime
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

        self.csv_path = ''
        self.root_folder = ''
        self.csv_mode = tk.StringVar()
        self.csv_mode.set('group_list')

        self.csv_entries = []
        self.cnc_records = []
        self.scan_records = []
        self.report_rows = []

        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill='both', expand=True)

        # CSV section
        csv_frame = ttk.LabelFrame(main, text='CSV projektu', padding=8)
        csv_frame.pack(fill='x', pady=4)

        ttk.Button(csv_frame, text='Wybierz plik CSV', command=self.select_csv).grid(row=0, column=0, sticky='w')
        self.csv_label = ttk.Label(csv_frame, text='Brak pliku CSV')
        self.csv_label.grid(row=0, column=1, sticky='w', padx=8)

        ttk.Label(csv_frame, text='Tryb CSV').grid(row=1, column=0, sticky='w', pady=4)
        mode = ttk.Combobox(csv_frame, textvariable=self.csv_mode, state='readonly', width=32)
        mode['values'] = ('group_list', 'program_list')
        mode.grid(row=1, column=1, sticky='w')

        # root folder section
        root_frame = ttk.LabelFrame(main, text='Folder główny projektu', padding=8)
        root_frame.pack(fill='x', pady=4)

        ttk.Button(root_frame, text='Wybierz folder główny projektu', command=self.select_root_folder).grid(row=0, column=0, sticky='w')
        self.root_label = ttk.Label(root_frame, text='Brak folderu')
        self.root_label.grid(row=0, column=1, sticky='w', padx=8)

        self.root_stats = ttk.Label(root_frame, text='Pliki .TCN: 0 | Grupy A_: 0 | Lista: -')
        self.root_stats.grid(row=1, column=0, columnspan=2, sticky='w', pady=4)

        # scanning section
        scan_frame = ttk.LabelFrame(main, text='Skanowanie', padding=8)
        scan_frame.pack(fill='both', pady=4)

        ttk.Label(scan_frame, text='Kod QR').grid(row=0, column=0, sticky='w')
        self.scan_entry = ttk.Entry(scan_frame, width=80)
        self.scan_entry.grid(row=0, column=1, sticky='we', padx=6)
        ttk.Button(scan_frame, text='Dodaj skan', command=self.add_scan).grid(row=0, column=2, sticky='w')

        self.scan_preview = ttk.Label(scan_frame, text='Oryginalny kod: - | group_id: - | program_name: - | compare_id: -')
        self.scan_preview.grid(row=1, column=0, columnspan=3, sticky='w', pady=4)

        self.scan_list = tk.Listbox(scan_frame, height=8)
        self.scan_list.grid(row=2, column=0, columnspan=3, sticky='nsew')

        # reports
        report_frame = ttk.LabelFrame(main, text='Raporty', padding=8)
        report_frame.pack(fill='both', expand=True, pady=4)

        btn_row = ttk.Frame(report_frame)
        btn_row.pack(fill='x')
        ttk.Button(btn_row, text='Generuj raport', command=self.generate_report).pack(side='left')
        ttk.Button(btn_row, text='Eksportuj raport CSV', command=self.export_report_csv).pack(side='left', padx=8)

        self.report_text = tk.Text(report_frame, height=16)
        self.report_text.pack(fill='both', expand=True, pady=4)

    def select_csv(self):
        path = filedialog.askopenfilename(filetypes=[('CSV', '*.csv'), ('All files', '*.*')])
        if not path:
            return
        self.csv_path = path
        self.csv_label.config(text=path)
        self.load_csv_entries()

    def select_root_folder(self):
        path = filedialog.askdirectory()
        if not path:
            return
        self.root_folder = path
        self.root_label.config(text=path)
        self.scan_cnc_folder()

    def normalize_path(self, value):
        if value is None:
            return ''
        txt = value.strip().strip('"').replace('/', '\\')
        return txt

    def parse_scanned_path(self, original_code, root_folder):
        clean = self.normalize_path(original_code)
        tokens = [t for t in clean.split('\\') if t]
        program_name = ''
        group_id = ''
        if tokens:
            program_name = tokens[-1]
            for part in tokens:
                if part.upper().startswith('A_'):
                    group_id = part
                    break
        compare_id = program_name
        if group_id:
            compare_id = group_id + '\\' + program_name

        relative_path = ''
        if root_folder:
            root_norm = self.normalize_path(root_folder).lower()
            clean_low = clean.lower()
            if clean_low.startswith(root_norm):
                relative_path = clean[len(self.normalize_path(root_folder)):].lstrip('\\')

        return {
            'original_code': original_code,
            'normalized_path': clean,
            'relative_path': relative_path,
            'program_name': program_name,
            'group_id': group_id,
            'compare_id': compare_id
        }

    def scan_cnc_folder(self):
        self.cnc_records = []
        if not self.root_folder:
            return
        for base, _, files in os.walk(self.root_folder):
            for filename in files:
                if not filename.lower().endswith('.tcn'):
                    continue
                full_path = os.path.join(base, filename)
                relative_path = os.path.relpath(full_path, self.root_folder)
                rel_norm = relative_path.replace('/', '\\')
                parts = [p for p in rel_norm.split('\\') if p]
                group_id = ''
                for part in parts:
                    if part.upper().startswith('A_'):
                        group_id = part
                        break
                compare_id = filename
                if group_id:
                    compare_id = group_id + '\\' + filename
                self.cnc_records.append({
                    'full_path': full_path,
                    'relative_path': rel_norm,
                    'program_name': filename,
                    'group_id': group_id,
                    'compare_id': compare_id
                })
        groups = sorted(set([r['group_id'] for r in self.cnc_records if r['group_id']]))
        group_list = ', '.join(groups) if groups else '-'
        self.root_stats.config(text='Pliki .TCN: {0} | Grupy A_: {1} | Lista: {2}'.format(len(self.cnc_records), len(groups), group_list))

    def load_csv_entries(self):
        self.csv_entries = []
        if not self.csv_path:
            return
        with open(self.csv_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            return

        header = [h.strip().lower() for h in rows[0]]
        has_header = ('group_id' in header) or ('compare_id' in header) or ('program_name' in header)

        data_rows = rows[1:] if has_header else rows
        for row in data_rows:
            if not row:
                continue
            if self.csv_mode.get() == 'group_list':
                val = ''
                if has_header and 'group_id' in header:
                    val = row[header.index('group_id')] if header.index('group_id') < len(row) else ''
                else:
                    val = row[0]
                val = self.normalize_path(val)
                if val:
                    self.csv_entries.append({'group_id': val})
            else:
                compare_id = ''
                program_name = ''
                if has_header and 'compare_id' in header:
                    compare_id = self.normalize_path(row[header.index('compare_id')] if header.index('compare_id') < len(row) else '')
                if has_header and 'program_name' in header:
                    program_name = self.normalize_path(row[header.index('program_name')] if header.index('program_name') < len(row) else '')
                if not compare_id and row:
                    compare_id = self.normalize_path(row[0])
                if not program_name and compare_id and ('\\' not in compare_id):
                    program_name = compare_id
                if compare_id or program_name:
                    self.csv_entries.append({'compare_id': compare_id, 'program_name': program_name})

    def add_scan(self):
        code = self.scan_entry.get()
        if not code.strip():
            return
        parsed = self.parse_scanned_path(code, self.root_folder)
        parsed['timestamp'] = datetime.datetime.now().isoformat()
        self.scan_records.append(parsed)

        self.scan_list.insert('end', '{0} | {1}'.format(parsed['group_id'] or '-', parsed['program_name'] or '-'))
        self.scan_preview.config(
            text='Oryginalny kod: {0} | group_id: {1} | program_name: {2} | compare_id: {3}'.format(
                parsed['original_code'], parsed['group_id'], parsed['program_name'], parsed['compare_id'])
        )
        self.scan_entry.delete(0, 'end')

    def generate_report(self):
        self.load_csv_entries()
        self.scan_cnc_folder()
        self.report_rows = []
        lines = []

        cnc_by_group = Counter()
        cnc_by_compare = Counter()
        for rec in self.cnc_records:
            cnc_by_group[rec['group_id']] += 1
            cnc_by_compare[rec['compare_id']] += 1

        scans_by_group = Counter()
        scans_by_compare = Counter()
        scans_by_program = Counter()
        for rec in self.scan_records:
            scans_by_group[rec['group_id']] += 1
            scans_by_compare[rec['compare_id']] += 1
            scans_by_program[rec['program_name']] += 1

        if self.csv_mode.get() == 'group_list':
            csv_groups = sorted(set([x['group_id'] for x in self.csv_entries if x.get('group_id')]))

            lines.append('=== A. CSV grupy vs folder CNC ===')
            for gid in csv_groups:
                count = cnc_by_group.get(gid, 0)
                status = 'OK' if count > 0 else 'BRAK PROGRAMÓW CNC'
                lines.append('{0} | programy: {1} | {2}'.format(gid, count, status))
                self.report_rows.append({'report_type': 'csv_vs_cnc_group', 'group_id': gid, 'program_name': '', 'compare_id': '', 'expected_count': 1, 'actual_count': count, 'status': status, 'note': ''})

            for gid in sorted([g for g in cnc_by_group.keys() if g and g not in csv_groups]):
                lines.append('{0} | GRUPA W FOLDERZE CNC NIE MA W CSV'.format(gid))
                self.report_rows.append({'report_type': 'cnc_group_not_in_csv', 'group_id': gid, 'program_name': '', 'compare_id': '', 'expected_count': 0, 'actual_count': cnc_by_group[gid], 'status': 'GRUPA W FOLDERZE CNC NIE MA W CSV', 'note': ''})

            lines.append('\n=== B. Folder CNC vs skany ===')
            for cid in sorted(cnc_by_compare.keys()):
                cnc_count = cnc_by_compare[cid]
                scan_count = scans_by_compare.get(cid, 0)
                status = 'OK' if scan_count >= cnc_count else 'NIE ZESKANOWANO'
                lines.append('{0} | cnc: {1} | scan: {2} | {3}'.format(cid, cnc_count, scan_count, status))
                self.report_rows.append({'report_type': 'cnc_vs_scans_program', 'group_id': cid.split('\\')[0] if '\\' in cid else '', 'program_name': cid.split('\\')[-1], 'compare_id': cid, 'expected_count': cnc_count, 'actual_count': scan_count, 'status': status, 'note': ''})

            lines.append('\n=== C. CSV grupy vs skany ===')
            for gid in csv_groups:
                cnc_count = cnc_by_group.get(gid, 0)
                scan_count = scans_by_group.get(gid, 0)
                if cnc_count == 0:
                    status = 'BRAK PROGRAMÓW CNC'
                elif scan_count >= cnc_count:
                    status = 'OK'
                else:
                    status = 'BRAKUJE SKANÓW'
                lines.append('{0} | cnc: {1} | scan: {2} | {3}'.format(gid, cnc_count, scan_count, status))
                self.report_rows.append({'report_type': 'csv_group_vs_scans', 'group_id': gid, 'program_name': '', 'compare_id': '', 'expected_count': cnc_count, 'actual_count': scan_count, 'status': status, 'note': ''})

        else:
            lines.append('=== Program list ===')
            for row in self.csv_entries:
                cid = row.get('compare_id', '')
                pname = row.get('program_name', '')
                if cid and ('\\' in cid):
                    expected = cnc_by_compare.get(cid, 0)
                    actual = scans_by_compare.get(cid, 0)
                    status = 'OK'
                    if expected == 0:
                        status = 'BRAK PROGRAMU CNC'
                    elif actual < expected:
                        status = 'NIE ZESKANOWANO'
                    lines.append('{0} | cnc: {1} | scan: {2} | {3}'.format(cid, expected, actual, status))
                    self.report_rows.append({'report_type': 'program_list_compare_id', 'group_id': cid.split('\\')[0], 'program_name': cid.split('\\')[-1], 'compare_id': cid, 'expected_count': expected, 'actual_count': actual, 'status': status, 'note': ''})
                else:
                    key = pname or cid
                    expected = sum([1 for r in self.cnc_records if r['program_name'] == key])
                    actual = scans_by_program.get(key, 0)
                    status = 'OK'
                    if expected == 0:
                        status = 'BRAK PROGRAMU CNC'
                    elif actual < expected:
                        status = 'NIE ZESKANOWANO'
                    lines.append('{0} | cnc: {1} | scan: {2} | {3}'.format(key, expected, actual, status))
                    self.report_rows.append({'report_type': 'program_list_name', 'group_id': '', 'program_name': key, 'compare_id': '', 'expected_count': expected, 'actual_count': actual, 'status': status, 'note': ''})

            csv_ids = set([x.get('compare_id') for x in self.csv_entries if x.get('compare_id')])
            for s in self.scan_records:
                if s.get('compare_id') and (s.get('compare_id') not in csv_ids):
                    lines.append('{0} | SKAN NIE MA W CSV'.format(s.get('compare_id')))
                    self.report_rows.append({'report_type': 'scan_not_in_csv', 'group_id': s.get('group_id', ''), 'program_name': s.get('program_name', ''), 'compare_id': s.get('compare_id', ''), 'expected_count': 0, 'actual_count': 1, 'status': 'SKAN NIE MA W CSV', 'note': ''})

        self.report_text.delete('1.0', 'end')
        self.report_text.insert('1.0', '\n'.join(lines))

    def export_report_csv(self):
        if not self.report_rows:
            self.generate_report()
        save_path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV', '*.csv')])
        if not save_path:
            return
        fields = ['report_type', 'group_id', 'program_name', 'compare_id', 'expected_count', 'actual_count', 'status', 'note']
        with open(save_path, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for row in self.report_rows:
                writer.writerow(row)


if __name__ == '__main__':
    root = tk.Tk()
    app = ScannerApp(root)
    root.mainloop()
