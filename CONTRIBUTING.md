# GK Healter — Katkı Rehberi / Contributing Guide

GK Healter'a katkı sağlamak istediğiniz için teşekkürler! Bu belge katkı sürecini açıklar.

## Geliştirme Ortamı

### Gereksinimler

- Python 3.9+
- GTK 3 (PyGObject)
- psutil
- Meson (build system)

### Kurulum (CachyOS / Arch)

```bash
sudo pacman -S python python-gobject gtk3 python-psutil meson ninja
```

### Kurulum (Pardus / Debian)

```bash
sudo apt install python3 python3-gi python3-psutil gir1.2-gtk-3.0 meson
```

### Projeyi Çalıştırma

```bash
cd gk-healter
make run
```

### Testleri Çalıştırma

```bash
pip install pytest
pytest tests/ -v
```

## Proje Yapısı

```
gk-healter/
├── src/                    # Python kaynak kodları
│   ├── main.py             # Uygulama giriş noktası
│   ├── ui.py               # GTK UI kontrolcüsü
│   ├── cleaner.py          # Temizleme motoru
│   ├── pardus_analyzer.py  # Pardus-spesifik analizler
│   ├── health_engine.py    # Sistem sağlık izleme
│   ├── ai_engine.py        # AI analiz motoru
│   └── ...
├── resources/              # GTK Builder XML dosyaları
├── data/                   # Desktop, metainfo, polkit policy
├── tests/                  # pytest test dosyaları
└── packaging/              # Dağıtım paketleme dosyaları
```

## Katkı Süreci

1. Repo'yu fork edin
2. Feature branch oluşturun: `git checkout -b feature/ozellik-adi`
3. Değişikliklerinizi yapın
4. Testleri çalıştırın: `pytest tests/ -v`
5. Commit edin: `git commit -m "feat: özellik açıklaması"`
6. Push edin: `git push origin feature/ozellik-adi`
7. Pull Request açın

## Commit Mesajları

[Conventional Commits](https://www.conventionalcommits.org/) formatını kullanın:

- `feat:` — Yeni özellik
- `fix:` — Hata düzeltme
- `docs:` — Dokümantasyon
- `test:` — Test ekleme/düzeltme
- `refactor:` — Kod yapısı değişikliği
- `style:` — Biçimlendirme (işlevsel değişiklik yok)

## Kod Standartları

- PEP 8 uyumlu kod
- Type hints kullanın
- Docstrings ekleyin
- Yeni özellikler için test yazın
- `logging` modülünü kullanın (`print()` değil)
- Subprocess çağrılarında `timeout` parametresi kullanın

## Lisans

MIT lisansı altında katkılar kabul edilir. Katkı yaparak kodunuzun MIT lisansı ile dağıtılmasını kabul etmiş olursunuz.
