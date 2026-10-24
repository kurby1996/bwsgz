"""霸王三国志：离线金手指界面，只使用 Python 标准库。"""
from pathlib import Path
import copy
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from .model import GameImage, NAME_BASE
except ImportError:
    from model import GameImage, NAME_BASE

ROOT = Path(__file__).resolve().parent.parent
ROM = ROOT / '霸王三国志-免登录版/roms/三國志II-霸王三国志.md'
EMU = ROOT / '霸王三国志-免登录版/blastem/blastem.exe'
LABELS = dict(intelligence='智力', war='武力', charm='魅力', loyalty='忠诚',
              troops='兵力（百人）', arms='武器量', training='训练', gold='金钱', food='粮草', population='人口')


def name_for(rom, identity):
    try:
        try:
            from .names import resolve_name
        except ImportError:
            from names import resolve_name
        return resolve_name(rom, identity)
    except (ImportError, ValueError, IndexError, KeyError):
        return f'武将 #{identity:03d}'


def recent_states():
    folders = [Path(os.environ.get('LOCALAPPDATA', '')) / 'blastem',
               Path.home() / 'AppData/Local/blastem', ROOT / '存档', ROOT / '4100975',
               ROOT / '霸王三国志-免登录版/saves']
    files = []
    for folder in dict.fromkeys(folders):
        if folder.is_dir():
            for ext in ('*.state', '*.gst', '*.gs?', '*.g??'):
                files.extend(folder.rglob(ext))
    return sorted(set(files), key=lambda p: p.stat().st_mtime, reverse=True)


class Trainer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('霸王三国志 · 金手指')
        self.geometry('1180x780')
        self.minsize(980, 650)
        self.option_add('*Font', ('Microsoft YaHei UI', 10))
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('Treeview', rowheight=29, font=('Microsoft YaHei UI', 10))
        style.configure('Treeview.Heading', font=('Microsoft YaHei UI', 10, 'bold'))
        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 19, 'bold'))
        self.image = None
        self.dirty = False
        self.saved_path = None
        self.nations = {'全部国家': None}
        self.nation = tk.StringVar(value='全部国家')
        self.query = tk.StringVar()
        self.status = tk.StringVar(value='请选择游戏文件。')
        self.summary = tk.StringVar()
        self.fields = {}
        self.rename = tk.StringVar()
        self._build()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Control-o>', lambda _: self.open_file())
        self.bind('<Control-Shift-S>', lambda _: self.save_as())
        self.open_path(ROM)

    def _build(self):
        shell = ttk.Frame(self, padding=18)
        shell.pack(fill='both', expand=True)
        ttk.Label(shell, text='霸王三国志 · 金手指', style='Title.TLabel').pack(anchor='w')
        ttk.Label(shell, text='武将养成 / 军事调整 / 国家资源　　修改后另存，回游戏读取生效').pack(anchor='w', pady=(3, 14))
        tools = ttk.Frame(shell)
        tools.pack(fill='x')
        for text, cmd in [('打开存档 / ROM', self.open_file), ('读取最新即时存档', self.open_latest),
                          ('新开局能力设置', lambda: self.open_path(ROM)), ('另存修改结果', self.save_as),
                          ('使用说明', self.help)]:
            ttk.Button(tools, text=text, command=cmd).pack(side='left', padx=(0, 7))
        ttk.Label(shell, textvariable=self.status, wraplength=1100).pack(anchor='w', pady=(12, 5))
        filters = ttk.Frame(shell)
        filters.pack(fill='x', pady=6)
        ttk.Label(filters, text='国家').pack(side='left')
        self.nation_box = ttk.Combobox(filters, textvariable=self.nation, state='readonly', width=25)
        self.nation_box.pack(side='left', padx=7)
        self.nation_box.bind('<<ComboboxSelected>>', lambda _: self.refresh())
        ttk.Label(filters, text='搜索姓名 / 编号').pack(side='left', padx=(15, 0))
        ttk.Entry(filters, textvariable=self.query, width=22).pack(side='left', padx=7)
        self.query.trace_add('write', lambda *_: self.refresh())
        ttk.Label(shell, textvariable=self.summary).pack(anchor='w', pady=(2, 7))
        self.tabs = ttk.Notebook(shell)
        self.tabs.pack(fill='both', expand=True)
        for mode, caption, columns in [
            ('officer', '武将与军事', [('id','编号'),('name','姓名'),('nation','国家'),('province','州'),
              ('intelligence','智力'),('war','武力'),('charm','魅力'),('loyalty','忠诚'),('troops','兵力/百人'),('arms','武器量'),('training','训练')]),
            ('province', '州城与国家资源', [('id','州编号'),('nation','国家'),('gold','金钱'),('food','粮草'),('population','人口'),('officers','武将数'),('troops','总兵力')])]:
            tab = ttk.Frame(self.tabs, padding=10)
            self.tabs.add(tab, text=caption)
            frame = ttk.Frame(tab)
            frame.pack(fill='both', expand=True)
            table = ttk.Treeview(frame, columns=[c[0] for c in columns], show='headings', selectmode='extended')
            for key, label in columns:
                table.heading(key, text=label)
                table.column(key, width=65 if key != 'name' else 110, anchor='center', stretch=True)
            bar = ttk.Scrollbar(frame, orient='vertical', command=table.yview)
            table.configure(yscrollcommand=bar.set)
            bar.pack(side='right', fill='y')
            table.pack(fill='both', expand=True)
            setattr(self, mode + '_table', table)
            table.bind('<<TreeviewSelect>>', lambda _, m=mode: self.select(m))
            edit = ttk.LabelFrame(tab, text='勾选要修改的项目，再应用到选中行（Ctrl / Shift 可多选）', padding=10)
            edit.pack(fill='x', pady=(12, 0))
            keys = ['intelligence','war','charm','loyalty','troops','arms','training'] if mode == 'officer' else ['gold','food','population']
            for n, key in enumerate(keys):
                enabled, value = tk.BooleanVar(), tk.StringVar(value='100' if mode == 'officer' else '30000')
                col = n % 4
                row = (n // 4) * 2
                check = ttk.Checkbutton(edit, text=LABELS[key], variable=enabled)
                check.grid(row=row, column=col*2, sticky='w', padx=(0,4), pady=4)
                entry = ttk.Entry(edit, textvariable=value, width=10)
                entry.grid(row=row, column=col*2+1, padx=(0,18), pady=4)
                self.fields[(mode,key)] = enabled, value, check, entry
            buttons = ttk.Frame(edit)
            buttons.grid(row=5, column=0, columnspan=8, sticky='w', pady=(8,0))
            ttk.Button(buttons, text='应用到选中行', command=lambda m=mode: self.apply(m)).pack(side='left', padx=(0,8))
            ttk.Button(buttons, text='选中当前筛选的全部行', command=lambda t=table: t.selection_set(t.get_children())).pack(side='left', padx=(0,8))
            ttk.Button(buttons, text='取消勾选', command=lambda m=mode: self.clear_checks(m)).pack(side='left')
        self.name_bar = ttk.Frame(shell)
        self.name_bar.pack(fill='x', pady=(10,0))
        ttk.Label(self.name_bar, text='ROM 改名（最多三个游戏已有汉字）').pack(side='left')
        ttk.Entry(self.name_bar, textvariable=self.rename, width=15).pack(side='left', padx=8)
        self.rename_button = ttk.Button(self.name_bar, text='修改所选武将姓名', command=self.rename_selected)
        self.rename_button.pack(side='left')
        ttk.Label(shell, text='兵力 0–100 百人（最多一万兵）；武器 0–10000。仅编辑内政地图即时存档，战斗或命令执行中不可编辑。').pack(anchor='w', pady=(10,0))

    def unsaved_ok(self):
        return not self.dirty or messagebox.askyesno('尚未保存', '当前修改还未另存，是否放弃这些修改？', parent=self)

    def open_file(self):
        path = filedialog.askopenfilename(title='选择霸王三国志即时存档或标准 ROM', initialdir=str(ROOT),
            filetypes=[('支持的文件','*.state *.gst *.gs? *.md *.bin'), ('所有文件','*.*')])
        if path:
            self.open_path(path)

    def open_latest(self):
        files = recent_states()
        errors = []
        for path in files:
            try:
                GameImage(path, ROM)
            except (ValueError, OSError) as e:
                errors.append(str(e))
                continue
            self.open_path(path)
            return
        messagebox.showinfo('还没有有效即时存档', '请在游戏内进入剧本与内政画面，按 ` 保存即时存档。\n\n' + (errors[0] if errors else '未发现 .state / .gst 即时存档。'), parent=self)

    def open_path(self, path):
        if not self.unsaved_ok():
            return
        try:
            image = GameImage(path, ROM)
            self.image = image
            self.saved_path = None
            self.dirty = False
            self.nations = {'全部国家':None}
            officers = {o['index']:o for o in image.get_officers()}
            for c in image.get_countries():
                if c['ruler_index'] is not None:
                    officer = officers[c['ruler_index']]
                    self.nations[f"国家 {c['index']+1} · {name_for(image.rom_data, officer['name_id'])}"] = c['index']
            self.nations['无所属 / 在野'] = 255
            self.nation.set('全部国家')
            self.nation_box['values'] = list(self.nations)
            self.nation_box.configure(state='disabled' if image.kind == 'rom' else 'readonly')
            self.status.set(('新开局 ROM：' if image.kind == 'rom' else '即时存档：') + str(image.path))
            self.tabs.tab(1, state='disabled' if image.kind == 'rom' else 'normal')
            for (mode,key), (_,_,check,entry) in self.fields.items():
                available = image.kind != 'rom' or key in ('intelligence','war','charm')
                check.configure(state='normal' if available else 'disabled')
                entry.configure(state='normal' if available else 'disabled')
            self.rename_button.configure(state='normal' if image.kind == 'rom' else 'disabled')
            self.clear_checks('officer')
            self.clear_checks('province')
            self.refresh()
        except (OSError, ValueError) as e:
            messagebox.showerror('无法读取', str(e), parent=self)

    def country_name(self, index):
        if index is None:
            return '新开局'
        if index == 255:
            return '无所属'
        for label, ident in self.nations.items():
            if ident == index:
                return label.split(' · ')[-1]
        return f'国家{index+1}'

    def refresh(self):
        if self.image is None:
            return
        nation = self.nations.get(self.nation.get())
        query = self.query.get().strip()
        os_ = self.image.get_officers()
        ps = self.image.get_provinces()
        for mode in ('officer', 'province'):
            table = getattr(self, mode+'_table')
            selected = set(table.selection())
            table.delete(*table.get_children())
            for row in os_ if mode == 'officer' else ps:
                if mode=='officer' and row['name_id'] >= 352:
                    continue
                if nation is not None and row['nation'] != nation:
                    continue
                if mode == 'officer':
                    name = name_for(self.image.rom_data, row['name_id'])
                    if query and query not in name and query not in str(row['index']+1):
                        continue
                    province = '—' if row['province'] is None else row['province']+1
                    values = [row['index']+1, name, self.country_name(row['nation']), province]
                    values.extend('—' if row.get(k) is None else row[k] for k in ('intelligence','war','charm','loyalty','troops','arms','training'))
                else:
                    ids = set(row['officer_indices'])
                    values = [row['index']+1,self.country_name(row['nation']),row['gold'],row['food'],row['population'],len(ids),sum(o['troops'] for o in os_ if o['index'] in ids)]
                iid = str(row['index'])
                table.insert('', 'end', iid=iid, values=values)
                if iid in selected:
                    table.selection_add(iid)
        visible_ps = [p for p in ps if nation is None or p['nation']==nation]
        if ps:
            self.summary.set(f"当前国家筛选：{len(visible_ps)} 州　金钱合计 {sum(p['gold'] for p in visible_ps):,}　粮草合计 {sum(p['food'] for p in visible_ps):,}　（搜索仅筛武将）")
        else:
            self.summary.set('新开局模式：修改历史武将的初始能力和姓名，另存 ROM 后从新剧本开始生效。')

    def select(self, mode):
        table = getattr(self, mode+'_table')
        selected = table.selection()
        if len(selected) != 1:
            return
        rows = self.image.get_officers() if mode=='officer' else self.image.get_provinces()
        row = next((r for r in rows if r['index']==int(selected[0])), None)
        if row is None:
            return
        for (m,key), (enabled,value,_,_) in self.fields.items():
            if m==mode and not enabled.get() and row.get(key) is not None:
                value.set(str(row[key]))
        if mode=='officer':
            self.rename.set(name_for(self.image.rom_data,row['name_id']))

    def clear_checks(self, mode):
        for (m,_),(flag,_,_,_) in self.fields.items():
            if m==mode:
                flag.set(False)

    def apply(self, mode):
        if self.image is None:
            return
        selected = getattr(self,mode+'_table').selection()
        if not selected:
            messagebox.showinfo('请选择记录', '请先选中要修改的一行或多行。', parent=self)
            return
        try:
            changes = {key:int(value.get()) for (m,key),(flag,value,_,_) in self.fields.items()
                       if m==mode and flag.get() and (self.image.kind!='rom' or key in ('intelligence','war','charm'))}
            if not changes:
                raise ValueError('请勾选至少一个要修改的项目。')
            trial = copy.deepcopy(self.image)
            method = trial.update_officer if mode=='officer' else trial.update_province
            for ident in selected:
                method(int(ident),changes)
            self.image = trial
            self.dirty = True
            self.status.set(f'已暂存 {len(selected)} 条修改，请点击“另存修改结果”写入文件。')
            self.refresh()
        except ValueError as e:
            messagebox.showerror('修改未应用', str(e), parent=self)

    def rename_selected(self):
        if self.image is None or self.image.kind!='rom':
            return
        selection = self.officer_table.selection()
        if len(selection)!=1:
            messagebox.showinfo('请选择一名武将', '改名时只选中一名武将。', parent=self)
            return
        try:
            try:
                from .names import rename_in_rom
            except ImportError:
                from names import rename_in_rom
            trial = copy.deepcopy(self.image)
            rename_in_rom(trial.data, int(selection[0]), self.rename.get().strip())
            self.image = trial
            self.dirty = True
            self.status.set('姓名修改已暂存；另存 ROM 并重新开局后生效。')
            self.refresh()
        except (ImportError, ValueError) as e:
            messagebox.showerror('无法改名', str(e), parent=self)

    def save_as(self):
        if self.image is None:
            return
        suffix = {'rom':'.md','gst':'.gst','native':'.state'}[self.image.kind]
        output = ROOT / '修改结果'
        output.mkdir(exist_ok=True)
        path = filedialog.asksaveasfilename(title='另存修改结果', initialdir=str(output),
                 initialfile=self.image.path.stem+'-修改'+suffix, defaultextension=suffix,
                 filetypes=[('游戏文件','*'+suffix)])
        if not path:
            return
        try:
            # 原 ROM 保留：新开局修改仅写新文件。
            if Path(path).resolve()==ROM.resolve():
                raise ValueError('请另存到“修改结果”目录，保留项目原 ROM。')
            self.saved_path = self.image.save(path)
            launcher = self.saved_path.with_suffix(self.saved_path.suffix + '.启动.bat')
            # 使用相对原始 ROM 和完整结果路径，避免槽位覆盖与错误读档。
            escaped_path = str(self.saved_path).replace('%', '%%')
            arguments = f'"{escaped_path}"' if self.image.kind=='rom' else f'-s "{escaped_path}" "{ROM}"'
            script = ('@echo off\r\nsetlocal DisableDelayedExpansion\r\nchcp 65001 >nul\r\n'
                      'echo 请先关闭正在运行的游戏窗口，再按任意键启动修改结果。\r\npause >nul\r\n'
                      f'cd /d "{EMU.parent}"\r\nstart "" "{EMU}" {arguments}\r\n')
            launcher.write_text(script, encoding='utf-8')
            self.dirty = False
            self.status.set('已保存：'+str(self.saved_path))
            instructions = ('打开这个新 ROM，从新剧本开始。' if self.image.kind=='rom' else
                '先关闭游戏，再运行结果文件旁的“.启动.bat”，会直接加载此修改存档。')
            backup = '\n覆盖前备份：'+str(self.image.last_backup) if self.image.last_backup else ''
            messagebox.showinfo('保存成功', instructions+backup, parent=self)
        except (OSError, ValueError) as e:
            messagebox.showerror('保存失败',str(e),parent=self)

    def help(self):
        messagebox.showinfo('使用说明',
            '已有进度：在内政地图按 ` 保存即时存档 → 读取最新即时存档 → 选国家/武将/州 → 勾选字段 → 应用 → 另存 → 回游戏读取。\n\n'
            '新游戏：点“新开局能力设置” → 修改能力或姓名 → 另存 ROM → 用新 ROM 开始新剧本。\n\n'
            '按键：方向键选择；A 确认、S 返回、D 为 C 键；Enter 开始；Esc 模拟器菜单；` 即时保存、L 即时读取；F7 暂停；Tab 重启。\n\n'
            '能力/忠诚/训练 0–100；兵力 0–100 百人；武器 0–10000；金钱粮草 0–30000。人口单位尚待画面核实。\n'
            '姓名在 ROM 内共享，同一历史人物的所有剧本都会使用新名。暂不修改所属国家与链表。',parent=self)

    def close(self):
        if self.unsaved_ok():
            self.destroy()


if __name__ == '__main__':
    Trainer().mainloop()
