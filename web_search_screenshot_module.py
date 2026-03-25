# web_search_screenshot_module.py
import asyncio
import aiohttp
import requests
import json
import time
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import base64
from io import BytesIO
from urllib.parse import urljoin, urlparse, quote_plus
import hashlib
import tempfile
try:
    from duckduckgo_search import DDGS
except ImportError:
    from ddgs import DDGS

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# SSL logging'i azalt
logging.getLogger("ddgs.ddgs").setLevel(logging.WARNING)

# Screenshot için gerekli kütüphaneler
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium kurulu değil. Screenshot özelliği çalışmayacak.")
    print("Kurulum: pip install selenium webdriver-manager")

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ Pillow kurulu değil. Görsel işleme özelliği sınırlı olacak.")

# BeautifulSoup HTML parsing için
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("⚠️ BeautifulSoup4 kurulu değil. HTML parsing çalışmayacak.")

# Webdriver manager için
try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


    
class WebSearchAgent:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        })
        
        # Search engine endpoints
        self.search_engines = {
            'google': {
                'url': 'https://www.googleapis.com/customsearch/v1',
                'params_builder': self._build_google_params,
                'parser': self._parse_google_results
            },
            'duckduckgo': {
                'url': None,  # requests.get() çağırılmayacak
                'params_builder': lambda q, max_results=10: {"q": q, "max_results": max_results},
                'parser': lambda data: self._ddg_wrapper(data["q"], data.get("max_results", 10))
            }
        }
        
        # Rate limiting
        self.last_search_time = {}
        self.min_search_interval = 2.0  # 2 saniye minimum aralık
        
    def _build_google_params(self, query: str, **kwargs) -> Dict:
        """Google Custom Search API parametreleri"""
        api_key = self.config.get('google_api_key') or os.getenv('GOOGLE_API_KEY')
        search_engine_id = self.config.get('google_search_engine_id') or os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        if not api_key or not search_engine_id:
            raise ValueError("Google API anahtarı veya Search Engine ID bulunamadı")
            
        return {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'num': kwargs.get('max_results', 10),
            'safe': 'active',
            'lr': 'lang_tr'  # Türkçe sonuçları öncelendir
        }
    
    def _build_duckduckgo_params(self, query: str, **kwargs) -> Dict:
        """DuckDuckGo API parametreleri - geliştirilmiş"""
        return {
            'q': query,
            'format': 'json',
            'no_redirect': '1',
            'no_html': '1',
            'skip_disambig': '1',
            'safe_search': 'moderate',
            't': 'bktyconsultancy'  # Custom identifier
        }
    
    def _parse_google_results(self, response_data: Dict) -> List[Dict]:
        """Google sonuçlarını parse et"""
        results = []
        items = response_data.get('items', [])
        
        for item in items:
            results.append({
                'title': item.get('title', ''),
                'url': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'display_url': item.get('displayLink', ''),
                'search_engine': 'google'
            })
            
        return results
    
    def _parse_duckduckgo_results(self, response_data: Dict) -> List[Dict]:
        """DuckDuckGo sonuçlarını parse et - geliştirilmiş"""
        results = []
        
        print(f"🔧 DuckDuckGo full response: {json.dumps(response_data, indent=2)[:1000]}...")
        
        # Abstract result
        abstract_text = response_data.get('Abstract', '').strip()
        if abstract_text:
            results.append({
                'title': response_data.get('AbstractSource', 'DuckDuckGo Abstract'),
                'url': response_data.get('AbstractURL', ''),
                'snippet': abstract_text,
                'display_url': response_data.get('AbstractSource', ''),
                'search_engine': 'duckduckgo'
            })
            print(f"✓ Abstract result added")

    def _ddg_wrapper(self, query: str, max_results: int = 10) -> List[Dict]:
        """DuckDuckGo gerçek SERP sonuçlarını getirir"""
        results = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                        "display_url": "duckduckgo.com",
                        "search_engine": "duckduckgo"
                    })
        except Exception as e:
            print(f"❌ DuckDuckGo wrapper hatası: {e}")
        return results

        # Answer result  
        answer_text = response_data.get('Answer', '').strip()
        if answer_text:
            results.append({
                'title': f"Direct Answer: {response_data.get('AnswerType', 'Information')}",
                'url': '',
                'snippet': answer_text,
                'display_url': 'DuckDuckGo',
                'search_engine': 'duckduckgo'
            })
            print(f"✓ Answer result added")

        # Definition result
        definition = response_data.get('Definition', '').strip()
        if definition:
            results.append({
                'title': f"Definition: {response_data.get('DefinitionSource', 'Dictionary')}",
                'url': response_data.get('DefinitionURL', ''),
                'snippet': definition,
                'display_url': response_data.get('DefinitionSource', ''),
                'search_engine': 'duckduckgo'
            })
            print(f"✓ Definition result added")

        # Related topics - hem flat hem nested
        for topic in response_data.get('RelatedTopics', []):
            if isinstance(topic, dict):
                if 'Text' in topic and topic['Text'].strip():
                    # Direct topic
                    results.append({
                        'title': topic.get('Text', '').split(' - ')[0][:100],
                        'url': topic.get('FirstURL', ''),
                        'snippet': topic.get('Text', ''),
                        'display_url': self._extract_domain(topic.get('FirstURL', '')),
                        'search_engine': 'duckduckgo'
                    })
                    print(f"✓ Topic result added")
                
                # Nested topics
                if 'Topics' in topic:
                    for subtopic in topic.get('Topics', []):
                        if isinstance(subtopic, dict) and subtopic.get('Text', '').strip():
                            results.append({
                                'title': subtopic.get('Text', '').split(' - ')[0][:100],
                                'url': subtopic.get('FirstURL', ''),
                                'snippet': subtopic.get('Text', ''),
                                'display_url': self._extract_domain(subtopic.get('FirstURL', '')),
                                'search_engine': 'duckduckgo'
                            })
                            print(f"✓ Subtopic result added")
        
        print(f"🔧 Total results parsed: {len(results)}")
        return results


    def search_with_fallback(self, query: str, engine: str = 'duckduckgo', max_results: int = 10):
        """Normal search + fallback system"""
        
        # Önce normal search
        result = self.search(query, engine, max_results)
        
        # Eğer başarılı ama 0 sonuç varsa fallback'leri dene
        if result.get('success') and result.get('total_results', 0) == 0:
            print(f"🔄 0 sonuç - fallback search deneniyor...")
            
            # 1. Wikipedia fallback
            wiki_results = self._search_wikipedia_fallback(query)
            if wiki_results:
                return {
                    "success": True,
                    "query": query,
                    "engine": "wikipedia_fallback",
                    "results": wiki_results,
                    "total_results": len(wiki_results),
                    "search_time": 0.5
                }
            
            # 2. Manual fallback
            manual_results = self._get_manual_results(query)
            if manual_results:
                return {
                    "success": True,
                    "query": query,
                    "engine": "manual_fallback",
                    "results": manual_results,
                    "total_results": len(manual_results),
                    "search_time": 0.1
                }
        
        return result

    def _search_wikipedia_fallback(self, query: str):
        """Wikipedia API fallback"""
        try:
            import requests
            
            # Türkçe Wikipedia'yı da dene
            for lang in ['en', 'tr']:
                wiki_url = f"https://{lang}.wikipedia.org/w/api.php"
                params = {
                    'action': 'query',
                    'format': 'json',
                    'list': 'search',
                    'srsearch': query,
                    'srlimit': 3
                }
                
                response = requests.get(wiki_url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    search_results = data.get('query', {}).get('search', [])
                    
                    if search_results:
                        results = []
                        for item in search_results:
                            title = item.get('title', '')
                            snippet = item.get('snippet', '')
                            # HTML tags temizle
                            import re
                            snippet = re.sub(r'<[^>]+>', '', snippet)
                            
                            results.append({
                                'title': title,
                                'url': f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}",
                                'snippet': snippet,
                                'display_url': f'{lang}.wikipedia.org',
                                'search_engine': f'wikipedia_{lang}'
                            })
                        
                        return results
        except Exception as e:
            print(f"Wikipedia fallback error: {e}")
        
        return []

    def _get_manual_results(self, query: str):
        """Manual curated results"""
        query_lower = query.lower()
        
        # Yapay zeka kütüphaneleri
        if any(term in query_lower for term in ['yapay zeka', 'ai', 'artificial intelligence', 'machine learning', 'ml', 'kütüphaneleri', 'libraries']):
            return [
                {
                    'title': 'TensorFlow - Yapay Zeka ve Makine Öğrenimi Kütüphanesi',
                    'url': 'https://www.tensorflow.org/',
                    'snippet': 'Google tarafından geliştirilen açık kaynaklı makine öğrenimi platformu. Derin öğrenme ve yapay zeka uygulamaları için kapsamlı araçlar sunar.',
                    'display_url': 'tensorflow.org',
                    'search_engine': 'manual'
                },
                {
                    'title': 'PyTorch - Derin Öğrenme Kütüphanesi',
                    'url': 'https://pytorch.org/',
                    'snippet': 'Meta (Facebook) AI tarafından geliştirilen dinamik sinir ağları kütüphanesi. Araştırmadan üretime esnek geçiş sağlar.',
                    'display_url': 'pytorch.org',
                    'search_engine': 'manual'
                },
                {
                    'title': 'scikit-learn - Python Makine Öğrenimi Kütüphanesi',
                    'url': 'https://scikit-learn.org/',
                    'snippet': 'Basit ve etkili veri analizi araçları. NumPy, SciPy ve matplotlib üzerine kurulu açık kaynak kütüphane.',
                    'display_url': 'scikit-learn.org',
                    'search_engine': 'manual'
                },
                {
                    'title': 'Keras - Derin Öğrenme API',
                    'url': 'https://keras.io/',
                    'snippet': 'İnsanlar için tasarlanmış derin öğrenme API. Basit, esnek ve güçlü yapay zeka modelleri oluşturmayı kolaylaştırır.',
                    'display_url': 'keras.io',
                    'search_engine': 'manual'
                }
            ]
        
        return []
    
    # web_search_screenshot_module.py içindeki search metodunu düzeltin

    def search(self, query: str, engine: str = 'duckduckgo', max_results: int = 10) -> Dict[str, Any]:
        """Web araması yap - 202 response düzeltilmiş"""
        print(f"🔍 Search başlatılıyor: query='{query}', engine='{engine}'")
        
        if not query.strip():
            return {"error": "Arama sorgusu boş olamaz"}
        
        # Query preprocessing - Türkçe karakterleri düzelt
        processed_query = self._preprocess_query(query)
        print(f"🔄 Processed query: '{processed_query}'")
        
        # Rate limiting check
        now = time.time()
        last_search = self.last_search_time.get(engine, 0)
        if now - last_search < self.min_search_interval:
            sleep_time = self.min_search_interval - (now - last_search)
            print(f"⏳ Rate limiting: waiting {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        try:
            if engine not in self.search_engines:
                return {"error": f"Desteklenmeyen arama motoru: {engine}"}
            
            search_config = self.search_engines[engine]
            params = search_config['params_builder'](processed_query, max_results=max_results)
            
            print(f"🔧 Request URL: {search_config['url']}")
            print(f"🔧 Request params: {params}")
            
            # DuckDuckGo için özel yol
            if engine == "duckduckgo":
                results = self._ddg_wrapper(processed_query, max_results)
                return {
                    "success": True,
                    "query": query,
                    "processed_query": processed_query,
                    "engine": engine,
                    "results": results,
                    "total_results": len(results),
                    "search_time": time.time() - now,
                    "response_status": 200
                }
            
            # Diğer motorlar için (Google vs.)
            headers = {
                'User-Agent': self.session.headers.get('User-Agent'),
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8'
            }
            
            response = self.session.get(
                search_config['url'],
                params=params,
                headers=headers,
                timeout=15
            )

            
            print(f"🔧 Response status: {response.status_code}")
            self.last_search_time[engine] = time.time()
            
            # 200 ve 202'yi başarılı olarak kabul et
            if response.status_code in [200, 202]:
                try:
                    data = response.json()
                    print(f"🔧 JSON parse başarılı, veri boyutu: {len(str(data))} karakter")
                    print(f"🔧 Response keys: {list(data.keys())}")
                    
                    results = search_config['parser'](data)
                    print(f"🔧 Parse edilmiş sonuç: {len(results)} adet")
                    
                    # Eğer sonuç yoksa ama response başarılıysa, boş sonuç döndür (hata değil)
                    if len(results) == 0:
                        print("⚠️ 0 sonuç - alternatif arama deneniyor...")
                        
                        # Sadece bir kez alternatif dene
                        if not hasattr(self, '_alternative_tried'):
                            self._alternative_tried = True
                            alternative_query = self._create_alternative_query(query)
                            
                            if alternative_query != processed_query:
                                print(f"🔄 Alternative query: {alternative_query}")
                                alternative_result = self.search(alternative_query, engine, max_results)
                                delattr(self, '_alternative_tried')  # Reset flag
                                return alternative_result
                            
                            delattr(self, '_alternative_tried')  # Reset flag
                        
                        # Alternatif de sonuç vermezse boş sonuç döndür
                        return {
                            "success": True,
                            "query": query,
                            "processed_query": processed_query,
                            "engine": engine,
                            "results": [],
                            "total_results": 0,
                            "search_time": time.time() - now,
                            "response_status": response.status_code,
                            "message": "Arama tamamlandı ancak sonuç bulunamadı"
                        }
                    
                    return {
                        "success": True,
                        "query": query,
                        "processed_query": processed_query,
                        "engine": engine,
                        "results": results,
                        "total_results": len(results),
                        "search_time": time.time() - now,
                        "response_status": response.status_code
                    }
                    
                except json.JSONDecodeError as json_error:
                    print(f"❌ JSON parse hatası: {json_error}")
                    print(f"❌ Response content (first 500 chars): {response.text[:500]}...")
                    return {
                        "success": False, 
                        "error": f"JSON parse hatası: {str(json_error)}",
                        "raw_response": response.text[:200]
                    }
            else:
                print(f"❌ HTTP error: {response.status_code}")
                print(f"❌ Response content: {response.text[:200]}...")
                return {
                    "success": False,
                    "error": f"HTTP hatası: {response.status_code}",
                    "status_code": response.status_code
                }
                
        except requests.exceptions.Timeout:
            print(f"❌ Timeout error")
            return {"success": False, "error": "Arama zaman aşımına uğradı"}
            
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection error")
            return {"success": False, "error": "Bağlantı hatası"}
            
        except Exception as e:
            print(f"❌ Genel hata: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": f"Arama hatası: {str(e)}"}

    def _preprocess_query(self, query: str) -> str:
        """Query'yi preprocessing yap"""
        import unicodedata
        
        # Türkçe karakterleri düzelt
        query = unicodedata.normalize('NFC', query)
        
        # Fazla boşlukları temizle
        query = ' '.join(query.split())
        
        # Çok uzun query'leri kısalt
        if len(query) > 200:
            query = query[:200]
        
        return query.strip()

    def _create_alternative_query(self, original_query: str) -> str:
        """Alternatif query oluştur"""
        query_lower = original_query.lower()
        
        # Türkçe -> İngilizce çeviriler (genel)
        common_translations = {
            "nedir": "what is",
            "nasıl": "how",
            "ne zaman": "when", 
            "nerede": "where",
            "kim": "who",
            "neden": "why",
            "araştır": "research",
            "ara": "search",
            "bul": "find",
            "incele": "investigate",
            "kontrol et": "check",
            "öğren": "learn about",
            "hakkında": "about",
            "ile ilgili": "about",
            "son haberler": "latest news",
            "güncel": "current",
            "bugün": "today",
            "şimdi": "now",
            "kütüphaneleri": "libraries",
            "araçları": "tools",
            "framework": "framework"
        }
        
        alternative = original_query
        for tr_word, en_word in common_translations.items():
            alternative = alternative.replace(tr_word, en_word)
        
        # Eğer değişiklik olduysa alternatifi döndür
        if alternative.lower() != original_query.lower():
            return alternative
        
        # Değişiklik olmadıysa orijinali döndür
        return original_query
    
    async def async_search(self, query: str, engine: str = 'duckduckgo', max_results: int = 10) -> Dict[str, Any]:
        """Asenkron web araması"""
        if not query.strip():
            return {"error": "Arama sorgusu boş olamaz"}
        
        try:
            if engine not in self.search_engines:
                return {"error": f"Desteklenmeyen arama motoru: {engine}"}
            
            search_config = self.search_engines[engine]
            params = search_config['params_builder'](query, max_results=max_results)
            
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.get(search_config['url'], params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = search_config['parser'](data)
                        
                        return {
                            "success": True,
                            "query": query,
                            "engine": engine,
                            "results": results,
                            "total_results": len(results),
                            "search_time": time.time() - start_time
                        }
                    else:
                        return {"error": f"Arama API hatası: {response.status}"}
                        
        except Exception as e:
            logger.error(f"Async search error: {e}")
            return {"error": f"Arama hatası: {str(e)}"}

class ScreenshotAgent:
    """Ekran görüntüsü alan agent"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.driver = None
        self.driver_options = None
        self._setup_driver_options()
        
    def _setup_driver_options(self):
        """Chrome driver seçeneklerini ayarla"""
        if not SELENIUM_AVAILABLE:
            return
            
        self.driver_options = Options()
        
        # Headless mode
        if self.config.get('headless', True):
            self.driver_options.add_argument('--headless')
            
        # Diğer seçenekler
        self.driver_options.add_argument('--no-sandbox')
        self.driver_options.add_argument('--disable-dev-shm-usage')
        self.driver_options.add_argument('--disable-web-security')
        self.driver_options.add_argument('--allow-running-insecure-content')
        self.driver_options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Pencere boyutu
        width = self.config.get('window_width', 1920)
        height = self.config.get('window_height', 1080)
        self.driver_options.add_argument(f'--window-size={width},{height}')
        
        # User agent
        user_agent = self.config.get('user_agent', 
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
        self.driver_options.add_argument(f'--user-agent={user_agent}')
    
    def _get_driver(self):
        """Driver'ı başlat"""
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("Selenium kurulu değil")
            
        if self.driver is None:
            try:
                if WEBDRIVER_MANAGER_AVAILABLE:
                    service = webdriver.chrome.service.Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=self.driver_options)
                else:
                    self.driver = webdriver.Chrome(options=self.driver_options)
                    
                # Timeouts
                self.driver.implicitly_wait(10)
                self.driver.set_page_load_timeout(30)
                
            except Exception as e:
                logger.error(f"Driver başlatma hatası: {e}")
                raise
                
        return self.driver
    
    def take_screenshot(self, url: str, output_path: str = None, 
                       wait_time: int = 3, full_page: bool = True) -> Dict[str, Any]:
        """Web sayfasının ekran görüntüsünü al"""
        if not SELENIUM_AVAILABLE:
            return {"error": "Selenium kurulu değil"}
        
        start_time = time.time()
        
        try:
            driver = self._get_driver()
            
            # Sayfayı yükle
            driver.get(url)
            
            # Sayfanın yüklenmesini bekle
            if wait_time > 0:
                time.sleep(wait_time)
            
            # Tam sayfa screenshot için scroll
            if full_page:
                # Sayfanın tam yüksekliğini al
                total_height = driver.execute_script("return document.body.scrollHeight")
                viewport_height = driver.execute_script("return window.innerHeight")
                
                # Eğer sayfa viewport'tan büyükse, tam sayfa için ayarlama yap
                if total_height > viewport_height:
                    driver.set_window_size(1920, total_height)
            
            # Screenshot al
            if output_path is None:
                # Geçici dosya oluştur
                timestamp = int(time.time())
                hash_url = hashlib.md5(url.encode()).hexdigest()[:8]
                output_path = f"screenshot_{hash_url}_{timestamp}.png"
            
            # Screenshot'ı kaydet
            success = driver.save_screenshot(output_path)
            
            if success and os.path.exists(output_path):
                # Dosya boyutunu kontrol et
                file_size = os.path.getsize(output_path)
                
                # Base64 encode (isteğe bağlı)
                image_base64 = None
                if self.config.get('return_base64', False):
                    with open(output_path, 'rb') as f:
                        image_base64 = base64.b64encode(f.read()).decode('utf-8')
                
                return {
                    "success": True,
                    "url": url,
                    "screenshot_path": output_path,
                    "file_size": file_size,
                    "image_base64": image_base64,
                    "full_page": full_page,
                    "processing_time": time.time() - start_time
                }
            else:
                return {"error": "Screenshot alınamadı"}
                
        except TimeoutException:
            return {"error": "Sayfa yükleme zaman aşımı"}
        except WebDriverException as e:
            return {"error": f"WebDriver hatası: {str(e)}"}
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return {"error": f"Screenshot hatası: {str(e)}"}
    
    def take_element_screenshot(self, url: str, selector: str, 
                              output_path: str = None) -> Dict[str, Any]:
        """Belirli bir elementin ekran görüntüsünü al"""
        if not SELENIUM_AVAILABLE:
            return {"error": "Selenium kurulu değil"}
        
        try:
            driver = self._get_driver()
            driver.get(url)
            
            # Element'i bekle ve bul
            wait = WebDriverWait(driver, 10)
            element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            
            # Element screenshot
            if output_path is None:
                timestamp = int(time.time())
                hash_selector = hashlib.md5(selector.encode()).hexdigest()[:8]
                output_path = f"element_{hash_selector}_{timestamp}.png"
            
            success = element.screenshot(output_path)
            
            if success and os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                return {
                    "success": True,
                    "url": url,
                    "selector": selector,
                    "screenshot_path": output_path,
                    "file_size": file_size
                }
            else:
                return {"error": "Element screenshot alınamadı"}
                
        except TimeoutException:
            return {"error": "Element bulunamadı"}
        except Exception as e:
            logger.error(f"Element screenshot error: {e}")
            return {"error": f"Element screenshot hatası: {str(e)}"}
    
    def close(self):
        """Driver'ı kapat"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Driver kapatma hatası: {e}")
            finally:
                self.driver = None

class WebContentExtractor:
    """Web sayfalarından içerik çıkarma"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_text_content(self, url: str) -> Dict[str, Any]:
        """Sayfadan metin içeriği çıkar"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            if not BS4_AVAILABLE:
                return {
                    "success": True,
                    "url": url,
                    "raw_html": response.text[:5000],  # İlk 5000 karakter
                    "text": "BeautifulSoup kurulu değil, HTML parse edilemiyor"
                }
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Script ve style etiketlerini kaldır
            for script in soup(["script", "style"]):
                script.extract()
            
            # Metin içeriğini al
            text = soup.get_text()
            
            # Temizle
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Başlık ve meta bilgileri
            title = soup.find('title')
            title_text = title.text.strip() if title else "Başlık bulunamadı"
            
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''
            
            return {
                "success": True,
                "url": url,
                "title": title_text,
                "description": description,
                "text": text[:2000],  # İlk 2000 karakter
                "full_text": text,
                "word_count": len(text.split()),
                "char_count": len(text)
            }
            
        except Exception as e:
            logger.error(f"Content extraction error: {e}")
            return {"error": f"İçerik çıkarma hatası: {str(e)}"}

class WebSearchScreenshotModule:
    """Ana modül - Web arama ve screenshot birleşimi"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.search_agent = WebSearchAgent(self.config.get('search', {}))  # This line must exist
        self.screenshot_agent = ScreenshotAgent(self.config.get('screenshot', {}))
        self.content_extractor = WebContentExtractor()


        
        # İstatistikler
        self.stats = {
            "total_searches": 0,
            "total_screenshots": 0,
            "successful_searches": 0,
            "successful_screenshots": 0,
            "avg_search_time": 0.0,
            "avg_screenshot_time": 0.0
        }
    
    def filter_to_language(text: str, lang: str = "tr") -> str:
        detected = self.detect_user_language(text)
        return text if detected == lang else ""
    
    def search_and_screenshot(self, query: str, take_screenshots: bool = True,
                            max_results: int = 5, screenshot_count: int = 3) -> Dict[str, Any]:
        """Arama yap ve sonuçların ekran görüntüsünü al"""
        start_time = time.time()
        
        # Önce arama yap
        search_result = self.search_agent.search(query, max_results=max_results)
        self.stats["total_searches"] += 1
        
        if not search_result.get("success"):
            return search_result
        
        self.stats["successful_searches"] += 1
        self.stats["avg_search_time"] = (
            (self.stats["avg_search_time"] * (self.stats["successful_searches"] - 1) + 
             search_result.get("search_time", 0)) / self.stats["successful_searches"]
        )
        
        results = [
            {**r, "snippet": self.filter_to_language(r.get("snippet", ""), lang="tr")}
            for r in results
        ]
        
        # Screenshot al (istenirse)
        if take_screenshots and SELENIUM_AVAILABLE:
            screenshot_results = []
            screenshot_taken = 0
            
            for i, result in enumerate(results):
                if screenshot_taken >= screenshot_count:
                    break
                
                url = result.get("url", "")
                if not url or not url.startswith("http"):
                    continue
                
                self.stats["total_screenshots"] += 1
                screenshot_result = self.screenshot_agent.take_screenshot(url)
                
                if screenshot_result.get("success"):
                    self.stats["successful_screenshots"] += 1
                    screenshot_taken += 1
                    
                    # Screenshot bilgilerini result'a ekle
                    result["screenshot"] = screenshot_result
                    screenshot_results.append(screenshot_result)
                    
                    # İstatistik güncelle
                    self.stats["avg_screenshot_time"] = (
                        (self.stats["avg_screenshot_time"] * (self.stats["successful_screenshots"] - 1) + 
                         screenshot_result.get("processing_time", 0)) / self.stats["successful_screenshots"]
                    )
                else:
                    logger.warning(f"Screenshot alınamadı: {url} - {screenshot_result.get('error')}")
        
        return {
            "success": True,
            "query": query,
            "search_results": results,
            "total_results": len(results),
            "screenshots_taken": screenshot_taken if take_screenshots else 0,
            "processing_time": time.time() - start_time,
            "has_screenshots": take_screenshots and SELENIUM_AVAILABLE
        }
    
    def casibom_specific_search(self, query: str = "casibom") -> Dict[str, Any]:
        """Casibom'a özel arama ve analiz"""
        # Güvenlik uyarısı
        warning_message = """
        ⚠️ UYARI: Casibom gibi bahis sitelerine erişim Türkiye'de yasal kısıtlamalara tabidir.
        
        Bu araç sadece bilgi amaçlı kullanılmalıdır. Kumar bağımlılığı ciddi bir sorundur.
        Yardım için: Kumar Bağımlıları Derneği - 0212 217 16 50
        """
        
        search_queries = [
            f"{query} güncel giriş adresi",
            f"{query} mobil uygulama",
            f"{query} güvenilir mi",
            f"{query} şikayet yorumları"
        ]
        
        all_results = []
        
        for search_query in search_queries:
            try:
                result = self.search_agent.search(search_query, max_results=3)
                if result.get("success"):
                    all_results.extend(result["results"])
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"Casibom search error: {e}")
        
        return {
            "success": True,
            "warning": warning_message,
            "query": query,
            "results": all_results,
            "total_results": len(all_results),
            "disclaimer": "Bu bilgiler sadece eğitim amaçlıdır. Yasal sorumluluk kullanıcıya aittir."
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Modül istatistikleri"""
        search_success_rate = 0
        screenshot_success_rate = 0
        
        if self.stats["total_searches"] > 0:
            search_success_rate = self.stats["successful_searches"] / self.stats["total_searches"]
        
        if self.stats["total_screenshots"] > 0:
            screenshot_success_rate = self.stats["successful_screenshots"] / self.stats["total_screenshots"]
        
        return {
            **self.stats,
            "search_success_rate": search_success_rate,
            "screenshot_success_rate": screenshot_success_rate,
            "selenium_available": SELENIUM_AVAILABLE,
            "bs4_available": BS4_AVAILABLE,
            "pil_available": PIL_AVAILABLE
        }
    
    def cleanup(self):
        """Temizlik işlemleri"""
        self.screenshot_agent.close()

# Global instance
web_search_screenshot_module = WebSearchScreenshotModule()

def search_web(query: str, engine: str = "duckduckgo", max_results: int = 10) -> Dict[str, Any]:
    """Basit web arama fonksiyonu"""
    return web_search_screenshot_module.search_agent.search(query, engine, max_results)

def take_website_screenshot(url: str, output_path: str = None) -> Dict[str, Any]:
    """Website screenshot alma fonksiyonu"""
    return web_search_screenshot_module.screenshot_agent.take_screenshot(url, output_path)

def search_and_capture(query: str, take_screenshots: bool = True) -> Dict[str, Any]:
    """Arama + screenshot birleşik fonksiyon"""
    return web_search_screenshot_module.search_and_screenshot(query, take_screenshots)

# Test fonksiyonu
def test_web_search_module():
    """Modül testleri"""
    print("🧪 Web Search & Screenshot Module Test")
    print("=" * 50)
    
    # Dependencies kontrol
    print(f"Selenium: {'✅' if SELENIUM_AVAILABLE else '❌'}")
    print(f"BeautifulSoup4: {'✅' if BS4_AVAILABLE else '❌'}")
    print(f"Pillow: {'✅' if PIL_AVAILABLE else '❌'}")
    
    # Web arama testi
    print("\n🔍 Web Arama Testi:")
    search_result = search_web("Python nedir", max_results=3)
    if search_result.get("success"):
        print(f"✅ Arama başarılı: {search_result['total_results']} sonuç")
        for i, result in enumerate(search_result["results"][:2]):
            print(f"  {i+1}. {result['title'][:50]}...")
    else:
        print(f"❌ Arama hatası: {search_result.get('error')}")
    
    # Screenshot testi (sadece Selenium varsa)
    if SELENIUM_AVAILABLE:
        print("\n📸 Screenshot Testi:")
        try:
            screenshot_result = take_website_screenshot("https://www.python.org")
            if screenshot_result.get("success"):
                print(f"✅ Screenshot başarılı: {screenshot_result['screenshot_path']}")
                print(f"   Boyut: {screenshot_result['file_size']} bytes")
            else:
                print(f"❌ Screenshot hatası: {screenshot_result.get('error')}")
        except Exception as e:
            print(f"❌ Screenshot exception: {str(e)}")
    else:
        print("\n📸 Screenshot testi atlandı (Selenium yok)")
    
    # İstatistikler
    print(f"\n📊 Modül İstatistikleri:")
    stats = web_search_screenshot_module.get_stats()
    print(f"  Toplam arama: {stats['total_searches']}")
    print(f"  Başarılı arama: {stats['successful_searches']}")
    print(f"  Toplam screenshot: {stats['total_screenshots']}")
    print(f"  Başarılı screenshot: {stats['successful_screenshots']}")

if __name__ == "__main__":
    print("🌐 Web Search & Screenshot Module")
    print("=" * 50)
    
    # Test çalıştır
    test_web_search_module()
    
    print("\nKullanım örnekleri:")
    print("from web_search_screenshot_module import search_web, take_website_screenshot")
    print("result = search_web('Python tutorial')")
    print("screenshot = take_website_screenshot('https://example.com')")
    
    # Temizlik
    web_search_screenshot_module.cleanup()