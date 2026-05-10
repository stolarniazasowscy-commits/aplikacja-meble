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

        self.root_folder = ''
        self.csv_mode = tk.StringVar()
        self.csv_mode.set('group_list')

        self.csv_files = []
        self.merged_project_data = []
        self.merged_counter = Counter()
        self.cnc_records = []
        self.scan_records = []
        self.report_rows = []

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

        cols = ('scan', 'cnc', 'csv', 'status', 'note')
        self.live_tree = ttk.Treeview(live_frame, columns=cols, show='headings', height=10)
        self.live_tree.heading('scan', text='Skan')
        self.live_tree.heading('cnc', text='Program CNC')
        self.live_tree.heading('csv', text='Element z CSV')
        self.live_tree.heading('status', text='Status')
        self.live_tree.heading('note', text='Uwagi')
        self.live_tree.column('scan', width=240)
        self.live_tree.column('cnc', width=90, anchor='center')
        self.live_tree.column('csv', width=100, anchor='center')
        self.live_tree.column('status', width=150)
        self.live_tree.column('note', width=360)
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

    def parse_scanned_path(self, original_code, root_folder):
        clean = self.normalize_path(original_code)
        tokens = [t for t in clean.split('\\') if t]
        program_name = tokens[-1] if tokens else ''
        group_id = ''
        for part in tokens:
            if part.upper().startswith('A_'):
                group_id = part
                break
        compare_id = group_id + '\\' + program_name if group_id else program_name
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'original_code': original_code,
            'group_id': group_id,
            'program_name': program_name,
            'compare_id': compare_id
        }

    def scan_cnc_folder(self):
        self.cnc_records = []
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
                self.cnc_records.append({'group_id': group_id, 'program_name': filename, 'compare_id': compare_id})
        groups = sorted(set([r['group_id'] for r in self.cnc_records if r['group_id']]))
        self.root_stats.config(text='Pliki .TCN: {0} | Grupy A_: {1} | Lista: {2}'.format(len(self.cnc_records), len(groups), ', '.join(groups) if groups else '-'))

    def reload_all_csv(self):
        self.merged_counter = Counter()
        self.merged_project_data = []
        for item in self.csv_files:
            path = item['path']
            if not os.path.isfile(path):
                continue
            with open(path, 'r') as f:
                rows = list(csv.reader(f))
            if not rows:
                continue
            header = [h.strip().lower() for h in rows[0]]
            has_header = ('group_id' in header) or ('compare_id' in header) or ('program_name' in header) or ('quantity' in header)
            data_rows = rows[1:] if has_header else rows
            for row in data_rows:
                if not row:
                    continue
                qty = 1
                if has_header and 'quantity' in header and header.index('quantity') < len(row):
                    qv = row[header.index('quantity')].strip()
                    try:
                        qty = int(qv)
                    except Exception:
                        qty = 1
                if self.csv_mode.get() == 'group_list':
                    gid = self.normalize_path(row[header.index('group_id')] if has_header and 'group_id' in header and header.index('group_id') < len(row) else row[0])
                    if gid:
                        self.merged_counter[('group', gid)] += qty
                else:
                    cid = ''
                    pname = ''
                    if has_header and 'compare_id' in header and header.index('compare_id') < len(row):
                        cid = self.normalize_path(row[header.index('compare_id')])
                    if has_header and 'program_name' in header and header.index('program_name') < len(row):
                        pname = self.normalize_path(row[header.index('program_name')])
                    if not cid and row:
                        cid = self.normalize_path(row[0])
                    if not pname:
                        pname = cid.split('\\')[-1] if cid else ''
                    key = cid or pname
                    if key:
                        self.merged_counter[('program', key)] += qty
        if self.csv_mode.get() == 'group_list':
            for key, val in self.merged_counter.items():
                if key[0] == 'group':
                    self.merged_project_data.append({'group_id': key[1], 'expected_count': val})
        else:
            for key, val in self.merged_counter.items():
                if key[0] == 'program':
                    self.merged_project_data.append({'lookup': key[1], 'expected_count': val})
        self.csv_stats.config(text='Pliki CSV: {0} | Pozycje CSV (scalone): {1}'.format(len(self.csv_files), len(self.merged_project_data)))

    def build_live_rows(self):
        rows = []
        scans_by_compare = Counter([s.get('compare_id', '') for s in self.scan_records if s.get('compare_id')])
        scans_by_group = Counter([s.get('group_id', '') for s in self.scan_records if s.get('group_id')])
        for rec in self.scan_records:
            cid = rec.get('compare_id', '')
            pname = rec.get('program_name', '')
            gid = rec.get('group_id', '')
            scan_label = cid or gid or pname

            exists_in_cnc = False
            if cid:
                exists_in_cnc = any([x for x in self.cnc_records if x['compare_id'] == cid])
            if (not exists_in_cnc) and pname:
                exists_in_cnc = any([x for x in self.cnc_records if x['program_name'] == pname])

            exists_in_csv = False
            expected = 0
            scanned_count = scans_by_compare.get(cid, 0) if cid else 0
            if self.csv_mode.get() == 'group_list':
                exists_in_csv = ('group', gid) in self.merged_counter
                expected = self.merged_counter.get(('group', gid), 0)
                scanned_count = scans_by_group.get(gid, 0)
            else:
                key = cid or pname
                exists_in_csv = ('program', key) in self.merged_counter
                expected = self.merged_counter.get(('program', key), 0)

            status = 'OK'
            note = 'Skan istnieje w CNC i CSV'
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
                'exists_in_cnc': 'TAK' if exists_in_cnc else 'BRAK',
                'exists_in_csv': 'TAK' if exists_in_csv else 'BRAK',
                'scanned_count': scanned_count,
                'expected_count': expected,
                'status': status,
                'note': note,
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
            tag = 'ok'
            if status in ('DUPLIKAT',):
                tag = 'warn'
            elif status in ('BRAKUJE',):
                tag = 'missing'
            elif status in ('BRAK PROGRAMU CNC', 'BRAK W CSV', 'NIEZNANY', 'ZA DUŻO'):
                tag = 'bad'
            else:
                ok_count += 1
            self.live_tree.insert('', 'end', values=(row['scan_label'], row['exists_in_cnc'], row['exists_in_csv'], row['status'], row['note']), tags=(tag,))

        problem_count = len(self.report_rows) - ok_count
        self.summary_label.config(text='CSV: {0} | CNC: {1} | Skany: {2} | OK: {3} | Problemy: {4}'.format(len(self.merged_project_data), len(self.cnc_records), len(self.scan_records), ok_count, problem_count))

        missing_lines = []
        if self.csv_mode.get() == 'group_list':
            scanned_by_group = Counter([r.get('group_id', '') for r in self.scan_records if r.get('group_id')])
            for item in self.merged_project_data:
                gid = item['group_id']
                if scanned_by_group.get(gid, 0) < item['expected_count']:
                    missing_lines.append('{0}: BRAKUJE ({1}/{2})'.format(gid, scanned_by_group.get(gid, 0), item['expected_count']))
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
        fields = ['timestamp', 'original_code', 'group_id', 'program_name', 'compare_id', 'exists_in_cnc', 'exists_in_csv', 'scanned_count', 'expected_count', 'status', 'note']
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
        self.scan_preview.config(text='Oryginalny kod: {0} | group_id: {1} | program_name: {2} | compare_id: {3}'.format(parsed.get('original_code', ''), parsed.get('group_id', ''), parsed.get('program_name', ''), parsed.get('compare_id', '')))
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
