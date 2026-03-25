# external_api_service.py - External API Integration Service
import os
import requests
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from functools import lru_cache
import json

# .env dosyasını yükle
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv yoksa devam et

logger = logging.getLogger(__name__)

class ExternalAPIService:
    """Harici API'lerden veri çeken servis"""
    
    def __init__(self):
        # API Keys - .env dosyasından yüklenecek
        self.exchangerate_api_key = os.getenv('EXCHANGERATE_API_KEY', '')
        self.newsapi_key = os.getenv('THENEWSAPI_KEY', '')
        self.tmdb_api_key = os.getenv('TMDB_API_KEY', '')
        
        # API Base URLs
        self.exchangerate_base = "https://v6.exchangerate-api.com/v6"
        self.newsapi_base = "https://api.thenewsapi.com/v1/news"
        self.tmdb_base = "https://api.themoviedb.org/3"
        
        # Cache settings
        self.cache_duration = 3600  # 1 saat
        self._cache = {}
    
    def _get_cached(self, key: str) -> Optional[Dict]:
        """Cache'den veri al"""
        if key in self._cache:
            cached_data, timestamp = self._cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_duration):
                return cached_data
            del self._cache[key]
        return None
    
    def _set_cache(self, key: str, data: Dict):
        """Cache'e veri kaydet"""
        self._cache[key] = (data, datetime.now())
    
    # =========================================================================
    # EXCHANGE RATE API - Döviz Kurları
    # =========================================================================
    
    def get_exchange_rates(self, base_currency: str = "USD") -> Dict[str, Any]:
        """
        Döviz kurlarını getir
        
        Args:
            base_currency: Ana para birimi (USD, EUR, GBP, TRY, etc.)
        
        Returns:
            Dict: Tüm döviz kurları
        """
        cache_key = f"exchange_{base_currency}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            if not self.exchangerate_api_key:
                return {"error": "Exchange Rate API key not configured"}
            
            url = f"{self.exchangerate_base}/{self.exchangerate_api_key}/latest/{base_currency}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('result') == 'success':
                result = {
                    "success": True,
                    "base_currency": base_currency,
                    "rates": data.get('conversion_rates', {}),
                    "last_update": data.get('time_last_update_utc', ''),
                    "next_update": data.get('time_next_update_utc', '')
                }
                self._set_cache(cache_key, result)
                return result
            else:
                return {"error": data.get('error-type', 'Unknown error')}
                
        except Exception as e:
            logger.error(f"Exchange rate API error: {e}")
            return {"error": f"Exchange rate fetch failed: {str(e)}"}
    
    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """
        Para birimi çevirme
        
        Args:
            amount: Miktar
            from_currency: Kaynak para birimi
            to_currency: Hedef para birimi
        
        Returns:
            Dict: Çevrilmiş miktar ve detaylar
        """
        try:
            if not self.exchangerate_api_key:
                return {"error": "Exchange Rate API key not configured"}
            
            url = f"{self.exchangerate_base}/{self.exchangerate_api_key}/pair/{from_currency}/{to_currency}/{amount}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('result') == 'success':
                return {
                    "success": True,
                    "from_currency": from_currency,
                    "to_currency": to_currency,
                    "amount": amount,
                    "converted_amount": data.get('conversion_result', 0),
                    "conversion_rate": data.get('conversion_rate', 0),
                    "last_update": data.get('time_last_update_utc', '')
                }
            else:
                return {"error": data.get('error-type', 'Conversion failed')}
                
        except Exception as e:
            logger.error(f"Currency conversion error: {e}")
            return {"error": f"Conversion failed: {str(e)}"}
    
    def get_popular_currency_rates(self, base_currency: str = "USD") -> Dict[str, Any]:
        """Popüler döviz kurlarını getir (USD, EUR, GBP, TRY, JPY, etc.)"""
        popular_currencies = ["EUR", "GBP", "TRY", "JPY", "CHF", "CAD", "AUD"]
        
        rates = self.get_exchange_rates(base_currency)
        
        if rates.get("success"):
            popular_rates = {
                currency: rates["rates"].get(currency, 0)
                for currency in popular_currencies
                if currency in rates["rates"]
            }
            
            return {
                "success": True,
                "base_currency": base_currency,
                "popular_rates": popular_rates,
                "last_update": rates.get("last_update", "")
            }
        
        return rates
    
    # =========================================================================
    # THE NEWS API - Haberler
    # =========================================================================
    
    def get_news(self, query: str = None, language: str = "en", 
                 categories: List[str] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Haberleri getir
        
        Args:
            query: Arama terimi
            language: Dil kodu (en, tr, etc.)
            categories: Kategori listesi (general, business, sports, etc.)
            limit: Maksimum haber sayısı
        
        Returns:
            Dict: Haber listesi
        """
        cache_key = f"news_{query}_{language}_{categories}_{limit}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            if not self.newsapi_key:
                return {"error": "News API key not configured"}
            
            params = {
                "api_token": self.newsapi_key,
                "language": language,
                "limit": limit
            }
            
            if query:
                params["search"] = query
            
            if categories:
                params["categories"] = ",".join(categories)
            
            url = f"{self.newsapi_base}/all"
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            articles = []
            for article in data.get('data', []):
                articles.append({
                    "title": article.get('title', ''),
                    "description": article.get('description', ''),
                    "url": article.get('url', ''),
                    "source": article.get('source', ''),
                    "published_at": article.get('published_at', ''),
                    "image_url": article.get('image_url', ''),
                    "categories": article.get('categories', [])
                })
            
            result = {
                "success": True,
                "total_results": len(articles),
                "articles": articles,
                "language": language
            }
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"News API error: {e}")
            return {"error": f"News fetch failed: {str(e)}"}
    
    def get_top_headlines(self, language: str = "en", category: str = None, 
                          limit: int = 10) -> Dict[str, Any]:
        """
        Top headlines getir
        
        Args:
            language: Dil kodu
            category: Kategori (general, business, technology, etc.)
            limit: Maksimum haber sayısı
        
        Returns:
            Dict: Top headlines
        """
        try:
            if not self.newsapi_key:
                return {"error": "News API key not configured"}
            
            params = {
                "api_token": self.newsapi_key,
                "language": language,
                "limit": limit
            }
            
            if category:
                params["categories"] = category
            
            url = f"{self.newsapi_base}/top"
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            headlines = []
            for article in data.get('data', []):
                headlines.append({
                    "title": article.get('title', ''),
                    "description": article.get('description', ''),
                    "url": article.get('url', ''),
                    "source": article.get('source', ''),
                    "published_at": article.get('published_at', ''),
                    "image_url": article.get('image_url', '')
                })
            
            return {
                "success": True,
                "total_results": len(headlines),
                "headlines": headlines,
                "language": language,
                "category": category or "all"
            }
            
        except Exception as e:
            logger.error(f"Top headlines error: {e}")
            return {"error": f"Headlines fetch failed: {str(e)}"}
    
    # =========================================================================
    # TMDB API - Filmler ve TV Dizileri
    # =========================================================================
    
    def search_movies(self, query: str, language: str = "en-US", 
                     page: int = 1) -> Dict[str, Any]:
        """
        Film ara
        
        Args:
            query: Arama terimi
            language: Dil kodu
            page: Sayfa numarası
        
        Returns:
            Dict: Film listesi
        """
        cache_key = f"movie_search_{query}_{language}_{page}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            if not self.tmdb_api_key:
                return {"error": "TMDB API key not configured"}
            
            url = f"{self.tmdb_base}/search/movie"
            params = {
                "api_key": self.tmdb_api_key,
                "query": query,
                "language": language,
                "page": page
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            movies = []
            for movie in data.get('results', []):
                movies.append({
                    "id": movie.get('id'),
                    "title": movie.get('title', ''),
                    "original_title": movie.get('original_title', ''),
                    "overview": movie.get('overview', ''),
                    "release_date": movie.get('release_date', ''),
                    "vote_average": movie.get('vote_average', 0),
                    "vote_count": movie.get('vote_count', 0),
                    "popularity": movie.get('popularity', 0),
                    "poster_path": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None,
                    "backdrop_path": f"https://image.tmdb.org/t/p/w1280{movie.get('backdrop_path')}" if movie.get('backdrop_path') else None
                })
            
            result = {
                "success": True,
                "total_results": data.get('total_results', 0),
                "page": page,
                "total_pages": data.get('total_pages', 0),
                "movies": movies
            }
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"TMDB search error: {e}")
            return {"error": f"Movie search failed: {str(e)}"}
    
    def get_movie_details(self, movie_id: int, language: str = "en-US") -> Dict[str, Any]:
        """
        Film detaylarını getir
        
        Args:
            movie_id: TMDB film ID
            language: Dil kodu
        
        Returns:
            Dict: Film detayları
        """
        cache_key = f"movie_details_{movie_id}_{language}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            if not self.tmdb_api_key:
                return {"error": "TMDB API key not configured"}
            
            url = f"{self.tmdb_base}/movie/{movie_id}"
            params = {
                "api_key": self.tmdb_api_key,
                "language": language,
                "append_to_response": "credits,videos,similar"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            movie = response.json()
            
            # Cast bilgisi
            cast = []
            for person in movie.get('credits', {}).get('cast', [])[:10]:
                cast.append({
                    "name": person.get('name', ''),
                    "character": person.get('character', ''),
                    "profile_path": f"https://image.tmdb.org/t/p/w185{person.get('profile_path')}" if person.get('profile_path') else None
                })
            
            # Video trailers
            videos = []
            for video in movie.get('videos', {}).get('results', []):
                if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                    videos.append({
                        "name": video.get('name', ''),
                        "key": video.get('key', ''),
                        "url": f"https://www.youtube.com/watch?v={video.get('key')}"
                    })
            
            result = {
                "success": True,
                "id": movie.get('id'),
                "title": movie.get('title', ''),
                "original_title": movie.get('original_title', ''),
                "tagline": movie.get('tagline', ''),
                "overview": movie.get('overview', ''),
                "release_date": movie.get('release_date', ''),
                "runtime": movie.get('runtime', 0),
                "budget": movie.get('budget', 0),
                "revenue": movie.get('revenue', 0),
                "vote_average": movie.get('vote_average', 0),
                "vote_count": movie.get('vote_count', 0),
                "popularity": movie.get('popularity', 0),
                "genres": [g.get('name') for g in movie.get('genres', [])],
                "production_companies": [c.get('name') for c in movie.get('production_companies', [])],
                "cast": cast,
                "trailers": videos,
                "poster_url": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None,
                "backdrop_url": f"https://image.tmdb.org/t/p/w1280{movie.get('backdrop_path')}" if movie.get('backdrop_path') else None,
                "homepage": movie.get('homepage', '')
            }
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"TMDB details error: {e}")
            return {"error": f"Movie details fetch failed: {str(e)}"}
    
    def get_popular_movies(self, language: str = "en-US", page: int = 1) -> Dict[str, Any]:
        """Popüler filmleri getir"""
        cache_key = f"popular_movies_{language}_{page}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        try:
            if not self.tmdb_api_key:
                return {"error": "TMDB API key not configured"}
            
            url = f"{self.tmdb_base}/movie/popular"
            params = {
                "api_key": self.tmdb_api_key,
                "language": language,
                "page": page
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            movies = []
            for movie in data.get('results', []):
                movies.append({
                    "id": movie.get('id'),
                    "title": movie.get('title', ''),
                    "overview": movie.get('overview', ''),
                    "release_date": movie.get('release_date', ''),
                    "vote_average": movie.get('vote_average', 0),
                    "popularity": movie.get('popularity', 0),
                    "poster_path": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None
                })
            
            result = {
                "success": True,
                "total_results": data.get('total_results', 0),
                "page": page,
                "movies": movies
            }
            
            self._set_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"TMDB popular movies error: {e}")
            return {"error": f"Popular movies fetch failed: {str(e)}"}
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_service_status(self) -> Dict[str, Any]:
        """Tüm servislerin durumunu kontrol et"""
        return {
            "exchangerate_api": {
                "configured": bool(self.exchangerate_api_key),
                "status": "ready" if self.exchangerate_api_key else "not configured"
            },
            "news_api": {
                "configured": bool(self.newsapi_key),
                "status": "ready" if self.newsapi_key else "not configured"
            },
            "tmdb_api": {
                "configured": bool(self.tmdb_api_key),
                "status": "ready" if self.tmdb_api_key else "not configured"
            },
            "cache_size": len(self._cache),
            "timestamp": datetime.now().isoformat()
        }
    
    def clear_cache(self):
        """Cache'i temizle"""
        self._cache.clear()
        return {"message": "Cache cleared", "timestamp": datetime.now().isoformat()}


# Global instance
external_api_service = ExternalAPIService()


# =========================================================================
# Helper Functions - AI Model için format edilmiş yanıtlar
# =========================================================================

def format_exchange_rate_response(data: Dict) -> str:
    """Döviz kuru bilgisini AI için formatla"""
    if not data.get("success"):
        return f"❌ Döviz kuru bilgisi alınamadı: {data.get('error', 'Bilinmeyen hata')}"
    
    # Conversion sonucu mu?
    if "converted_amount" in data:
        from_curr = data.get("from_currency", "")
        to_curr = data.get("to_currency", "")
        amount = data.get("amount", 1)
        converted = data.get("converted_amount", 0)
        rate = data.get("conversion_rate", 0)
        
        response = f"💱 **Döviz Çevirme:**\n\n"
        response += f"{amount} {from_curr} = {converted:.4f} {to_curr}\n"
        response += f"Kur: 1 {from_curr} = {rate:.4f} {to_curr}\n"
        response += f"🕐 Son güncelleme: {data.get('last_update', 'N/A')}"
        return response
    
    # Normal rates sonucu
    base = data.get("base_currency", "USD")
    rates = data.get("rates", {}) or data.get("popular_rates", {})
    
    response = f"💱 **{base} Döviz Kurları:**\n\n"
    
    # Popüler kurlar
    popular = ["EUR", "GBP", "TRY", "JPY", "CHF"]
    for currency in popular:
        if currency in rates and currency != base:
            response += f"• 1 {base} = {rates[currency]:.4f} {currency}\n"
    
    response += f"\n🕐 Son güncelleme: {data.get('last_update', 'N/A')}"
    
    return response

def format_news_response(data: Dict) -> str:
    """Haber bilgisini AI için formatla"""
    if not data.get("success"):
        return f"❌ Haber bilgisi alınamadı: {data.get('error', 'Bilinmeyen hata')}"
    
    articles = data.get("articles", [])
    
    if not articles:
        return "📰 İlgili haber bulunamadı."
    
    response = f"📰 **Son Haberler** ({data.get('total_results', 0)} sonuç):\n\n"
    
    for i, article in enumerate(articles[:5], 1):
        response += f"{i}. **{article['title']}**\n"
        response += f"   📝 {article['description'][:150]}...\n"
        response += f"   🔗 {article['url']}\n"
        response += f"   📅 {article['published_at']}\n\n"
    
    return response


def format_movie_response(data: Dict) -> str:
    """Film bilgisini AI için formatla"""
    if not data.get("success"):
        return f"❌ Film bilgisi alınamadı: {data.get('error', 'Bilinmeyen hata')}"
    
    # Film detayları mı yoksa arama sonuçları mı?
    if "title" in data:  # Tek film detayı
        movie = data
        response = f"🎬 **{movie['title']}**"
        
        if movie.get('tagline'):
            response += f"\n*{movie['tagline']}*"
        
        response += f"\n\n📅 Çıkış: {movie.get('release_date', 'N/A')}"
        response += f"\n⭐ Puan: {movie.get('vote_average', 0)}/10 ({movie.get('vote_count', 0)} oy)"
        response += f"\n⏱️ Süre: {movie.get('runtime', 0)} dakika"
        
        if movie.get('genres'):
            response += f"\n🎭 Tür: {', '.join(movie['genres'])}"
        
        response += f"\n\n📖 {movie.get('overview', 'Özet yok')}"
        
        if movie.get('cast'):
            cast_names = [c['name'] for c in movie['cast'][:5]]
            response += f"\n\n👥 Oyuncular: {', '.join(cast_names)}"
        
        if movie.get('trailers'):
            response += f"\n\n🎥 Fragman: {movie['trailers'][0]['url']}"
        
    else:  # Arama sonuçları
        movies = data.get("movies", [])
        response = f"🎬 **Film Arama Sonuçları** ({data.get('total_results', 0)} sonuç):\n\n"
        
        for i, movie in enumerate(movies[:5], 1):
            response += f"{i}. **{movie['title']}** ({movie.get('release_date', 'N/A')[:4]})\n"
            response += f"   ⭐ {movie.get('vote_average', 0)}/10\n"
            if movie.get('overview'):
                response += f"   📝 {movie['overview'][:100]}...\n"
            response += "\n"
    
    return response


if __name__ == "__main__":
    # Test kodları
    service = ExternalAPIService()
    
    print("🧪 Service Status:")
    print(json.dumps(service.get_service_status(), indent=2))
    
    # Exchange rate test
    # rates = service.get_popular_currency_rates("USD")
    # print("\n💱 Exchange Rates:")
    # print(format_exchange_rate_response(rates))