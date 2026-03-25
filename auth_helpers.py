# auth_helpers.py - Kimlik doğrulama yardımcıları ve decoratorlar
from functools import wraps
from flask import session, request, redirect, url_for, flash, g
import sqlite3
from datetime import datetime
import logging
import re 

logger = logging.getLogger(__name__)
DATABASE_PATH = 'bkty_consultancy.db'

def login_required(f):
    """Giriş yapmış kullanıcı gerektirir"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Kullanıcı ID var mı?
        if 'user_id' not in session:
            flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login_page'))

        # 2FA kontrolü (eğer aktifse)
        if 'pending_user_id' in session:
            flash('Lütfen önce e-posta adresinize gelen 2FA kodunu doğrulayın.', 'warning')
            return redirect(url_for('twofa_page'))

        # Kullanıcı bilgilerini yükle ve kontrol et
        g.current_user = get_current_user()
        if not g.current_user:
            session.clear()
            flash('Kullanıcı bilgileri bulunamadı. Lütfen tekrar giriş yapın.', 'error')
            return redirect(url_for('login_page'))

        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Admin yetkisi gerektirir"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # API endpoint için JSON dön
            if request.path.startswith('/admin/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login_page'))
        
        user = get_current_user()
        if not user or not user.get('is_admin'):
            # API endpoint için JSON dön
            if request.path.startswith('/admin/api/'):
                return jsonify({'error': 'Admin access required'}), 403
            flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
            return redirect(url_for('user_dashboard'))
        
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def verified_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login_page'))
        
        user = get_current_user()
        if not user or not user.get('is_verified'):
            flash('Bu özelliği kullanmak için email adresinizi doğrulamalısınız.', 'warning')
            return redirect(url_for('verify_email_page'))  # veya user_dashboard
        
        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def consent_required(consent_type):
    """Belirli bir onay türü gerektirir"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
                return redirect(url_for('login_page'))
            
            user = get_current_user()
            if not user:
                session.clear()
                return redirect(url_for('login_page'))
            
            # Onay kontrolü
            if consent_type == 'ai_data' and not user.get('ai_data_consent'):
                flash('AI özelliklerini kullanmak için veri işleme onayı vermelisiniz.', 'warning')
                return redirect(url_for('consent_page'))
            
            if consent_type == 'terms' and not user.get('terms_accepted'):
                flash('Hizmet şartlarını kabul etmelisiniz.', 'warning')
                return redirect(url_for('terms_page'))
            
            if consent_type == 'privacy' and not user.get('privacy_accepted'):
                flash('Gizlilik politikasını kabul etmelisiniz.', 'warning')
                return redirect(url_for('privacy_page'))
            
            g.current_user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    """Mevcut kullanıcı bilgilerini getir"""
    if 'user_id' not in session:
        return None
    
    from database import UserManager
    user = UserManager.get_user(session['user_id'])
    
    if user:
        # Son aktiviteyi güncelle
        UserManager.update_user_activity(session['user_id'])
    
    return user

def log_user_activity(action, details=None):
    """Kullanıcı aktivitesini logla"""
    user_id = session.get('user_id')
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO system_logs (user_id, action, details, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action, details, ip_address, user_agent))
        
        conn.commit()
        logger.info(f"User activity logged: {action} - User: {user_id}, IP: {ip_address}")
        
    except Exception as e:
        logger.error(f"Failed to log user activity: {e}")
    finally:
        conn.close()

def check_user_permissions(user, required_permission):
    """Kullanıcı izinlerini kontrol et"""
    if not user:
        return False
    
    # Admin tüm izinlere sahip
    if user.get('is_admin'):
        return True
    
    # Temel izin kontrolleri
    permission_map = {
        'ai_chat': user.get('ai_data_consent', False) and user.get('is_verified', False),
        'profile_edit': user.get('is_verified', False),
        'data_export': user.get('data_processing_consent', False),
        'admin_panel': user.get('is_admin', False),
        'user_management': user.get('is_admin', False)
    }
    
    return permission_map.get(required_permission, False)

def create_password_reset_token(email):
    """Şifre sıfırlama tokeni oluştur"""
    try:
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE email = ? AND is_active = TRUE', (email,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return None
        
        reset_token = secrets.token_urlsafe(32)
        
        # DÜZELTME: datetime'ı string'e çevir
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        
        cursor.execute('''
            UPDATE users SET reset_token = ?, reset_token_expires = ?
            WHERE email = ?
        ''', (reset_token, expires_at, email))  # Bu satır düzeldi
        
        conn.commit()
        conn.close()
        
        return reset_token
        
    except Exception as e:
        logger.error(f"Create reset token error: {e}")
        return None

def validate_reset_token(token):
    """Şifre sıfırlama tokenini doğrula"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, email, reset_token_expires FROM users 
        WHERE reset_token = ? AND is_active = TRUE
    ''', (token,))
    
    user = cursor.fetchone()
    conn.close()
    
    if user and datetime.fromisoformat(user[2]) > datetime.now():
        return {'valid': True, 'user_id': user[0], 'email': user[1]}
    
    return {'valid': False}

def reset_user_password(user_id, new_password):
    """Kullanıcı şifresini sıfırla"""
    from werkzeug.security import generate_password_hash
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    password_hash = generate_password_hash(new_password)
    
    cursor.execute('''
        UPDATE users SET 
            password_hash = ?, 
            reset_token = NULL, 
            reset_token_expires = NULL
        WHERE id = ?
    ''', (password_hash, user_id))
    
    conn.commit()
    conn.close()
    
    log_user_activity("password_reset", f"Password reset for user ID: {user_id}")




def send_verification_email(user_id, email, verification_token, language='tr'):
    """Email doğrulama maili gönder - düzeltilmiş versiyon"""
    try:
        from flask_mail import Message
        
        print(f"📧 Attempting to send verification email to {email}")  # Debug
        
        # Mail instance'ını import et
        try:
            from app import mail
            print(f"✅ Mail instance imported successfully")  # Debug
        except ImportError as mail_error:
            print(f"❌ Mail instance import error: {mail_error}")  # Debug
            return False
        
        # Hardcoded URL kullan (route problemi için)
        verification_url = f"https://bktyconsultancy.co.uk/verify-email/{verification_token}"

        
        # Email içeriği oluştur
        if language == 'en':
            subject = "BKTY Consultancy - Email Verification Required"
            
            body_text = f"""
Dear User,

Welcome to BKTY Consultancy!

To complete your registration, please verify your email address by clicking the link below:

{verification_url}

This verification link will expire in 24 hours for security reasons.

If you didn't create this account, please ignore this email.

Best regards,
BKTY Consultancy Team
Email: info@bktyconsultancy.co.uk
Website: https://bktyconsultancy.co.uk
"""
            
            body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Email Verification</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ padding: 30px; }}
        .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Email Verification Required</h1>
        </div>
        <div class="content">
            <p>Dear User,</p>
            <p><strong>Welcome to BKTY Consultancy!</strong></p>
            <p>To complete your registration and activate your account, please verify your email address by clicking the button below:</p>
            <p style="text-align: center;">
                <a href="{verification_url}" class="button">Verify Email Address</a>
            </p>
            <p>If the button doesn't work, copy and paste this link into your browser:</p>
            <p style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 5px;">{verification_url}</p>
            <p><strong>Important:</strong> This verification link will expire in 24 hours for security reasons.</p>
            <p>If you didn't create this account, please ignore this email.</p>
        </div>
        <div class="footer">
            <p><strong>BKTY Consultancy</strong><br>
            Email: <a href="mailto:info@bktyconsultancy.co.uk">info@bktyconsultancy.co.uk</a><br>
            Website: <a href="https://bktyconsultancy.co.uk">bktyconsultancy.co.uk</a></p>
        </div>
    </div>
</body>
</html>
"""
        else:  # Turkish
            subject = "BKTY Consultancy - Email Doğrulama Gerekli"
            
            body_text = f"""
Sayın Kullanıcı,

BKTY Consultancy'ye hoş geldiniz!

Kayıt işleminizi tamamlamak için lütfen aşağıdaki linke tıklayarak email adresinizi doğrulayın:

{verification_url}

Bu doğrulama linki güvenlik nedeniyle 24 saat sonra geçersiz olacaktır.

Bu hesabı siz oluşturmadıysanız, bu emaili görmezden gelin.

Saygılarımızla,
BKTY Consultancy Ekibi
Email: info@bktyconsultancy.co.uk
Website: https://bktyconsultancy.co.uk
"""
            
            body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Email Doğrulama</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ padding: 30px; }}
        .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Email Doğrulama Gerekli</h1>
        </div>
        <div class="content">
            <p>Sayın Kullanıcı,</p>
            <p><strong>BKTY Consultancy'ye hoş geldiniz!</strong></p>
            <p>Kayıt işleminizi tamamlamak ve hesabınızı aktifleştirmek için lütfen aşağıdaki butona tıklayarak email adresinizi doğrulayın:</p>
            <p style="text-align: center;">
                <a href="{verification_url}" class="button">Email Adresini Doğrula</a>
            </p>
            <p>Buton çalışmıyorsa, bu linki tarayıcınıza kopyalayarak yapıştırın:</p>
            <p style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 5px;">{verification_url}</p>
            <p><strong>Önemli:</strong> Bu doğrulama linki güvenlik nedeniyle 24 saat sonra geçersiz olacaktır.</p>
            <p>Bu hesabı siz oluşturmadıysanız, bu emaili görmezden gelin.</p>
        </div>
        <div class="footer">
            <p><strong>BKTY Consultancy</strong><br>
            Email: <a href="mailto:info@bktyconsultancy.co.uk">info@bktyconsultancy.co.uk</a><br>
            Website: <a href="https://bktyconsultancy.co.uk">bktyconsultancy.co.uk</a></p>
        </div>
    </div>
</body>
</html>
"""
        
        # Email mesajını oluştur
        try:
            msg = Message(
                subject=subject,
                recipients=[email],
                body=body_text,
                html=body_html,
                sender='info@bktyconsultancy.co.uk'
            )
            
            print(f"📧 Message created, attempting to send...")  # Debug
            
            # Email gönder
            mail.send(msg)
            
            print(f"✅ Verification email sent successfully to {email}")  # Debug
            
            # Activity log
            log_user_activity("verification_email_sent", f"Verification email sent to: {email}")
            
            return True
            
        except Exception as msg_error:
            print(f"❌ Message creation/sending error: {msg_error}")  # Debug
            logger.error(f"Message error: {msg_error}")
            return False
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")
        print(f"❌ General email sending error: {e}")  # Debug
        return False

def send_password_reset_email(email, reset_token, language='tr'):
    """Şifre sıfırlama maili gönder - verification email pattern'i ile"""
    try:
        from flask_mail import Message
        
        print(f"📧 Attempting to send password reset email to {email}")
        
        try:
            from app import mail
            print(f"✅ Mail instance imported successfully")
        except ImportError as mail_error:
            print(f"❌ Mail instance import error: {mail_error}")
            return False
        
        # Reset URL
        reset_url = f"https://bktyconsultancy.co.uk/reset-password/{reset_token}"
        
        # Email içeriği
        if language == 'en':
            subject = "BKTY Consultancy - Password Reset Request"
            
            body_text = f"""
Dear User,

You have requested to reset your password for your BKTY Consultancy account.

To reset your password, please click the link below:

{reset_url}

This link will expire in 1 hour for security reasons.

If you didn't request this password reset, please ignore this email. Your password will remain unchanged.

Best regards,
BKTY Consultancy Team
Email: info@bktyconsultancy.co.uk
Website: https://bktyconsultancy.co.uk
"""
            
            body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Password Reset</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ padding: 30px; }}
        .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #666; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Dear User,</p>
            <p>You have requested to reset your password for your BKTY Consultancy account.</p>
            <p>To reset your password, please click the button below:</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </p>
            <p>If the button doesn't work, copy and paste this link into your browser:</p>
            <p style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 5px;">{reset_url}</p>
            <div class="warning">
                <p><strong>⏰ Important:</strong> This password reset link will expire in 1 hour for security reasons.</p>
            </div>
            <p>If you didn't request this password reset, please ignore this email. Your password will remain unchanged and your account is secure.</p>
        </div>
        <div class="footer">
            <p><strong>BKTY Consultancy</strong><br>
            Email: <a href="mailto:info@bktyconsultancy.co.uk">info@bktyconsultancy.co.uk</a><br>
            Website: <a href="https://bktyconsultancy.co.uk">bktyconsultancy.co.uk</a></p>
        </div>
    </div>
</body>
</html>
"""
        else:  # Turkish
            subject = "BKTY Consultancy - Şifre Sıfırlama Talebi"
            
            body_text = f"""
Sayın Kullanıcı,

BKTY Consultancy hesabınızın şifresini sıfırlamak için bir talepte bulundunuz.

Şifrenizi sıfırlamak için lütfen aşağıdaki linke tıklayın:

{reset_url}

Bu link güvenlik nedeniyle 1 saat sonra geçersiz olacaktır.

Eğer bu şifre sıfırlama talebinde siz bulunmadıysanız, bu emaili görmezden gelin. Şifreniz değişmeyecek ve hesabınız güvende kalacaktır.

Saygılarımızla,
BKTY Consultancy Ekibi
Email: info@bktyconsultancy.co.uk
Website: https://bktyconsultancy.co.uk
"""
            
            body_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Şifre Sıfırlama</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ padding: 30px; }}
        .button {{ display: inline-block; padding: 15px 30px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #666; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Şifre Sıfırlama Talebi</h1>
        </div>
        <div class="content">
            <p>Sayın Kullanıcı,</p>
            <p>BKTY Consultancy hesabınızın şifresini sıfırlamak için bir talepte bulundunuz.</p>
            <p>Şifrenizi sıfırlamak için lütfen aşağıdaki butona tıklayın:</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">Şifreyi Sıfırla</a>
            </p>
            <p>Buton çalışmıyorsa, bu linki tarayıcınıza kopyalayarak yapıştırın:</p>
            <p style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 5px;">{reset_url}</p>
            <div class="warning">
                <p><strong>⏰ Önemli:</strong> Bu şifre sıfırlama linki güvenlik nedeniyle 1 saat sonra geçersiz olacaktır.</p>
            </div>
            <p>Eğer bu şifre sıfırlama talebinde siz bulunmadıysanız, bu emaili görmezden gelin. Şifreniz değişmeyecek ve hesabınız güvende kalacaktır.</p>
        </div>
        <div class="footer">
            <p><strong>BKTY Consultancy</strong><br>
            Email: <a href="mailto:info@bktyconsultancy.co.uk">info@bktyconsultancy.co.uk</a><br>
            Website: <a href="https://bktyconsultancy.co.uk">bktyconsultancy.co.uk</a></p>
        </div>
    </div>
</body>
</html>
"""
        
        # Email mesajı oluştur
        try:
            msg = Message(
                subject=subject,
                recipients=[email],
                body=body_text,
                html=body_html,
                sender='info@bktyconsultancy.co.uk'
            )
            
            print(f"📧 Message created, attempting to send...")
            
            mail.send(msg)
            
            print(f"✅ Password reset email sent successfully to {email}")
            
            # Activity log
            log_user_activity("password_reset_email_sent", f"Password reset email sent to: {email}")
            
            return True
            
        except Exception as msg_error:
            print(f"❌ Message creation/sending error: {msg_error}")
            logger.error(f"Message error: {msg_error}")
            return False
        
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        print(f"❌ General email sending error: {e}")
        return False



def validate_password_strength(password):
    """Şifre güçlülüğünü kontrol et"""
    errors = []
    
    if len(password) < 8:
        errors.append("Şifre en az 8 karakter olmalıdır")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Şifre en az bir büyük harf içermelidir")
    
    if not re.search(r'[a-z]', password):
        errors.append("Şifre en az bir küçük harf içermelidir")
    
    if not re.search(r'\d', password):
        errors.append("Şifre en az bir rakam içermelidir")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Şifre en az bir özel karakter içermelidir")
    
    return len(errors) == 0, errors

def cleanup_expired_sessions():
    """Süresi dolmuş oturumları temizle"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE user_sessions SET is_active = FALSE 
        WHERE expires_at < CURRENT_TIMESTAMP AND is_active = TRUE
    ''')
    
    cleaned_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    if cleaned_count > 0:
        logger.info(f"Cleaned up {cleaned_count} expired sessions")
    
    return cleaned_count


import secrets
from datetime import datetime, timedelta

def generate_twofa_code(user_id):
    """Kullanıcı için 2FA kodu üret ve DB'ye kaydet"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # 6 haneli random kod
    code = str(secrets.randbelow(1000000)).zfill(6)
    expires_at = datetime.now() + timedelta(minutes=5)

    # Kullanıcı tablosuna ek alanlar yoksa ekle (ilk sefer)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN twofa_code TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN twofa_expires TIMESTAMP")
    except:
        pass

    # Kodu yaz
    cursor.execute('''
        UPDATE users SET twofa_code = ?, twofa_expires = ?
        WHERE id = ?
    ''', (code, expires_at, user_id))

    conn.commit()
    conn.close()
    return code


def send_twofa_email(email, code, language="tr"):
    """Kullanıcıya 2FA kodunu mail gönder"""
    from flask_mail import Message
    from app import mail

    try:
        if language == "tr":
            subject = "BKTY Consultancy - Giriş Doğrulama Kodu"
            body = f"""
Merhaba,

Girişinizi doğrulamak için aşağıdaki 2FA kodunu kullanın:

🔑 {code}

Kod yalnızca 5 dakika geçerlidir.

Eğer bu işlemi siz yapmadıysanız, lütfen görmezden gelin.

Saygılarımızla,
BKTY Consultancy Ekibi
"""
        else:
            subject = "BKTY Consultancy - Login Verification Code"
            body = f"""
Hello,

Use the following 2FA code to verify your login:

🔑 {code}

The code is valid for 5 minutes only.

If you did not request this, please ignore.

Best regards,
BKTY Consultancy Team
"""

        msg = Message(
            subject=subject, 
            recipients=[email], 
            body=body,
            sender='info@bktyconsultancy.co.uk'
        )
        mail.send(msg)
        logger.info(f"2FA email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send 2FA email: {e}")
        return False

def verify_twofa_code(user_id, input_code):
    """Kullanıcının girdiği 2FA kodunu doğrula"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT twofa_code, twofa_expires FROM users WHERE id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False

    code, expires_at = row
    if not code or not expires_at:
        return False

    try:
        expires_at = datetime.fromisoformat(expires_at)
    except:
        return False

    if datetime.now() > expires_at:
        return False

    return input_code == code

