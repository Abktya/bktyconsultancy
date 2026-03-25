import requests
import time
import random
from typing import Dict, Optional, List

class DDoSSimulationTester:
    # WebShare proxy havuzu - Sınıf seviyesinde tanımla
    PROXY_POOL = [
        {
            "http": "http://ersinbom-TR-rotate:v6ziohc5x07t@p.webshare.io:80",
            "https": "http://ersinbom-TR-rotate:v6ziohc5x07t@p.webshare.io:80"
        }
    ]
    
    # User-Agent listesi - Çeşitlilik için
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.69"
    ]
    
    def __init__(self, target_url: str, scan_id: str):
        self.target_url = target_url
        self.scan_id = scan_id
        self.request_counter = 0  # İstek sayacı
        self.proxy_stats = {}  # Proxy istatistikleri
        # ... diğer init kodları
    
    def send_request(self) -> Dict:
        """
        Optimize edilmiş HTTP isteği gönderme metodu
        
        Returns:
            Dict: İstek sonucu içeren dictionary
        """
        start_time = time.time()
        self.request_counter += 1
        
        try:
            # Proxy seçimi - Eğer birden fazla proxy varsa rastgele seç
            proxy = None
            proxy_info = "No proxy"
            
            if self.PROXY_POOL:
                if len(self.PROXY_POOL) > 1:
                    # Birden fazla proxy varsa rastgele seç
                    proxy = random.choice(self.PROXY_POOL)
                else:
                    # Tek proxy var
                    proxy = self.PROXY_POOL[0]
                
                proxy_info = proxy["http"] if proxy else "No proxy"
            
            # Rastgele User-Agent seç
            user_agent = random.choice(self.USER_AGENTS)
            
            # Request headers
            headers = {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "X-SiteTestPro-Test": "ddos-simulation",
                "X-Request-ID": f"{self.scan_id}-{self.request_counter}"
            }
            
            # Session kullan (connection pooling için)
            session = requests.Session()
            
            # Proxy ayarla
            if proxy:
                session.proxies.update(proxy)
            
            # SSL doğrulamayı kapat (test için)
            session.verify = False
            
            # Timeout değerleri
            timeout = (5, 30)  # (connection timeout, read timeout)
            
            # İsteği gönder
            response = session.get(
                self.target_url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
                stream=False  # Tüm içeriği indir
            )
            
            # Session'ı kapat
            session.close()
            
            response_time = time.time() - start_time
            
            # Başarılı istek istatistikleri
            self._update_proxy_stats(proxy_info, True, response_time)
            
            return {
                "success": True,
                "status_code": response.status_code,
                "response_time": round(response_time, 3),
                "proxy_used": proxy_info,
                "request_id": self.request_counter,
                "content_length": len(response.content) if response.content else 0,
                "headers_count": len(response.headers)
            }
            
        except requests.exceptions.ProxyError as e:
            response_time = time.time() - start_time
            self._update_proxy_stats(proxy_info, False, response_time)
            
            return {
                "success": False,
                "error": "ProxyError",
                "error_detail": str(e)[:100],
                "response_time": round(response_time, 3),
                "proxy_used": proxy_info,
                "request_id": self.request_counter
            }
            
        except requests.exceptions.Timeout as e:
            response_time = time.time() - start_time
            self._update_proxy_stats(proxy_info, False, response_time)
            
            return {
                "success": False,
                "error": "Timeout",
                "error_detail": "Request exceeded timeout limit",
                "response_time": round(response_time, 3),
                "proxy_used": proxy_info,
                "request_id": self.request_counter
            }
            
        except requests.exceptions.ConnectionError as e:
            response_time = time.time() - start_time
            self._update_proxy_stats(proxy_info, False, response_time)
            
            return {
                "success": False,
                "error": "ConnectionError",
                "error_detail": str(e)[:100],
                "response_time": round(response_time, 3),
                "proxy_used": proxy_info,
                "request_id": self.request_counter
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            self._update_proxy_stats(proxy_info, False, response_time)
            
            return {
                "success": False,
                "error": type(e).__name__,
                "error_detail": str(e)[:100],
                "response_time": round(response_time, 3),
                "proxy_used": proxy_info,
                "request_id": self.request_counter
            }
    
    def _update_proxy_stats(self, proxy_info: str, success: bool, response_time: float):
        """Proxy istatistiklerini güncelle"""
        if proxy_info not in self.proxy_stats:
            self.proxy_stats[proxy_info] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_response_time": 0,
                "avg_response_time": 0
            }
        
        stats = self.proxy_stats[proxy_info]
        stats["total_requests"] += 1
        stats["total_response_time"] += response_time
        
        if success:
            stats["successful_requests"] += 1
        else:
            stats["failed_requests"] += 1
        
        stats["avg_response_time"] = stats["total_response_time"] / stats["total_requests"]
    
    def get_proxy_statistics(self) -> Dict:
        """Proxy kullanım istatistiklerini döndür"""
        return self.proxy_stats
    
    @classmethod
    def add_proxy(cls, proxy_url: str, proxy_type: str = "both"):
        """Yeni proxy ekle"""
        if proxy_type == "both":
            new_proxy = {
                "http": proxy_url,
                "https": proxy_url
            }
        elif proxy_type == "http":
            new_proxy = {"http": proxy_url}
        elif proxy_type == "https":
            new_proxy = {"https": proxy_url}
        else:
            raise ValueError("Invalid proxy type. Use 'http', 'https', or 'both'")
        
        cls.PROXY_POOL.append(new_proxy)
        print(f"✅ Proxy eklendi: {proxy_url}")
    
    @classmethod
    def remove_proxy(cls, proxy_url: str):
        """Proxy'yi havuzdan çıkar"""
        cls.PROXY_POOL = [
            p for p in cls.PROXY_POOL 
            if proxy_url not in (p.get("http", ""), p.get("https", ""))
        ]
        print(f"✅ Proxy kaldırıldı: {proxy_url}")
    
    @classmethod
    def list_proxies(cls):
        """Tüm proxy'leri listele"""
        print(f"\n📋 Aktif Proxy Listesi ({len(cls.PROXY_POOL)} adet):")
        for i, proxy in enumerate(cls.PROXY_POOL, 1):
            print(f"   {i}. {proxy.get('http', proxy.get('https', 'N/A'))}")


# Kullanım örneği
if __name__ == "__main__":
    # Test için
    tester = DDoSSimulationTester("http://httpbin.org/anything", "test-123")
    
    # Tek istek gönder
    result = tester.send_request()
    print(f"\nTest Sonucu:")
    print(f"  Başarılı: {result['success']}")
    print(f"  Status: {result.get('status_code', 'N/A')}")
    print(f"  Süre: {result['response_time']}s")
    print(f"  Proxy: {result['proxy_used']}")
    
    # Proxy istatistikleri
    stats = tester.get_proxy_statistics()
    print(f"\nProxy İstatistikleri:")
    for proxy, stat in stats.items():
        print(f"  {proxy}:")
        print(f"    - Toplam: {stat['total_requests']}")
        print(f"    - Başarılı: {stat['successful_requests']}")
        print(f"    - Başarısız: {stat['failed_requests']}")
        print(f"    - Ort. Süre: {stat['avg_response_time']:.3f}s")
