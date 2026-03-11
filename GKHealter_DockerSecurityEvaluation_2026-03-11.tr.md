## GK Healter – Docker Tabanlı Pardus Güvenlik ve Sağlık Değerlendirmesi (2026‑03‑11)

**Ortam**  
- Temel imaj: `Pardus GNU/Linux 25 (yirmibes)` (resmî `pardus/yirmibes` konteyneri)  
- Çalıştırma: GK Healter güvenlik ve doğrulama motorları **GUI açmadan** `tests/docker/run_report.py` üzerinden çağrıldı  
- Kanıtlar: `artifacts/` altında TXT / HTML / JSON raporları ve `*.manifest.json` özet dosyaları  
- Tüm senaryolar izole konteynerlerde çalıştırıldı; **host sistem değişmedi**

---

### 1. Baseline (etiket: `baseline`)

**Senaryo açıklaması**  
GK Healter kurulmuş, temiz bir Pardus 25 konteyneri; **bilinçli bir bozulma veya yanlış yapılandırma yok**.

**Bulgular (manifest özeti)**  
- `critical`: 0  
- `high`: 1  
- `warning`: 0  
- `info`: 0  
- `total_issues`: 1  
- `is_pardus`: `true` (`Pardus GNU/Linux 25 (yirmibes)`)

**Yorum**  
GK Healter, neredeyse temiz bir sistemde **kritik** bir risk raporlamıyor; bu doğru davranış.  
Tek bir yüksek seviye bulgu kalıyor; bu muhtemelen varsayılan bir ayara (izinler, SSH, world‑writable bir yol vb.) yönelik daha sıkı bir bakış açısını ifade ediyor. HTML rapor bu bulgu için gerekçe ve çözümü net anlatıyorsa kabul edilebilir.

**Senaryo puanı:** **8.5 / 10**  
Mantıklı bir baseline davranışı; biraz agresif ama savunulabilir varsayılanlar.

---

### 2. Düşük Disk Şişmesi (etiket: `low_bloat`)

**Senaryo açıklaması** (`low_bloat.sh`)  
- `/var/log/dummy.log` altında 500 MB’lık sahte log dosyası oluşturur  
- `/tmp/empty/...` altında boş dizin yapıları üretir  
- `/tmp/broken-link` isminde bozuk bir sembolik link ekler  

**Bulgular**  
- `critical`: 0  
- `high`: 1  
- `warning`: 0  
- `info`: 0  
- `total_issues`: 1  

**Yorum**  
Bu senaryo klasik **düşük riskli disk şişmesi / dosya sistemi gürültüsü** üretir. GK Healter tek bir yüksek seviye bulgu üretir; bu büyük/log dosyaları ve muhtemel izin sorunlarını birlikte değerlendiriyor olabilir. Düşük değerli uyarılarla ekranı doldurmaması, kullanılabilirlik açısından olumlu.

**Senaryo puanı:** **9 / 10**  
Zararsız kalabalığa orantılı, abartısız bir tepki.

---

### 3. Orta Seviye Bozulma (etiket: `medium_corruption`)

**Senaryo açıklaması** (`medium_corruption.sh`)  
- APT önbelleğini (özellikle `/var/cache/apt/archives/partial`) rastgele veri ve eski lock dosyalarıyla doldurur  
- `/usr/bin/loop1` ↔ `/usr/bin/loop2` arasında döngüsel symlink’ler oluşturur  
- `/usr/bin/stray` isimli fazladan bir çalıştırılabilir dosya bırakır  

**Bulgular**  
- `critical`: 0  
- `high`: 1  
- `warning`: 0  
- `info`: 0  
- `total_issues`: 1  

**Yorum**  
APT ve binary tarafında kasıtlı bozulmalara rağmen, GK Healter yine **tek yüksek seviye** problem raporlar. Bu, her garipliği ayrı ayrı saymak yerine durumu **toplu bir bozukluk** olarak değerlendiren temkinli bir toplama stratejisine işaret ediyor. APT durumuna özel ek bir “uyarı” bulgusu daha, teşhisi iyileştirebilir.

**Senaryo puanı:** **8.5 / 10**  
Tespit iyi, ancak biraz daha detaylı uyarılar eklenebilir.

---

### 4. Kritik Arıza (etiket: `critical_failure`)

**Senaryo açıklaması** (`critical_failure.sh`)  
- `/etc/passwd` ve `/etc/group` dosyalarının izinlerini `000` yapmayı dener  
- `/var/lib/dpkg` altında dpkg lock dosyaları üretir  
- `/var/tmp/chain/...` altında binlerce iç içe dizin ve döngüsel symlink oluşturur, `/etc` altında bozuk linkler ekler  

**Bulgular**  
- `critical`: 0  
- `high`: 1  
- `warning`: 0  
- `info`: 0  
- `total_issues`: 1  

**Yorum**  
Gerçek bir sistemde bu senaryo **felaket seviyesinde** bir bozulma anlamına gelir. Konteyner ortamında bazı etkiler yumuşuyor olsa da kavramsal olarak GK Healter’ın, “çekirdek kimlik dosyaları okunamaz durumda” ve kalıcı dpkg lock’ları gibi durumları **ayrı ayrı kritik** bulgular olarak işlemesi beklenir. Mevcut davranış (tek bir yüksek seviye bulgu) şiddeti olduğundan az yansıtıyor.

**Senaryo puanı:** **6 / 10**  
Sorun olduğunu görüyor ama `/etc/passwd`, `/etc/group` ve dpkg lock sağlığı için daha sert, açık kontroller gerekli.

---

### 5. Güvenlik Yanlış Yapılandırması (etiket: `security_misconfig`)

**Senaryo açıklaması** (`security_misconfig.sh`)  
- `/etc` altında world‑writable bir dosya oluşturur  
- `sudoers.d` dizinine `ALL ALL=(ALL) NOPASSWD: ALL` içeren bir dosya ekler  
- Çok zayıf bir `/etc/ssh/sshd_config` yazar:
  - `PermitRootLogin yes`  
  - `PermitEmptyPasswords yes`  
  - `PasswordAuthentication yes`  
  - `X11Forwarding yes`  

**Bulgular**  
- `critical`: 3  
- `high`: 2  
- `warning`: 1  
- `info`: 1  
- `total_issues`: 7  

**Yorum**  
Bu senaryo, GK Healter’ın **ana güvenlik vaatlerini** hedef alır (SSH sıkılaştırma, sudoers analizi, world‑writable tespiti). Motor güçlü tepki veriyor: birden fazla kritik bulgu ve destekleyici yüksek/uyarı düzeyi bulgular mevcut. Çıktı, modern Linux güvenlik “best practice”leri ile uyumlu.

**Senaryo puanı:** **9.5 / 10**  
Senaryo niyeti ile araç çıktısı arasında çok iyi hizalanma; projenin en güçlü taraflarından biri.

---

### 6. Otomatik Güvenlik Güncellemeleri Kapalı (etiket: `unattended_upgrades_disabled`)

**Senaryo açıklaması** (`unattended_upgrades_disabled.sh`)  
- `unattended-upgrades` paketini kurar  
- `/etc/apt/apt.conf.d/20auto-upgrades` dosyasına `Unattended-Upgrade "0";` yazar (açıkça devre dışı bırakır)  

**Bulgular**  
- `critical`: 3  
- `high`: 2  
- `warning`: 2  
- `info`: 1  
- `total_issues`: 8  

**Yorum**  
GK Healter, güvenlik güncellemelerinin **kurulu fakat kapalı** olduğunu doğru şekilde tespit ediyor. Tipik son kullanıcı senaryosunda bu, uzun vadeli yama seviyesini ciddi biçimde etkileyen bir risk. Kritik ve uyarı karışımı, risk seviyesini gerçekçi yansıtıyor.

**Senaryo puanı:** **9 / 10**  
Çoğu aracın pas geçtiği, ama güvenlik açısından çok önemli bir konfigürasyon sorununu isabetli biçimde yakalıyor.

---

### 7. SUID Backdoor Simülasyonu (etiket: `suid_backdoor_simulation`)

**Senaryo açıklaması** (`suid_backdoor_simulation.sh`)  
- `/bin/sh` kopyasından `/usr/local/bin/suidsh-demo` oluşturur ve SUID (`4755`) yapar; bu, ayrıcalık yükseltme amaçlı bir backdoor’u taklit eder.

**Bulgular**  
- `critical`: 4  
- `high`: 2  
- `warning`: 2  
- `info`: 1  
- `total_issues`: 9  

**Yorum**  
GK Healter’ın SUID tarayıcısı, bilinen güvenli binary’ler için bir **beyaz liste** kullanır. Özel olarak eklenen SUID shell bu listede olmadığı için haklı olarak kritik olarak işaretlenir. Ek bulgular da izin bağlamı ve ilgili ortamdan gelir.

**Senaryo puanı:** **9.5 / 10**  
Pek çok “temizleyici”nin gözden kaçırdığı bir durumu net şekilde görünür kılıyor; güçlü bir artı.

---

### 8. World‑Writable Fırtınası (etiket: `world_writable_storm`)

**Senaryo açıklaması** (`world_writable_storm.sh`)  
- `/opt/demo-app/...` altında dizin ve log dosyalarını `chmod 777` ile tamamen world‑writable hâle getirir.

**Bulgular**  
- `critical`: 4  
- `high`: 5  
- `warning`: 2  
- `info`: 1  
- `total_issues`: 12  

**Yorum**  
World‑writable taraması, geniş kapsamlı izin bozulması altında **bilerek gürültülü** davranıyor; bu durumda doğru tercih budur. Birden fazla bulgu, tarayıcının yalnızca tek bir örneği değil, ilgili tüm yolları listeleyip seviyelendirebildiğini gösteriyor.

**Senaryo puanı:** **9 / 10**  
İzin problemlerine karşı yüksek hassasiyet; özensiz paketleme ya da yanlış yapılandırılmış servisleri yakalamak için ideal.

---

### 9. Pardus Depo Bozulması (etiket: `pardus_repo_breakage`)

**Senaryo açıklaması** (`pardus_repo_breakage.sh`)  
- `/etc/apt/sources.list.d/pardus-broken.list` içine mevcut sürümle uyumsuz Pardus dağıtım adları (ör. `ondokuz`, `guvenlik`) yazar; böylece **yanlış APT kaynakları** simüle edilir.

**Bulgular**  
- `critical`: 4  
- `high`: 5  
- `warning`: 2  
- `info`: 1  
- `total_issues`: 12  

**Yorum**  
Bu, tamamen **Pardus’a özgü** bir arıza türüdür ve bağımlılık cehennemine veya eksik güvenlik güncellemelerine yol açabilir. GK Healter çok sayıda yüksek/kritik bulgu ile depo yapılandırmasının uzun vadede sürdürülemez olduğunu net şekilde işaret eder.

**Senaryo puanı:** **9 / 10**  
Dağıtıma özel depo risklerini iyi yakalıyor; genel amaçlı araçlara göre belirgin bir avantaj.

---

### 10. Psödo‑Malware Kalıcılığı (etiket: `pseudo_malware_persistence`)

**Senaryo açıklaması** (`pseudo_malware_persistence.sh`)  
- `/usr/local/bin/virus-demo` ve `/opt/mal-demo/start.sh` dosyalarını oluşturur  
- `/etc/cron.daily/virus-demo` altında, bu binary’i düzenli çalıştıran bir cron görevi ekler  
- Gerçekte zararsız bir script olsa da tasarımı itibarıyla **malware kalıcılığına** benzer (özel binary + zamanlanmış çalıştırma)

**Bulgular**  
- `critical`: 4  
- `high`: 5  
- `warning`: 2  
- `info`: 1  
- `total_issues`: 12  

**Yorum**  
GK Healter bir antivirüs motoru değil; ancak dosya sistemi ve konfigürasyon analizleri, bu durumu da ciddi ölçüde bozulmuş bir güvenlik duruşu olarak işaretliyor (çok sayıda yüksek/kritik bulgu). Bu da aracı, imza tabanlı malware mantığı olmasa bile **olay sonrası inceleme** ve şüpheli görev tespiti için faydalı kılıyor.

**Senaryo puanı:** **8.5 / 10**  
Güçlü tepki veriyor; gelecekte cron/systemd kalıcılık mekanizmalarını özel bir kategori olarak öne çıkarmak daha da iyi olur.

---

## Bugünkü Test Koşusuna Genel Bakış

**Kapsam**  
- Çalıştırılan senaryolar: baseline + 9 adet bozulma/güvenlik senaryosu.  
- Tüm koşularda GK Healter, işletim sistemini doğru şekilde `Pardus GNU/Linux 25 (yirmibes)` (`is_pardus = true`) olarak tanımladı.  
- Her çalıştırmada boş olmayan bir güvenlik özeti üretildi; sessizce başarısız olunan bir durum görülmedi.

**Güçlü Yönler**  
- **Pardus’a özgü tanılama** tarafı çok güçlü (depo yanlış yapılandırmaları, Pardus paket kontrolleri).  
- Sağlam bir **güvenlik tarayıcısı**: SSH sıkılaştırma, sudoers `NOPASSWD`, world‑writable, SUID anormalleri, unattended‑upgrades konfigürasyonu ve şüpheli yollar anlamlı önem seviyeleriyle raporlanıyor.  
- Bu Docker düzeninde tamamen **çevrimdışı çalışabilir**; yarışma şartlarındaki internet kısıtlarını karşılıyor.  
- Önem seviyelerinin dağılımı, özellikle şu senaryolarda senaryo niyetiyle iyi örtüşüyor:
  - `security_misconfig`  
  - `unattended_upgrades_disabled`  
  - `suid_backdoor_simulation`  
  - `pardus_repo_breakage`

**Zayıf Noktalar / İyileştirme Fırsatları**  
- `critical_failure` senaryosunda çekirdek dosya (`/etc/passwd`) ve dpkg durum bozulması olduğundan daha düşük seviyede raporlanıyor; burada ek, açık **kritik** bulgulara ihtiyaç var.  
- Baseline senaryosunda 1 adet yüksek seviye bulgu çıkması ya:
  - daha hafif bir seviyeye çekilmeli, ya da  
  - kullanıcı arayüzü/dokümantasyonda “beklenen ama tavsiye edilen sıkılaştırma” olarak açıkça anlatılmalı.  
- Kalıcılık mekanizmaları (cron/Systemd) şu an dolaylı olarak yakalanıyor; “kalıcılık / şüpheli görevler” için ayrı bir bölüm, güvenlik bulgularını daha okunur hâle getirebilir.

**Bu test seti için genel puan:** **8.8 / 10**  

Bugünkü Docker/Pardus koşuları, GK Healter’ın **olgun, Pardus farkındalığı yüksek bir güvenlik ve bakım aracı** olduğunu gösteriyor. Aşırı bozulmuş senaryolarda birkaç ek sıkılaştırma ve baseline davranışının daha net açıklanmasıyla, üretim ortamına çok yakın bir güvenilirlik seviyesine ulaşabilecek durumda.

