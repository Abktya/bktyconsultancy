# ai_external_api_agent.py - AI modelinin external API'leri kullanması için agent
import re
import logging
from typing import Dict, List, Any, Optional
from external_api_service import (
    external_api_service,
    format_exchange_rate_response,
    format_news_response,
    format_movie_response
)

logger = logging.getLogger(__name__)


class ExternalAPIAgent:
    """AI modelinin external API'leri kullanması için agent sınıfı"""
    
    def __init__(self):
        self.api_service = external_api_service
        
        # Intent detection patterns
        self.intent_patterns = {
            "exchange_rate": [
                r'\b(döviz|kur|currency|exchange|rate)\b',
                r'\b(usd|eur|gbp|try|tl|jpy|chf)\b',  # ← tl eklendi
                r'\b(dollar|dolar|euro|pound|sterlin|lira|yen|frank)\b',  # ← genişletildi
                r'\b(kaç|ne kadar|how much|convert)\b.*\b(dolar|euro|sterlin|lira|tl)\b',  # ← tl eklendi
                r'\d+\s*(dolar|dollar|euro|sterlin|pound|lira|tl|yen)\s+(kaç|ne kadar)',  # ← yeni pattern
            ],
            "news": [
                r'\b(haber|news|gündem|haberler|headlines)\b',
                r'\b(son\s+haber|latest\s+news|breaking\s+news)\b',
                r'\b(teknoloji|spor|ekonomi|dünya|technology|sports|business|world)\s+(haber|news)\b',
                r'\b(ne\s+oluyor|what\'s\s+happening|neler\s+var)\b'
            ],
            "movies": [
                r'\b(film|movie|sinema|cinema)\b',
                r'\b(imdb|tmdb|rotten\s+tomatoes)\b',
                r'\b(fragman|trailer|oyuncu|cast|yönetmen|director)\b',
                r'\b(hangi\s+film|which\s+movie|film\s+öner|movie\s+recommend)\b'
            ]
        }
    
    def detect_intent(self, prompt: str) -> Dict[str, Any]:
        """Kullanıcının intent'ini algıla"""
        prompt_lower = prompt.lower().strip()
        
        detected_intents = []
        
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, prompt_lower):
                    detected_intents.append(intent_type)
                    break
        
        if not detected_intents:
            return {
                "has_api_intent": False,
                "intents": [],
                "confidence": 0.0
            }
        
        # En güçlü intent'i belirle
        primary_intent = detected_intents[0]
        confidence = 0.9 if len(detected_intents) == 1 else 0.7
        
        return {
            "has_api_intent": True,
            "intents": detected_intents,
            "primary_intent": primary_intent,
            "confidence": confidence,
            "extracted_query": self._extract_query(prompt, primary_intent)
        }
    
    def _extract_query(self, prompt: str, intent_type: str) -> Dict[str, Any]:
        """Intent'e göre query parametrelerini çıkar"""
        if intent_type == "exchange_rate":
            return self._extract_currency_query(prompt)
        elif intent_type == "news":
            return self._extract_news_query(prompt)
        elif intent_type == "movies":
            return self._extract_movie_query(prompt)
        
        return {}
    
    def _extract_currency_query(self, prompt: str) -> Dict[str, Any]:
        """Döviz query'sini çıkar"""
        prompt_lower = prompt.lower()
        
        # Currency codes - TL eklendi
        currencies = {
            'dolar': 'USD', 'dollar': 'USD', 'usd': 'USD',
            'euro': 'EUR', 'eur': 'EUR',
            'sterlin': 'GBP', 'pound': 'GBP', 'gbp': 'GBP',
            'lira': 'TRY', 'türk lirası': 'TRY', 'try': 'TRY', 'tl': 'TRY',  # ← TL eklendi
            'yen': 'JPY', 'jpy': 'JPY',
            'frank': 'CHF', 'chf': 'CHF'
        }
        
        detected_currencies = []
        for name, code in currencies.items():
            if name in prompt_lower:
                detected_currencies.append(code)
        
        # Conversion pattern: "X dollar kaç euro" / "convert X USD to EUR"
        conversion_patterns = [
            r'(\d+(?:\.\d+)?)\s*(\w+)\s+(?:kaç|ne kadar|to)\s+(\w+)',
            r'convert\s+(\d+(?:\.\d+)?)\s+(\w+)\s+to\s+(\w+)'
        ]
        
        for pattern in conversion_patterns:
            match = re.search(pattern, prompt_lower)
            if match:
                amount = float(match.group(1))
                from_curr = match.group(2).upper()
                to_curr = match.group(3).upper()
                
                # Currency name'leri code'a çevir
                from_curr = currencies.get(from_curr.lower(), from_curr)
                to_curr = currencies.get(to_curr.lower(), to_curr)
                
                return {
                    "action": "convert",
                    "amount": amount,
                    "from_currency": from_curr,
                    "to_currency": to_curr
                }
        
        # Basit kur sorgusu
        if detected_currencies:
            return {
                "action": "get_rates",
                "base_currency": detected_currencies[0] if detected_currencies else "USD"
            }
        
        return {"action": "get_rates", "base_currency": "USD"}
    
    def _extract_news_query(self, prompt: str) -> Dict[str, Any]:
        """Haber query'sini çıkar"""
        prompt_lower = prompt.lower()
        
        # Language detection
        language = "tr" if any(word in prompt_lower for word in ["haber", "haberler", "gündem"]) else "en"
        
        # Category detection
        category_map = {
            "teknoloji": "technology",
            "technology": "technology",
            "tech": "technology",
            "spor": "sports",
            "sports": "sports",
            "ekonomi": "business",
            "business": "business",
            "iş": "business",
            "dünya": "world",
            "world": "world",
            "sağlık": "health",
            "health": "health"
        }
        
        detected_category = None
        for keyword, category in category_map.items():
            if keyword in prompt_lower:
                detected_category = category
                break
        
        # Extract search terms
        search_terms = []
        
        # Remove common question words
        cleaned_prompt = re.sub(r'\b(son|latest|breaking|güncel|neler|what|haber|haberler|news)\b', '', prompt_lower)
        cleaned_prompt = cleaned_prompt.strip()
        
        if cleaned_prompt and len(cleaned_prompt) > 3:
            search_terms.append(cleaned_prompt)
        
        return {
            "action": "search_news",
            "language": language,
            "category": detected_category,
            "query": search_terms[0] if search_terms else None
        }
    
    def _extract_movie_query(self, prompt: str) -> Dict[str, Any]:
        """Film query'sini çıkar"""
        prompt_lower = prompt.lower()
        
        # Language detection
        language = "tr-TR" if any(word in prompt_lower for word in ["film", "sinema"]) else "en-US"
        
        # Specific movie title extraction
        # Pattern: "X filmi hakkında" / "about X movie"
        title_patterns = [
            r'(?:film[i]?\s+)([^?]+?)(?:\s+hakkında|\s+bilgi|\s+detay|$)',
            r'([^?]+?)\s+(?:film[i]?|movie)',
            r'(?:about|regarding)\s+([^?]+?)(?:\s+movie|$)'
        ]
        
        movie_title = None
        for pattern in title_patterns:
            match = re.search(pattern, prompt_lower)
            if match:
                movie_title = match.group(1).strip()
                break
        
        # Remove common words
        if movie_title:
            remove_words = ['bir', 'a', 'an', 'the', 'hangi', 'which', 'ne', 'what']
            movie_title = ' '.join([w for w in movie_title.split() if w not in remove_words])
        
        # Popüler filmler sorgusu
        if any(word in prompt_lower for word in ['popüler', 'popular', 'trending', 'güncel']):
            return {
                "action": "popular_movies",
                "language": language
            }
        
        if movie_title:
            return {
                "action": "search_movie",
                "query": movie_title,
                "language": language
            }
        
        return {
            "action": "popular_movies",
            "language": language
        }
    
    def execute_api_call(self, intent_data: Dict) -> Dict[str, Any]:
        """Intent'e göre API çağrısı yap"""
        try:
            primary_intent = intent_data.get("primary_intent")
            extracted_query = intent_data.get("extracted_query", {})
            
            if primary_intent == "exchange_rate":
                return self._execute_currency_api(extracted_query)
            elif primary_intent == "news":
                return self._execute_news_api(extracted_query)
            elif primary_intent == "movies":
                return self._execute_movie_api(extracted_query)
            
            return {"error": "Unknown intent type"}
            
        except Exception as e:
            logger.error(f"API execution error: {e}")
            return {"error": f"API call failed: {str(e)}"}
    
    def _execute_currency_api(self, query: Dict) -> Dict[str, Any]:
        """Döviz API'sini çağır"""
        action = query.get("action", "get_rates")
        
        if action == "convert":
            # Önce base currency ile tüm kurları çek
            from_curr = query.get("from_currency", "USD")
            to_curr = query.get("to_currency", "EUR")
            amount = query.get("amount", 1)
            
            # Tüm kurları al
            rates_result = self.api_service.get_exchange_rates(from_curr)
            
            if rates_result.get("success") and to_curr in rates_result.get("rates", {}):
                # Manuel hesaplama yap
                rate = rates_result["rates"][to_curr]
                converted = amount * rate
                
                result = {
                    "success": True,
                    "from_currency": from_curr,
                    "to_currency": to_curr,
                    "amount": amount,
                    "converted_amount": converted,
                    "conversion_rate": rate,
                    "last_update": rates_result.get("last_update", "")
                }
            else:
                result = {"success": False, "error": f"Kur bilgisi bulunamadı: {to_curr}"}
        else:
            result = self.api_service.get_popular_currency_rates(
                base_currency=query.get("base_currency", "USD")
            )
        
        # Formatted response ekle
        if result.get("success"):
            from external_api_service import format_exchange_rate_response
            result["formatted_response"] = format_exchange_rate_response(result)
        
        return result
    
    def _execute_news_api(self, query: Dict) -> Dict[str, Any]:
        """Haber API'sini çağır"""
        action = query.get("action", "search_news")
        
        if action == "search_news":
            result = self.api_service.get_news(
                query=query.get("query"),
                language=query.get("language", "en"),
                categories=[query["category"]] if query.get("category") else None,
                limit=5
            )
        else:
            result = self.api_service.get_top_headlines(
                language=query.get("language", "en"),
                category=query.get("category"),
                limit=5
            )
        
        if result.get("success"):
            result["formatted_response"] = format_news_response(result)
        
        return result
    
    def _execute_movie_api(self, query: Dict) -> Dict[str, Any]:
        """Film API'sini çağır"""
        action = query.get("action", "search_movie")
        
        if action == "popular_movies":
            result = self.api_service.get_popular_movies(
                language=query.get("language", "en-US")
            )
        else:
            result = self.api_service.search_movies(
                query=query.get("query", ""),
                language=query.get("language", "en-US")
            )
        
        if result.get("success"):
            result["formatted_response"] = format_movie_response(result)
        
        return result
    
    def enhance_prompt_with_api_data(self, original_prompt: str, api_result: Dict) -> str:
        if not api_result.get("success"):
            return original_prompt
        
        # Sadece ihtiyaç duyulan bilgiyi al
        if api_result.get("converted_amount"):
            # Conversion sonucu - çok kısa
            amount = api_result.get("amount", 1)
            from_curr = api_result.get("from_currency", "")
            to_curr = api_result.get("to_currency", "")
            converted = api_result.get("converted_amount", 0)
            
            enhanced_prompt = f"{original_prompt}\n\nGüncel kur: {amount} {from_curr} = {converted:.4f} {to_curr}\nKısa yanıt ver."
        else:
            # Diğer durumlar için de kısa tut
            formatted = api_result.get("formatted_response", "")[:200] 
    
    
    def process_user_query(self, prompt: str) -> Dict[str, Any]:
        """Kullanıcı sorgusunu işle - tam pipeline"""
        # 1. Intent detection
        intent_data = self.detect_intent(prompt)
        
        if not intent_data.get("has_api_intent"):
            return {
                "api_used": False,
                "original_prompt": prompt,
                "enhanced_prompt": prompt
            }
        
        # 2. API call
        api_result = self.execute_api_call(intent_data)
        
        # 3. Enhance prompt
        enhanced_prompt = self.enhance_prompt_with_api_data(prompt, api_result)
        
        return {
            "api_used": True,
            "original_prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "intent_data": intent_data,
            "api_result": api_result,
            "api_success": api_result.get("success", False)
        }


# Global instance
external_api_agent = ExternalAPIAgent()


# Helper function for easy integration
def enhance_ai_prompt_with_apis(prompt: str) -> Dict[str, Any]:
    """
    AI prompt'unu external API'lerle güçlendir
    
    Returns:
        Dict with:
            - enhanced_prompt: API verileriyle zenginleştirilmiş prompt
            - api_used: API kullanıldı mı?
            - api_data: Ham API verisi (varsa)
    """
    return external_api_agent.process_user_query(prompt)


if __name__ == "__main__":
    # Test cases
    test_prompts = [
        "1 dolar kaç euro?",
        "USD to TRY exchange rate",
        "son teknoloji haberleri",
        "latest sports news",
        "Inception filmi hakkında bilgi",
        "popular movies"
    ]
    
    for prompt in test_prompts:
        print(f"\n{'='*60}")
        print(f"Prompt: {prompt}")
        print(f"{'='*60}")
        
        result = enhance_ai_prompt_with_apis(prompt)
        
        print(f"API Used: {result['api_used']}")
        if result['api_used']:
            print(f"Intent: {result['intent_data']['primary_intent']}")
            print(f"API Success: {result['api_success']}")
            if result['api_success']:
                print(f"\nFormatted Response:")
                print(result['api_result'].get('formatted_response', 'N/A'))