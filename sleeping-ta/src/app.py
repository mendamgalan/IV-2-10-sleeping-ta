import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from model import Model

class App:
    def __init__(self, root):
        self.root, self.running = root, False
        root.title('Sleeping Teaching Assistant • F.CSM302 / 10')
        root.geometry('1120x800'); root.minsize(980, 740)
        root.configure(bg='#101827')
        self.model = Model()
        style = ttk.Style(); style.theme_use('clam')
        style.configure('TFrame', background='#101827')
        style.configure('TLabel', background='#101827', foreground='#e6edf7', font=('DejaVu Sans', 10))
        style.configure('TButton', font=('DejaVu Sans', 10), padding=8)
        main = ttk.Frame(root, padding=20); main.pack(fill='both', expand=True)
        ttk.Label(main, text='THE SLEEPING TEACHING ASSISTANT', font=('DejaVu Sans', 21, 'bold')).pack(anchor='w')
        ttk.Label(main, text='10 / Үйлдлийн систем     •     Бодит Pthreads + mutex + semaphore').pack(anchor='w', pady=(4,18))
        form = ttk.Frame(main); form.pack(fill='x')
        self.fields = {}
        for i,(key,label,value) in enumerate([('n','Оюутан',8),('chairs','Сандал',3),('amin','Ирэх min (сек)',1),('amax','Ирэх max (сек)',4),('hmin','Туслах min (сек)',1.5),('hmax','Туслах max (сек)',3),('seed','Seed',42)]):
            box=ttk.Frame(form);box.grid(row=0,column=i,padx=(0,12),sticky='w')
            ttk.Label(box,text=label).pack(anchor='w')
            v=tk.StringVar(value=str(value)); self.fields[key]=v
            ttk.Entry(box,textvariable=v,width=11).pack(pady=5)
        bar=ttk.Frame(main);bar.pack(fill='x',pady=12)
        for label,cmd in [('▶ Ажиллуулах',self.play),('Ⅱ Түр зогсоох',self.pause),('→ Алхам +0.1с',self.step),('↺ Тохиргоогоор reset',self.reset),('CSV хадгалах',self.export)]:
            ttk.Button(bar,text=label,command=cmd).pack(side='left',padx=(0,8))
        self.stats=ttk.Label(main,text='');self.stats.pack(anchor='w',pady=(0,10))
        self.canvas=tk.Canvas(main,bg='#18243a',highlightthickness=0,height=370)
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw())
        ttk.Label(main,text='Цэнхэр: программчилж байна   •   Шар: хүлээж байна   •   Ногоон: тусламж авч байна').pack(anchor='w',pady=8)
        self.log=tk.Text(main,height=6,bg='#0b1220',fg='#c7d5e8',font=('DejaVu Sans Mono',10),relief='flat')
        self.log.pack(fill='x')
        ttk.Label(main,text='1 алхам = загварын 100 мс. Тохиргоог reset дарж хэрэглэнэ. Ирэх завсар нь оюутан бүрийн программчлах хугацаа.').pack(anchor='w',pady=7)
        self.reset(); root.protocol('WM_DELETE_WINDOW',self.close); root.after(100,self.loop)

        #Оргилсайхан
    def reset(self):
        try:
            f=self.fields

            try:  # Тоо биш утга (abc, хоосон, 3.5) оруулбал энгийн алдаа өгнө Utga n too bish baiwal (abc, hooson, 3.5 geh met)

                values={k:int(f[k].get()) for k in ('n','chairs','seed')}

                times={k:float(f[k].get()) for k in ('amin','amax','hmin','hmax')}

            except ValueError:raise ValueError('Буруу утга орууллаа.')
            
            if not 1<=values['n']<=40 or not 0<=values['chairs']<=20:raise ValueError('Буруу утга орууллаа.')  # 4294967297 gesen hyzgaar too 1 bolohoos sergiilew

            if not 0<=values['seed']<=4294967295: raise ValueError('Seed: 0–4294967295.')
            
            for k in ('amin','amax','hmin','hmax'):
                x=times[k]
                if not .1<=x<=600 or abs(x*10-round(x*10))>1e-6: raise ValueError('Хугацаа: 0.1–600 секунд, 0.1-ийн алхамтай.')
                values[k]=round(x*10)
            self.model.reset(**values)
        except (ValueError,OverflowError) as e:
            messagebox.showerror('Оролтын алдаа',str(e));return
        self.running=False; self.config=values; self.draw()
    def play(self): self.running=True
    def pause(self): self.running=False
    def step(self):
        self.running=False; self.model.step(); self.draw()
    def loop(self):
        if self.running:self.model.step();self.draw()
        self.root.after(100,self.loop)
    def draw(self):
        if not hasattr(self,'config'):return
        s=self.model.snapshot();c=self.canvas;c.delete('all');w=max(c.winfo_width(),940)
        self.stats.config(text=f"Хугацаа {s['tick']/10:.1f} с     |     Ирэлт {s['arrivals']}     |     Дууссан {s['completed']}     |     Сандалгүй буцсан {s['rejected']}     |     Хүлээлт {len(s['queue'])}/{self.config['chairs']}")
        def text(x,y,t,color='#e6edf7',size=12):c.create_text(x,y,text=t,fill=color,font=('DejaVu Sans',size),anchor='w')
        c.create_rectangle(20,20,280,165,fill='#22334d',outline='#41536b')
        text(38,43,'TA / ӨРӨӨ',size=14)
        text(38,78,'Унтаж байна • Zzz' if s['current']<0 else f"Оюутан {s['current']+1}-д тусалж байна",'#72e2b6' if s['current']>=0 else '#a9bbd3')
        text(38,115,f"Үлдсэн: {s['remaining']/10:.1f} с" if s['current']>=0 else 'Ирэх оюутныг хүлээнэ')
        text(310,35,'ХҮЛЭЭЛГИЙН ДАРААЛАЛ → FIFO',size=13)
        seats=self.config['chairs']; cols=10
        if not seats:text(310,85,'Сандалгүй: зөвхөн TA сул үед орно.')
        for i in range(seats):
            x=310+(i%cols)*max(48,(w-340)/cols); y=60+(i//cols)*58
            occupied=i<len(s['queue']);color='#eac16b' if occupied else '#2b3d56'
            c.create_rectangle(x,y,x+45,y+40,fill=color,outline='')
            text(x+5,y+20,str(s['queue'][i]+1) if occupied else '—','#17243a' if occupied else '#8195b2')
        text(20,195,'ОЮУТНУУД / төлөв ба авсан тусламж',size=13)
        labels=['Код','Хүлээнэ','Тусламж','Дууссан'];colors=['#77b7f7','#eac16b','#72e2b6','#b8a0eb']
        for i,student in enumerate(s['students']):
            x=20+(i%10)*((w-40)/10);y=218+(i//10)*45
            text(x,y,f"S{i+1} · {labels[student['state']]}",colors[student['state']],10)
            text(x,y+17,f"{student['visits']} удаа",'#8ea2bd',9)
        lines=self.model.events().splitlines()[-6:]
        self.log.configure(state='normal');self.log.delete('1.0','end');self.log.insert('end','\n'.join(lines));self.log.configure(state='disabled')
    def export(self):
        filename=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')])
        if filename:
            try:Path(filename).write_text(self.model.events(),encoding='utf-8')
            except OSError as e:messagebox.showerror('Хадгалах алдаа',str(e))
    def close(self):self.model.close();self.root.destroy()

if __name__=='__main__':
    try:App(tk.Tk()).root.mainloop()
    except (OSError,tk.TclError) as e:
        print(f'Ажиллуулах боломжгүй: {e}\nmake команд ажиллуулж, python3-tk болон график орчин байгаа эсэхийг шалгана.')
        raise SystemExit(1)
