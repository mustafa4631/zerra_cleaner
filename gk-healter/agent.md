# GK Healter - Project Intelligence

## Overview
**GK Healter** Linux tabanlı sistemler (özellikle Pardus) için geliştirilmiş modern bir bakım, temizlik ve güvenlik aracıdır.

## Temel Özellikler
- **Sistem Temizleyici**: Loglar, coredump dosyaları ve tarayıcı önbelleklerini temizler. Paket yöneticisi (APT/DNF) entegrasyonuna sahiptir.
- **Yapay Zeka (AI) Motoru**: Sistem analizi yaparak performans iyileştirme önerileri sunar.
- **Güvenlik Tarayıcı**: Sistem zafiyetlerini denetler ve güvenlik skorlaması yapar.
- **Sağlık İzleyici**: CPU, RAM ve Disk kullanımını anlık izleyerek "Sistem Sağlık Puanı" hesaplar.
- **Disk Analizi**: Dosya boyutlarını görselleştirir ve yer kaplayan öğeleri tespit eder.
- **Otomatik Bakım**: Planlanmış rutin temizlik görevlerini yönetir.
- **Pardus Özelleştirmeleri**: Pardus sistem bileşenleri için özel doğrulama ve analiz araçları içerir.

## Teknik Detaylar
- **Dil**: Python 3
- **Arayüz**: PyQt / Qt (.ui dosyaları ile desteklenir)
- **Paketleme**: Debian (.deb) ve Flatpak desteği.
- **Bağımlılıklar**: `psutil` (izleme), `pkexec` (yetkili işlemler), `gettext` (i18n).

## Dizin Yapısı
- `src/cleaner.py`: Temizlik mantığı ve güvenlik kontrolleri.
- `src/health_engine.py`: Donanım kaynakları ve sağlık skorlama.
- `src/ai_engine.py`: Analiz ve öneri algoritmaları.
- `src/ui.py`: Kullanıcı arayüzü ve olay yönetimi.
- `src/settings_manager.py`: Uygulama yapılandırmaları.
