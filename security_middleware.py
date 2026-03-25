import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from flask import request, abort, jsonify
import logging

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    def __init__(self, app):
        self.app = app
        self.ip_tracker = defaultdict(lambda: {
            'requests': [],
            '404_count': 0,
            'blocked_until': None,
            'threat_score': 0
        })
        
        # Şüpheli patternler
        self.malicious_patterns = [
            r'\.(rar|zip|sql|mdb|bak|old|backup|tar\.gz|7z)$',
            r'/(backup|database|admin|config|sql|data|wwwroot)',
            r'\.\./|\.\.\\|%2e%2e',
            r'/\d+\.(rar|zip)$',
            r'/(新建|网站|数据库|备份|源码)',  # Çince karakterler
        ]
        
        # Otomatik blok süresi (saniye)
        self.auto_block_duration = 3600  # 1 saat
        
    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        ip = environ.get('REMOTE_ADDR', '')
        
        # Bloklu IP kontrolü
        if self._is_blocked(ip):
            logger.warning(f"Blocked IP access attempt: {ip}")
            response = jsonify({'error': 'Access denied'})
            start_response('403 Forbidden', [
                ('Content-Type', 'application/json'),
                ('X-Blocked-Reason', 'Suspicious activity detected')
            ])
            return [b'{"error": "Access denied"}']
        
        # Pattern kontrolü
        for pattern in self.malicious_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                self._record_suspicious_activity(ip, path)
                logger.warning(f"Suspicious pattern detected: {ip} -> {path}")
                
                # Direkt blokla
                if self.ip_tracker[ip]['threat_score'] > 20:
                    self._block_ip(ip)
                    start_response('403 Forbidden', [('Content-Type', 'text/plain')])
                    return [b'Access Denied']
        
        # Normal istek - devam et
        return self.app(environ, start_response)
    
    def _is_blocked(self, ip):
        tracker = self.ip_tracker[ip]
        if tracker['blocked_until']:
            if datetime.now() < tracker['blocked_until']:
                return True
            else:
                # Block süresi dolmuş
                tracker['blocked_until'] = None
                tracker['threat_score'] = 0
        return False
    
    def _record_suspicious_activity(self, ip, path):
        tracker = self.ip_tracker[ip]
        tracker['threat_score'] += 5
        tracker['requests'].append({
            'time': datetime.now(),
            'path': path
        })
        
        # Son 1 dakikadaki istek sayısı
        recent = [r for r in tracker['requests'] 
                 if datetime.now() - r['time'] < timedelta(minutes=1)]
        
        if len(recent) > 10:
            tracker['threat_score'] += 10
        
        # Otomatik blok
        if tracker['threat_score'] > 30:
            self._block_ip(ip)
    
    def _block_ip(self, ip):
        self.ip_tracker[ip]['blocked_until'] = datetime.now() + timedelta(
            seconds=self.auto_block_duration
        )
        logger.critical(f"IP auto-blocked for {self.auto_block_duration}s: {ip}")
        
        # Email alert
        try:
            self._send_alert(ip)
        except:
            pass
    
    def _send_alert(self, ip):
        from flask_mail import Message
        from app import mail
        
        msg = Message(
            subject=f"🚨 Security: IP Blocked - {ip}",
            recipients=['admin@bktyconsultancy.co.uk'],
            body=f"""
Security Alert

Blocked IP: {ip}
Time: {datetime.now()}
Threat Score: {self.ip_tracker[ip]['threat_score']}
Recent Requests: {len(self.ip_tracker[ip]['requests'])}
Block Duration: {self.auto_block_duration}s

Check security.log for details.
            """
        )
        mail.send(msg)