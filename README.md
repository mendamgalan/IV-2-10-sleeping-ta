# The Sleeping Teaching Assistant IV-2-10

F.CSM302 Үйлдлийн систем · Бие даалт 1 · хувилбар 1.1

C / POSIX Pthreads хөдөлгүүр, Python Tkinter удирдах цонхтой.
TA болон оюутан бүр тусдаа OS thread. Сул TA semaphore дээр унтаж, ирсэн оюутан сэрээнэ;
завгүй үед оюутан сандал дээр FIFO дарааллаар хүлээж, дүүрэн бол дараа ирнэ. Сандал,
программчлах ба тусламжийн хугацаа, seed-ийг тохируулж, алхамчилж эсвэл бодит цагаар харна.

## Debian / Ubuntu дээр эхлүүлэх

```bash
sudo apt update
sudo apt install git build-essential python3 python3-tk
git clone https://github.com/mendamgalan/IV-2-10-sleeping-ta.git
cd IV-2-10-sleeping-ta/sleeping-ta
make
make run
```

Repository-ийн үндсэн хавтсаас бол `make -C sleeping-ta run`. Python-ийн нэмэлт pip сан
хэрэггүй. Linux desktop шаардлагатай (WSL2 + WSLg туршаагүй). Native Windows/macOS дэмжихгүй.

## Шалгах

```bash
make -C sleeping-ta test            # C 2 тест + Python 26 тест
xvfb-run -a make -C sleeping-ta test  # дэлгэцгүй серверт (sudo apt install xvfb)
make -C sleeping-ta tsan            # ThreadSanitizer-тэй stress тест
```

- `resource_failure` — thread/semaphore үүсгэх алдааны 3 нөхцөл.
- `stress` — чөлөөт горимд 15 000 tick, tick бүрт дүрэм (сандлын хязгаар, FIFO, баланс).
- Python: хөдөлгүүр 8, regression 9, UI 9 тест. Дэлгэцгүй үед UI-ийн 9 тест SKIP.

GitHub Actions push/PR бүрд `-Werror` build, Xvfb-тэй тест, ThreadSanitizer ажиллуулна.
Сүүлийн гаралт: [docs/test-results.txt](sleeping-ta/docs/test-results.txt).

## Удирдлага

- Ажиллуулах / Түр зогсоох / Алхам +0.1с / Reset, хурд ×1 / ×5 / ×20.
- 1 tick = загварын 100 мс; автомат горим бодит цагтай ижил хурдтай.
- Талбарыг өөрчилсний дараа Reset дарна (`*` тэмдэг гарна); буруу утгад талбарын нэр, хязгаар гарна.
- CSV хадгалах нь бүх түүхийг хуулна; Reset эсвэл хаахаас өмнө экспортлоно.

## Thread-ийн загвар

- **Seed горим (өгөгдмөл):** нэг tick-д TA, дараа нь оюутнууд seed-ээр холисон дарааллаар
  ээлжлэн ажиллана; ижил seed яг ижил үр дүн өгнө.
- **Чөлөөт горим:** оюутнууд нэг tick дотор зэрэг ажиллаж TA, сандал, mutex-ийн төлөө өрсөлдөнө.

Хоёр горимд сандал дээрх оюутан `called[i]`, тусламж авч буй оюутан `done[i]` semaphore дээр
блоклогдож, сул TA `work` дээр унтана. Дэлгэрэнгүй: Report 4–5, 9-р хэсэг.

## Баримт бичиг

- [Хэрэглэгчийн болон operational заавар](sleeping-ta/docs/Manual.md) · [PDF](sleeping-ta/docs/IV-2-10_Manual.pdf)
- [Тайлан](sleeping-ta/docs/Report.md) · [PDF](sleeping-ta/docs/IV-2-10_BD1_Report.pdf)
- Туршилтыг давтах: `python3 sleeping-ta/docs/experiments.py`
- PDF-ийг Markdown-оос дахин үүсгэх: `make -C sleeping-ta docs` (`python3-markdown`, LibreOffice)

Хувилбар: `v1.0` — БД1 постын хувилбар, `v1.1` — дотоод шүүмжийн засвартай хувилбар.

Код: `sleeping-ta/src/`; тест: `sleeping-ta/tests/`.
AI хэрэглээ: OpenAI ChatGPT (v1.0-ийн код, тест, баримт), Claude (v1.1-ийн шүүмж, засвар,
баримт). Үр дүнг баг ажиллуулж шалгасан.
Эх сурвалж: OS_BD1_Guide.pdf болон Operating System Concepts-ийн
Project 2 — The Sleeping Teaching Assistant.
