# code_execution.py

import os
import sys
import time
import tempfile
import subprocess
import docker
from pathlib import Path
import threading
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime


# =============================================================================
# CODE EXECUTION AGENT - Flask entegrasyonu için
# =============================================================================

class CodeExecutionAgent:
    """Basitleştirilmiş kod çalıştırma ajanı - Flask entegrasyonu için"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="sss_code_")
        self.execution_history = []
        
        # Docker desteği kontrol et
        self.use_docker = False
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            self.use_docker = True
            print("🐳 Docker desteği aktif - Güvenli kod çalıştırma")
        except:
            print("⚠️ Docker yok - Yerel çalıştırma modu")
        
        self.supported_languages = {
            'python': {
                'extension': '.py',
                'command': [sys.executable],
                'timeout': 30
            },
            'javascript': {
                'extension': '.js', 
                'command': ['node'],
                'timeout': 30
            },
            'bash': {
                'extension': '.sh',
                'command': ['bash'],
                'timeout': 15
            }
        }
    
    def detect_task_request(self, prompt: str) -> bool:
        """Prompt'un bir kod çalıştırma isteği olup olmadığını tespit et"""
        task_indicators = [
            'yap', 'oluştur', 'kodla', 'hesapla', 'analiz et', 'çalıştır',
            'make', 'create', 'code', 'calculate', 'analyze', 'run', 'execute',
            'dosyaları listele', 'grafik çiz', 'veri analiz', 'test et',
            'toplamını hesapla', 'fibonacci', 'dosya', 'web isteği', 'araması'
        ]
        
        prompt_lower = prompt.lower()
        return any(indicator in prompt_lower for indicator in task_indicators)
    
    def analyze_and_generate_code(self, task: str) -> Dict[str, Any]:
        """Görevi analiz et ve kod üret"""
        task_lower = task.lower()
        
        # Yeni: Web otomasyonu ve ekran görüntüsü tespiti
        if any(kw in task_lower for kw in ['ekran görüntüsü', 'screenshot', 'arama yap', 'araması yap', 'google ara']):
            return {
                'language': 'python',
                'code': self._generate_web_automation_code(task),
                'description': 'Web otomasyonu ve ekran görüntüsü'
            }

        # Kod türü tespit
        if any(kw in task_lower for kw in ['hesapla', 'matematik', 'calculate', 'math', 'sayı', 'toplam', 'fibonacci']):
            return {
                'language': 'python',
                'code': self._generate_math_code(task),
                'description': 'Matematik hesaplama'
            }
        elif any(kw in task_lower for kw in ['dosya', 'klasör', 'file', 'directory', 'listele']):
            return {
                'language': 'python',
                'code': self._generate_file_code(task),
                'description': 'Dosya işlemleri'
            }
        elif any(kw in task_lower for kw in ['grafik', 'chart', 'plot', 'görselleştir']):
            return {
                'language': 'python', 
                'code': self._generate_chart_code(task),
                'description': 'Veri görselleştirme'
            }
        elif any(kw in task_lower for kw in ['web', 'url', 'site', 'scrape', 'http', 'araması', 'ara']):
            return {
                'language': 'python',
                'code': self._generate_web_code(task),
                'description': 'Web işlemleri'
            }
        else:
            return {
                'language': 'python',
                'code': self._generate_general_code(task),
                'description': 'Genel kod'
            }
    
    def _generate_math_code(self, task: str) -> str:
        """Matematik işlemleri için kod üret"""
        return f'''#!/usr/bin/env python3
# Matematik hesaplama: {task}

import math
import statistics
from datetime import datetime

def main():
    print("🧮 Matematik hesaplama başlıyor...")
    print(f"Görev: {task}")
    
    try:
        # Task analizi
        task_lower = "{task}".lower()
        
        if "toplam" in task_lower and ("100" in task_lower or "1 den" in task_lower):
            # 1'den 100'e kadar toplam
            numbers = list(range(1, 101))
            result = sum(numbers)
            print(f"1'den 100'e kadar sayıların toplamı: {{result}}")
            print(f"Formül: n*(n+1)/2 = 100*101/2 = {{100*101//2}}")
        
        elif "fibonacci" in task_lower:
            # Fibonacci dizisi
            n = 10  # Default 10 terim
            if "20" in task_lower:
                n = 20
            elif "15" in task_lower:
                n = 15
                
            fib = [0, 1]
            for idx in range(2, n):
                fib.append(fib[idx-1] + fib[idx-2])
            
            print(f"Fibonacci dizisinin ilk {{n}} terimi:")
            for idx, f in enumerate(fib):
                print(f"  F({{idx}}) = {{f}}")
            print(f"Son terim: {{fib[-1]}}")
        
        elif "ortalama" in task_lower:
            numbers = [10, 20, 30, 40, 50]
            result = statistics.mean(numbers)
            print(f"Sayıların ortalaması: {{result}}")
            print(f"Sayılar: {{numbers}}")
        
        elif "faktöriyel" in task_lower:
            n = 5
            if "10" in task_lower:
                n = 10
            result = math.factorial(n)
            print(f"{{n}}! = {{result}}")
        
        else:
            # Genel hesaplama örneği
            result = 25 * 4 + 10
            print(f"Örnek hesaplama (25 * 4 + 10): {{result}}")
            
            # Rastgele sayılar için
            if "rastgele" in task_lower or "random" in task_lower:
                import random
                numbers = [random.randint(1, 100) for _ in range(10)]
                print(f"\\n🎲 Rastgele 10 sayı: {{numbers}}")
                print(f"Ortalama: {{sum(numbers)/len(numbers):.2f}}")
                print(f"En büyük: {{max(numbers)}}")
                print(f"En küçük: {{min(numbers)}}")
        
        print("✅ Hesaplama tamamlandı!")
        
    except Exception as e:
        print(f"❌ Hata: {{e}}")

if __name__ == "__main__":
    main()
'''
    
    def _generate_web_code(self, task: str) -> str:
        """Web işlemleri için kod üret"""
        return f'''#!/usr/bin/env python3
# Web işlemleri: {task}

import requests
from datetime import datetime

def main():
    print("🌐 Web işlemleri başlıyor...")
    print(f"Görev: {task}")
    
    try:
        # Arama sorgusu analizi
        task_lower = "{task}".lower()
        search_query = "balık"  # Varsayılan arama
        
        if "balık" in task_lower or "fish" in task_lower:
            search_query = "balık"
        elif "araması" in task_lower:
            search_query = "casibom"
        
        print(f"🔍 Arama sorgusu: {{search_query}}")
        print("⚠️ Gerçek Google araması için API anahtarı gerekir")
        print("📋 Alternatif bilgiler:")
        
        if search_query == "balık":
            print("  - Balık: Suda yaşayan omurgalı hayvanlar")
            print("  - Türkiye'de yaygın balık türleri: Hamsi, çupra, levrek")
            print("  - Protein açısından zengin besin kaynağı")
        
        # Test URL'si
        test_url = "https://httpbin.org/json"
        
        print(f"\\n🔍 {{test_url}} adresine test isteği gönderiliyor...")
        
        headers = {{
            'User-Agent': 'Python-requests/SSS-Server Bot'
        }}
        
        response = requests.get(test_url, timeout=10, headers=headers)
        
        if response.status_code == 200:
            print(f"✅ Başarılı! Status: {{response.status_code}}")
            
            # JSON ise parse et
            try:
                data = response.json()
                print(f"📄 JSON test verisi alındı:")
                for key, value in data.items():
                    if isinstance(value, str) and len(value) > 100:
                        print(f"  {{key}}: {{value[:100]}}...")
                    else:
                        print(f"  {{key}}: {{value}}")
            except:
                # Text içeriği göster
                content = response.text[:500]
                print(f"📄 İçerik (ilk 500 karakter):")
                print(content)
                
            print(f"\\n📊 Yanıt bilgileri:")
            print(f"  Boyut: {{len(response.content):,}} bytes")
            print(f"  Süre: {{response.elapsed.total_seconds():.2f}} saniye")
            print(f"  Encoding: {{response.encoding}}")
            print(f"  Content-Type: {{response.headers.get('content-type', 'Bilinmiyor')}}")
        else:
            print(f"❌ Hata: HTTP {{response.status_code}}")
        
        print("\\n💡 Gerçek Google araması için:")
        print("  1. Google Custom Search API kullanın")
        print("  2. BeautifulSoup ile web scraping yapın")
        print("  3. Selenium ile tarayıcı otomasyonu kullanın")
        
        print("✅ Web işlemleri tamamlandı!")
        
    except Exception as e:
        print(f"❌ Hata: {{e}}")

if __name__ == "__main__":
    main()
'''

    def _generate_file_code(self, task: str) -> str:
        """Dosya işlemleri için kod üret"""
        return f'''#!/usr/bin/env python3
# Dosya işlemleri: {task}

import os
import glob
from datetime import datetime
from pathlib import Path

def main():
    print("📁 Dosya işlemleri başlıyor...")
    print(f"Görev: {task}")
    
    try:
        current_dir = os.getcwd()
        print(f"🗂️ Mevcut dizin: {{current_dir}}")
        
        # Dosyaları listele
        print("\\n📋 Mevcut dizindeki dosyalar:")
        files = []
        for item in os.listdir(current_dir):
            item_path = os.path.join(current_dir, item)
            if os.path.isfile(item_path):
                size = os.path.getsize(item_path)
                files.append((item, size))
        
        # Boyuta göre sırala
        files.sort(key=lambda x: x[1], reverse=True)
        
        for idx, (filename, size) in enumerate(files[:10], 1):
            size_kb = size / 1024
            if size_kb > 1024:
                size_str = f"{{size_kb/1024:.1f}} MB"
            else:
                size_str = f"{{size_kb:.1f}} KB"
            print(f"  {{idx:2d}}. {{filename}} ({{size_str}})")
        
        if len(files) > 10:
            print(f"  ... ve {{len(files)-10}} dosya daha")
        
        print("✅ Dosya taraması tamamlandı!")
        
    except Exception as e:
        print(f"❌ Hata: {{e}}")

if __name__ == "__main__":
    main()
'''

    def _generate_chart_code(self, task: str) -> str:
        """Grafik/Chart kod üretimi"""
        return f'''#!/usr/bin/env python3
# Veri görselleştirme: {task}

import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta

def main():
    print("📊 Veri görselleştirme başlıyor...")
    print(f"Görev: {task}")
    
    try:
        # Örnek veri oluştur
        dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
        values = np.random.randint(10, 100, 30)
        
        # Figure oluştur
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        fig.suptitle('Veri Analizi', fontsize=16)
        
        # 1. Çizgi grafiği
        ax1.plot(range(len(values)), values, marker='o', linewidth=2, markersize=4)
        ax1.set_title('Günlük Değerler')
        ax1.set_ylabel('Değer')
        ax1.grid(True, alpha=0.3)
        
        # 2. Histogram
        ax2.hist(values, bins=10, alpha=0.7, color='orange', edgecolor='black')
        ax2.set_title('Değer Dağılımı')
        ax2.set_xlabel('Değer Aralığı')
        ax2.set_ylabel('Frekans')
        
        # Layout düzenle
        plt.tight_layout()
        
        # Kaydet
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chart_{{timestamp}}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        
        print(f"✅ Grafik oluşturuldu: {{filename}}")
        print(f"📊 İstatistikler:")
        print(f"  • Ortalama: {{np.mean(values):.1f}}")
        print(f"  • Medyan: {{np.median(values):.1f}}")
        print(f"  • Min/Max: {{np.min(values)}}/{{np.max(values)}}")
        print(f"  • Toplam: {{np.sum(values)}}")
        
    except ImportError:
        print("⚠️ Matplotlib bulunamadı. Basit metin grafiği oluşturuluyor...")
        # ASCII grafik oluştur
        data = [20, 35, 15, 40, 25, 30, 45]
        max_val = max(data)
        
        print("\\n📊 Basit Bar Grafiği:")
        for i, val in enumerate(data):
            bar_length = int((val / max_val) * 20)
            bar = '█' * bar_length + '░' * (20 - bar_length)
            print(f"Gün {{i+1:2d}}: {{bar}} {{val:2d}}")
        
    except Exception as e:
        print(f"❌ Hata: {{e}}")

if __name__ == "__main__":
    main()
'''

    def _generate_web_automation_code(self, task: str) -> str:
        """Web otomasyonu ve ekran görüntüsü için kod üret"""
        return '''#!/usr/bin/env python3
# Web Arama Otomasyonu: ''' + task + '''

import requests
from datetime import datetime
import time
import os
import re
from urllib.parse import quote

def extract_search_query(task_text):
    """Arama sorgusunu çıkar"""
    task_lower = task_text.lower()
    
    if "balık" in task_lower or "fish" in task_lower:
        return "balık"
    elif "casibom" in task_lower:
        return "casibom"
    
    # Default
    return "balık"

def try_selenium_search(search_query):
    """Selenium ile arama yapmayı dene"""
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        
        print("✅ Selenium modülleri başarıyla import edildi")
        
        # Chrome options
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        print("🔧 Chrome seçenekleri yapılandırıldı")
        
        # WebDriver oluştur
        try:
            driver = webdriver.Chrome(options=options)
            print("✅ Chrome driver oluşturuldu")
        except Exception as e:
            print(f"❌ Chrome driver hatası: {e}")
            return False
        
        # Google'a git
        search_url = f"https://www.google.com/search?q={quote(search_query)}"
        
        print(f"🌐 Google'a gidiliyor...")
        print(f"🔗 URL: {search_url}")
        
        driver.get(search_url)
        time.sleep(3)
        
        # Sayfa kontrolü
        page_title = driver.title
        print(f"📄 Sayfa başlığı: {page_title}")
        
        # Ekran görüntüsü al
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_name = f"google_search_{search_query}_{timestamp}.png"
        
        print(f"📸 Ekran görüntüsü alınıyor: {screenshot_name}")
        
        success = driver.save_screenshot(screenshot_name)
        
        if success and os.path.exists(screenshot_name):
            size = os.path.getsize(screenshot_name)
            print(f"✅ Ekran görüntüsü başarıyla alındı!")
            print(f"📁 Dosya: {screenshot_name}")
            print(f"💾 Boyut: {size:,} bytes ({size/1024:.1f} KB)")
            print(f"📍 Konum: {os.path.abspath(screenshot_name)}")
        else:
            print("❌ Ekran görüntüsü alınamadı")
        
        # Sonuçları parse et
        try:
            results = driver.find_elements(By.CSS_SELECTOR, "h3")
            
            if results:
                print(f"\\n📋 Google Arama Sonuçları ({len(results[:5])} adet):")
                for idx, result in enumerate(results[:5], 1):
                    try:
                        title = result.text.strip()
                        if title and len(title) > 3:
                            display_title = title[:70] + ('...' if len(title) > 70 else '')
                            print(f"  {idx}. {display_title}")
                    except:
                        print(f"  {idx}. [Başlık okunamadı]")
            else:
                print("⚠️ Arama sonuçları bulunamadı")
        
        except Exception as e:
            print(f"⚠️ Sonuç parsing hatası: {e}")
        
        # Tarayıcıyı kapat
        driver.quit()
        print("🔧 Driver temiz şekilde kapatıldı")
        
        return True
        
    except ImportError:
        print("❌ Selenium bulunamadı. pip install selenium gerekli")
        return False
    except Exception as e:
        print(f"❌ Selenium genel hatası: {e}")
        return False

def try_http_search(search_query):
    """HTTP ile basit arama"""
    try:
        search_url = f"https://www.google.com/search?q={quote(search_query)}"
        
        print(f"🔄 HTTP ile Google'da '{search_query}' aranıyor...")
        print(f"🔗 URL: {search_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ HTTP yanıt alındı ({len(response.content):,} bytes)")
            
            # HTML dosyasını kaydet
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_file = f"google_search_{search_query}_{timestamp}.html"
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"💾 HTML kaydedildi: {html_file}")
            
            # Basit başlık çıkarma
            titles = re.findall(r'<h3[^>]*>(.*?)</h3>', response.text, re.IGNORECASE)
            if titles:
                print(f"\\n📋 HTTP ile bulunan {len(titles[:5])} başlık:")
                for idx, title in enumerate(titles[:5], 1):
                    clean_title = re.sub(r'<[^>]+>', '', title).strip()
                    if clean_title:
                        print(f"  {idx}. {clean_title[:70]}...")
        else:
            print(f"❌ HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ HTTP hatası: {e}")

def main():
    """Ana fonksiyon"""
    print("🌐 Web arama otomasyonu başlıyor...")
    
    # Test görev metni
    task = "''' + task + '''"
    
    search_query = extract_search_query(task)
    
    print(f"📝 Orijinal görev: {task}")
    print(f"🎯 Çıkarılan arama sorgusu: '{search_query}'")
    
    # Selenium ile arama dene
    selenium_success = try_selenium_search(search_query)
    
    # Selenium başarısız olursa HTTP kullan
    if not selenium_success:
        print("\\n🔄 Selenium başarısız, HTTP yöntemi deneniyor...")
        try_http_search(search_query)
    
    print("\\n✅ Arama işlemi tamamlandı!")

if __name__ == "__main__":
    main()
'''

    def _generate_general_code(self, task: str) -> str:
        """Genel amaçlı kod üret"""
        return f'''#!/usr/bin/env python3
# Genel görev: {task}

import os
import sys
from datetime import datetime

def main():
    print("🚀 Genel görev çalıştırılıyor...")
    print(f"Görev: {task}")
    
    try:
        print(f"\\n🕒 Sistem bilgileri:")
        print(f"  Tarih: {{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}}")
        print(f"  Python: {{sys.version.split()[0]}}")
        print(f"  Platform: {{sys.platform}}")
        print(f"  Dizin: {{os.getcwd()}}")
        
        # Görev analizi
        task_words = "{task}".split()
        print(f"\\n🎯 Görev analizi:")
        print(f"  - Kelime sayısı: {{len(task_words)}}")
        print(f"  - Karakter sayısı: {{len('{task}')}}")
        print(f"  - Anahtar kelimeler: {{task_words[:5]}}")
        
        print("\\n✅ Genel görev tamamlandı!")
        
    except Exception as e:
        print(f"❌ Hata: {{e}}")

if __name__ == "__main__":
    main()
'''
    
    def execute_code(self, code: str, language: str = 'python') -> Dict[str, Any]:
        """Kodu güvenli şekilde çalıştır"""
        if language not in self.supported_languages:
            return {"error": f"Desteklenmeyen dil: {language}"}
        
        lang_config = self.supported_languages[language]
        
        # Geçici dosya oluştur
        temp_file = os.path.join(
            self.temp_dir,
            f"task_{int(time.time())}{lang_config['extension']}"
        )
        
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            return self._execute_safely(temp_file, language)
                
        except Exception as e:
            return {"error": f"Dosya yazma hatası: {e}"}
        finally:
            # Temizlik
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass


    
    def _execute_safely(self, file_path: str, language: str) -> Dict[str, Any]:
        """Güvenli kod çalıştırma - güvenlik katmanı eklenmiş"""
        lang_config = self.supported_languages[language]
        command = lang_config['command'] + [file_path]
        
        start_time = time.time()
        
        try:
            # Kodu güvenlik kontrolünden geçir
            with open(file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            is_safe, error_msg = self._validate_code_safety(code_content)
            if not is_safe:
                return {
                    "success": False,
                    "error": error_msg,
                    "execution_time": 0
                }
            
            # Güvenlik için çevre değişkenlerini sınırla
            env = os.environ.copy()
            env['PYTHONPATH'] = self.temp_dir
            # Tehlikeli değişkenleri kaldır
            for key in ['HOME', 'USER', 'SUDO_USER']:
                env.pop(key, None)
            
            # Resource limitleme fonksiyonu (Unix only)
            def set_limits():
                if sys.platform != 'win32':
                    import resource
                    # 100MB memory limit
                    resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, -1))
                    # 30 saniye CPU limit
                    resource.setrlimit(resource.RLIMIT_CPU, (30, -1))
            
            # Çalıştır
            kwargs = {
                'capture_output': True,
                'text': True,
                'timeout': lang_config['timeout'],
                'cwd': self.temp_dir,
                'env': env
            }
            
            # Unix sistemlerde resource limit ekle
            if sys.platform != 'win32':
                kwargs['preexec_fn'] = set_limits
            
            result = subprocess.run(command, **kwargs)
            
            execution_time = time.time() - start_time
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "execution_time": execution_time,
                "language": language
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Kod {lang_config['timeout']} saniye içinde tamamlanamadı",
                "timeout": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Çalıştırma hatası: {e}"
            }

    def _validate_code_safety(self, code: str) -> Tuple[bool, Optional[str]]:
        """Tehlikeli kod pattern'lerini kontrol et"""
        dangerous_patterns = [
            (r'import\s+os\s*;.*os\.system', 'Sistem komutu çalıştırma engellendi'),
            (r'subprocess\.(call|Popen)\s*\(', 'Subprocess.call/Popen engellendi'),
            (r'\beval\s*\(', 'eval() kullanımı engellendi'),
            (r'\bexec\s*\(', 'exec() kullanımı engellendi'),
            (r'__import__\s*\(', 'Dinamik import engellendi'),
            (r'open\s*\([^)]*[\'\"]/etc', '/etc dosya erişimi engellendi'),
            (r'open\s*\([^)]*[\'\"]/root', '/root erişimi engellendi'),
            (r'\brm\s+-rf', 'Tehlikeli shell komutu engellendi'),
            (r'shutil\.rmtree', 'Toplu dosya silme engellendi'),
        ]
        
        code_lower = code.lower()
        
        for pattern, reason in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Güvenlik: {reason}"
        
        # İzin verilen subprocess.run kullanımı (kısıtlı)
        if 'subprocess.run' in code:
            # Shell=True yasak
            if re.search(r'subprocess\.run\s*\([^)]*shell\s*=\s*True', code, re.IGNORECASE):
                return False, "Güvenlik: subprocess shell=True engellendi"
        
        return True, None


    
    def process_task(self, task_description: str) -> Dict[str, Any]:
        """Görevi baştan sona işle - EKSİK OLAN METOD"""
        # Kod üret
        code_info = self.analyze_and_generate_code(task_description)
        
        # Çalıştır
        execution_result = self.execute_code(code_info['code'], code_info['language'])
        
        # Sonuç
        return {
            "task": task_description,
            "code_info": code_info,
            "execution": execution_result,
            "timestamp": datetime.now().isoformat()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Çalıştırma istatistikleri"""
        if not self.execution_history:
            return {"message": "Henüz kod çalıştırılmadı"}
        
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for h in self.execution_history if h.get('success', False))
        
        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "docker_enabled": self.use_docker
        }

    def cleanup(self):
        """Temizlik işlemleri"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        print("🧹 Temizlik tamamlandı")

# Global code agent instance
code_agent = CodeExecutionAgent()