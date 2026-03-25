# football_prediction_agent.py
import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class FootballPredictionAgent:
    """API-Football ile maç tahminleri"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('FOOTBALL_API_KEY')
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        self.enabled = bool(self.api_key)
        
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """API isteği yap"""
        if not self.enabled:
            return {"errors": ["API key not configured"]}
            
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Football API error: {e}")
            return {"errors": [str(e)]}
    
    def search_team(self, team_name: str) -> Optional[int]:
        """Takım adından ID bul"""
        result = self._make_request("teams", {"search": team_name})
        
        if result.get("response") and len(result["response"]) > 0:
            return result["response"][0]["team"]["id"]
        return None
    
    def get_team_statistics(self, team_id: int, league_id: int, season: int = 2024) -> Dict:
        """Takım istatistiklerini al"""
        return self._make_request("teams/statistics", {
            "team": team_id,
            "league": league_id,
            "season": season
        })
    
    def get_upcoming_matches(self, league_id: int, days: int = 7) -> List[Dict]:
        """Yaklaşan maçlar"""
        today = datetime.now()
        end_date = today + timedelta(days=days)
        
        result = self._make_request("fixtures", {
            "league": league_id,
            "from": today.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d")
        })
        
        return result.get("response", [])

    def create_analysis_prompt(self, team1_name: str, team2_name: str, league_id: int = 203) -> str:
        """Maç analizi için prompt oluştur"""
        
        if not self.enabled:
            return f"""⚽ **Maç Analizi: {team1_name} vs {team2_name}**

❌ Football API entegrasyonu aktif değil (API key eksik).

Genel değerlendirme yapabilirsiniz ama detaylı istatistik sunulamaz.

⚠️ **UYARI:** Bu bir tahmin DEĞİL, genel yorumdur."""

        team1_id = self.search_team(team1_name)
        team2_id = self.search_team(team2_name)
        
        if not team1_id or not team2_id:
            return f"""⚽ **Maç Analizi: {team1_name} vs {team2_name}**

❌ Takımlar API'de bulunamadı.

Lütfen tam takım isimlerini kullanın (örn: "Galatasaray", "Fenerbahce").

⚠️ **UYARI:** Bu bir tahmin DEĞİL."""

        stats1 = self.get_team_statistics(team1_id, league_id)
        stats2 = self.get_team_statistics(team2_id, league_id)
        
        # İstatistik çıkarma
        def extract_stats(stats_data):
            if "errors" in stats_data or not stats_data.get("response"):
                return "Veri yok"
            r = stats_data["response"]
            fixtures = r.get("fixtures", {})
            goals = r.get("goals", {})
            return f"""- Maç: {fixtures.get('played', {}).get('total', 0)}
- Galibiyet: {fixtures.get('wins', {}).get('total', 0)}
- Beraberlik: {fixtures.get('draws', {}).get('total', 0)}
- Mağlubiyet: {fixtures.get('loses', {}).get('total', 0)}
- Attığı Gol: {goals.get('for', {}).get('total', {}).get('total', 0)}
- Yediği Gol: {goals.get('against', {}).get('total', {}).get('total', 0)}"""
        
        prompt = f"""⚽ **Maç Analizi: {team1_name} vs {team2_name}**

📊 **İstatistikler:**

**{team1_name}:**
{extract_stats(stats1)}

**{team2_name}:**
{extract_stats(stats2)}

**Lütfen şu konularda objektif bir analiz yap:**
1. Her iki takımın güçlü/zayıf yönleri
2. İstatistiksel karşılaştırma
3. Olası senaryo değerlendirmesi

⚠️ **ÖNEMLİ:** KESİN TAHMİN YAPMA, sadece istatistiksel değerlendirme yap. Futbolda sürprizler olur."""

        return prompt


# Multi-user Ollama entegrasyonu
def integrate_football_predictions(multi_user_ollama_instance):
    """Football prediction'ı mevcut AI sistemine entegre et"""
    
    football_agent = FootballPredictionAgent()
    
    # ✅ DÜZELTME: Metod adını predict_football_match olarak değiştir
    def predict_football_match(team1: str, team2: str, user_id: str = "football_user") -> Dict:
        """Maç tahmini yap - SORUMLULUK REDDİ ile"""
        try:
            # Analiz promptu oluştur
            analysis_prompt = football_agent.create_analysis_prompt(team1, team2)
            
            # AI'dan analiz al
            ai_result = multi_user_ollama_instance.chat_with_model(
                model_name="qwen2.5:14b-instruct",
                prompt=analysis_prompt,
                user_id=user_id,
                system_prompt="Sen futbol istatistik analistisin. Sadece verilere dayalı objektif değerlendirme yaparsın, KESİN TAHMİN VERMEZSİN. Futbolda sürprizler olduğunu her zaman vurgularsın.",
                auto_select_model=False
            )
            
            if "error" in ai_result:
                return {"success": False, "error": ai_result["error"]}
            
            # Sorumluluk reddi ekle
            disclaimer = "\n\n⚠️ **SORUMLULUK REDDİ:** Bu bir istatistiksel analizdir, kesin tahmin DEĞİLDİR. Bahis/kumar amaçlı kullanmayın. Sonuçlardan sorumluluk kabul edilmez."
            
            # ✅ Frontend'in beklediği format
            return {
                "success": True,
                "analysis": ai_result.get("response", "Analiz yapılamadı") + disclaimer,
                "model": ai_result.get("model", "qwen2.5:14b-instruct"),
                "response_time": ai_result.get("response_time", 0)
            }
            
        except Exception as e:
            logger.error(f"Football prediction error: {e}")
            return {"success": False, "error": str(e)}
    
    # Instance'a metod ekle
    multi_user_ollama_instance.predict_football_match = predict_football_match
    multi_user_ollama_instance.football_agent = football_agent
    
    return multi_user_ollama_instance