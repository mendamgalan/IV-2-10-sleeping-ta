# The Sleeping Teaching Assistant IV-2-10
F.CSM302 Үйлдлийн систем, Бие даалт 1.

C / POSIX Pthreads хөдөлгүүр + Python Tkinter удирдах цонх.
Оюутан бүр, TA тусдаа OS thread. UI нь C хөдөлгүүрийн snapshot-ыг харуулж,
тухайн хөдөлгүүрийг ажиллуулах, түр зогсоох, алхамчлах, reset хийх команд өгнө.

## Debian / Ubuntu дээр эхлүүлэх
```bash
sudo apt update
sudo apt install build-essential python3 python3-tk
make
make run
```
Python-ийн нэмэлт pip сан, интернет холболт ажиллах үед шаардлагагүй.
Linux график орчин шаардлагатай; Windows дээр WSL2 + WSLg ашиглана.
macOS болон native Windows энэ хувилбарын дэмжих орчин биш.

## Шалгах
```bash
make test
```
8 тест: FIFO, 0 сандал, 1 оюутан, их ачаалал, унтах/сэрэх,
seed/reset, буруу оролт, үйлчилгээний хугацаа.

## Файлууд
- `src/engine.c`: thread, mutex, semaphore, FIFO, загварын цаг.
- `src/model.py`: ctypes интерфейс.
- `src/app.py`: үндсэн удирдах цонх.
- `tests/test_engine.py`: хөдөлгүүрийн тест.
- `docs/Manual.md`: хэрэглэгчийн болон operational заавар.
- `docs/Report.md`: зохиомж, хэрэгжилт, туршилтын бодит үр дүн.
- `docs/test-results.txt`: ажиллуулсан тестийн гаралт.

## Хугацааны загвар
1 tick = 100 мс. Автомат горимд Tkinter 100 мс тутам хөдөлгүүрт tick өгнө.
Pause үед загварын цаг зогсоно; Step яг нэг tick ажиллуулж дууссаныг хүлээнэ.
Бодит `sleep()`-ийн оронд загварын цаг хэрэглэснээр pause/step найдвартай.
Thread-үүд semaphore дээр бодитоор блоклогдоно, busy-wait байхгүй.
Нэг tick дотор үйлчилгээ дуусах үйл явдлыг эхэлж, дараа нь оюутнуудыг
эргэдэг дарааллаар ажиллуулна. Иймээс энэ нь CPU scheduling хэмжих benchmark биш.

AI хэрэглээ: энэ хэрэгжилт, баримт бичиг, тестийг OpenAI ChatGPT-ийн тусламжтай боловсруулав.
Үндсэн эх сурвалж: өгсөн OS_BD1_Guide.pdf болон хэрэглэгчийн оруулсан
Operating System Concepts, Project 2 — The Sleeping Teaching Assistant шаардлага.
