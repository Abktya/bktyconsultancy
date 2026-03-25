# ai_captcha_solver_module.py

import requests
import base64
import time
import json
import os
from typing import Dict, List, Optional, Any, Tuple
import asyncio
import aiohttp
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import io
import re
import hashlib
from datetime import datetime, timedelta

class CaptchaSolverModule:
    """AI için kapsamlı captcha çözüm modülü"""
    
    def __init__(self, config: Dict[str, str] = None):
        """
        config = {
            'anticaptcha_api_key': 'your_key',
            '2captcha_api_key': 'your_key',
            'capmonster_api_key': 'your_key',
            'deathbycaptcha_username': 'user',
            'deathbycaptcha_password': 'pass'
        }
        """
        self.config = config or {}
        self.temp_dir = Path("captcha_temp")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Captcha türleri ve çözüm stratejileri
        self.captcha_types = {
            'recaptcha_v2': {'priority_services': ['anticaptcha', '2captcha', 'capmonster']},
            'recaptcha_v3': {'priority_services': ['anticaptcha', '2captcha']},
            'hcaptcha': {'priority_services': ['anticaptcha', '2captcha', 'capmonster']},
            'funcaptcha': {'priority_services': ['anticaptcha', '2captcha']},
            'geetest': {'priority_services': ['anticaptcha', '2captcha']},
            'image_captcha': {'priority_services': ['2captcha', 'anticaptcha', 'deathbycaptcha']},
            'text_captcha': {'priority_services': ['2captcha', 'anticaptcha']},
            'audio_captcha': {'priority_services': ['2captcha']},
            'slider_captcha': {'priority_services': ['anticaptcha', 'capmonster']},
            'rotate_captcha': {'priority_services': ['anticaptcha', '2captcha']},
            'click_captcha': {'priority_services': ['anticaptcha', '2captcha']}
        }
        
        # Servis API endpoints
        self.api_endpoints = {
            'anticaptcha': {
                'create': 'https://api.anti-captcha.com/createTask',
                'result': 'https://api.anti-captcha.com/getTaskResult',
                'balance': 'https://api.anti-captcha.com/getBalance'
            },
            '2captcha': {
                'submit': 'http://2captcha.com/in.php',
                'result': 'http://2captcha.com/res.php',
                'balance': 'http://2captcha.com/res.php?action=getbalance'
            },
            'capmonster': {
                'create': 'https://api.capmonster.cloud/createTask',
                'result': 'https://api.capmonster.cloud/getTaskResult',
                'balance': 'https://api.capmonster.cloud/getBalance'
            }
        }
        
        # Çözüm geçmişi ve istatistikler
        self.solving_history = []
        self.success_rates = {}
        
        print("🤖 Captcha Solver Module initialized")
        print(f"📁 Temp directory: {self.temp_dir}")
        
    def detect_captcha_type(self, image_path: str = None, html_content: str = None, 
                          url: str = None) -> Dict[str, Any]:
        """Captcha türünü otomatik tespit et"""
        
        detection_result = {
            'type': 'unknown',
            'confidence': 0.0,
            'properties': {},
            'recommended_service': None
        }
        
        # HTML içeriğinden tespit
        if html_content:
            html_lower = html_content.lower()
            
            if 'recaptcha' in html_lower and 'v3' in html_lower:
                detection_result.update({
                    'type': 'recaptcha_v3',
                    'confidence': 0.9,
                    'properties': {'site_key': self._extract_site_key(html_content)}
                })
            elif 'recaptcha' in html_lower or 'g-recaptcha' in html_lower:
                detection_result.update({
                    'type': 'recaptcha_v2',
                    'confidence': 0.85,
                    'properties': {'site_key': self._extract_site_key(html_content)}
                })
            elif 'hcaptcha' in html_lower or 'h-captcha' in html_lower:
                detection_result.update({
                    'type': 'hcaptcha',
                    'confidence': 0.9,
                    'properties': {'site_key': self._extract_hcaptcha_key(html_content)}
                })
            elif 'funcaptcha' in html_lower or 'arkoselabs' in html_lower:
                detection_result.update({
                    'type': 'funcaptcha',
                    'confidence': 0.8
                })
            elif 'geetest' in html_lower:
                detection_result.update({
                    'type': 'geetest',
                    'confidence': 0.85
                })
        
        # Görsel analiz ile tespit
        if image_path and os.path.exists(image_path):
            visual_analysis = self._analyze_captcha_image(image_path)
            if visual_analysis['confidence'] > detection_result['confidence']:
                detection_result.update(visual_analysis)
        
        # Önerilen servisi belirle
        if detection_result['type'] in self.captcha_types:
            services = self.captcha_types[detection_result['type']]['priority_services']
            detection_result['recommended_service'] = self._get_best_available_service(services)
        
        return detection_result
    
    def _analyze_captcha_image(self, image_path: str) -> Dict[str, Any]:
        """Görsel analiz ile captcha türü tespit et"""
        try:
            # OpenCV ile görsel analiz
            img = cv2.imread(image_path)
            if img is None:
                return {'type': 'unknown', 'confidence': 0.0}
            
            height, width = img.shape[:2]
            
            # Boyut analizi
            if width > 300 and height > 300:
                # reCAPTCHA benzeri
                return {
                    'type': 'recaptcha_v2',
                    'confidence': 0.6,
                    'properties': {'size': f'{width}x{height}'}
                }
            elif 50 < height < 100 and 100 < width < 300:
                # Klasik text captcha
                return {
                    'type': 'image_captcha',
                    'confidence': 0.7,
                    'properties': {'size': f'{width}x{height}', 'text_based': True}
                }
            elif width > height * 2:
                # Slider captcha olabilir
                return {
                    'type': 'slider_captcha',
                    'confidence': 0.5,
                    'properties': {'size': f'{width}x{height}'}
                }
            
            return {
                'type': 'image_captcha',
                'confidence': 0.4,
                'properties': {'size': f'{width}x{height}'}
            }
            
        except Exception as e:
            print(f"Image analysis error: {e}")
            return {'type': 'unknown', 'confidence': 0.0}
    
    def _extract_site_key(self, html_content: str) -> Optional[str]:
        """reCAPTCHA site key çıkar"""
        patterns = [
            r'data-sitekey=["\']([^"\']+)["\']',
            r'sitekey:\s*["\']([^"\']+)["\']',
            r'"sitekey":\s*"([^"]+)"'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                return match.group(1)
        return None
    
    def _extract_hcaptcha_key(self, html_content: str) -> Optional[str]:
        """hCaptcha site key çıkar"""
        patterns = [
            r'data-sitekey=["\']([^"\']+)["\']',
            r'sitekey=["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                return match.group(1)
        return None
    
    def _get_best_available_service(self, services: List[str]) -> Optional[str]:
        """Mevcut en iyi servisi seç"""
        for service in services:
            if service in self.config and self.config.get(f'{service}_api_key'):
                return service
        return None
    
    async def solve_captcha(self, captcha_type: str, **kwargs) -> Dict[str, Any]:
        """Ana captcha çözüm fonksiyonu"""
        
        start_time = time.time()
        
        # Servisleri öncelik sırasına göre dene
        services = self.captcha_types.get(captcha_type, {}).get('priority_services', ['2captcha'])
        
        for service in services:
            if not self._is_service_available(service):
                continue
                
            try:
                print(f"🔄 Trying {service} for {captcha_type}...")
                
                result = await self._solve_with_service(service, captcha_type, **kwargs)
                
                if result.get('success'):
                    solving_time = time.time() - start_time
                    
                    # İstatistikleri güncelle
                    self._update_statistics(service, captcha_type, True, solving_time)
                    
                    result.update({
                        'service_used': service,
                        'solving_time': solving_time,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    print(f"✅ Solved with {service} in {solving_time:.2f}s")
                    return result
                else:
                    print(f"❌ {service} failed: {result.get('error')}")
                    
            except Exception as e:
                print(f"❌ {service} error: {e}")
                continue
        
        # Tüm servisler başarısız
        total_time = time.time() - start_time
        return {
            'success': False,
            'error': 'All services failed',
            'solving_time': total_time,
            'services_tried': services
        }
    
    async def _solve_with_service(self, service: str, captcha_type: str, **kwargs) -> Dict[str, Any]:
        """Belirli bir servis ile çözüm"""
        
        if service == 'anticaptcha':
            return await self._solve_anticaptcha(captcha_type, **kwargs)
        elif service == '2captcha':
            return await self._solve_2captcha(captcha_type, **kwargs)
        elif service == 'capmonster':
            return await self._solve_capmonster(captcha_type, **kwargs)
        elif service == 'deathbycaptcha':
            return await self._solve_deathbycaptcha(captcha_type, **kwargs)
        else:
            return {'success': False, 'error': f'Unknown service: {service}'}
    
    async def _solve_anticaptcha(self, captcha_type: str, **kwargs) -> Dict[str, Any]:
        """AntiCaptcha servis entegrasyonu"""
        
        api_key = self.config.get('anticaptcha_api_key')
        if not api_key:
            return {'success': False, 'error': 'AntiCaptcha API key not provided'}
        
        # Task oluşturma payload'ı hazırla
        if captcha_type == 'recaptcha_v2':
            task_data = {
                "clientKey": api_key,
                "task": {
                    "type": "NoCaptchaTaskProxyless",
                    "websiteURL": kwargs.get('page_url'),
                    "websiteKey": kwargs.get('site_key')
                }
            }
        elif captcha_type == 'recaptcha_v3':
            task_data = {
                "clientKey": api_key,
                "task": {
                    "type": "RecaptchaV3TaskProxyless",
                    "websiteURL": kwargs.get('page_url'),
                    "websiteKey": kwargs.get('site_key'),
                    "minScore": kwargs.get('min_score', 0.3),
                    "pageAction": kwargs.get('action', 'submit')
                }
            }
        elif captcha_type == 'hcaptcha':
            task_data = {
                "clientKey": api_key,
                "task": {
                    "type": "HCaptchaTaskProxyless",
                    "websiteURL": kwargs.get('page_url'),
                    "websiteKey": kwargs.get('site_key')
                }
            }
        elif captcha_type == 'image_captcha':
            # Görsel captcha için base64 encode
            image_path = kwargs.get('image_path')
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    image_b64 = base64.b64encode(f.read()).decode()
                
                task_data = {
                    "clientKey": api_key,
                    "task": {
                        "type": "ImageToTextTask",
                        "body": image_b64,
                        "phrase": kwargs.get('is_phrase', False),
                        "case": kwargs.get('case_sensitive', False),
                        "numeric": kwargs.get('numeric_only', False),
                        "math": kwargs.get('is_math', False),
                        "minLength": kwargs.get('min_length', 0),
                        "maxLength": kwargs.get('max_length', 0)
                    }
                }
            else:
                return {'success': False, 'error': 'Image file not found'}
        else:
            return {'success': False, 'error': f'Unsupported captcha type: {captcha_type}'}
        
        try:
            # Task oluştur
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_endpoints['anticaptcha']['create'],
                    json=task_data,
                    timeout=30
                ) as response:
                    create_result = await response.json()
            
            if create_result.get('errorId') != 0:
                return {
                    'success': False,
                    'error': f"AntiCaptcha error: {create_result.get('errorDescription')}"
                }
            
            task_id = create_result.get('taskId')
            
            # Sonuç için bekle
            max_attempts = 60  # 5 dakika
            for attempt in range(max_attempts):
                await asyncio.sleep(5)
                
                result_data = {
                    "clientKey": api_key,
                    "taskId": task_id
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.api_endpoints['anticaptcha']['result'],
                        json=result_data,
                        timeout=15
                    ) as response:
                        result = await response.json()
                
                if result.get('status') == 'ready':
                    solution = result.get('solution', {})
                    
                    if captcha_type in ['recaptcha_v2', 'recaptcha_v3', 'hcaptcha']:
                        return {
                            'success': True,
                            'solution': solution.get('gRecaptchaResponse'),
                            'task_id': task_id
                        }
                    elif captcha_type == 'image_captcha':
                        return {
                            'success': True,
                            'solution': solution.get('text'),
                            'task_id': task_id
                        }
                
                elif result.get('errorId') != 0:
                    return {
                        'success': False,
                        'error': f"AntiCaptcha error: {result.get('errorDescription')}"
                    }
            
            return {'success': False, 'error': 'Solving timeout'}
            
        except Exception as e:
            return {'success': False, 'error': f'AntiCaptcha request error: {e}'}
    
    async def _solve_2captcha(self, captcha_type: str, **kwargs) -> Dict[str, Any]:
        """2Captcha servis entegrasyonu"""
        
        api_key = self.config.get('2captcha_api_key')
        if not api_key:
            return {'success': False, 'error': '2Captcha API key not provided'}
        
        try:
            # Submit request hazırla
            submit_data = {'key': api_key}
            
            if captcha_type == 'recaptcha_v2':
                submit_data.update({
                    'method': 'userrecaptcha',
                    'googlekey': kwargs.get('site_key'),
                    'pageurl': kwargs.get('page_url')
                })
            elif captcha_type == 'recaptcha_v3':
                submit_data.update({
                    'method': 'userrecaptcha',
                    'version': 'v3',
                    'googlekey': kwargs.get('site_key'),
                    'pageurl': kwargs.get('page_url'),
                    'action': kwargs.get('action', 'submit'),
                    'min_score': kwargs.get('min_score', 0.3)
                })
            elif captcha_type == 'hcaptcha':
                submit_data.update({
                    'method': 'hcaptcha',
                    'sitekey': kwargs.get('site_key'),
                    'pageurl': kwargs.get('page_url')
                })
            elif captcha_type == 'image_captcha':
                image_path = kwargs.get('image_path')
                if image_path and os.path.exists(image_path):
                    with open(image_path, 'rb') as f:
                        image_b64 = base64.b64encode(f.read()).decode()
                    
                    submit_data.update({
                        'method': 'base64',
                        'body': image_b64
                    })
                    
                    # Ek parametreler
                    if kwargs.get('is_phrase'):
                        submit_data['phrase'] = 1
                    if kwargs.get('case_sensitive'):
                        submit_data['regsense'] = 1
                    if kwargs.get('numeric_only'):
                        submit_data['numeric'] = 1
                    if kwargs.get('is_math'):
                        submit_data['calc'] = 1
                    if kwargs.get('min_length'):
                        submit_data['min_len'] = kwargs['min_length']
                    if kwargs.get('max_length'):
                        submit_data['max_len'] = kwargs['max_length']
                else:
                    return {'success': False, 'error': 'Image file not found'}
            else:
                return {'success': False, 'error': f'Unsupported captcha type: {captcha_type}'}
            
            # Submit request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_endpoints['2captcha']['submit'],
                    data=submit_data,
                    timeout=30
                ) as response:
                    submit_result = await response.text()
            
            if not submit_result.startswith('OK|'):
                return {'success': False, 'error': f'2Captcha submit error: {submit_result}'}
            
            captcha_id = submit_result.split('|')[1]
            
            # Sonuç için bekle
            max_attempts = 60
            for attempt in range(max_attempts):
                await asyncio.sleep(5)
                
                result_url = f"{self.api_endpoints['2captcha']['result']}?key={api_key}&action=get&id={captcha_id}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(result_url, timeout=15) as response:
                        result = await response.text()
                
                if result.startswith('OK|'):
                    solution = result.split('|')[1]
                    return {
                        'success': True,
                        'solution': solution,
                        'captcha_id': captcha_id
                    }
                elif result != 'CAPCHA_NOT_READY':
                    return {'success': False, 'error': f'2Captcha error: {result}'}
            
            return {'success': False, 'error': 'Solving timeout'}
            
        except Exception as e:
            return {'success': False, 'error': f'2Captcha request error: {e}'}
    
    async def _solve_capmonster(self, captcha_type: str, **kwargs) -> Dict[str, Any]:
        """CapMonster servis entegrasyonu"""
        # AntiCaptcha'ya benzer API yapısı
        api_key = self.config.get('capmonster_api_key')
        if not api_key:
            return {'success': False, 'error': 'CapMonster API key not provided'}
        
        # CapMonster implementation (AntiCaptcha'ya çok benzer)
        # Burada kısaltılmış version - tam implementation gerekirse ekleyebiliriz
        return {'success': False, 'error': 'CapMonster implementation pending'}
    
    async def _solve_deathbycaptcha(self, captcha_type: str, **kwargs) -> Dict[str, Any]:
        """DeathByCaptcha servis entegrasyonu"""
        username = self.config.get('deathbycaptcha_username')
        password = self.config.get('deathbycaptcha_password')
        
        if not username or not password:
            return {'success': False, 'error': 'DeathByCaptcha credentials not provided'}
        
        # DeathByCaptcha implementation
        return {'success': False, 'error': 'DeathByCaptcha implementation pending'}
    
    def _is_service_available(self, service: str) -> bool:
        """Servisin kullanılabilir olup olmadığını kontrol et"""
        required_configs = {
            'anticaptcha': 'anticaptcha_api_key',
            '2captcha': '2captcha_api_key',
            'capmonster': 'capmonster_api_key',
            'deathbycaptcha': ['deathbycaptcha_username', 'deathbycaptcha_password']
        }
        
        if service not in required_configs:
            return False
        
        config_keys = required_configs[service]
        if isinstance(config_keys, str):
            return bool(self.config.get(config_keys))
        else:
            return all(self.config.get(key) for key in config_keys)
    
    def _update_statistics(self, service: str, captcha_type: str, success: bool, solving_time: float):
        """İstatistikleri güncelle"""
        key = f"{service}_{captcha_type}"
        
        if key not in self.success_rates:
            self.success_rates[key] = {
                'total_attempts': 0,
                'successful_attempts': 0,
                'avg_solving_time': 0,
                'last_success': None
            }
        
        stats = self.success_rates[key]
        stats['total_attempts'] += 1
        
        if success:
            stats['successful_attempts'] += 1
            stats['last_success'] = datetime.now().isoformat()
            
            # Moving average for solving time
            current_avg = stats['avg_solving_time']
            stats['avg_solving_time'] = (current_avg * 0.8) + (solving_time * 0.2)
        
        # Geçmişe ekle
        self.solving_history.append({
            'timestamp': datetime.now().isoformat(),
            'service': service,
            'captcha_type': captcha_type,
            'success': success,
            'solving_time': solving_time
        })
        
        # Geçmişi sınırla (son 1000 kayıt)
        if len(self.solving_history) > 1000:
            self.solving_history = self.solving_history[-1000:]
    
    async def get_service_balance(self, service: str) -> Dict[str, Any]:
        """Servis bakiyesini kontrol et"""
        
        if service == 'anticaptcha':
            api_key = self.config.get('anticaptcha_api_key')
            if not api_key:
                return {'success': False, 'error': 'API key not provided'}
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.api_endpoints['anticaptcha']['balance'],
                        json={'clientKey': api_key},
                        timeout=15
                    ) as response:
                        result = await response.json()
                
                if result.get('errorId') == 0:
                    return {
                        'success': True,
                        'balance': result.get('balance'),
                        'currency': 'USD'
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('errorDescription')
                    }
            except Exception as e:
                return {'success': False, 'error': f'Request error: {e}'}
        
        elif service == '2captcha':
            api_key = self.config.get('2captcha_api_key')
            if not api_key:
                return {'success': False, 'error': 'API key not provided'}
            
            try:
                balance_url = f"{self.api_endpoints['2captcha']['balance']}&key={api_key}"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(balance_url, timeout=15) as response:
                        result = await response.text()
                
                try:
                    balance = float(result)
                    return {
                        'success': True,
                        'balance': balance,
                        'currency': 'USD'
                    }
                except ValueError:
                    return {'success': False, 'error': f'Invalid response: {result}'}
            except Exception as e:
                return {'success': False, 'error': f'Request error: {e}'}
        
        else:
            return {'success': False, 'error': f'Unsupported service: {service}'}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Çözüm istatistiklerini al"""
        return {
            'success_rates': self.success_rates,
            'total_solves': len(self.solving_history),
            'recent_history': self.solving_history[-10:],  # Son 10 kayıt
            'services_configured': [
                service for service in ['anticaptcha', '2captcha', 'capmonster', 'deathbycaptcha']
                if self._is_service_available(service)
            ]
        }
    
    def cleanup(self):
        """Temizlik işlemleri"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        print("🧹 Captcha solver cleaned up")

# Integration with main AI system
class AICaptchaSolver:
    """Ana AI sistemi için captcha çözücü wrapper"""
    
    def __init__(self, config: Dict[str, str]):
        self.solver = CaptchaSolverModule(config)
        
    async def solve_web_captcha(self, page_url: str, site_key: str = None, 
                               captcha_type: str = None) -> Dict[str, Any]:
        """Web sayfasındaki captcha'yı çöz"""
        
        if not captcha_type:
            # Otomatik tespit et
            try:
                import requests
                response = requests.get(page_url, timeout=10)
                detection = self.solver.detect_captcha_type(html_content=response.text, url=page_url)
                captcha_type = detection['type']
                
                if not site_key and 'site_key' in detection.get('properties', {}):
                    site_key = detection['properties']['site_key']
                    
            except Exception as e:
                return {'success': False, 'error': f'Page analysis failed: {e}'}
        
        return await self.solver.solve_captcha(
            captcha_type=captcha_type,
            page_url=page_url,
            site_key=site_key
        )
    
    async def solve_image_captcha(self, image_path: str, **options) -> Dict[str, Any]:
        """Görsel captcha çöz"""
        return await self.solver.solve_captcha(
            captcha_type='image_captcha',
            image_path=image_path,
            **options
        )

# Test function
async def test_captcha_solver():
    """Captcha solver test"""
    
    # Test config (gerçek anahtarları buraya koyun)
    config = {
        'anticaptcha_api_key': 'your_anticaptcha_key',
        '2captcha_api_key': 'your_2captcha_key'
    }
    
    solver = AICaptchaSolver(config)
    
    # Test görsel captcha
    print("🧪 Testing image captcha...")
    # Burada gerçek bir captcha görsel dosyası gerekir
    
    # Test reCAPTCHA
    print("🧪 Testing reCAPTCHA...")
    result = await solver.solve_web_captcha(
        page_url="https://www.google.com/recaptcha/api2/demo",
        captcha_type="recaptcha_v2"
    )
    
    print(f"Result: {result}")
    
    # İstatistikleri göster
    stats = solver.solver.get_statistics()
    print(f"Statistics: {stats}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_captcha_solver())