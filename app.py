# app.py - Gelişmiş BKTY Consultancy Flask Uygulaması
# Kullanıcı yönetimi, admin paneli, yasal sayfalar ve güvenlik özellikleri ile

from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, Response, abort
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
import os
import secrets
import unicodedata
import re
import time
import hashlib
import sqlite3
import json
from datetime import datetime, timedelta
import logging
from functools import wraps
import warnings
import bleach
import sys
import uuid
import threading
from collections import defaultdict
from typing import Dict, List, Any, Optional
from werkzeug.utils import secure_filename

def safe_cleanup_expired_sessions():
    """Güvenli session temizleme"""
    try:
        cleanup_expired_sessions()
    except Exception as e:
        logger.error(f"Session cleanup error: {e}")
# Özel modülleri import et
try:
    from multi_user_ollama_runner import multi_user_ollama
    OLLAMA_AVAILABLE = True
    print("✅ Ollama runner loaded successfully")
except ImportError as e:
    print(f"⚠️ Ollama runner import error: {e}")
    OLLAMA_AVAILABLE = False
    multi_user_ollama = None

# Database ve helper modülleri import et
from database import init_database, UserManager, SessionManager
from auth_helpers import (
    login_required, admin_required, verified_required, consent_required,
    get_current_user, log_user_activity, cleanup_expired_sessions,
    validate_password_strength, send_verification_email, send_password_reset_email
)

# Flask-Limiter uyarısını gizle
warnings.filterwarnings('ignore', message='Using the in-memory storage')

# Dotenv support
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Werkzeug loglarını sustur
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Flask uygulaması oluştur
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

app.config['TURNSTILE_SITE_KEY'] = os.getenv('TURNSTILE_SITE_KEY')
app.config['TURNSTILE_SECRET_KEY'] = os.getenv('TURNSTILE_SECRET_KEY')


# Konfigürasyon
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(16))
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
if not hasattr(app, 'ip_registrations'):
    app.ip_registrations = defaultdict(list)

# Rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"]
)

# Security globals
BLOCKED_IPS = set()
SUSPICIOUS_IPS = {}
active_tasks = defaultdict(dict)

# Mail konfigürasyonu
def clean_config_value(value):
    if not value:
        return value
    value = value.replace('\xa0', '').replace('\u00a0', '')
    value = ''.join(value.split())
    return value

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = clean_config_value(os.getenv('MAIL_USERNAME', 'bktyconsultancy@gmail.com'))
app.config['MAIL_PASSWORD'] = clean_config_value(os.getenv('MAIL_PASSWORD', 'your-app-password-here'))
app.config['MAIL_DEFAULT_SENDER'] = clean_config_value(os.getenv('MAIL_USERNAME', 'bktyconsultancy@gmail.com'))
app.config['MAIL_ASCII_ATTACHMENTS'] = False
app.config['MAIL_DEFAULT_CHARSET'] = 'utf-8'

mail = Mail(app)
# =============================================================================
# =============================================================================
# =============================================================================
# =============================================================================
# =============================================================================
# Güvenlik Fonksiyonları (Mevcut kodunuzdan)
# =============================================================================
# =============================================================================
# =============================================================================
# =============================================================================
# =============================================================================
def generate_nonce():
    return secrets.token_urlsafe(16)

def is_ip_blocked(ip):
    return ip in BLOCKED_IPS

def track_suspicious_activity(ip):
    now = datetime.now()
    
    if ip in SUSPICIOUS_IPS:
        SUSPICIOUS_IPS[ip]['count'] += 1
        SUSPICIOUS_IPS[ip]['last_attempt'] = now
        
        if SUSPICIOUS_IPS[ip]['count'] > 10:
            BLOCKED_IPS.add(ip)
            logger.warning(f"IP blocked due to suspicious activity: {ip}")
            return True
    else:
        SUSPICIOUS_IPS[ip] = {'count': 1, 'last_attempt': now}
    
    return False

def clean_suspicious_ips():
    now = datetime.now()
    to_remove = []
    
    for ip, data in SUSPICIOUS_IPS.items():
        if now - data['last_attempt'] > timedelta(hours=1):
            to_remove.append(ip)
    
    for ip in to_remove:
        del SUSPICIOUS_IPS[ip]

def detect_malicious_content(content):
    if not content:
        return False
    
    content_lower = content.lower()
    
    malicious_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*=',
        r'onmouseover\s*=',
        r'<iframe',
        r'<embed',
        r'<object',
        r'eval\s*\(',
        r'document\.cookie',
        r'window\.location',
        r'alert\s*\(',
        r'confirm\s*\(',
        r'prompt\s*\(',
    ]
    
    for pattern in malicious_patterns:
        if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
            return True
    
    return False

def security_check_decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = get_remote_address()
        
        if is_ip_blocked(client_ip):
            logger.warning(f"Blocked IP attempted access: {client_ip}")
            return "Access denied", 403
        
        if request.method == 'POST':
            for field_name, field_value in request.form.items():
                if detect_malicious_content(str(field_value)):
                    logger.warning(f"Malicious content detected from IP {client_ip}: {field_name}")
                    track_suspicious_activity(client_ip)
                    flash('Güvenlik nedeniyle istek reddedildi.', 'error')
                    return redirect(request.url)
        
        clean_suspicious_ips()
        return f(*args, **kwargs)
    return decorated_function

def validate_email(email: str) -> str:
    if not email:
        return ""
    
    email = email.strip()
    
    if len(email) > 254:
        return ""
    
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9._%+-]{0,63}@[a-zA-Z0-9][a-zA-Z0-9.-]{0,62}\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return ""
    
    try:
        email.encode('ascii')
        return email
    except UnicodeEncodeError:
        return ""

def validate_and_sanitize_input(text: str, max_length: int = 1000) -> str:
    if not text:
        return ""
    
    if len(text) > max_length:
        text = text[:max_length]
    
    if detect_malicious_content(text):
        return ""
    
    text = unicodedata.normalize('NFKD', text)
    
    replacements = {
        '\xa0': ' ', '\u00a0': ' ',
        '\u2019': "'", '\u2018': "'",
        '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-',
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    text = bleach.clean(text, tags=[], strip=True)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def csrf_protect():
    if request.method == "POST":
        # Yalnızca programatik API ve voice endpoint'leri CSRF dışında
        # /admin/, /en/admin/, /tr/admin/ ARTIK CSRF KORUMASININ DIŞINDA DEĞİL
        if (request.path.startswith('/api/') or
            request.path.startswith('/voice/') or
            request.path.startswith('/admin/api/')):
            return

        token = session.get('csrf_token')
        submitted = (request.form.get('csrf_token') or
                     request.headers.get('X-CSRF-Token'))
        if not token or not submitted or token != submitted:
            logger.warning(f"CSRF ihlali: {request.path} — IP: {request.remote_addr}")
            abort(403)

# Bu fonksiyonu before_request olarak kaydedin:
@app.before_request
def csrf_protection():
    csrf_protect()


def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(16)
    return session['csrf_token']

def verify_csrf_token(token):
    return token and token == session.get('csrf_token')

app.jinja_env.globals['csrf_token'] = generate_csrf_token

import secrets
from flask import g

@app.before_request
def add_nonce():
    g.nonce = secrets.token_urlsafe(16)

@app.context_processor
def inject_nonce():
    return dict(nonce=g.get('nonce'))

# =============================================================================
# =============================================================================
# =============================================================================
# =============================================================================



from collections import defaultdict
from datetime import datetime, timedelta
import re

class SimpleSecurityMiddleware:
    def __init__(self, app):
        self.app = app
        self.blocked_ips = set()
        self.ip_data = defaultdict(lambda: {
            '404_count': 0,
            'last_reset': datetime.now(),
            'suspicious_count': 0
        })
        self.auto_block_ranges = {
            '31.173.': 'Persistent bot attacks',
            '178.176.': 'Persistent bot attacks',
            '94.25.': 'Bot activity detected'
        }
        
        # Whitelist - bu IP'ler asla bloklanmaz
        self.whitelist = {'127.0.0.1', 'localhost', '::1'}  # ← YENİ
        
        self.blocked_extensions = [
            '.rar', '.zip', '.sql', '.mdb', '.bak', 
            '.backup', '.tar.gz', '.7z', '.old'
        ]
        
        self.blocked_paths = [
            '/backup', '/database', '/sql', '/wwwroot',
            '/admin.', '/config.', '/data.'
        ]
    
    def __call__(self, environ, start_response):
        ip = environ.get('REMOTE_ADDR', 'unknown')
        path = environ.get('PATH_INFO', '/')
        
        # Whitelist kontrolü - önce bunu kontrol et
        if ip in self.whitelist:  # ← YENİ
            return self.app(environ, start_response)
        
        # Bloklu IP kontrolü
        if ip in self.blocked_ips:
            logger.warning(f"Blocked IP attempt: {ip}")
            start_response('403 Forbidden', [('Content-Type', 'text/plain')])
            return [b'Access Denied']
        
        # Şüpheli path kontrolü
        path_lower = path.lower()
        
        # Uzantı kontrolü
        for ext in self.blocked_extensions:
            if path_lower.endswith(ext):
                self._record_suspicious(ip, path)
                start_response('403 Forbidden', [('Content-Type', 'text/plain')])
                return [b'Access Denied']
        
        # Path kontrolü
        for blocked in self.blocked_paths:
            if blocked in path_lower:
                self._record_suspicious(ip, path)
                start_response('403 Forbidden', [('Content-Type', 'text/plain')])
                return [b'Access Denied']
        
        for ip_range, reason in self.auto_block_ranges.items():
            if ip.startswith(ip_range):
                if path in ['/register', '/en/register', '/tr/register']:
                    logger.warning(f"🚫 Auto-blocked IP range: {ip} ({reason})")
                    start_response('403 Forbidden', [('Content-Type', 'text/plain')])
                    return [b'Access Denied - Automated traffic detected']


        # Normal request - devam et
        return self.app(environ, start_response)
    
    def _record_suspicious(self, ip, path):
        data = self.ip_data[ip]
        data['suspicious_count'] += 1
        
        logger.warning(f"Suspicious request: {ip} -> {path}")
        
        # 10 şüpheli istek = blok
        if data['suspicious_count'] >= 10:
            self.blocked_ips.add(ip)
            logger.critical(f"IP auto-blocked: {ip}")
            
            # Email gönder
            try:
                self._send_alert(ip)
            except:
                pass
    
    def _send_alert(self, ip):
        from flask_mail import Message
        try:
            msg = Message(
                subject=f"🚨 IP Blocked: {ip}",
                recipients=[app.config.get('MAIL_USERNAME')],
                body=f"IP {ip} blocked due to suspicious activity at {datetime.now()}"
            )
            mail.send(msg)
        except Exception as e:
            logger.error(f"Alert email failed: {e}")

app.wsgi_app = SimpleSecurityMiddleware(app.wsgi_app)



@app.route('/admin/security/unblock-ip', methods=['POST'])
@admin_required
def unblock_ip():
    """Admin panelinden IP bloğunu kaldır"""
    try:
        data = request.get_json()
        ip_to_unblock = data.get('ip', '').strip()
        
        if not ip_to_unblock:
            return jsonify({"error": "IP adresi gerekli"}), 400
        
        # Middleware'den bloğu kaldır
        if hasattr(app.wsgi_app, 'blocked_ips'):
            if ip_to_unblock in app.wsgi_app.blocked_ips:
                app.wsgi_app.blocked_ips.remove(ip_to_unblock)
                logger.info(f"IP unblocked by admin: {ip_to_unblock}")
                return jsonify({
                    "success": True,
                    "message": f"IP {ip_to_unblock} bloğu kaldırıldı"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "IP zaten bloklu değil"
                })
        
        return jsonify({"error": "Security middleware bulunamadı"}), 500
        
    except Exception as e:
        logger.error(f"Unblock IP error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/admin/security/blocked-ips', methods=['GET'])
@admin_required
def get_blocked_ips():
    """Bloklu IP listesini göster"""
    try:
        if hasattr(app.wsgi_app, 'blocked_ips'):
            return jsonify({
                "blocked_ips": list(app.wsgi_app.blocked_ips),
                "total": len(app.wsgi_app.blocked_ips)
            })
        return jsonify({"blocked_ips": [], "total": 0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# =============================================================================
# app.py içine ekleyin
import hashlib
from datetime import datetime, timedelta

class RegistrationProtection:
    def __init__(self):
        self.honeypot_field = "website_url"  # Botların dolduracağı gizli alan
        self.min_form_time = 3  # Minimum 3 saniye form doldurma süresi
        self.ip_registrations = defaultdict(list)
        
    def validate_registration(self, request):
        """Kayıt isteğini doğrula"""
        ip = get_remote_address()
        errors = []
        
        # 1. Honeypot kontrolü
        honeypot = request.form.get(self.honeypot_field, '').strip()
        if honeypot:
            logger.warning(f"Honeypot triggered from IP: {ip}")
            return False, "Form validation failed"
        
        # 2. Form zamanlaması kontrolü
        form_timestamp = request.form.get('form_timestamp', '')
        if form_timestamp:
            try:
                submitted_time = float(form_timestamp)
                elapsed = time.time() - submitted_time
                if elapsed < self.min_form_time:
                    logger.warning(f"Form submitted too quickly: {elapsed}s from {ip}")
                    return False, "Please take your time filling the form"
            except:
                return False, "Invalid form submission"
        
        # 3. IP rate limiting (aynı IP'den 1 saatte max 3 kayıt)
        recent_registrations = [
            reg_time for reg_time in self.ip_registrations[ip]
            if datetime.now() - reg_time < timedelta(hours=1)
        ]
        
        if len(recent_registrations) >= 3:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            return False, "Too many registration attempts. Please try again later."
        
        # 4. Email domain kontrolü
        email = request.form.get('email', '').lower()
        suspicious_domains = [
            'trustreports.info', 'tempmail.com', 'guerrillamail.com',
            '10minutemail.com', 'throwaway.email'
        ]
        
        email_domain = email.split('@')[-1] if '@' in email else ''
        if email_domain in suspicious_domains:
            logger.warning(f"Suspicious email domain: {email_domain} from {ip}")
            return False, "Please use a valid business or personal email"
        
        # 5. Username pattern kontrolü
        username_pattern = r'^[A-Z][a-z]+[A-Z]{2,}[A-Z]{2}$'  # EdgarkigVK gibi
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        
        if re.match(username_pattern, first_name) or re.match(username_pattern, last_name):
            logger.warning(f"Suspicious name pattern from {ip}: {first_name} {last_name}")
            return False, "Invalid name format"
        
        # Başarılı - IP'yi kaydet
        self.ip_registrations[ip].append(datetime.now())
        return True, None

# Global instance
registration_protection = RegistrationProtection()




# =============================================================================
# =============================================================================
# =============================================================================

@app.before_request
def detect_language():
    # URL parametre: ?lang=en
    lang = request.args.get('lang')
    if lang in ['en', 'tr']:
        session['lang'] = lang

    g.lang = session.get('lang', 'tr')  # varsayılan Türkçe

@app.context_processor
def inject_language():
    lang = getattr(g, "lang", "en")  # Eğer g.lang yoksa 'en' kullan
    return dict(lang=lang)

@app.before_request
def check_access():
    if request.path.startswith("/voice/"):
        return 



# =============================================================================
# Route Registrations - Modül bazında route'ları kaydet
# =============================================================================

# Authentication routes import ve kaydet
from auth_routes import register_auth_routes
register_auth_routes(app, limiter, security_check_decorator, 
                    validate_and_sanitize_input, validate_email,
                    generate_csrf_token, verify_csrf_token)

# User dashboard routes import ve kaydet
from user_dashboard import register_user_routes
register_user_routes(app, limiter, security_check_decorator, 
                    validate_and_sanitize_input, validate_email,
                    generate_csrf_token, verify_csrf_token, generate_nonce)

# Admin dashboard routes import ve kaydet
from admin_dashboard import register_admin_routes
register_admin_routes(app, limiter, security_check_decorator, 
                     validate_and_sanitize_input, validate_email,
                     generate_csrf_token, verify_csrf_token, generate_nonce)

# Legal pages routes import ve kaydet
from legal_pages import register_legal_routes
register_legal_routes(app, limiter, security_check_decorator, 
                     validate_and_sanitize_input, generate_csrf_token, 
                     verify_csrf_token, generate_nonce)

# =============================================================================
# Mevcut Ana Sayfalar (Orijinal kodunuzdan)
# =============================================================================

@app.get("/")
def home():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("tr/index.html", lang="tr", nonce=nonce)

@app.get("/en")
def home_en():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("en/index.html", lang="en", nonce=nonce)

@app.get("/tr/about")
def about_tr():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("tr/about.html", lang="tr", nonce=nonce)

@app.get("/en/about")
def about_en():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("en/about.html", lang="en", nonce=nonce)

@app.get("/tr/services")
def services_tr():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("tr/services.html", lang="tr", nonce=nonce)

@app.get("/en/services")
def services_en():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("en/services.html", lang="en", nonce=nonce)

@app.get("/tr/apps")
def apps_tr():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("tr/apps.html", lang="tr", nonce=nonce)

@app.get("/en/apps")
def apps_en():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("en/apps.html", lang="en", nonce=nonce)

@app.get("/tr/joker-glint")
def joker_glint_tr():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("tr/product_joker_glint.html", lang="tr", nonce=nonce)

@app.get("/en/joker-glint")
def joker_glint_en():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("en/product_joker_glint.html", lang="en", nonce=nonce)

@app.get("/tr/ai")
@consent_required('ai_data')
def ai_tr():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("tr/ai.html", lang="tr", nonce=nonce)

@app.get("/en/ai")
@consent_required('ai_data')
def ai_en():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("en/ai.html", lang="en", nonce=nonce)

# SwipeFoto App Pages (Mevcut - değiştirmeyin)
@app.get("/tr/swipefoto")
def swipefoto_tr():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("tr/swipefoto.html", lang="tr", nonce=nonce)

@app.get("/en/swipefoto")
def swipefoto_en():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("en/swipefoto.html", lang="en", nonce=nonce)

# ⬇️ YENİ ROUTE'LAR - BURADAN BAŞLAYIN ⬇️

# SwipeFoto Privacy Policy
@app.get("/tr/swipefoto/privacy")
def swipefoto_privacy_tr():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("swipefoto/privacy_tr.html", lang="tr", nonce=nonce)

@app.get("/en/swipefoto/privacy")
def swipefoto_privacy_en():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("swipefoto/privacy.html", lang="en", nonce=nonce)

# SwipeFoto Terms of Service
@app.get("/tr/swipefoto/terms")
def swipefoto_terms_tr():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("swipefoto/terms_tr.html", lang="tr", nonce=nonce)

@app.get("/en/swipefoto/terms")
def swipefoto_terms_en():
    nonce = generate_nonce()
    session['csp_nonce'] = nonce
    return render_template("swipefoto/terms.html", lang="en", nonce=nonce)


# =============================================================================
# Mevcut İletişim Sayfaları (Güncellenerek korundu)
# =============================================================================

@app.route('/tr/contact', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
@security_check_decorator
def contact_tr():
    if request.method == 'GET':
        csrf_token = generate_csrf_token()
        return render_template('tr/contact.html', lang='tr', csrf_token=csrf_token)
    
    # POST işlemi için mevcut kodunuz aynı kalacak
    # Sadece veritabanına kaydetme eklenecek
    try:
        csrf_token = request.form.get('csrf_token', '')
        if not verify_csrf_token(csrf_token):
            logger.warning(f"CSRF token mismatch from IP: {get_remote_address()}")
            flash('Güvenlik hatası. Lütfen tekrar deneyin.', 'error')
            return redirect(url_for('contact_tr'))
        
        name = validate_and_sanitize_input(request.form.get('name', ''), 100)
        email_raw = request.form.get('email', '')
        phone = validate_and_sanitize_input(request.form.get('phone', ''), 20)
        company = validate_and_sanitize_input(request.form.get('company', ''), 100)
        service = validate_and_sanitize_input(request.form.get('service', ''), 50)
        message = validate_and_sanitize_input(request.form.get('message', ''), 2000)
        
        email = validate_email(email_raw)
        
        if not name or not email or not message:
            flash('Lütfen tüm zorunlu alanları doldurun.', 'error')
            return redirect(url_for('contact_tr'))
        
        if len(name) < 2 or len(message) < 10:
            flash('Ad ve mesaj çok kısa.', 'error')
            return redirect(url_for('contact_tr'))
        
        # Veritabanına kaydet
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO contact_submissions 
            (name, email, phone, company, service_type, message, ip_address, language)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, phone, company, service, message, get_remote_address(), 'tr'))
        
        conn.commit()
        conn.close()
        
        # Email gönder (mevcut kod)
        # ... email gönderme kodu ...
        
        logger.info(f"Contact form submitted successfully from IP: {get_remote_address()}, Email: {email}")
        flash('Mesajınız başarıyla gönderildi!', 'success')
        session.pop('csrf_token', None)
        
    except Exception as e:
        logger.error(f"Contact form error: {e}, IP: {get_remote_address()}")
        flash('Mesaj gönderilirken bir hata oluştu.', 'error')
    
    return redirect(url_for('contact_tr'))

@app.route('/en/contact', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
@security_check_decorator
def contact_en():
    # English contact form - similar implementation
    if request.method == 'GET':
        csrf_token = generate_csrf_token()
        return render_template('en/contact.html', lang='en', csrf_token=csrf_token)
    
    # POST implementation similar to Turkish version
    return redirect(url_for('contact_en'))


# =============================================================================
# 2fa mail 
# =============================================================================

@app.route('/twofa', methods=['GET', 'POST'])
def twofa_page():
    lang = 'en' if '/en/' in request.path else 'tr'

    if request.method == 'GET':
        return render_template(f"{lang}/twofa.html", lang=lang)

    input_code = request.form.get("code", "").strip()
    user_id = session.get("pending_user_id")

    if not user_id:
        flash("Geçersiz oturum. Lütfen tekrar giriş yapın.", "error")
        return redirect(url_for("login_page"))

    if verify_twofa_code(user_id, input_code):
        # Kod doğru → giriş tamamla
        session['user_id'] = user_id
        session.pop("pending_user_id", None)
        flash("Giriş başarıyla doğrulandı!", "success")
        return redirect(url_for("dashboard"))
    else:
        flash("Geçersiz veya süresi dolmuş 2FA kodu.", "error")
        return redirect(url_for("twofa_page"))



# =============================================================================
# SEO ve Utility Routes
# =============================================================================

@app.route("/robots.txt")
def robots_txt():
    content = """User-agent: *
Disallow: /admin
Disallow: /dashboard
Disallow: /api
Disallow: /login
Disallow: /register
Disallow: /alexa-chat

Sitemap: https://bktyconsultancy.co.uk/sitemap.xml
"""
    return Response(content, mimetype="text/plain")

@app.route("/sitemap.xml")
def sitemap():
    base_url = "https://bktyconsultancy.co.uk"

    # İngilizce sayfalar
    en_pages = [
        "/en/", "/en/about", "/en/apps", "/en/contact", 
        "/en/services", "/en/ai", "/en/joker-glint",
        "/en/terms", "/en/privacy", "/en/cookies"
    ]

    # Türkçe sayfalar
    tr_pages = [
        "/", "/tr/about", "/tr/apps", "/tr/contact", 
        "/tr/services", "/tr/ai", "/tr/joker-glint",
        "/tr/terms", "/tr/privacy", "/tr/cookies"
    ]

    all_pages = en_pages + tr_pages

    urls = []
    for page in all_pages:
        urls.append(f"""
        <url>
            <loc>{base_url}{page}</loc>
            <changefreq>weekly</changefreq>
            <priority>0.8</priority>
        </url>""")

    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        {''.join(urls)}
    </urlset>"""

    return Response(sitemap_xml, mimetype="application/xml")


# =============================================================================
# Security Headers ve Error Handlers
# =============================================================================

@app.after_request
def set_security_headers(response):
    nonce = session.get('csp_nonce', '')
    
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    response.headers['Permissions-Policy'] = (
        'geolocation=(), '
        'microphone=(), '
        'camera=(), '
        'payment=(), '
        'usb=(), '
        'magnetometer=(), '
        'gyroscope=(), '
        'accelerometer=()'
    )
    
    if nonce:
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com "
            "https://use.fontawesome.com "
            "https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com; "
            "font-src 'self' "
            "https://fonts.gstatic.com "
            "https://use.fontawesome.com "
            "https://cdnjs.cloudflare.com; "
            f"script-src 'self' 'nonce-{nonce}' "
            "https://cdnjs.cloudflare.com "
            "https://cdn.jsdelivr.net "
            "https://kit.fontawesome.com "
            "https://challenges.cloudflare.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' https://challenges.cloudflare.com; "
            "frame-src https://challenges.cloudflare.com; "
            "media-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none';"
        )
    else:
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com "
            "https://use.fontawesome.com "
            "https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com; "
            "font-src 'self' "
            "https://fonts.gstatic.com "
            "https://use.fontawesome.com "
            "https://cdnjs.cloudflare.com; "
            "script-src 'self' 'unsafe-inline' "
            "https://cdnjs.cloudflare.com "
            "https://cdn.jsdelivr.net "
            "https://kit.fontawesome.com "
            "https://challenges.cloudflare.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' https://challenges.cloudflare.com; "
            "frame-src https://challenges.cloudflare.com; "
            "media-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none';"
        )
    
    return response

@app.errorhandler(403)
def forbidden(e):
    if request.path.startswith("/voice/"):
        return jsonify({"success": False, "error": "Forbidden"}), 403
    return render_template("error/403.html", now=datetime.now()), 403


@app.errorhandler(404)
def not_found(error):
    return render_template('error/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error/500.html'), 500

# İkinci handle_exception'ı silin ve yerine şunu ekleyin:

from flask_limiter.errors import RateLimitExceeded

@app.errorhandler(429)
@app.errorhandler(RateLimitExceeded)
def ratelimit_handler(e):
    """Rate limit hatalarını yakala"""
    lang = 'en' if '/en/' in request.path else 'tr'
    
    # JSON request için
    if request.path.startswith('/api/'):
        return jsonify({
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later." if lang == 'en' else "Çok fazla istek. Lütfen daha sonra tekrar deneyin."
        }), 429
    
    # HTML request için
    message = 'Too many requests. Please try again in a few minutes.' if lang == 'en' else 'Çok fazla istek gönderdiniz. Lütfen birkaç dakika sonra tekrar deneyin.'
    flash(message, 'error')
    return redirect(request.referrer or url_for('home')), 429

# Genel exception handler'ı güncelle
@app.errorhandler(Exception)
def handle_exception(e):
    """Genel exception handler - rate limit hariç"""
    # Rate limit exception'ı atla
    if isinstance(e, RateLimitExceeded):
        return ratelimit_handler(e)
    
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    
    # API request için JSON dön
    if request.path.startswith('/api/'):
        return jsonify({"error": "Server error"}), 500
    
    # HTML request için
    return render_template('error/500.html'), 500

# =============================================================================
# Background Tasks ve Maintenance
# =============================================================================

def cleanup_background_tasks():
    """Arka plan temizlik görevleri"""
    while True:
        try:
            # Süresi dolmuş session'ları temizle
            cleanup_expired_sessions()
            
            # Eski task'ları temizle
            current_time = time.time()
            old_tasks = []
            
            for task_id, task in list(active_tasks.items()):
                if current_time - task["started_at"] > 3600:  # 1 saat
                    old_tasks.append(task_id)
                    del active_tasks[task_id]
            
            if old_tasks:
                logger.info(f"Cleaned up {len(old_tasks)} old tasks")
            
            # Şüpheli IP'leri temizle
            clean_suspicious_ips()
            
            # 1 saatte bir çalıştır
            time.sleep(3600)
            
        except Exception as e:
            logger.error(f"Background cleanup error: {e}")
            time.sleep(300)  # Hata durumunda 5 dakika bekle

# Background thread başlat
cleanup_thread = threading.Thread(target=cleanup_background_tasks, daemon=True)
cleanup_thread.start()

# =============================================================================
# Application Context ve Startup
# =============================================================================

def ensure_static_directories():
    """Gerekli static dizinleri oluştur"""
    static_dir = os.path.join(app.root_path, 'static', 'generated_images')
    os.makedirs(static_dir, exist_ok=True)
    print(f"📁 Static directory ensured: {static_dir}")
    return static_dir

# @app.before_first_request
def initialize_app_old():
    """Uygulama ilk başladığında çalışır"""
    # Veritabanını başlat
    init_database()
    
    # Static dizinleri oluştur
    ensure_static_directories()
    
    logger.info("Application initialized successfully")



# =============================================================================
# =============================================================================
# AI Chat Blueprint Integration
# =============================================================================
# =============================================================================
# =============================================================================
# =============================================================================
# AI Chat Blueprint Integration
# =============================================================================
import threading
import time
from collections import defaultdict
from flask import jsonify, request, send_from_directory

active_tasks = defaultdict(dict)

print("🔧 AI Chat Blueprint yükleniyor...")

RESEARCH_BLUEPRINT_AVAILABLE = False

# -----------------------------
# Ana AI Chat Endpoint (text modelleri için)
# -----------------------------
import threading
from collections import defaultdict

# Global task storage
task_status_store = defaultdict(dict)

def background_image_generation(task_id, prompt, user_id):
    """Arka planda görüntü üretimi - frontend uyumlu"""
    try:
        start_time = time.time()
        
        # İlk durum
        task_status_store[task_id] = {
            "status": "starting",
            "message": "Görüntü üretimi başlatılıyor...",
            "elapsed": 0,
            "started_at": start_time
        }
        
        # Progress tracking thread
        def update_progress():
            while task_id in task_status_store and task_status_store[task_id]["status"] in ["starting", "generating"]:
                elapsed = time.time() - start_time
                task_status_store[task_id]["elapsed"] = elapsed
                task_status_store[task_id]["message"] = f"Görüntü üretiliyor... ({elapsed:.0f}s)"
                time.sleep(2)
        
        # Progress thread başlat
        task_status_store[task_id]["status"] = "generating"
        progress_thread = threading.Thread(target=update_progress, daemon=True)
        progress_thread.start()
        
        # Gerçek görüntü üretimi
        result = multi_user_ollama.generate_image_with_comfyui_sync(
            prompt=prompt,
            user_id=user_id
        )
        
        elapsed = time.time() - start_time
        
        if result.get("success"):
            task_status_store[task_id] = {
                "status": "completed",
                "image_url": result.get("image_url"),
                "image_base64": result.get("image_base64"),
                "response_time": elapsed,
                "elapsed": elapsed,
                "prompt": prompt,
                "file_size": result.get("file_size", 0),
                "request_id": result.get("request_id", task_id)
            }
            logger.info(f"✅ Image generation completed: {task_id} ({elapsed:.2f}s)")
        else:
            task_status_store[task_id] = {
                "status": "error",
                "error": result.get("error", "Bilinmeyen hata"),
                "elapsed": elapsed
            }
            logger.error(f"❌ Image generation failed: {task_id}")
            
    except Exception as e:
        logger.error(f"Background image generation error: {e}", exc_info=True)
        task_status_store[task_id] = {
            "status": "error",
            "error": str(e),
            "elapsed": time.time() - start_time if 'start_time' in locals() else 0
        }

@app.route('/api/ask-ai-with-code', methods=['POST'])
@login_required
def ask_ai_with_code_main():
    """Ana AI chat endpoint — login gerektirir"""
    if not OLLAMA_AVAILABLE or multi_user_ollama is None:
        return jsonify({"error": "Ollama servisi mevcut değil"}), 503

    try:
        data = request.get_json(silent=True) or {}
        question = data.get('question', '').strip()
        if not question:
            return jsonify({"error": "Soru gereklidir"}), 400

        model = data.get('model', 'auto')
        user_id = request.remote_addr or 'anonymous'

        logger.info(f"AI request from {user_id}: {question[:50]}...")

        # API enhancement
        from ai_external_api_agent import enhance_ai_prompt_with_apis
        api_enhancement = enhance_ai_prompt_with_apis(question)
        final_prompt = api_enhancement.get('enhanced_prompt', question)
        api_used = api_enhancement.get('api_used', False)

        # ✅ Görüntü üretimi için /api/generate-image'a yönlendir
        if model == "stable-diffusion-v1.5" or (model == "auto" and any(kw in question.lower() for kw in ["resim", "görsel", "çiz", "image", "draw", "picture"])):
            # Frontend zaten /api/generate-image kullanıyor, burası kullanılmayacak
            # Ama güvenlik için yine de döndürelim
            return jsonify({
                "error": "Lütfen görüntü üretimi için model seçimini yapın",
                "suggestion": "Model dropdown'dan 'Stable Diffusion' seçin"
            }), 400

        # Normal chat flow
        result = multi_user_ollama.chat_with_model(
            model_name=model,
            prompt=final_prompt,
            user_id=user_id,
            auto_select_model=True
        )

        print(f"\n{'='*60}")
        print(f"🔍 RESULT KEYS: {list(result.keys())}")
        if 'research_intent' in result:
            print(f"🔍 Research Intent Action: {result['research_intent'].get('action')}")
            print(f"🔍 Is Weather Query: {result['research_intent'].get('is_weather_query')}")
        if 'research_performed' in result:
            print(f"✅ Research Performed: {result['research_performed']}")
            print(f"✅ Research Type: {result.get('research_type', 'N/A')}")
        if 'weather_data' in result:
            print(f"🌤️ Weather Data: {result['weather_data']}")
        print(f"{'='*60}\n")

        if "error" in result:
            logger.warning(f"AI user-level error: {result['error']}")
            content = f"⚠️ {result['error']}"
        else:
            content = result.get("response", "Yanıt alınamadı")

        response = {
            "choices": [{"message": {"content": content}}],
            "model": result.get("model", model),
            "response_time": result.get("response_time", 0),
            "api_enhancement": {
                "used": api_used,
                "type": api_enhancement.get('intent_data', {}).get('primary_intent') if api_used else None
            }
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"AI chat error: {str(e)}", exc_info=True)
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


@app.route('/api/check-task/<task_id>', methods=['GET'])
def check_task(task_id):
    """Task durumunu kontrol et"""
    status = task_status_store.get(task_id)
    
    if not status:
        return jsonify({"error": "Task bulunamadı"}), 404
    
    return jsonify(status), 200



@app.route('/api/research/toggle', methods=['POST'])
def toggle_research():
    """Web araştırma özelliğini aç/kapat"""
    if not OLLAMA_AVAILABLE or multi_user_ollama is None:
        return jsonify({"error": "Ollama servisi mevcut değil"}), 503
    
    try:
        data = request.get_json() or {}
        enabled = data.get('enabled', True)
        
        result = multi_user_ollama.toggle_web_research(enabled)
        
        return jsonify({
            "success": True,
            "web_research_enabled": result["web_research_enabled"],
            "message": f"Web araştırma {'açıldı' if enabled else 'kapatıldı'}"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Ayar değiştirilemedi: {str(e)}"
        }), 500

@app.route('/api/research/system-stats', methods=['GET'])
def research_system_stats():
    """Research system istatistikleri"""
    if not OLLAMA_AVAILABLE or multi_user_ollama is None:
        return jsonify({"error": "Ollama servisi mevcut değil"}), 503
    
    try:
        research_stats = multi_user_ollama.get_research_stats()
        system_stats = multi_user_ollama.get_system_stats()
        
        return jsonify({
            "success": True,
            "research_available": RESEARCH_BLUEPRINT_AVAILABLE,
            "research_stats": research_stats,
            "system_stats": system_stats,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"İstatistik alınamadı: {str(e)}"
        }), 500

# Otomatik cleanup için background thread
def auto_cleanup_tasks():
    """Eski task'ları otomatik temizle"""
    while True:
        try:
            time.sleep(300)  # 5 dakikada bir
            current_time = time.time()
            
            for task_id in list(task_status_store.keys()):
                task = task_status_store[task_id]
                started_at = task.get("started_at", current_time)
                
                # 10 dakikadan eski task'ları sil
                if current_time - started_at > 600:
                    del task_status_store[task_id]
                    logger.info(f"🧹 Cleaned up old task: {task_id}")
                    
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# App başlatıldığında cleanup thread'i başlat
cleanup_thread = threading.Thread(target=auto_cleanup_tasks, daemon=True)
cleanup_thread.start()

# =============================================================================
# Static Directories için ek route'lar
# =============================================================================

@app.route('/static/screenshots/<filename>')
def serve_research_screenshot(filename):
    """Research screenshot dosyalarını serve et"""
    try:
        # Güvenlik kontrolü
        if '..' in filename or '/' in filename or '\\' in filename:
            return "Invalid filename", 403
            
        # Sadece belirli uzantılara izin ver
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.gif']
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return "Invalid file type", 403
            
        screenshots_dir = os.path.join(app.static_folder, "screenshots")
        file_path = os.path.join(screenshots_dir, filename)
        
        # Path traversal kontrolü
        if not file_path.startswith(screenshots_dir):
            return "Access denied", 403
            
        # Dosyanın varlığını kontrol et
        if not os.path.exists(file_path):
            return "File not found", 404
            
        return send_from_directory(screenshots_dir, filename)
        
    except Exception as e:
        logger.error(f"Screenshot serve error: {e}")
        return "Server error", 500

# =============================================================================
# Enhanced Static Directories Setup
# =============================================================================

def ensure_research_directories():
    """Research için gerekli dizinleri oluştur"""
    directories = [
        os.path.join(app.static_folder, "screenshots"),
        os.path.join(app.static_folder, "generated_images"),
        os.path.join(app.static_folder, "research_data")
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Directory ensured: {directory}")
    
    return directories



# =============================================================================
# Test Endpoints
# =============================================================================

@app.route('/api/test-research-integration', methods=['GET'])
def test_research_integration():
    """Research entegrasyonunu test et"""
    try:
        test_results = {
            "ollama_available": OLLAMA_AVAILABLE,
            "research_blueprint_available": RESEARCH_BLUEPRINT_AVAILABLE,
            "multi_user_ollama_type": type(multi_user_ollama).__name__ if multi_user_ollama else None,
            "research_agent_initialized": research_agent is not None if 'research_agent' in globals() else False,
            "enhanced_runner_features": []
        }
        
        # Enhanced runner özelliklerini kontrol et
        if multi_user_ollama and hasattr(multi_user_ollama, 'enable_web_research'):
            test_results["enhanced_runner_features"].append("web_research_toggle")
            test_results["web_research_enabled"] = multi_user_ollama.enable_web_research
        
        if multi_user_ollama and hasattr(multi_user_ollama, 'research_agent'):
            test_results["enhanced_runner_features"].append("research_agent")
        
        if multi_user_ollama and hasattr(multi_user_ollama, 'get_research_stats'):
            test_results["enhanced_runner_features"].append("research_stats")
        
        # Blueprint routes kontrolü
        research_routes = [rule.rule for rule in app.url_map.iter_rules() if rule.rule.startswith('/api/research')]
        test_results["research_routes"] = research_routes
        
        return jsonify({
            "success": True,
            "test_results": test_results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500



# =============================================================================
# Enhanced Debug Function
# =============================================================================

def debug_research_integration():
    """Research entegrasyonunu debug et"""
    print("\n" + "="*60)
    print("DEBUG: RESEARCH INTEGRATION")
    print("="*60)
    
    print(f"✓ OLLAMA_AVAILABLE: {OLLAMA_AVAILABLE}")
    print(f"✓ RESEARCH_BLUEPRINT_AVAILABLE: {RESEARCH_BLUEPRINT_AVAILABLE}")
    print(f"✓ multi_user_ollama type: {type(multi_user_ollama).__name__ if multi_user_ollama else 'None'}")
    
    if 'research_agent' in globals():
        print(f"✓ research_agent initialized: {research_agent is not None}")
    else:
        print("❌ research_agent variable not found")
    
    # Research routes
    research_routes = [rule.rule for rule in app.url_map.iter_rules() if rule.rule.startswith('/api/research')]
    if research_routes:
        print(f"✅ {len(research_routes)} research routes registered:")
        for route in research_routes:
            print(f"  📍 {route}")
    else:
        print("❌ No research routes found!")
    
    # Enhanced runner features
    if multi_user_ollama:
        features = []
        if hasattr(multi_user_ollama, 'enable_web_research'):
            features.append("web_research_toggle")
        if hasattr(multi_user_ollama, 'research_agent'):
            features.append("research_agent")
        if hasattr(multi_user_ollama, 'get_research_stats'):
            features.append("research_stats")
        
        print(f"✅ Enhanced runner features: {features}")
    else:
        print("❌ multi_user_ollama not available")
    
    print("="*60)



# -----------------------------
# Mevcut modeller
# -----------------------------
@app.route('/api/models', methods=['GET'])
def get_models():
    """Mevcut modelleri listele"""
    if not OLLAMA_AVAILABLE or multi_user_ollama is None:
        return jsonify({"models": [], "error": "Ollama mevcut değil"})

    try:
        stats = multi_user_ollama.get_system_stats()
        models = [{"id": m, "name": m, "available": True} for m in stats.get('available_models', [])]
        return jsonify({"models": models})
    except Exception as e:
        return jsonify({"models": [], "error": str(e)})


print("✅ AI Chat endpoints registered directly")


# -----------------------------
# Görüntü üretimi - Asenkron
# -----------------------------
@app.route('/api/generate-image', methods=['POST'])
@login_required
def generate_image_async():
    """Asenkron görüntü üretimi — login gerektirir"""
    if not OLLAMA_AVAILABLE or multi_user_ollama is None:
        return jsonify({"error": "Ollama servisi mevcut değil"}), 503

    try:
        data = request.get_json() or {}
        prompt = data.get('question', '').strip()
        user_id = request.remote_addr or 'anonymous'

        if not prompt:
            return jsonify({"error": "Prompt gerekli"}), 400

        logger.info(f"🎨 Image generation request from {user_id}: {prompt[:50]}...")

        # Task ID oluştur (unique)
        task_id = f"img_{uuid.uuid4().hex[:12]}"
        
        # Background thread başlat
        thread = threading.Thread(
            target=background_image_generation,
            args=(task_id, prompt, user_id),
            daemon=True
        )
        thread.start()
        
        # Hemen task bilgisini döndür
        return jsonify({
            "task_id": task_id,
            "status": "starting",
            "message": "Görüntü üretimi başlatıldı"
        }), 202

    except Exception as e:
        logger.error(f"Image generation error: {e}", exc_info=True)
        return jsonify({"error": f"Sunucu hatası: {str(e)}"}), 500


# app.py'deki get_task_status fonksiyonunu değiştirin

@app.route('/api/task-status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """Task durumunu kontrol et - geliştirilmiş"""
    if task_id not in active_tasks:
        return jsonify({"error": "Task bulunamadı"}), 404

    task = active_tasks[task_id]
    elapsed = time.time() - task["started_at"]

    if task["status"] == "completed":
        result = task["result"]
        
        # Task'ı temizle (5 dakika sonra)
        if elapsed > 300:  # 5 dakika
            del active_tasks[task_id]

        if result.get("success"):
            return jsonify({
                "status": "completed",
                "choices": [{"message": {"content": "🎨 Görüntü üretildi"}}],
                "model": result.get("model", "stable-diffusion-v1.5"),
                "image_url": result.get("image_url"),
                "image_base64": result.get("image_base64"),
                "response_time": result.get("response_time", 0),
                "prompt_used": result.get("prompt_used", ""),
                "request_id": result.get("request_id", ""),
                "file_size": result.get("file_size", 0),
                "elapsed_total": elapsed
            })
        else:
            return jsonify({
                "status": "error", 
                "error": result.get("error", "Bilinmeyen hata"),
                "elapsed": elapsed
            })

    elif task["status"] == "error":
        error_msg = task.get("error", "Bilinmeyen hata")
        if elapsed > 300:  # 5 dakika sonra temizle
            del active_tasks[task_id]
        return jsonify({
            "status": "error", 
            "error": error_msg,
            "elapsed": elapsed
        })

    # Hala işleniyor
    progress_msg = "Görüntü üretiliyor..."
    if elapsed > 60:
        progress_msg = f"Görüntü üretiliyor... ({elapsed:.0f}s geçti)"
    if elapsed > 180:
        progress_msg = f"Büyük görüntü üretiliyor, lütfen bekleyin... ({elapsed:.0f}s)"
        
    return jsonify({
        "status": task["status"],
        "elapsed": elapsed,
        "message": progress_msg,
        "prompt": task.get("prompt", "")
    })

@app.route('/api/cleanup-tasks', methods=['POST'])
def cleanup_old_tasks():
    """Eski task'ları temizle"""
    try:
        current_time = time.time()
        old_tasks = []
        
        for task_id, task in list(active_tasks.items()):
            if current_time - task["started_at"] > 600:  # 10 dakika
                old_tasks.append(task_id)
                del active_tasks[task_id]
        
        return jsonify({
            "cleaned_tasks": len(old_tasks),
            "remaining_tasks": len(active_tasks),
            "task_ids_cleaned": old_tasks
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/active-tasks', methods=['GET'])
@login_required
def get_active_tasks():
    """Aktif task'ları listele — yalnızca kendi task'larını göster"""
    current_time = time.time()
    task_info = {}
    current_uid = str(session.get("user_id", request.remote_addr))

    for task_id, task in active_tasks.items():
        # Başkasının task'ını gösterme
        if task.get("user_id") != current_uid:
            continue
        task_info[task_id] = {
            "status": task["status"],
            "elapsed": current_time - task["started_at"],
        }

    return jsonify({
        "total_tasks": len(task_info),
        "tasks": task_info
    })

# -----------------------------
# Statik üretilmiş görselleri sunma
# -----------------------------
import os
from flask import send_from_directory

# Static dosyalar için özel route (güvenlik nedeniyle)
@app.route('/static/generated_images/<filename>')
def serve_generated_image(filename):
    """Üretilen görüntüleri güvenli şekilde serve et"""
    try:
        # Sadece .png, .jpg, .jpeg dosyalarına izin ver
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.gif']
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return "Invalid file type", 403
            
        # Path traversal saldırılarını önle
        if '..' in filename or '/' in filename or '\\' in filename:
            return "Invalid filename", 403
            
        static_dir = os.path.join(app.root_path, 'static', 'generated_images')
        file_path = os.path.join(static_dir, filename)
        
        # Dosyanın gerçekten static dizinde olduğunu kontrol et
        if not file_path.startswith(static_dir):
            return "Invalid path", 403
            
        # Dosyanın varlığını kontrol et
        if not os.path.exists(file_path):
            return "File not found", 404
            
        return send_from_directory(static_dir, filename)
        
    except Exception as e:
        logger.error(f"Error serving image {filename}: {e}")
        return "Server error", 500

# Test endpoint - görüntü üretimi sonrası test için
@app.route('/api/test-image-url/<filename>')
def test_image_url(filename):
    """Görüntü URL'inin çalışıp çalışmadığını test et"""
    static_dir = os.path.join(app.root_path, 'static', 'generated_images')
    file_path = os.path.join(static_dir, filename)
    
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        return jsonify({
            "exists": True,
            "path": file_path,
            "size": file_size,
            "url": f"/static/generated_images/{filename}"
        })
    else:
        return jsonify({
            "exists": False,
            "path": file_path,
            "error": "File not found"
        }), 404

@app.route('/comfy-output/<path:filename>')
def serve_comfy_output(filename):
    return send_from_directory("/home/bktyserver/ComfyUI/output", filename)

app.static_folder = 'static'
app.static_url_path = '/static'


def ensure_static_directories():
    """Gerekli static dizinleri oluştur"""
    static_dir = os.path.join(app.root_path, 'static', 'generated_images')
    os.makedirs(static_dir, exist_ok=True)
    print(f"📁 Static directory ensured: {static_dir}")
    return static_dir

@app.route('/api/test-comfyui', methods=['GET'])
def test_comfyui():
    """ComfyUI bağlantısını test et"""
    if not OLLAMA_AVAILABLE or multi_user_ollama is None:
        return jsonify({"error": "Ollama servisi mevcut değil"}), 503
    
    try:
        # ComfyUI API instance
        comfy_api = multi_user_ollama.comfy_api
        
        # Server durumu
        server_status = comfy_api.check_server_status()
        
        # Queue durumu
        queue_status = comfy_api.get_queue_status()
        
        # System stats çek
        import requests
        try:
            stats_response = requests.get("http://127.0.0.1:8188/system_stats", timeout=5)
            system_stats = stats_response.json() if stats_response.status_code == 200 else None
        except:
            system_stats = None
        
        return jsonify({
            "server_status": server_status,
            "queue_running": len(queue_status.get("queue_running", [])),
            "queue_pending": len(queue_status.get("queue_pending", [])),
            "system_stats": system_stats,
            "server_address": comfy_api.server_address,
            "test_time": time.time()
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "test_time": time.time()
        }), 500


# =============================================================================
# =============================================================================
# Voice Blueprint Registration 
# =============================================================================
# =============================================================================
# =============================================================================

print("🔧 Voice blueprint kayıt işlemi başlatılıyor...")

try:
    print("📦 voice_blueprint modülünü import etmeye çalışıyorum...")
    from voice_blueprint import voice_bp
    print(f"✅ voice_bp başarıyla import edildi: {voice_bp}")
    
    print("📋 Blueprint kayıt ediliyor...")
    app.register_blueprint(voice_bp, url_prefix="/voice")
    print("✅ Voice blueprint başarıyla kaydedildi")
    
    # Kayıtlı route'ları kontrol et
    print("📍 Tüm route'ları kontrol ediyorum...")
    voice_routes = [rule.rule for rule in app.url_map.iter_rules() if rule.rule.startswith('/voice')]
    print(f"📍 Voice routes: {voice_routes}")
    
    if not voice_routes:
        print("❌ Voice route'ları kayıtlı değil!")
    
except ImportError as e:
    print(f"❌ Import hatası: {e}")
    print("📁 voice_blueprint.py dosyası mevcut dizinde var mı kontrol edin")
    import os
    files = [f for f in os.listdir('.') if f.endswith('.py')]
    print(f"📁 Python dosyaları: {files}")
    
except Exception as e:
    print(f"❌ Blueprint kayıt hatası: {e}")
    import traceback
    print("📋 Detaylı hata:")
    traceback.print_exc()

@app.route('/api/voice-system-check')
def voice_system_check():
    """Voice system durumunu kontrol et"""
    try:
        # Doğru import - voice_blueprint modülünden voice objesini al
        from voice_blueprint import voice
        
        if voice and hasattr(voice, 'is_available') and voice.is_available():
            return jsonify({
                "success": True,
                "status": "Voice system operational",
                "whisper_loaded": voice.whisper is not None,
                "tts_loaded": voice.tts_engine is not None
            })
        else:
            return jsonify({
                "success": False,
                "status": "Voice system not fully available",
                "error": "Voice interface not properly initialized"
            })
    except ImportError as e:
        return jsonify({
            "success": False,
            "status": "Voice system import error",
            "error": f"voice objesi import edilemedi: {str(e)}"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "status": "Voice system error",
            "error": str(e)
        })

def ensure_audio_directory():
    """Audio dizinini oluştur"""
    audio_dir = os.path.join(app.root_path, 'static', 'audio')
    os.makedirs(audio_dir, exist_ok=True)
    return audio_dir

# Audio dosyalarını serve etmek için route (ana app.py'ye ekleyin)
@app.route('/audio/<filename>')
def serve_audio_file(filename):
    """Oluşturulan ses dosyalarını serve et"""
    try:
        # Güvenlik kontrolü
        secure_name = secure_filename(filename)
        if secure_name != filename:
            return "Invalid filename", 400
        
        # Sadece .wav dosyalarına izin ver
        if not filename.lower().endswith('.wav'):
            return "Only WAV files allowed", 400
        
        audio_dir = os.path.join(app.root_path, 'static', 'audio')
        file_path = os.path.join(audio_dir, secure_name)
        
        # Dosya var mı ve güvenli mi kontrol et
        if not os.path.exists(file_path):
            return "File not found", 404
        
        if not os.path.abspath(file_path).startswith(os.path.abspath(audio_dir)):
            return "Access denied", 403
        
        return send_from_directory(audio_dir, secure_name, mimetype="audio/wav")
        
    except Exception as e:
        logger.error(f"Audio serve error: {e}")
        return "Server error", 500

# Voice system cleanup route (opsiyonel)
@app.route('/api/cleanup-audio', methods=['POST'])
def cleanup_old_audio():
    """Eski ses dosyalarını temizle"""
    try:
        audio_dir = os.path.join(app.root_path, 'static', 'audio')
        if not os.path.exists(audio_dir):
            return jsonify({"cleaned": 0, "message": "Audio directory does not exist"})
        
        import time
        current_time = time.time()
        cleaned_files = []
        
        for filename in os.listdir(audio_dir):
            file_path = os.path.join(audio_dir, filename)
            if os.path.isfile(file_path):
                # 1 saatten eski dosyaları sil
                if current_time - os.path.getmtime(file_path) > 3600:
                    try:
                        os.remove(file_path)
                        cleaned_files.append(filename)
                    except:
                        pass
        
        return jsonify({
            "cleaned": len(cleaned_files),
            "files": cleaned_files
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# =============================================================================
# =============================================================================
# AI web search
# =============================================================================
# =============================================================================
# AI web search
# =============================================================================

print("🔧 AI Web Research yükleniyor...")

RESEARCH_BLUEPRINT_AVAILABLE = False

try:
    from ai_web_research_agent import enhanced_ollama_runner
    print(f"📦 Enhanced runner imported: {type(enhanced_ollama_runner)}")

    if OLLAMA_AVAILABLE and enhanced_ollama_runner:
        multi_user_ollama = enhanced_ollama_runner
        print("✅ Enhanced Ollama runner (with research) loaded successfully")

        # Agent kontrolü
        if hasattr(multi_user_ollama, 'research_agent') and multi_user_ollama.research_agent:
            print("✅ Research agent initialized successfully")
            RESEARCH_BLUEPRINT_AVAILABLE = True
        else:
            print("⚠️ Research agent boş, manual init deneniyor...")
            if hasattr(multi_user_ollama, "init_research_agent"):
                try:
                    multi_user_ollama.init_research_agent()
                    if multi_user_ollama.research_agent:
                        print("✅ Research agent manually initialized")
                        RESEARCH_BLUEPRINT_AVAILABLE = True
                    else:
                        print("❌ Research agent init başarısız")
                except Exception as e:
                    print(f"❌ Research agent init failed: {e}")

except ImportError as e:
    print(f"⚠️ AI Web Research import error: {e}")
    RESEARCH_BLUEPRINT_AVAILABLE = False



@app.route('/api/research/search', methods=['POST'])
@login_required
def research_search_endpoint():
    print("🔎 Research search endpoint called")
    print("OLLAMA_AVAILABLE:", OLLAMA_AVAILABLE)
    print("multi_user_ollama:", type(multi_user_ollama))
    print("Has research_agent:", hasattr(multi_user_ollama, 'research_agent'))
    """Direct research search endpoint - fallback search ile güncellenmiş"""
    try:
        # Enhanced runner kontrolü
        if not OLLAMA_AVAILABLE or not multi_user_ollama:
            return jsonify({
                "success": False,
                "error": "Ollama servisi mevcut değil"
            }), 503
        
        # Research agent kontrolü
        if not hasattr(multi_user_ollama, 'research_agent') or not multi_user_ollama.research_agent:
            return jsonify({
                "success": False,
                "error": "Research agent initialized değil"
            }), 503
        
        # Request data validation
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "JSON data gerekli"
            }), 400
            
        query = data.get('query', '').strip()
        if not query:
            return jsonify({
                "success": False,
                "error": "Query parametresi gerekli"
            }), 400
        
        max_results = data.get('max_results', 10)
        
        # Research agent'dan web_module'ü al
        web_module = multi_user_ollama.research_agent.web_module
        if not web_module or not hasattr(web_module, 'search_agent'):
            return jsonify({
                "success": False,
                "error": "Web search module bulunamadı"
            }), 503
        
        # Önce normal search dene
        search_result = web_module.search_agent.search_with_fallback(
            query=query,
            engine="duckduckgo",
            max_results=max_results
        )
        
        # Eğer sonuç yoksa fallback search'leri dene
        if search_result.get("success") and search_result.get("total_results", 0) == 0:
            logger.info(f"DuckDuckGo 0 sonuç - fallback search deneniyor: {query}")
            
            # ✅ Burada artık app.py’deki global fonksiyon değil,
            #    research_agent içindeki metodu çağırıyoruz
            wiki_results = multi_user_ollama.research_agent._search_wikipedia_fallback(query)
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
                manual_results = get_manual_search_results(query)
                if manual_results:
                    search_result = {
                        "success": True,
                        "query": query,
                        "engine": "manual_fallback", 
                        "results": manual_results,
                        "total_results": len(manual_results),
                        "search_time": 0.1
                    }
        
        # Sonucu formatla
        if search_result.get("success"):
            formatted_results = []
            for i, result in enumerate(search_result.get("results", []), 1):
                formatted_results.append({
                    "rank": i,
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("snippet", ""),
                    "domain": result.get("display_url", "")
                })
            
            return jsonify({
                "success": True,
                "query": query,
                "total_results": len(formatted_results),
                "results": formatted_results,
                "search_time": search_result.get("search_time", 0),
                "engine": search_result.get("engine", "duckduckgo"),
                "fallback_used": search_result.get("engine") != "duckduckgo"
            })
        else:
            return jsonify({
                "success": False,
                "error": search_result.get("error", "Arama başarısız"),
                "query": query
            })
            
    except Exception as e:
        logger.error(f"Research search error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Sunucu hatası: {str(e)}",
            "debug_info": {
                "ollama_available": OLLAMA_AVAILABLE,
                "multi_user_ollama_type": type(multi_user_ollama).__name__ if multi_user_ollama else None,
                "has_research_agent": hasattr(multi_user_ollama, 'research_agent') if multi_user_ollama else False
            }
        }), 500


def get_manual_search_results(query: str) -> List[Dict]:
    """Specific topics için manual curated results"""
    query_lower = query.lower()
    
    # Python ML kütüphaneleri
    if 'python' in query_lower and any(term in query_lower for term in ['machine learning', 'ml', 'ai', 'artificial intelligence', 'libraries', 'kütüphaneleri']):
        return [
            {
                'title': 'scikit-learn: Machine Learning in Python',
                'url': 'https://scikit-learn.org/',
                'snippet': 'Simple and efficient tools for predictive data analysis. Built on NumPy, SciPy, and matplotlib. Open source, commercially usable - BSD license.',
                'display_url': 'scikit-learn.org',
                'search_engine': 'manual'
            },
            {
                'title': 'TensorFlow - An end-to-end open source machine learning platform',
                'url': 'https://www.tensorflow.org/',
                'snippet': 'TensorFlow is an end-to-end open source platform for machine learning. It has a comprehensive, flexible ecosystem of tools, libraries and community resources.',
                'display_url': 'tensorflow.org',
                'search_engine': 'manual'
            },
            {
                'title': 'PyTorch - Tensors and Dynamic neural networks in Python',
                'url': 'https://pytorch.org/',
                'snippet': 'An open source machine learning framework that accelerates the path from research prototyping to production deployment.',
                'display_url': 'pytorch.org',
                'search_engine': 'manual'
            },
            {
                'title': 'Keras: Deep Learning for humans',
                'url': 'https://keras.io/',
                'snippet': 'Keras is an API designed for human beings, not machines. Simple, flexible, and powerful deep learning API.',
                'display_url': 'keras.io',
                'search_engine': 'manual'
            }
        ]
    
    # Web development
    elif 'python' in query_lower and any(term in query_lower for term in ['web', 'framework', 'django', 'flask']):
        return [
            {
                'title': 'Django - The Web framework for perfectionists with deadlines',
                'url': 'https://www.djangoproject.com/',
                'snippet': 'Django makes it easier to build better web apps more quickly and with less code. The web framework for perfectionists with deadlines.',
                'display_url': 'djangoproject.com',
                'search_engine': 'manual'
            },
            {
                'title': 'Flask - A lightweight WSGI web application framework',
                'url': 'https://flask.palletsprojects.com/',
                'snippet': 'Flask is a lightweight WSGI web application framework. It is designed to make getting started quick and easy, with the ability to scale up to complex applications.',
                'display_url': 'flask.palletsprojects.com',
                'search_engine': 'manual'
            }
        ]
    
    # Data science
    elif 'python' in query_lower and any(term in query_lower for term in ['data', 'pandas', 'numpy', 'analytics']):
        return [
            {
                'title': 'pandas - Python Data Analysis Library',
                'url': 'https://pandas.pydata.org/',
                'snippet': 'pandas is a fast, powerful, flexible and easy to use open source data analysis and manipulation tool, built on top of the Python programming language.',
                'display_url': 'pandas.pydata.org',
                'search_engine': 'manual'
            },
            {
                'title': 'NumPy - The fundamental package for scientific computing with Python',
                'url': 'https://numpy.org/',
                'snippet': 'NumPy is the fundamental package for scientific computing in Python. It is a Python library that provides a multidimensional array object.',
                'display_url': 'numpy.org',
                'search_engine': 'manual'
            }
        ]
    
    return []

@app.route('/api/research/analyze', methods=['POST'])
@login_required
def research_analyze_endpoint():
    """Direct webpage analysis endpoint — login gerektirir — SSRF korumalı"""
    try:
        if not OLLAMA_AVAILABLE or not multi_user_ollama:
            return jsonify({
                "success": False,
                "error": "Ollama servisi mevcut değil"
            }), 503
        
        if not hasattr(multi_user_ollama, 'research_agent') or not multi_user_ollama.research_agent:
            return jsonify({
                "success": False,
                "error": "Research agent initialized değil"
            }), 503
            
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "JSON data gerekli"
            }), 400
            
        url = data.get('url', '').strip()
        if not url:
            return jsonify({
                "success": False,
                "error": "URL parametresi gerekli"
            }), 400
            
        # Protocol ekle
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        # SSRF koruması — iç ağ / metadata endpoint'lerini engelle
        import ipaddress, socket
        from urllib.parse import urlparse as _urlparse
        def _is_safe_url(u):
            try:
                host = _urlparse(u).hostname or ""
                if host.lower() in {"localhost", "127.0.0.1", "0.0.0.0", "::1",
                                     "169.254.169.254", "metadata.google.internal"}:
                    return False
                ip = socket.gethostbyname(host)
                addr = ipaddress.ip_address(ip)
                return not (addr.is_private or addr.is_loopback or addr.is_link_local)
            except Exception:
                return False

        if not _is_safe_url(url):
            logger.warning(f"SSRF girişimi engellendi: {url} — IP: {request.remote_addr}")
            return jsonify({"success": False, "error": "Geçersiz veya erişilemeyen URL"}), 400

        # Content extractor'ı kullan
        web_module = multi_user_ollama.research_agent.web_module
        content_result = web_module.content_extractor.extract_text_content(url)
        
        if content_result.get("success"):
            return jsonify({
                "success": True,
                "url": url,
                "title": content_result.get("title", ""),
                "description": content_result.get("description", ""),
                "content_summary": content_result.get("text", "")[:1500],
                "word_count": content_result.get("word_count", 0),
                "domain": content_result.get("domain", "")
            })
        else:
            return jsonify({
                "success": False,
                "error": content_result.get("error", "Sayfa analizi başarısız"),
                "url": url
            })
            
    except Exception as e:
        logger.error(f"Research analyze error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Sunucu hatası: {str(e)}"
        }), 500

@app.route('/api/research/status', methods=['GET'])
def research_status():
    """Research system durumunu kontrol et"""
    try:
        status = {
            "ollama_available": OLLAMA_AVAILABLE,
            "research_blueprint_available": RESEARCH_BLUEPRINT_AVAILABLE,
            "multi_user_ollama_initialized": multi_user_ollama is not None,
            "research_agent_available": False,
            "web_module_available": False,
            "search_agent_available": False
        }
        
        if multi_user_ollama and hasattr(multi_user_ollama, 'research_agent'):
            status["research_agent_available"] = multi_user_ollama.research_agent is not None
            
            if multi_user_ollama.research_agent:
                web_module = multi_user_ollama.research_agent.web_module
                status["web_module_available"] = web_module is not None
                
                if web_module and hasattr(web_module, 'search_agent'):
                    status["search_agent_available"] = web_module.search_agent is not None
        
        return jsonify({
            "success": True,
            "status": status,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# Debug endpoint
@app.route('/api/research/debug', methods=['GET'])
def research_debug():
    """Research system debug bilgileri"""
    try:
        debug_info = {
            "environment": {
                "ollama_available": OLLAMA_AVAILABLE,
                "research_blueprint_available": RESEARCH_BLUEPRINT_AVAILABLE
            },
            "multi_user_ollama": {
                "type": type(multi_user_ollama).__name__ if multi_user_ollama else None,
                "attributes": dir(multi_user_ollama) if multi_user_ollama else []
            },
            "research_agent": {},
            "web_module": {},
            "routes": []
        }
        
        # Research agent info
        if multi_user_ollama and hasattr(multi_user_ollama, 'research_agent'):
            research_agent = multi_user_ollama.research_agent
            debug_info["research_agent"] = {
                "initialized": research_agent is not None,
                "type": type(research_agent).__name__ if research_agent else None,
                "attributes": dir(research_agent) if research_agent else []
            }
            
            # Web module info
            if research_agent and hasattr(research_agent, 'web_module'):
                web_module = research_agent.web_module
                debug_info["web_module"] = {
                    "initialized": web_module is not None,
                    "type": type(web_module).__name__ if web_module else None,
                    "has_search_agent": hasattr(web_module, 'search_agent') if web_module else False
                }
        
        # Routes info
        research_routes = [rule.rule for rule in app.url_map.iter_rules() if 'research' in rule.rule]
        debug_info["routes"] = research_routes
        
        return jsonify({
            "success": True,
            "debug_info": debug_info,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500




# -----------------------------------------------------------------------------
# =============================================================================
# =============================================================================

from api_integration_routes import register_api_integration_routes
from ai_external_api_agent import enhance_ai_prompt_with_apis, external_api_agent

print("🔧 Registering external API routes...")
try:
    from api_integration_routes import register_api_integration_routes
    register_api_integration_routes(app)
    print("✅ External API routes registered")
except ImportError as e:
    print(f"⚠️ External API routes import failed: {e}")
except Exception as e:
    print(f"❌ External API routes registration failed: {e}")


# Add this after the blueprint registration, around line 1100-1200 in app.py

@app.route('/api/test-external-apis', methods=['GET'])
def test_external_apis():
    """External API entegrasyonunu test et"""
    try:
        from external_api_service import external_api_service
        
        # Service status
        status = external_api_service.get_service_status()
        
        # Test results
        test_results = {}
        
        # Exchange rate test
        if status['exchangerate_api']['configured']:
            try:
                rates = external_api_service.get_popular_currency_rates("USD")
                test_results['exchange_rate'] = {
                    "success": rates.get("success", False),
                    "sample_rate": f"1 USD = {rates.get('popular_rates', {}).get('EUR', 'N/A')} EUR" if rates.get("success") else "Failed"
                }
            except Exception as e:
                test_results['exchange_rate'] = {"error": str(e)}
        
        # News API test
        if status['news_api']['configured']:
            try:
                news = external_api_service.get_top_headlines(language="en", limit=3)
                test_results['news'] = {
                    "success": news.get("success", False),
                    "articles_count": len(news.get("headlines", []))
                }
            except Exception as e:
                test_results['news'] = {"error": str(e)}
        
        # TMDB test
        if status['tmdb_api']['configured']:
            try:
                movies = external_api_service.get_popular_movies(language="en-US", page=1)
                test_results['tmdb'] = {
                    "success": movies.get("success", False),
                    "movies_count": len(movies.get("movies", []))
                }
            except Exception as e:
                test_results['tmdb'] = {"error": str(e)}
        
        return jsonify({
            "success": True,
            "service_status": status,
            "test_results": test_results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =============================================================================
# Football Api 
# =============================================================================

from football_prediction_agent import FootballPredictionAgent, integrate_football_predictions

# Startup'ta entegre edin
if OLLAMA_AVAILABLE and multi_user_ollama:
    multi_user_ollama = integrate_football_predictions(multi_user_ollama)
    print("⚽ Football prediction agent integrated")

@app.route('/api/football/predict', methods=['POST'])
def football_predict():
    """Maç tahmini endpoint'i"""
    try:
        data = request.get_json() or {}
        team1 = data.get('team1', '').strip()
        team2 = data.get('team2', '').strip()
        
        if not team1 or not team2:
            return jsonify({"error": "İki takım adı gerekli"}), 400
        
        user_id = request.remote_addr or 'anonymous'
        
        # ✅ predict_match yerine doğru metod adını kullan
        result = multi_user_ollama.predict_football_match(team1, team2, user_id)
        
        if "error" in result:
            return jsonify(result), 400
        
        # ✅ success anahtarını kontrol et
        if result.get("success"):
            return jsonify({
                "success": True,
                "analysis": result.get("analysis", "Analiz yapılamadı")
            }), 200
        else:
            return jsonify({"error": result.get("error", "Bilinmeyen hata")}), 400
        
    except Exception as e:
        logger.error(f"Football predict error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/football/upcoming/<int:league_id>', methods=['GET'])
def get_upcoming_matches(league_id):
    """Yaklaşan maçlar"""
    try:
        days = int(request.args.get('days', 7))
        
        # Football agent kontrolü
        if not hasattr(multi_user_ollama, 'football_agent'):
            return jsonify({"error": "Football agent not initialized"}), 503
            
        matches = multi_user_ollama.football_agent.get_upcoming_matches(league_id, days)
        
        return jsonify({
            "league_id": league_id,
            "matches": matches,
            "count": len(matches)
        })
        
    except Exception as e:
        logger.error(f"Upcoming matches error: {e}")
        return jsonify({"error": str(e)}), 500
# =============================================================================
# Context Processor ve Startup
# =============================================================================


def init_app_startup():
    """Uygulama başlangıç fonksiyonu - research ile güncellenmiş"""
    try:
        init_database()
        ensure_static_directories()
        ensure_audio_directory()
        
        if RESEARCH_BLUEPRINT_AVAILABLE:
            ensure_research_directories()
        
        print("✅ Database, static, audio ve research directories initialized")
        
        if RESEARCH_BLUEPRINT_AVAILABLE and 'research_agent' in globals():
            if research_agent:
                print("✅ Research agent operational")
            else:
                print("⚠️ Research agent not initialized")
        
    except Exception as e:
        import traceback
        print("⚠️ Initialization error (detailed):")
        traceback.print_exc()



# Update your existing inject_user function to include datetime:
@app.context_processor  
def inject_user():
    from datetime import datetime
    
    user = None
    if 'user_id' in session:
        try:
            user = get_current_user()
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            pass
    
    return dict(
        current_user=user,
        cookie_consent_given=session.get('cookie_consent_given', False),
        cookie_preferences=session.get('cookie_preferences', {}),
        current_time=datetime.now(),
        datetime=datetime
    )

    
# =============================================================================
# Debug
# =============================================================================
def debug_admin_routes():
    """Admin route'larının kayıtlı olup olmadığını kontrol et"""
    admin_routes = []
    all_routes = []
    
    for rule in app.url_map.iter_rules():
        all_routes.append(f"{rule.methods} {rule.rule}")
        if '/admin/' in rule.rule:
            admin_routes.append(f"{rule.methods} {rule.rule} -> {rule.endpoint}")
    
    print("\n" + "="*60)
    print("DEBUG: ADMIN ROUTES")
    print("="*60)
    
    if admin_routes:
        print(f"✅ {len(admin_routes)} admin route kayıtlı:")
        for route in admin_routes:
            print(f"  📍 {route}")
    else:
        print("❌ Hiç admin route kayıtlı değil!")
    
    print(f"\n📊 Toplam route sayısı: {len(all_routes)}")
    print("="*60)
    
    return len(admin_routes) > 0

# Test route ekleyin
@app.route('/admin-test')
@admin_required
def admin_test_route():
    return "Admin routes çalışıyor!"

# app.py'nin if __name__ == '__main__': bloğunu güncelleyin:
if __name__ == '__main__':
    # Uygulama başlat
    init_app_startup()
    
    # Admin routes debug
    debug_success = debug_admin_routes()
    if not debug_success:
        print("⚠️ Admin routes kayıtlı değil - admin_dashboard.py kontrol edin!")
    
    print("="*60)
    print("🚀 BKTY Consultancy Flask Uygulaması")
    print("="*60)
    print("📍 URL: http://127.0.0.1:8083")
    print("🔧 Test URL: http://127.0.0.1:8083/admin-test")
    
    app.run(host='127.0.0.1', port=8083, debug=True)


# =============================================================================
# Main Execution
# =============================================================================


if __name__ == '__main__':
    # Uygulama başlat
    init_app_startup()
    
    print("="*60)
    print("🚀 BKTY Consultancy Flask Uygulaması")
    print("="*60)
    print("📍 URL: http://127.0.0.1:8083")
    print("🔧 Features:")
    print("  ✓ User Management & Admin Panel")
    print("  ✓ Security & Rate Limiting") 
    print("  ✓ AI Chat Integration")
    print("  ✓ Voice Chat (STT + TTS)") 
    print("  ✓ Web Research & Screenshot")
    print("  ✓ Legal Compliance (GDPR)")
    print()
    
    # Mail config check
    mail_password = clean_config_value(os.getenv('MAIL_PASSWORD', ''))
    if not mail_password or mail_password == 'your-app-password-here':
        print("⚠️  MAIL_PASSWORD not configured")
    else:
        print("✓ Mail configuration ready")
    
    print("="*60)
    
    app.run(host='127.0.0.1', port=8083, debug=True)# Basit register route
