# Sleeping TA программын хавтас

Төслийн бүрэн танилцуулга, clone болон суулгах заавар: [үндсэн README](../README.md).

Энэ хавтас Makefile агуулна:

```bash
make          # libta.so
make run      # цонх
make test     # C 2 тест + Python 26 тест (дэлгэцгүй бол: xvfb-run -a make test)
make tsan     # ThreadSanitizer-тэй stress тест
make docs     # Report.md, Manual.md-ээс PDF
```

- [Manual](docs/Manual.md) · [PDF](docs/IV-2-10_Manual.pdf)
- [Эцсийн тайлан (БД2)](docs/Report.md) · [PDF](docs/IV-2-10_BD2_Report.pdf) · [БД1-ийн тайлан](docs/IV-2-10_BD1_Report.pdf)
- [Тестийн гаралт](docs/test-results.txt)
