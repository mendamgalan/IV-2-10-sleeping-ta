# UI input validation includes the checks contributed by Оргилсайхан.
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox, filedialog
from model import Model

BG = '#101827'
MUTED = '#9fb0c8'
STATE_LABELS = ['Программчилж байна', 'Сандал дээр хүлээж байна', 'Тусламж авч байна']
STATE_COLORS = ['#77b7f7', '#eac16b', '#72e2b6']
# key, group label, sub label, default
FIELDS = [
    ('n', 'Оюутан', '', '8'),
    ('chairs', 'Сандал', '', '3'),
    ('amin', 'Программчлах, с', 'min', '1'),
    ('amax', 'Программчлах, с', 'max', '4'),
    ('hmin', 'Тусламж, с', 'min', '1.5'),
    ('hmax', 'Тусламж, с', 'max', '3'),
    ('seed', 'Seed', '', '42'),
]
HINT = ('1 алхам = загварын 100 мс. Программчлах = тусламжийн дараа дахин ирэх хүртэлх хугацаа. '
        'Талбарыг өөрчилсний дараа Reset дарна.')
COLS, ROW_H, STUDENTS_Y = 10, 44, 172


class App:

    def __init__(self, root):
        self.root, self.running = (root, False)
        root.title('Sleeping Teaching Assistant • F.CSM302 / IV-2-10')
        root.geometry('1120x800')
        root.minsize(980, 740)
        root.configure(bg=BG)
        self.model = Model()
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=BG)
        style.configure('TLabel', background=BG, foreground='#e6edf7', font=('DejaVu Sans', 10))
        style.configure('TButton', font=('DejaVu Sans', 10), padding=6)
        style.configure('TCheckbutton', background=BG, foreground='#e6edf7', font=('DejaVu Sans', 10))
        self.small = tkfont.Font(family='DejaVu Sans', size=9)
        main = ttk.Frame(root, padding=(18, 14))
        main.pack(fill='both', expand=True)

        header = ttk.Frame(main)
        header.pack(fill='x')
        ttk.Label(header, text='THE SLEEPING TEACHING ASSISTANT', font=('DejaVu Sans', 18, 'bold')).pack(side='left')
        ttk.Label(header, text='IV-2-10 · POSIX threads + mutex + semaphore', foreground=MUTED).pack(side='right')

        form = ttk.Frame(main)
        form.pack(fill='x', pady=(10, 0))
        self.fields, self.entries, self.group_labels, groups = {}, {}, {}, {}
        for key, group, sub, default in FIELDS:
            if group not in groups:
                box = ttk.Frame(form)
                box.pack(side='left', padx=(0, 18))
                label = ttk.Label(box, text=group)
                label.pack(anchor='w')
                row = ttk.Frame(box)
                row.pack(anchor='w', pady=(3, 0))
                groups[group] = (label, row)
            label, row = groups[group]
            if sub:
                ttk.Label(row, text=sub, foreground=MUTED).pack(side='left', padx=(0, 3))
            var = tk.StringVar(value=default)
            entry = ttk.Entry(row, textvariable=var, width=7)
            entry.pack(side='left', padx=(0, 8))
            self.fields[key], self.entries[key] = var, entry
            self.group_labels[key] = (label, group)

        self.bar = ttk.Frame(main)
        self.bar.pack(fill='x', pady=8)
        for label, cmd in [('▶ Ажиллуулах', self.play), ('Ⅱ Түр зогсоох', self.pause), ('→ Алхам +0.1с', self.step),
                           ('↺ Reset', self.reset), ('CSV хадгалах', self.export)]:
            ttk.Button(self.bar, text=label, command=cmd).pack(side='left', padx=(0, 8))
        self.hint = ttk.Label(main, text=HINT, foreground=MUTED, font=('DejaVu Sans', 9))
        self.hint.pack(anchor='w')
        self.stats = ttk.Label(main, text='')
        self.stats.pack(anchor='w', pady=(4, 2))
        main.bind('<Configure>', lambda e: self.stats.configure(wraplength=e.width - 40), add='+')
        self.warning = ttk.Label(main, text='', foreground='#ffb4a2')
        # Packed before the canvas so a small window shrinks the canvas, not the log.
        self.log = tk.Text(main, height=6, bg='#0b1220', fg='#c7d5e8', font=('DejaVu Sans Mono', 10), relief='flat')
        self.log.pack(side='bottom', fill='x', pady=(6, 0))
        self.canvas = tk.Canvas(main, bg='#18243a', highlightthickness=0, height=360)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<Configure>', lambda e: self.draw())
        self.reset()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.loop)

    def reset(self):
        try:
            f = self.fields
            try:
                values = {k: int(f[k].get()) for k in ('n', 'chairs', 'seed')}
                times = {k: float(f[k].get()) for k in ('amin', 'amax', 'hmin', 'hmax')}
            except ValueError:
                raise ValueError('Буруу утга орууллаа.')
            if not 1 <= values['n'] <= 40 or not 0 <= values['chairs'] <= 20:
                raise ValueError('Буруу утга орууллаа.')
            if not 0 <= values['seed'] <= 4294967295:
                raise ValueError('Seed: 0–4294967295.')
            for k in ('amin', 'amax', 'hmin', 'hmax'):
                x = times[k]
                if not 0.1 <= x <= 600 or abs(x * 10 - round(x * 10)) > 1e-06:
                    raise ValueError('Хугацаа: 0.1–600 секунд, 0.1-ийн алхамтай.')
                values[k] = round(x * 10)
            self.model.reset(**values)
        except (ValueError, OverflowError, OSError) as e:
            if not self.model.snapshot()['active']:
                self.running = False
            messagebox.showerror('Тохиргооны алдаа', str(e))
            return
        self.running = False
        self.config = values
        self.draw()

    def play(self):
        if not self.model.snapshot()['active']:
            messagebox.showerror('Ажиллуулах алдаа', 'Эхлээд reset хийж хөдөлгүүрийг эхлүүлнэ.')
            return
        self.running = True

    def pause(self):
        self.running = False

    def step(self):
        self.running = False
        self.model.step()
        self.draw()

    def loop(self):
        if self.running:
            self.model.step()
            self.draw()
        self.root.after(100, self.loop)

    def text(self, x, y, t, color='#e6edf7', size=12, anchor='w', bold=False):
        font = ('DejaVu Sans', size, 'bold') if bold else ('DejaVu Sans', size)
        self.canvas.create_text(x, y, text=t, fill=color, font=font, anchor=anchor)

    def draw(self):
        if not hasattr(self, 'config'):
            return
        s = self.model.snapshot()
        c = self.canvas
        c.delete('all')
        w = max(c.winfo_width(), 900)
        queue, current, chairs = s['queue'], s['current'], self.config['chairs']
        helped = s['completed'] + (current >= 0)
        wait = s['wait_sum'] / helped / 10 if helped else 0.0
        load = 100 * s['busy'] / s['tick'] if s['tick'] else 0.0
        self.stats.config(text=f"Хугацаа {s['tick'] / 10:.1f} с  ·  Ирэлт {s['arrivals']}  ·  "
                               f"Тусламж дууссан {s['completed']}  ·  Сандалгүй буцсан {s['rejected']}  ·  "
                               f"Хүлээлт {len(queue)}/{chairs}  ·  Дундаж хүлээлт {wait:.1f} с  ·  "
                               f"TA ачаалал {load:.0f} %")

        c.create_rectangle(16, 12, 286, 132, fill='#22334d', outline='#41536b')
        self.text(32, 34, 'TA / ӨРӨӨ', size=13)
        if current >= 0:
            self.text(32, 68, f'S{current + 1}-д тусалж байна', STATE_COLORS[2])
            self.text(32, 102, f"Үлдсэн: {s['remaining'] / 10:.1f} с", size=11)
        else:
            self.text(32, 68, 'Унтаж байна · Zzz', MUTED)
            self.text(32, 102, 'Ирэх оюутныг хүлээнэ', size=11)

        self.text(310, 24, 'ХҮЛЭЭЛГИЙН ДАРААЛАЛ (FIFO) → TA', size=12)
        if not chairs:
            self.text(310, 70, 'Сандалгүй: TA сул үед л тусламж авна.', size=11)
        gap = max(48, (w - 330) / 10)
        for i in range(chairs):
            x, y = 310 + i % 10 * gap, 44 + i // 10 * 46
            occupied = i < len(queue)
            c.create_rectangle(x, y, x + 44, y + 38, fill=STATE_COLORS[1] if occupied else '#2b3d56', outline='')
            self.text(x + 22, y + 19, f'S{queue[i] + 1}' if occupied else '—',
                      '#13203a' if occupied else '#8195b2', 11, anchor='center', bold=occupied)

        self.text(16, 150, 'ОЮУТНУУД', size=12)
        x = 130
        for color, label in zip(STATE_COLORS, STATE_LABELS):
            c.create_rectangle(x, 144, x + 12, 156, fill=color, outline='')
            self.text(x + 18, 150, label, MUTED, 9)
            x += 18 + self.small.measure(label) + 24
        cell = (w - 32) / COLS
        badge = min(cell - 10, 84)
        for i, student in enumerate(s['students']):
            x = 16 + i % COLS * cell
            y = STUDENTS_Y + i // COLS * ROW_H
            c.create_rectangle(x, y, x + badge, y + 22, fill=STATE_COLORS[student['state']], outline='')
            self.text(x + badge / 2, y + 11, f'S{i + 1}', '#13203a', 10, anchor='center', bold=True)
            self.text(x, y + 33, f"{student['visits']} удаа", '#8ea2bd', 9)

        message = 'Журнал бичихэд алдаа гарлаа. Дискний зайг шалгаад reset хийнэ; CSV бүрэн биш.' if s['journal_error'] else ''
        self.warning.config(text=message)
        if message and not self.warning.winfo_manager():
            self.warning.pack(after=self.stats, anchor='w')
        elif not message and self.warning.winfo_manager():
            self.warning.pack_forget()
        lines = self.model.recent_events().splitlines()
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.insert('end', '\n'.join(lines))
        self.log.configure(state='disabled')

    def export(self):
        filename = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV', '*.csv')])
        if filename:
            try:
                self.model.export(filename)
            except OSError as e:
                messagebox.showerror('Хадгалах алдаа', str(e))

    def close(self):
        self.model.close()
        self.root.destroy()


if __name__ == '__main__':
    try:
        App(tk.Tk()).root.mainloop()
    except (OSError, tk.TclError) as e:
        print(f'Ажиллуулах боломжгүй: {e}\nmake команд ажиллуулж, python3-tk болон график орчин байгаа эсэхийг шалгана.')
        raise SystemExit(1)
