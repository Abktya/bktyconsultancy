# ai_web_research_agent.py - AI Modeline Web Araştırma Yeteneği Ekleyen Entegrasyon

import asyncio
import json
import re
import time
import logging
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse
print("🚀 ai_web_research_agent.py yükleniyor...")

logger = logging.getLogger(__name__)


# Mevcut modüllerinizi import edin
from multi_user_ollama_runner import MultiUserOllamaRunner, OLLAMA_MODELS
from web_search_screenshot_module import WebSearchScreenshotModule
import os
os.environ['OPENWEATHER_API_KEY'] = 'b3c7ffa1da923ffab2e384a7e6773084'
try:
    from football_prediction_agent import integrate_football_predictions
    FOOTBALL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Football predictions not available: {e}")
    integrate_football_predictions = None
    FOOTBALL_AVAILABLE = False

class WebResearchAgent:
    """AI modeline web araştırma yeteneği kazandıran agent"""
    
    def __init__(self, ollama_runner: MultiUserOllamaRunner):
        self.ollama_runner = ollama_runner
        self.web_module = WebSearchScreenshotModule()
        
        # Research session tracking
        self.active_research_sessions = {}
        
        # Tool definitions for AI model
        self.available_tools = {
            "web_search": {
                "description": "İnternette arama yapar ve sonuçları getirir",
                "parameters": {
                    "query": "Arama terimi",
                    "max_results": "Maksimum sonuç sayısı (varsayılan: 5)"
                }
            },
            "analyze_webpage": {
                "description": "Belirli bir web sayfasını analiz eder ve içeriğini özetler",
                "parameters": {
                    "url": "Analiz edilecek web sayfasının URL'si"
                }
            },
            "take_screenshot": {
                "description": "Web sayfasının ekran görüntüsünü alır",
                "parameters": {
                    "url": "Screenshot alınacak web sayfasının URL'si"
                }
            },
            "research_topic": {
                "description": "Kapsamlı bir konu araştırması yapar",
                "parameters": {
                    "topic": "Araştırılacak konu",
                    "depth": "Araştırma derinliği (basic/detailed/comprehensive)"
                }
            }
        }
    
    # ai_web_research_agent.py dosyasındaki detect_research_intent metodunu güncelleyin

    def detect_research_intent(self, prompt: str) -> Dict[str, Any]:
        """Kullanıcının araştırma isteğini algıla - düzeltilmiş"""
        prompt_lower = prompt.lower().strip()
        
        # Debug için yazdır
        print(f"🔍 Intent detection for: '{prompt_lower}'")

        casual_phrases = [
            "selam", "merhaba", "hello", "hi", "hey", "naber", "nasılsın", "nasıl gidiyor",
            "iyi misin", "ne yapıyorsun", "how are you", "what's up", "good morning", "good afternoon",
            "teşekkür", "sağol", "thanks", "thank you", "tamam", "okay", "ok", "anladım",
            "güzel", "iyi", "süper", "harika", "good", "great", "nice", "cool",
            "neden", "nasıl", "ne zaman", "kim", "nerede"  # sadece tek kelime olanlar
        ]
        
        # Eğer prompt sadece casual phrase ise research yapma
        if any(phrase == prompt_lower for phrase in casual_phrases):
            return {
                "has_research_intent": False,
                "action": None,
                "confidence": 0.0,
                "extracted_query": "",
                "extracted_urls": [],
                "research_type": None,
                "trigger_found": "casual_chat",
                "is_weather_query": False
            }
        
        # URL varlığını kontrol et
        url_pattern = r'https?://[^\s]+'
        urls = re.findall(url_pattern, prompt)
        
        # TEKIL HAVA DURUMU KONTROLÜ - birleştirilmiş
        weather_triggers = [
            # Türkçe
            "hava durumu", "hava durumunu", "hava durumuna", "havası nasıl", "hava",
            "sıcaklık", "yağmur", "kar", "rüzgar", "nem", "basınç", "derece", "kaç derece",
            "bugünkü hava", "şu anki hava", "güncel hava", "meteoroloji", "hava kaç derece", 
            # İngilizce  
            "weather", "temperature", "rain", "snow", "wind", "humidity", 
            "current weather", "today weather", "weather forecast", "climate"
        ]
        
        # Hava durumu pattern'leri
        weather_location_patterns = [
            r'(.*)\s+(hava durumu|weather)',
            r'(hava durumu|weather)\s+(.*)',
            r'weather\s+in\s+(.*)',
            r'(.*)\s+de\s+hava',
            r'(.*)\s+da\s+hava'
        ]
        
        is_weather = any(trigger in prompt_lower for trigger in weather_triggers)
        has_location = any(re.search(pattern, prompt_lower) for pattern in weather_location_patterns)
        
        if is_weather or has_location:
            print(f"🌤️ Weather query detected")
            return {
                "has_research_intent": True,
                "action": "weather_api_direct", 
                "confidence": 0.9,
                "research_type": "weather",
                "trigger_found": "weather_query",
                "is_weather_query": True,
                "extracted_query": self._extract_weather_query(prompt),
                "extracted_urls": urls
            }
        
        # Normal arama tetikleyicileri
        search_triggers = [
            "araştır", "ara", "bul", "incele", "kontrol et", "arama yap",
            "neler oluyor", "son haberler", "güncel", "internetten bul",
            "google'da ara", "web'de ara", "sitelerden bul",
            # Soru kelimeleri  
            "nedir", "nasıl", "ne zaman", "nerede", "kim", "neden", "hangi",
            "kaç", "ne kadar", "hangisi", "ne", "neyi", "neye",
            # Öğrenme/bilgi alma
            "öğren", "bilgi ver", "anlat", "açıkla", "detayını ver",
            "hakkında bilgi", "ile ilgili", "konusunda", "çevresinde",
            # İngilizce
            "search", "research", "find", "look up", "investigate", 
            "what's happening", "latest news", "current", "find online",
            "what is", "how", "when", "where", "who", "why", "which"
        ]
        
        # Normal arama kontrolü
        max_confidence = 0.0
        best_trigger = None
        
        for trigger in search_triggers:
            if trigger in prompt_lower:
                trigger_pos = prompt_lower.find(trigger)
                position_bonus = 0.2 if trigger_pos < 20 else 0.1
                question_bonus = 0.3 if trigger in ["nedir", "nasıl", "what is", "how"] else 0.0
                confidence = 0.6 + position_bonus + question_bonus
                
                if confidence > max_confidence:
                    max_confidence = confidence
                    best_trigger = trigger
        
        if max_confidence > 0.0:
            return {
                "has_research_intent": True,
                "action": "web_search",
                "confidence": min(max_confidence, 0.95),
                "research_type": "search",
                "trigger_found": best_trigger,
                "is_weather_query": False,
                "extracted_query": self._extract_search_query(prompt, best_trigger),
                "extracted_urls": urls
            }
        
        # URL analizi kontrolü
        if urls and any(trigger in prompt_lower for trigger in ["analiz et", "özetle", "analyze", "summarize"]):
            return {
                "has_research_intent": True,
                "action": "analyze_webpage",
                "confidence": 0.9,
                "research_type": "url_analysis",
                "trigger_found": "url_analysis",
                "is_weather_query": False,
                "extracted_query": prompt.strip(),
                "extracted_urls": urls
            }
        
        # Soru pattern'leri (son çare)
        question_patterns = [
            r'\b(ne|nasıl|kim|nerede|ne zaman|neden|hangi|kaç)\b',
            r'\b(what|how|who|where|when|why|which)\b',
            r'.*\?$'
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, prompt_lower):
                return {
                    "has_research_intent": True,
                    "action": "web_search",
                    "confidence": 0.7,
                    "research_type": "question",
                    "trigger_found": "question_pattern",
                    "is_weather_query": False,
                    "extracted_query": prompt.strip(),
                    "extracted_urls": urls
                }
        

        sports_triggers = [
            "maç", "skor", "karşılaşma", "puan durumu", "kim kazanır", "kaç kaç biter",
            "juventus", "galatasaray", "fenerbahçe", "beşiktaş", "real madrid",
            "barcelona", "manchester", "arsenal", "chelsea", "psg", "inter", "milan",
            "şampiyonlar ligi", "premier league", "serie a", "laliga"
        ]

        if any(trigger in prompt_lower for trigger in sports_triggers):
            print("⚽ Football query detected")

            # Eğer kullanıcı maç takvimi, bugün, hangi maçlar var gibi şeyler soruyorsa
            if any(word in prompt_lower for word in ["hangi maç", "bugün", "bu akşam", "maçlar var", "maç programı", "fikstür"]):
                return {
                    "has_research_intent": True,
                    "action": "web_search",
                    "confidence": 0.95,
                    "research_type": "sports_fixtures",
                    "trigger_found": "sports_schedule",
                    "is_weather_query": False,
                    "extracted_query": prompt,
                    "extracted_urls": []
                }

            # Diğer durumlarda prediction
            return {
                "has_research_intent": True,
                "action": "football_prediction",
                "confidence": 0.95,
                "research_type": "sports",
                "trigger_found": "sports_query",
                "is_weather_query": False,
                "extracted_query": prompt,
                "extracted_urls": []
            }

        # Hiçbir şey bulunamadı
        return {
            "has_research_intent": False,
            "action": None,
            "confidence": 0.0,
            "extracted_query": "",
            "extracted_urls": urls,
            "research_type": None,
            "trigger_found": None,
            "is_weather_query": False
        }



    def _extract_weather_query(self, prompt: str) -> str:  
        """Returns (query, city)"""
        import unicodedata
        import re
        
        # Türkçe karakterleri ASCII'ye normalize et
        prompt_normalized = unicodedata.normalize('NFKD', prompt)
        prompt_normalized = prompt_normalized.encode('ascii', 'ignore').decode('ascii')
        prompt_lower = prompt_normalized.lower()
        
        city_keywords = [
            'istanbul', 'ankara', 'izmir', 'bursa', 'antalya', 'adana', 'konya', 
            'gaziantep', 'kayseri', 'diyarbakir', 'samsun', 'trabzon', 'eskisehir',
            'london', 'paris', 'berlin', 'madrid', 'rome', 'amsterdam', 'brussels', 
            'vienna', 'zurich', 'stockholm', 'rugby', 'manchester', 'birmingham',
            'new york', 'los angeles', 'chicago', 'miami', 'washington', 'boston',
            'tokyo', 'osaka', 'seoul', 'beijing', 'shanghai', 'hong kong', 'singapore'
        ]
        
        found_city = None
        for city in city_keywords:
            if city in prompt_lower:
                found_city = city
                break
        
        # Eğer direkt bulunamadıysa, pattern matching dene
        if not found_city:
            # Daha spesifik pattern'ler - şehir ismini doğru yakalayacak
            location_patterns = [
                r'^(\w+)\s*(da|de|te)\s+hava',                      # ← "te" ekle
                r'^(\w+)\s*(da|de|te)\s+hava\s+durumu',
                r'(\w+)\s*(da|de|te)\s+(kac|ne)\s+derece',          # ← "te" ekle
                r'(\w+)\s+hava\s+durumu\s+nedir',
                r'(\w+)\s+hava\s+durumu',
                r'hava\s+durumu\s+(\w+)',
                r'(\w+)\s+sicaklik',
                r'(\w+)\s+(kac|ne)\s+derece',
            ]
            
            invalid_words = ['hava', 'durumu', 'kac', 'ne', 'nedir', 'nasil', 'bugun', 'su', 'an', 'sicaklik']
            
            for pattern in location_patterns:
                match = re.search(pattern, prompt_lower)
                if match:
                    potential = match.group(1).strip()
                    if potential not in invalid_words and len(potential) > 2:
                        found_city = potential
                        print(f"🔍 Pattern matched: '{found_city}'")
                        break
        
        # Location translations and corrections
        location_translations = {
            # Türkiye şehirleri
            "istanbul": "istanbul turkey",
            "ankara": "ankara turkey", 
            "izmir": "izmir turkey",
            "bursa": "bursa turkey",
            "antalya": "antalya turkey",
            "adana": "adana turkey",
            "konya": "konya turkey",
            'hatay': 'antakya turkey',  
            
            # İngiltere
            "rugby": "rugby england",
            "london": "london england", 
            "manchester": "manchester england",
            "birmingham": "birmingham england",
            "liverpool": "liverpool england",
            "glasgow": "glasgow scotland",
            "edinburgh": "edinburgh scotland",
            "cardiff": "cardiff wales",
            "belfast": "belfast northern ireland",
            
            # Diğer Avrupa
            "paris": "paris france",
            "berlin": "berlin germany",
            "madrid": "madrid spain", 
            "rome": "rome italy",
            "amsterdam": "amsterdam netherlands",
            "brussels": "brussels belgium",
            "vienna": "vienna austria",
            "zurich": "zurich switzerland",
            "stockholm": "stockholm sweden",
            
            # ABD
            "new york": "new york usa",
            "los angeles": "los angeles usa",
            "chicago": "chicago usa",
            "miami": "miami usa",
            "washington": "washington dc usa",
            "boston": "boston usa",
            "san francisco": "san francisco usa",
            "seattle": "seattle usa",
            
            # Asya
            "tokyo": "tokyo japan",
            "osaka": "osaka japan",
            "seoul": "seoul south korea",
            "beijing": "beijing china",
            "shanghai": "shanghai china",
            "hong kong": "hong kong",
            "singapore": "singapore",
            "bangkok": "bangkok thailand",
            "delhi": "delhi india",
            "mumbai": "mumbai india"
        }
        
        if found_city:
            # Debug için yazdır
            print(f"🎯 Weather city found: '{found_city}'")
            
            # Çeviri varsa kullan
            if found_city in location_translations:
                translated_location = location_translations[found_city]
                print(f"🌍 Translated to: '{translated_location}'")
                return f"weather in {translated_location} today"
            else:
                return f"weather in {found_city} today"
    
        # Fallback - genel hava durumu
        print(f"⚠️ No city found in: '{prompt}' - using general weather")
        return "current weather forecast"



    def _extract_search_query(self, prompt: str, trigger: str) -> str:
        """Prompt'tan arama sorgusunu çıkar - geliştirilmiş"""
        prompt_lower = prompt.lower()
        
        # Trigger'dan sonraki kısmı al
        trigger_index = prompt_lower.find(trigger)
        if trigger_index != -1:
            after_trigger = prompt[trigger_index + len(trigger):].strip()
            
            # Gereksiz başlangıç kelimelerini temizle
            cleanup_starts = ["hakkında", "konusunda", "ile ilgili", "about", "regarding", "for", "için"]
            for word in cleanup_starts:
                if after_trigger.lower().startswith(word):
                    after_trigger = after_trigger[len(word):].strip()
            
            # Gereksiz son kelimeleri temizle
            cleanup_ends = ["lütfen", "please", "şimdi", "now"]
            for word in cleanup_ends:
                if after_trigger.lower().endswith(word):
                    after_trigger = after_trigger[:-len(word)].strip()
            
            if after_trigger:
                return after_trigger[:150].strip()  # Limit artırıldı
        
        # Trigger bulunamazsa, soru kalıplarını kontrol et
        question_patterns = [
            (r'^(nedir|what is)\s+(.+)', lambda m: m.group(2)),
            (r'^(nasıl|how)\s+(.+)', lambda m: m.group(2)),
            (r'^(.+)\s+(nedir|what is)$', lambda m: m.group(1)),
            (r'^(.+)\s+\?$', lambda m: m.group(1)),
        ]
        
        for pattern, extractor in question_patterns:
            match = re.match(pattern, prompt.strip(), re.IGNORECASE)
            if match:
                extracted = extractor(match)
                return extracted.strip()[:150]
        
        # Son çare: tüm prompt'u döndür
        return prompt.strip()[:150]
    
 
    
    async def perform_web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Web araması gerçekleştir - fallback system ile"""
        try:
            # WebSearchScreenshotModule üzerinden search_agent kullan
            if hasattr(self.web_module, 'search_agent') and self.web_module.search_agent:
                # Önce normal search dene
                search_result = self.web_module.search_agent.search(
                    query=query,
                    engine="duckduckgo", 
                    max_results=max_results
                )
                
                # Eğer başarılı ama 0 sonuç varsa fallback'leri dene
                if search_result.get("success") and search_result.get("total_results", 0) == 0:
                    logger.info(f"DuckDuckGo 0 sonuç - fallback deneniyor: {query}")
                    
                    # Wikipedia fallback
                    wiki_results = self._search_wikipedia_fallback(query)
                    if wiki_results:
                        search_result = {
                            "success": True,
                            "query": query,
                            "engine": "wikipedia_fallback",
                            "results": wiki_results,
                            "total_results": len(wiki_results),
                            "search_time": 0.5
                        }
                    else:
                        # Manual results fallback
                        manual_results = self._get_manual_results(query)
                        if manual_results:
                            search_result = {
                                "success": True,
                                "query": query,
                                "engine": "manual_fallback",
                                "results": manual_results,
                                "total_results": len(manual_results),
                                "search_time": 0.1
                            }
            else:
                # Alternatif: Doğrudan WebSearchAgent oluştur
                from web_search_screenshot_module import WebSearchAgent
                search_agent = WebSearchAgent()
                search_result = search_agent.search(
                    query=query,
                    engine="duckduckgo",
                    max_results=max_results
                )
                
                # Fallback logic burada da
                if search_result.get("success") and search_result.get("total_results", 0) == 0:
                    manual_results = self._get_manual_results(query)
                    if manual_results:
                        search_result = {
                            "success": True,
                            "query": query,
                            "engine": "manual_fallback",
                            "results": manual_results,
                            "total_results": len(manual_results),
                            "search_time": 0.1
                        }
            
            if search_result.get("success"):
                # Sonuçları AI için uygun formata çevir
                formatted_results = []
                for i, result in enumerate(search_result["results"], 1):
                    formatted_results.append({
                        "rank": i,
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "snippet": result.get("snippet", ""),
                        "domain": result.get("display_url", "")
                    })
                
                return {
                    "success": True,
                    "query": query,
                    "total_results": len(formatted_results),
                    "results": formatted_results,
                    "search_time": search_result.get("search_time", 0),
                    "engine": search_result.get("engine", "duckduckgo")
                }
            else:
                return {"error": search_result.get("error", "Arama başarısız")}
                
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {"error": f"Arama hatası: {str(e)}"}


    def _search_wikipedia_fallback(self, query: str):
        """Wikipedia API ile fallback search (önce tr, sonra en)"""
        import requests, re
        from requests.exceptions import RequestException, SSLError

        headers = {
            "User-Agent": "BktyResearchBot/1.0 (https://bktyconsultancy.co.uk/; contact@bktyconsultancy.co.uk)"
        }

        for lang in ["tr", "en"]:
            try:
                wiki_url = f"https://{lang}.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "format": "json",
                    "list": "search",
                    "srsearch": query,
                    "srlimit": 3,
                    "srprop": "snippet"
                }
                response = requests.get(
                    wiki_url,
                    params=params,
                    headers=headers,   # 🔑 User-Agent eklendi
                    timeout=5
                )
                response.raise_for_status()

                data = response.json()
                results = []
                for item in data.get("query", {}).get("search", []):
                    snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
                    results.append({
                        "title": item.get("title", ""),
                        "url": f"https://{lang}.wikipedia.org/wiki/{item.get('title', '').replace(' ', '_')}",
                        "snippet": snippet,
                        "display_url": f"{lang}.wikipedia.org",
                        "search_engine": "wikipedia"
                    })
                if results:
                    return results
            except SSLError as e:
                logger.warning(f"Wikipedia SSL hatası ({lang}): {e}")
            except RequestException as e:
                logger.error(f"Wikipedia request error ({lang}): {e}")
            except Exception as e:
                logger.error(f"Wikipedia fallback error ({lang}): {e}")

        return []



    def _get_manual_results(self, query: str):
        """Manual curated results - enhanced with weather data"""
        query_lower = query.lower()
        
        # Universal weather results
        if any(term in query_lower for term in ['weather', 'hava durumu', 'temperature', 'sıcaklık', 'forecast']):
            
            # Şehir çıkar
            location = self._extract_location_from_query(query_lower)
            
            if location:
                # Gerçek hava durumu verisi almaya çalış
                weather_data = self._get_real_weather_data(location)
                
                if weather_data:
                    # Gerçek veri ile sonuçlar
                    temp_info = f"Current: {weather_data['temperature']}°C"
                    condition_info = weather_data['description'].title()
                    
                    return [
                        {
                            'title': f'{location.title()} Weather - {temp_info}',
                            'url': f'https://www.bbc.co.uk/weather/search?q={location.replace(" ", "+")}',
                            'snippet': f'🌡️ Temperature: {weather_data["temperature"]}°C (feels like {weather_data["feels_like"]}°C). {condition_info}. Humidity: {weather_data["humidity"]}%. Wind: {weather_data["wind_speed"]} m/s.',
                            'display_url': 'live-weather-data',
                            'search_engine': 'weather_api'
                        },
                        {
                            'title': f'BBC Weather - {location.title()}',
                            'url': f'https://www.bbc.co.uk/weather/search?q={location.replace(" ", "+")}',
                            'snippet': f'Detailed forecast for {location.title()}. Current conditions show {condition_info} with {weather_data["temperature"]}°C. 7-day outlook available.',
                            'display_url': 'bbc.co.uk',
                            'search_engine': 'manual'
                        },
                        {
                            'title': f'Weather.com - {location.title()} Extended Forecast',
                            'url': f'https://weather.com/weather/today/l/{location.replace(" ", "+")}',
                            'snippet': f'Hourly and 10-day weather forecast for {location.title()}. Currently {weather_data["temperature"]}°C with {condition_info}.',
                            'display_url': 'weather.com',
                            'search_engine': 'manual'
                        }
                    ]
                else:
                    # Fallback - estimated data based on season and location
                    estimated_data = self._get_estimated_weather(location)
                    
                    return [
                        {
                            'title': f'{location.title()} Weather Forecast',
                            'url': f'https://www.bbc.co.uk/weather/search?q={location.replace(" ", "+")}',
                            'snippet': f'Estimated current conditions for {location.title()}: {estimated_data["temp_range"]}. {estimated_data["typical_condition"]}. Check live sources for exact temperature.',
                            'display_url': 'bbc.co.uk',
                            'search_engine': 'manual'
                        },
                        {
                            'title': f'Weather.com - {location.title()} Weather',
                            'url': f'https://weather.com/weather/today/l/{location.replace(" ", "+")}',
                            'snippet': f'Current weather and forecast for {location.title()}. Typical conditions: {estimated_data["typical_condition"]}. Live updates available.',
                            'display_url': 'weather.com',
                            'search_engine': 'manual'
                        },
                        {
                            'title': f'AccuWeather - {location.title()} Live Weather',
                            'url': f'https://www.accuweather.com/en/search-locations?query={location.replace(" ", "+")}',
                            'snippet': f'Real-time weather data for {location.title()}. Hourly and 15-day forecasts with radar and weather alerts.',
                            'display_url': 'accuweather.com',
                            'search_engine': 'manual'
                        }
                    ]
            else:
                # Genel weather results
                return [
                    {
                        'title': 'BBC Weather - Global Weather Forecasts',
                        'url': 'https://www.bbc.co.uk/weather',
                        'snippet': 'Current weather conditions worldwide. Search any city for live temperature, conditions, and 7-day forecast.',
                        'display_url': 'bbc.co.uk',
                        'search_engine': 'manual'
                    },
                    {
                        'title': 'Weather.com - Live Weather Data',
                        'url': 'https://weather.com/',
                        'snippet': 'Real-time weather updates, radar maps, and detailed forecasts for any location worldwide.',
                        'display_url': 'weather.com',
                        'search_engine': 'manual'
                    }
                ]
        
        # Yapay zeka kütüphaneleri (unchanged)
        elif any(term in query_lower for term in ['yapay zeka', 'ai', 'artificial intelligence', 'machine learning', 'ml', 'kütüphaneleri', 'libraries']):
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
    
    def _get_real_weather_data(self, location: str):
        """Her şehir için ülke doğrulamasıyla güvenilir hava durumu getirir."""
        import requests, os, re
        from urllib.parse import quote

        try:
            api_key = os.getenv("OPENWEATHER_API_KEY")
            if not api_key:
                print("❌ OPENWEATHER_API_KEY bulunamadı.")
                return None

            # Normalize et
            location = (
                location.lower()
                .strip()
                .replace("ş", "s")
                .replace("ı", "i")
                .replace("ğ", "g")
                .replace("ü", "u")
                .replace("ö", "o")
                .replace("ç", "c")
            )
            location = re.sub(r"\b(da|de|ta|te|hava|durumu|bugun|su an|kac derece|sicaklik)\b", "", location).strip()
            if not location:
                location = "london"

            # 🇹🇷 Türkiye şehirleri için TR kodu zorunlu ekle
            if "," not in location and not any(kw in location for kw in ["england", "france", "usa", "germany", "japan", "china"]):
                location_query = f"{location},TR"
            else:
                location_query = location

            encoded_query = quote(location_query)

            # 🌍 1️⃣ Doğrudan şehir araması
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": encoded_query, "appid": api_key, "units": "metric", "lang": "tr"}
            response = requests.get(url, params=params, timeout=7)

            # 🌍 2️⃣ Eğer bulunamazsa, Geo API ile arama (TR filtreli)
            if response.status_code == 404 or "city not found" in response.text.lower():
                print(f"⚠️ '{location_query}' bulunamadı, geo API denemesi yapılıyor...")
                geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={quote(location)}&limit=5&appid={api_key}"
                geo_response = requests.get(geo_url, timeout=7)

                if geo_response.status_code == 200 and geo_response.json():
                    geo_candidates = geo_response.json()

                    # 🇹🇷 TR olanı seç
                    valid_geo = next((item for item in geo_candidates if item.get("country") == "TR"), None)
                    if not valid_geo:
                        valid_geo = geo_candidates[0]

                    # ❗ Hatay / Antakya özel fallback
                    if location in ["hatay", "antakya"]:
                        valid_geo = {"lat": 36.2025, "lon": 36.1600, "name": "Hatay", "country": "TR"}

                    lat, lon = valid_geo.get("lat"), valid_geo.get("lon")
                    if lat and lon:
                        weather_url = (
                            f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=tr"
                        )
                        response = requests.get(weather_url, timeout=7)

            # 🌤️ 3️⃣ Başarılı sonuç
            if response.status_code == 200:
                data = response.json()
                city_name = data.get("name") or location.title()
                country_code = data.get("sys", {}).get("country", "")
                # ❌ Weather Island gibi saçmalıkları filtrele
                if city_name.lower().startswith("weather island"):
                    city_name = location.title()
                    country_code = "TR"

                return {
                    "temperature": round(data["main"]["temp"]),
                    "feels_like": round(data["main"]["feels_like"]),
                    "humidity": data["main"]["humidity"],
                    "description": data["weather"][0]["description"],
                    "wind_speed": round(data["wind"].get("speed", 0), 1),
                    "city": city_name,
                    "country": country_code,
                }

            print(f"⚠️ Hava durumu alınamadı: {response.status_code} {response.text[:100]}")
            return None

        except Exception as e:
            print(f"❌ Weather API error: {e}")
            return None



    def _get_estimated_weather(self, location: str):
        """Tahmini hava durumu verisi (API çalışmadığında)"""
        import datetime
        month = datetime.datetime.now().month
        
        # Seasonal estimates
        weather_estimates = {
            'rugby': {
                'winter': {'temp_range': '2-8°C', 'typical_condition': 'Cloudy with occasional rain'},
                'spring': {'temp_range': '8-15°C', 'typical_condition': 'Mild with scattered showers'},
                'summer': {'temp_range': '12-20°C', 'typical_condition': 'Partly cloudy'},
                'autumn': {'temp_range': '6-14°C', 'typical_condition': 'Cool and overcast'}
            },
            'istanbul': {
                'winter': {'temp_range': '5-12°C', 'typical_condition': 'Cool with occasional rain'},
                'spring': {'temp_range': '12-20°C', 'typical_condition': 'Mild and pleasant'},
                'summer': {'temp_range': '20-28°C', 'typical_condition': 'Warm and mostly sunny'},
                'autumn': {'temp_range': '15-22°C', 'typical_condition': 'Comfortable temperatures'}
            },
            'london': {
                'winter': {'temp_range': '2-7°C', 'typical_condition': 'Cold and damp'},
                'spring': {'temp_range': '8-15°C', 'typical_condition': 'Cool with showers'},
                'summer': {'temp_range': '15-22°C', 'typical_condition': 'Mild summer weather'},
                'autumn': {'temp_range': '8-16°C', 'typical_condition': 'Cool and wet'}
            },
            'paris': {
                'winter': {'temp_range': '3-8°C', 'typical_condition': 'Cold and cloudy'},
                'spring': {'temp_range': '10-18°C', 'typical_condition': 'Pleasant spring weather'},
                'summer': {'temp_range': '18-25°C', 'typical_condition': 'Warm and sunny'},
                'autumn': {'temp_range': '10-17°C', 'typical_condition': 'Cool autumn days'}
            }
        }
        
        # Determine season
        if month in [12, 1, 2]:
            season = 'winter'
        elif month in [3, 4, 5]:
            season = 'spring'
        elif month in [6, 7, 8]:
            season = 'summer'
        else:
            season = 'autumn'
        
        location_lower = location.lower()
        if location_lower in weather_estimates:
            return weather_estimates[location_lower][season]
        else:
            # Default estimate
            return {'temp_range': '10-18°C', 'typical_condition': 'Variable conditions'}


    def _extract_location_from_query(self, query_lower: str) -> str:
        """Kullanıcı sorgusundan şehir adını çıkar (her ülke/şehir için dinamik)"""
        import re, requests, os
        from urllib.parse import quote

        # Bilinen şehir listesi (öncelik)
        known_cities = [
            'istanbul', 'ankara', 'izmir', 'bursa', 'antalya', 'adana', 'konya',
            'gaziantep', 'kayseri', 'diyarbakir', 'samsun', 'trabzon', 'eskisehir',
            'london', 'paris', 'berlin', 'madrid', 'rome', 'amsterdam', 'vienna',
            'zurich', 'stockholm', 'new york', 'los angeles', 'tokyo', 'seoul',
            'peking', 'beijing', 'shanghai', 'mumbai', 'delhi', 'singapore'
        ]

        for city in known_cities:
            if city in query_lower:
                return city

        # 🔍 Eğer listede yoksa Türkçe veya İngilizce patternlerle tahmin et
        match = re.search(r'(\b[a-zçğıöşü]{3,}\b)\s*(hava|durumu|kaç derece|weather|temperature)', query_lower)
        if match:
            potential_city = match.group(1).strip()
        else:
            # fallback: ilk kelimeyi şehir olarak dene
            potential_city = query_lower.split()[0] if query_lower else None

        if not potential_city:
            return None

        # 🧠 OpenWeather Geocoding API ile doğrulama
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if api_key:
            encoded = quote(potential_city)
            geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={encoded}&limit=1&appid={api_key}"
            try:
                r = requests.get(geo_url, timeout=5)
                if r.status_code == 200 and r.json():
                    city_name = r.json()[0].get("name", potential_city)
                    print(f"🌍 Geo-confirmed city: {city_name}")
                    return city_name.lower()
            except Exception as e:
                print(f"⚠️ Geo check failed: {e}")

        # fallback — tahmini şehir adı
        return potential_city.lower()


    async def analyze_webpage(self, url: str) -> Dict[str, Any]:
        """Web sayfasını analiz et"""
        try:
            # İçerik çıkarma
            content_result = self.web_module.content_extractor.extract_text_content(url)
            
            if content_result.get("success"):
                return {
                    "success": True,
                    "url": url,
                    "title": content_result.get("title", ""),
                    "description": content_result.get("description", ""),
                    "content_summary": content_result.get("text", "")[:1500],  # İlk 1500 karakter
                    "word_count": content_result.get("word_count", 0),
                    "domain": urlparse(url).netloc
                }
            else:
                return {"error": content_result.get("error", "Sayfa analizi başarısız")}
                
        except Exception as e:
            logger.error(f"Webpage analysis error: {e}")
            return {"error": f"Sayfa analizi hatası: {str(e)}"}
    
    async def comprehensive_research(self, topic: str, depth: str = "detailed") -> Dict[str, Any]:
        """Kapsamlı konu araştırması"""
        research_session_id = f"research_{int(time.time())}_{hash(topic) % 1000}"
        
        research_steps = {
            "basic": [f"{topic}"],
            "detailed": [f"{topic}", f"{topic} detaylı bilgi", f"{topic} son gelişmeler"],
            "comprehensive": [
                f"{topic}",
                f"{topic} detaylı analiz",
                f"{topic} son haberler",
                f"{topic} uzman görüşleri",
                f"{topic} istatistikler veriler"
            ]
        }
        
        queries = research_steps.get(depth, research_steps["detailed"])
        all_results = []
        
        for query in queries:
            search_result = await self.perform_web_search(query, max_results=3)
            if search_result.get("success"):
                all_results.extend(search_result["results"])
            
            # Rate limiting
            await asyncio.sleep(1)
        
        # Benzersiz sonuçları filtrele
        unique_results = []
        seen_urls = set()
        
        for result in all_results:
            url = result.get("url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        return {
            "success": True,
            "topic": topic,
            "depth": depth,
            "session_id": research_session_id,
            "total_results": len(unique_results),
            "results": unique_results[:15],  # En fazla 15 sonuç
            "research_queries": queries
        }
    
    def format_research_for_ai(self, research_data: Dict[str, Any]) -> str:
        if not research_data.get("success"):
            return f"Araştırma hatası: {research_data.get('error', 'Bilinmeyen hata')}"
        
        if research_data.get("action") == "web_search" or "results" in research_data:
            formatted = f"🔍 Web Araması Sonuçları:\n"
            formatted += f"Sorgu: {research_data.get('query', research_data.get('topic', ''))}\n"
            formatted += f"Toplam: {research_data.get('total_results', 0)} sonuç\n\n"
            
            # ← Only take top 2 results instead of 5
            for result in research_data.get("results", [])[:2]:
                formatted += f"{result.get('rank', '')}. **{result.get('title', '')}**\n"
                formatted += f"   🔗 {result.get('url', '')}\n"
                # ← Truncate snippet to 100 chars
                snippet = result.get('snippet', '')[:100]
                formatted += f"   📝 {snippet}...\n\n"
            
            return formatted
        
        elif research_data.get("action") == "analyze_webpage":
            # Sayfa analizi formatı
            formatted = f"📄 Web Sayfası Analizi:\n"
            formatted += f"URL: {research_data.get('url', '')}\n"
            formatted += f"Başlık: {research_data.get('title', '')}\n"
            formatted += f"Açıklama: {research_data.get('description', '')}\n"
            formatted += f"İçerik Özeti:\n{research_data.get('content_summary', '')}\n"
            
            return formatted
        
        return str(research_data)
    
    async def enhanced_chat_with_research(self, model_name: str, prompt: str, 
                                        user_id: str, **kwargs) -> Dict[str, Any]:
        
        research_intent = self.detect_research_intent(prompt)
        
        if research_intent["has_research_intent"]:
            research_data = None
            
            if research_intent.get("is_weather_query", False):
                query = research_intent["extracted_query"] or prompt
                location = self._extract_location_from_query(query.lower()) or query.lower().strip()

                
                print(f"🌤️ Direct weather API call for: {location}")
                weather_data = self._get_real_weather_data(location)
                
                if weather_data:
                    weather_prompt = f"""Sen hava durumu asistanısın. Aşağıdaki GERÇEK ZAMANLI veriyi kullanarak yanıt ver:

    📍 Şehir: {weather_data['city']}, {weather_data['country']}
    🌡️ Sıcaklık: {weather_data['temperature']}°C (hissedilen: {weather_data['feels_like']}°C)
    ☁️ Durum: {weather_data['description']}
    💧 Nem: {weather_data['humidity']}%
    🌬️ Rüzgar: {weather_data['wind_speed']} m/s

    Kullanıcı sorusu: {prompt}

    Kısa ve net yanıt ver. Sadece yukarıdaki verileri kullan."""

                    # ✅ KWARGS'TAN system_prompt ÇIKAR
                    clean_kwargs = {k: v for k, v in kwargs.items() if k != 'system_prompt'}
                    
                    chat_result = await self.ollama_runner.async_chat_with_model(
                        model_name=model_name,
                        prompt=weather_prompt,
                        user_id=user_id,
                        system_prompt="Sen hava durumu asistanısın. Sadece verilen API verilerini kullan.",
                        **clean_kwargs  # ✅ system_prompt olmadan
                    )
                    
                    chat_result["research_performed"] = True
                    chat_result["research_type"] = "weather_api"
                    chat_result["weather_data"] = weather_data
                    
                    return chat_result
                else:
                    # API başarısız - fallback
                    print("❌ Weather API failed - falling back to web search")
                    research_data = await self.perform_web_search(query)
                    research_data["action"] = "web_search"
            
            # Normal web search flow (değişmeden)
            elif research_intent["action"] == "web_search":
                query = research_intent["extracted_query"] or prompt
                research_data = await self.perform_web_search(query)
                research_data["action"] = "web_search"

            elif research_intent["action"] == "football_prediction":
                print("⚽ Football prediction path triggered")
                
                # Takım adlarını çıkar
                import re
                match = re.findall(r'([A-Za-zğüşöçİıĞÜŞÖÇ]+)\s+vs\s+([A-Za-zğüşöçİıĞÜŞÖÇ]+)', prompt)
                if not match:
                    words = prompt.split()
                    if len(words) >= 2:
                        team1, team2 = words[0], words[1]
                    else:
                        team1, team2 = "Juventus", "Inter"
                else:
                    team1, team2 = match[0]
                
                # ✅ DÜZELTME: hasattr ile kontrol et
                if hasattr(self.ollama_runner, 'predict_football_match'):
                    result = self.ollama_runner.predict_football_match(team1, team2, user_id=user_id)
                    
                    if result.get("success"):
                        # ✅ Frontend formatına uygun döndür
                        return {
                            "success": True,
                            "response": result.get("analysis", "Analiz yapılamadı"),
                            "model": result.get("model", "qwen2.5:14b-instruct"),
                            "response_time": result.get("response_time", 0),
                            "research_performed": True,
                            "research_type": "football"
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.get("error", "Football prediction failed")
                        }
                else:
                    return {
                        "success": False,
                        "error": "Football prediction not available (not integrated)"
                    }

                
            elif research_intent["action"] == "analyze_webpage":
                urls = research_intent["extracted_urls"]
                if urls:
                    research_data = await self.analyze_webpage(urls[0])
                    research_data["action"] = "analyze_webpage"
                    
            elif research_intent["action"] == "take_screenshot":
                urls = research_intent["extracted_urls"]
                if urls:
                    screenshot_result = self.web_module.screenshot_agent.take_screenshot(urls[0])
                    research_data = {
                        "success": screenshot_result.get("success", False),
                        "action": "take_screenshot",
                        "url": urls[0],
                        "screenshot_path": screenshot_result.get("screenshot_path", ""),
                        "error": screenshot_result.get("error")
                    }
            
            # Araştırma sonuçlarını AI prompt'una ekle
            if research_data and research_data.get("success"):
                research_summary = self.format_research_for_ai(research_data)
                
                # ← Shorter, more direct prompt
                enhanced_prompt = f"""Kaynaklara göre yanıtla:

{research_summary}

Soru: {prompt}

Kısa ve öz yanıt ver."""

                # Normal chat ile devam et ama enhanced prompt ile
                chat_result = await self.ollama_runner.async_chat_with_model(
                    model_name=model_name,
                    prompt=enhanced_prompt,
                    user_id=user_id,
                    **kwargs
                )
                
                # Research bilgilerini ekle
                if "success" in chat_result and chat_result["success"]:
                    chat_result["research_performed"] = True
                    chat_result["research_data"] = research_data
                    chat_result["research_intent"] = research_intent
                
                return chat_result
            else:
                # Araştırma başarısız, normal chat yap
                error_msg = research_data.get("error", "Araştırma yapılamadı") if research_data else "Araştırma başarısız"
                fallback_prompt = f"Araştırma hatası: {error_msg}\n\nOrijinal soru: {prompt}\n\nLütfen mevcut bilgilerinle yanıtla."
                
                chat_result = await self.ollama_runner.async_chat_with_model(
                    model_name=model_name,
                    prompt=fallback_prompt,
                    user_id=user_id,
                    **kwargs
                )
                
                chat_result["research_error"] = error_msg
                return chat_result
        
        else:
            # Normal chat
            return await self.ollama_runner.async_chat_with_model(
                model_name=model_name,
                prompt=prompt,
                user_id=user_id,
                **kwargs
            )
    
    def cleanup(self):
        """Temizlik işlemleri"""
        self.web_module.cleanup()

# MultiUserOllamaRunner'ı genişlet
# ai_web_research_agent.py içinde, EnhancedMultiUserOllamaRunner sınıfına ekleyin

class EnhancedMultiUserOllamaRunner(MultiUserOllamaRunner):
    """Web araştırma yeteneği eklenmiş Ollama Runner"""
    
    def __init__(self):
        super().__init__()
        self.research_agent = WebResearchAgent(self)
        self.enable_web_research = True
        
        # LoRA health check
        self.lora_available = self._check_lora_health()
        if self.lora_available:
            logger.info("🚀 LoRA API is available")
        else:
            logger.warning("⚠️ LoRA API not available - will use fallback")

        # Football integration
        if FOOTBALL_AVAILABLE and integrate_football_predictions:
            try:
                integrate_football_predictions(self)
                logger.info("⚽ FootballPredictionAgent integrated")
            except Exception as e:
                logger.error(f"⚠️ Football integration failed: {e}")

    def _check_lora_health(self) -> bool:
        """LoRA API'nin çalışır durumda olup olmadığını kontrol eder."""
        import requests
        try:
            response = requests.get("http://localhost:5005/health", timeout=3)
            if response.status_code == 200:
                logger.info("✅ LoRA API sağlıklı çalışıyor.")
                return True
            else:
                logger.warning(f"⚠️ LoRA API yanıtı beklenmedik: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.warning("❌ LoRA API bağlantısı başarısız.")
            return False
        except Exception as e:
            logger.error(f"❌ LoRA health check error: {e}")
            return False


    # ✅ EKSIK METOD 1
    def _run_async_in_thread(self, coro):
        """Async coroutine'i sync context'te çalıştır"""
        import asyncio
        import concurrent.futures
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, coro).result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    # ✅ EKSIK METOD 2
    def _call_lora_api(self, prompt: str, user_id: str, 
                    system_prompt: str = None, use_context: bool = True) -> Dict[str, Any]:
        """LoRA API çağrısı - Flask API'ye bağlanır"""
        import requests
        
        try:
            logger.info(f"🔗 LoRA API call for user: {user_id}")
            
            # Session context'i al (eğer kullanılacaksa)
            if use_context:
                session = self.get_or_create_session(user_id)
                context = session.get_context_string()
                if context:
                    prompt = f"{context}\n\nKullanıcı: {prompt}"
            
            # System prompt belirleme
            if system_prompt is None:
                system_prompt = "Sen yardımsever bir Türkçe asistansın."
            
            # LoRA API endpoint
            lora_api_url = "http://localhost:5005/generate"
            
            # Request payload
            payload = {
                "prompt": prompt,
                "system": system_prompt,
                "max_new_tokens": 150  # İhtiyaca göre ayarlayın
            }
            
            # API çağrısı
            start_time = time.time()
            response = requests.post(
                lora_api_url,
                json=payload,
                timeout=60  # 60 saniye timeout
            )
            response.raise_for_status()
            
            # Response parse
            result = response.json()
            response_time = time.time() - start_time
            
            if "error" in result:
                logger.error(f"❌ LoRA API error: {result['error']}")
                return {
                    "success": False,
                    "error": result["error"]
                }
            
            ai_response = result.get("response", "").strip()
            
            # Session'a ekle (eğer context kullanılıyorsa)
            if use_context:
                session = self.get_or_create_session(user_id)
                session.add_context(prompt, ai_response, "qwen2.5-lora")
            
            # Response formatı (diğer metodlarla uyumlu)
            return {
                "success": True,
                "response": ai_response,
                "model": "qwen2.5-lora",
                "response_time": response_time,
                "tokens_generated": result.get("tokens_generated", 0),
                "user_id": user_id,
                "timestamp": time.time()
            }
            
        except requests.exceptions.Timeout:
            logger.error("❌ LoRA API timeout")
            return {
                "success": False,
                "error": "LoRA API timeout - model yanıt vermedi"
            }
        
        except requests.exceptions.ConnectionError:
            logger.error("❌ LoRA API connection error - falling back to Ollama")
            # Fallback: Normal Ollama modeline geç
            return super().chat_with_model(
                model_name="qwen2.5:14b-instruct",
                prompt=prompt,
                user_id=user_id,
                system_prompt=system_prompt,
                use_context=use_context,
                auto_select_model=False
            )
        
        except Exception as e:
            logger.error(f"❌ LoRA API unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": f"LoRA API failed: {str(e)}"
            }

    # ✅ MEVCUT METOD (Parent'tan override)
    async def async_chat_with_model(self, model_name: str, prompt: str, user_id: str, 
                                    system_prompt: str = None, use_context: bool = True) -> Dict[str, Any]:
        """Async chat metodu - parent class'tan miras alınmış"""
        return await super().async_chat_with_model(
            model_name, prompt, user_id, system_prompt, use_context
        )
    
    def chat_with_model(self, model_name: str, prompt: str, user_id: str = "anonymous",
                    system_prompt: str = None, use_context: bool = True, 
                    auto_select_model: bool = False, enable_research: bool = None) -> Dict[str, Any]:
        
        # ✅ MODEL SEÇİMİ
        if auto_select_model or model_name == "auto":
            session = self.get_or_create_session(user_id)
            context_length = len(session.get_context_string())
            model_name = self.model_selector.select_model(prompt, session.preferred_model, context_length)
            print(f"🎯 Auto-selected model: {model_name}")
        
        # ✅ RESEARCH KONTROLÜ - MODEL SEÇİMİNDEN ÖNCE
        if enable_research is None:
            enable_research = self.enable_web_research
        
        prompt_lower = prompt.lower().strip()
        single_word_casual = ["selam", "merhaba", "hi", "hello", "hey", "naber"]
        
        if prompt_lower in single_word_casual:
            enable_research = False
        
        # ✅ RESEARCH VARSA VE HAVA DURUMU SORGUSU İSE - LORA'YA GİTMEDEN ÖNCE KONTROL ET
        if enable_research:
            research_intent = self.research_agent.detect_research_intent(prompt)
            print(f"🔍 Pre-routing research check: {research_intent.get('action')}, weather={research_intent.get('is_weather_query')}")
            
            if research_intent.get("is_weather_query", False):
                print(f"🌤️ Weather query detected - forcing research path")
                # Weather için özel handling - LoRA bypass
                coro = self.research_agent.enhanced_chat_with_research(
                    model_name, prompt, user_id, 
                    system_prompt=system_prompt, 
                    use_context=use_context
                )
                return self._run_async_in_thread(coro)
        
        # ✅ LoRA routing (weather olmadığında)
        if model_name == "qwen2.5-lora":
            # LoRA sağlıklı mı kontrol et
            if not hasattr(self, 'lora_available') or not self.lora_available:
                logger.warning("⚠️ LoRA not available - checking health...")
                self.lora_available = self._check_lora_health()
            
            if self.lora_available:
                print(f"🔗 Routing to LoRA API")
                return self._call_lora_api(prompt, user_id, system_prompt, use_context)
            else:
                logger.warning("⚠️ LoRA unavailable - falling back to Ollama")
                model_name = "qwen2.5:14b-instruct" 
        
        # ✅ Stable Diffusion routing
        if model_name == "stable-diffusion-v1.5":
            return self.generate_image_with_comfyui_sync(prompt, user_id)
        
        # ✅ Normal research flow
        if enable_research:
            print(f"✅ Calling research agent...")
            coro = self.research_agent.enhanced_chat_with_research(
                model_name=model_name,
                prompt=prompt,
                user_id=user_id,
                system_prompt=system_prompt,
                use_context=use_context
            )
            return self._run_async_in_thread(coro)
        else:
            return super().chat_with_model(
                model_name, prompt, user_id, 
                system_prompt, use_context, 
                auto_select_model=False
            )
        
    def toggle_web_research(self, enabled: bool):
        """Web araştırma özelliğini aç/kapat"""
        self.enable_web_research = enabled
        return {"web_research_enabled": enabled}
    
    def get_research_stats(self) -> Dict[str, Any]:
        """Araştırma istatistikleri"""
        web_stats = self.research_agent.web_module.get_stats()
        return {
            "web_research_enabled": self.enable_web_research,
            "available_tools": list(self.research_agent.available_tools.keys()),
            "web_module_stats": web_stats
        }

# ============================================================
# Global instance - enhanced version (safe initialization)
# ============================================================

try:
    enhanced_ollama_runner = EnhancedMultiUserOllamaRunner()
    print("✅ Enhanced Ollama Runner initialized successfully.")
except Exception as e:
    import traceback
    print("❌ Enhanced Ollama Runner initialization failed!")
    traceback.print_exc()
    enhanced_ollama_runner = None


# ============================================================
# Backward compatibility helper
# ============================================================

def send_prompt_with_research(model_name: str, prompt: str, user_id: str = "legacy_user") -> str:
    """Araştırma yeteneği ekli prompt gönderme"""
    if enhanced_ollama_runner:
        result = enhanced_ollama_runner.chat_with_model(
            model_name=model_name,
            prompt=prompt,
            user_id=user_id,
            enable_research=True
        )
        return result.get("response", f"❌ Hata: {result.get('error', 'Yanıt alınamadı')}")
    else:
        return "❌ Runner başlatılamadı."


# ============================================================
# Debug info when running standalone
# ============================================================

if __name__ == "__main__":
    print("🔬 AI Web Research Agent başlatılıyor...\n")
    if enhanced_ollama_runner:
        stats = enhanced_ollama_runner.get_research_stats()
        print(f"📊 Research Stats:")
        print(f"   Enabled: {stats['web_research_enabled']}")
        print(f"   Tools: {stats['available_tools']}")
    else:
        print("⚠️ Enhanced runner yüklenemedi.")
