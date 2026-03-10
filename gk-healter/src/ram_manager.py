import os
import subprocess
import psutil
import logging
from typing import Dict, Any

logger = logging.getLogger("gk-healter.ram_manager")

class RAMManager:
    """
    Linux sistemleri için profesyonel RAM (PageCache, dentries, inodes) temizleyici.
    pkexec (Polkit) üzerinden yetki yükselterek çalışır.
    """

    def __init__(self):
        self.supported = self._check_support()
        
    def _check_support(self) -> bool:
        """Sistemin Linux olup olmadığını ve drop_caches dosyasını destekleyip desteklemediğini kontrol eder."""
        if os.name != "posix":
            return False
        if not os.path.exists("/proc/sys/vm/drop_caches"):
            return False
        return True

    def clean_ram(self, level: int = 3) -> Dict[str, Any]:
        """
        Belirtilen seviyede RAM önbelleğini temizler (Drop Caches).
        
        Seviyeler (Linux Kernel):
        1 - Sadece PageCache temizler
        2 - Sadece dentries ve inodes temizler
        3 - PageCache, dentries ve inodes'un hepsini temizler
        
        Dönen dict formatı (ui.py ve history_manager.py entegrasyonu için):
        {
            "supported": bool,
            "needed": bool,
            "success": bool,
            "freed_mb": float,
            "before_percent": float,
            "after_percent": float,
            "message": str,
            "error": str (sadece hata varsa)
        }
        """
        result = {
            "supported": self.supported,
            "needed": True,
            "success": False,
            "freed_mb": 0.0,
            "before_percent": 0.0,
            "after_percent": 0.0,
            "message": "",
        }

        if not self.supported:
            result["error"] = "İşletim sistemi RAM temizliğini desteklemiyor (Sadece Linux desteklenir)."
            result["message"] = "Desteklenmeyen Sistem"
            return result

        if level not in [1, 2, 3]:
            level = 3

        try:
            mem_before = psutil.virtual_memory()
            result["before_percent"] = mem_before.percent
            
            # Removed the 20% restriction to allow manual override.
            # If user clicks the button, we perform the action regardless of current usage.

            # pkexec ile güvenli subprocess oluşturulması (önce veri kaybını önlemek için sync çalıştırılır)
            cmd = ["pkexec", "sh", "-c", f"sync && echo {level} > /proc/sys/vm/drop_caches"]
            
            logger.info("RAM önbellek temizliği başlatılıyor. Komut: %s", cmd)
            
            # Capture stderr to provide better error messages if pkexec fails
            subprocess.run(cmd, check=True, timeout=120, stderr=subprocess.PIPE)
            
            # Temizlik işlemi sonrasında belleğin durumu kontrol edilir
            mem_after = psutil.virtual_memory()
            result["after_percent"] = mem_after.percent
            
            # Ne kadar alanın boşaltıldığını Linux'ta genelde "cached" düşüşü ile anlarız.
            if hasattr(mem_before, 'cached') and hasattr(mem_after, 'cached'):
                freed_bytes = mem_before.cached - mem_after.cached
            else:
                freed_bytes = mem_after.free - mem_before.free

            # Dalgalanmalar nedeniyle eksi değer çıkarsa 0 olarak kabul edelim
            freed_mb = max(0.0, freed_bytes / (1024 * 1024))
            
            result["freed_mb"] = freed_mb
            result["success"] = True
            
            if freed_mb > 0:
                result["message"] = f"Başarıyla {freed_mb:.2f} MB RAM önbellek temizlendi."
            else:
                result["message"] = "Önbellek temizlendi ancak belirgin bir MB boşalması olmadı."

        except subprocess.TimeoutExpired:
            logger.error("RAM temizliği yetkilendirme zaman aşımına uğradı.")
            result["error"] = "Yetkilendirme zaman aşımı"
            result["message"] = "İşlem çok uzun sürdü"
        except subprocess.CalledProcessError as e:
            stderr_msg = e.stderr.decode(errors='replace') if e.stderr else "Bilinmeyen hata"
            logger.error("RAM temizliği komutu başarısız oldu. Hata Kodu: %s, Hata: %s", e.returncode, stderr_msg)
            # pkexec hataları (126, 127 genellikle iptal veya no-auth)
            if e.returncode in [126, 127, 1]:
                result["error"] = "Kullanıcı root yetkisini iptal etti veya yetki reddedildi."
                result["message"] = "Yetkilendirme iptal edildi"
            else:
                result["error"] = f"Komut başarısız oldu: {stderr_msg}"
                result["message"] = "Temizlik komutu çalışmadı"
        except PermissionError:
            logger.error("RAM temizleyici için root yetkisi verilmedi (PermissionError).")
            result["error"] = "root yetkisi gereklidir."
            result["message"] = "Yetki reddedildi"
        except Exception as e:
            logger.error("RAM temizliği sırasında beklenmeyen hata oluştu: %s", str(e))
            result["error"] = str(e)
            result["message"] = "Bilinmeyen bir hata oluştu"

        return result
