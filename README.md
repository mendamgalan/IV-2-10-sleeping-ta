# The Sleeping Teaching Assistant IV-2-10

F.CSM302 Үйлдлийн систем · Бие даалт 1

C / POSIX Pthreads хөдөлгүүр, Python Tkinter удирдах цонхтой.
Оюутан бүр болон TA тусдаа OS thread. Сандал, ирэх завсар, туслах хугацааг
тохируулж, FIFO дараалал ба TA-ийн төлөвийг алхамчилж харуулна.

## Debian / Ubuntu дээр эхлүүлэх

```bash
sudo apt update
sudo apt install git build-essential python3 python3-tk
git clone https://github.com/mendamgalan/IV-2-10-sleeping-ta.git
cd IV-2-10-sleeping-ta/sleeping-ta
make
make run
```

Repository-г өмнө татсан бол Makefile байгаа `sleeping-ta` хавтас руу орно.
Python-ийн нэмэлт pip сан ажиллуулахад хэрэггүй. Linux desktop эсвэл
Windows-ийн WSL2 + WSLg шаардлагатай. Native Windows/macOS дэмжихгүй.

## Шалгах

Repository-ийн үндсэн хавтсаас:

```bash
make -C sleeping-ta test
```

Үүнд 14 хөдөлгүүр/интерфейсийн тест, 4 UI тест, C нөөцийн алдааны 3 нөхцөл орно.
Дэлгэцгүй үед UI-ийн 4 тест SKIP болно. Бүгдийг ажиллуулахад:

```bash
sudo apt install xvfb
xvfb-run -a make -C sleeping-ta test
```

GitHub Actions нь push/PR бүрд warnings-as-errors build болон Xvfb-тэй тест хийнэ.

## Удирдлага ба журнал

- Run / Pause / Step / Reset нь C хөдөлгүүрийн цагийг удирдана.
- 1 tick = загварын 100 мс; ирэх завсар нь оюутан тус бүрийн программчлах хугацаа.
- UI зөвхөн сүүлийн 6 үйл явдлыг харуулна. Бүтэн түүх түр файлд хадгалагдана.
- CSV экспорт нь бүх түүхийг хуулна; амжилтгүй бол өмнөх файлыг солихгүй.
- Reset эсвэл хаахаас **өмнө** хэрэгтэй CSV-ээ экспортлоно. Түр түүх устдаг.
- Диск дүүрвэл UI алдааг харуулж, дутуу CSV-г бүтэн мэт экспортлохгүй.

## Thread-ийн гүйцэтгэлийн загвар

Энэ нь **алхамчилсан загвар**. Worker-үүд бодит Pthreads боловч нэг tick дотор
үйлдлүүдийг ack semaphore-аар дараалан гүйцэтгүүлдэг. Pause үед загварын цаг
зогсоно; Step бүрэн дууссаны дараа snapshot уншина. Ижил seed, тохиргоо ижил
үйл явдал өгнө. Энэ хувилбар чөлөөт OS scheduling-ийн race/stress benchmark биш,
тусдаа real-time горимгүй. TA сул үед `work` semaphore дээр бодитоор блоклогдоно.

## Баримт бичиг

- [Хэрэглэгчийн болон operational заавар](sleeping-ta/docs/Manual.md)
- [10 бүлэгтэй тайлан](sleeping-ta/docs/Report.md)
- [Report PDF](sleeping-ta/docs/IV-2-10_BD1_Report.pdf)
- [Manual PDF](sleeping-ta/docs/IV-2-10_Manual.pdf)
- [Шинэ шалгалтын гаралт](sleeping-ta/docs/test-results-review.txt)
- [Release хийх заавар](sleeping-ta/docs/Release.md)

Код: `sleeping-ta/src/`; тест: `sleeping-ta/tests/`.
AI хэрэглээ: OpenAI ChatGPT-ийг код, тест, баримт бичиг боловсруулахад ашигласан.
Эх сурвалж: OS_BD1_Guide.pdf болон Operating System Concepts-ийн
Project 2 — The Sleeping Teaching Assistant.
