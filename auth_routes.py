# auth_routes.py - Login hatasını düzelten versiyon

from flask import request, render_template, redirect, url_for, flash, session, jsonify
from database import UserManager, SessionManager
from auth_helpers import (
    login_required, log_user_activity, create_password_reset_token,
    validate_reset_token, reset_user_password, send_verification_email,
    send_password_reset_email, validate_password_strength, get_current_user
)
from activity_tracking import ActivityTracker
import re
import logging
import sqlite3
import secrets
from datetime import datetime
import time
import requests
import os
import json
from flask_limiter.util import get_remote_address
from collections import defaultdict
from datetime import datetime, timedelta
logger = logging.getLogger(__name__)

def register_auth_routes(app, limiter, security_check_decorator, 
                        validate_and_sanitize_input, validate_email,
                        generate_csrf_token, verify_csrf_token):
    """Authentication route'larını kaydet"""
    
    # =============================================================================
    # Giriş Sayfası - DÜZELTİLMİŞ
    # =============================================================================
    @app.route('/login', methods=['GET', 'POST'])
    @app.route('/tr/login', methods=['GET', 'POST'])
    @app.route('/en/login', methods=['GET', 'POST'])
    @limiter.limit("10 per minute")
    @security_check_decorator
    def login_page():
        lang = 'en' if '/en/' in request.path else 'tr'
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            return render_template(f'{lang}/login.html', lang=lang, csrf_token=csrf_token)
        
        # POST - Login işlemi
        try:
            # CSRF kontrolü
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                flash('Güvenlik hatası. Lütfen tekrar deneyin.' if lang == 'tr' 
                    else 'Security error. Please try again.', 'error')
                return redirect(request.url)
            
            email = validate_email(request.form.get('email', '').strip())
            password = request.form.get('password', '')
            remember_me = request.form.get('remember_me') == 'on'
            
            if not email or not password:
                flash('Email ve şifre gereklidir.' if lang == 'tr' 
                    else 'Email and password are required.', 'error')
                return redirect(request.url)
            
            # Kullanıcı bilgilerini getir
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, password_hash, is_active, is_verified, is_admin, 
                    locked_until, failed_login_attempts, email, first_name, last_name
                FROM users 
                WHERE email = ?
            ''', (email,))
            
            user_data = cursor.fetchone()
            conn.close()
            
            if not user_data:
                UserManager.log_failed_login(email, 'User not found')
                flash('Hatalı email veya şifre.' if lang == 'tr' 
                    else 'Invalid email or password.', 'error')
                return redirect(request.url)
            
            user_id, password_hash, is_active, is_verified, is_admin, locked_until, failed_attempts, user_email, first_name, last_name = user_data
            
            # Hesap aktif kontrolü
            if not is_active:
                flash('Hesabınız deaktif edilmiş.' if lang == 'tr' 
                    else 'Your account has been deactivated.', 'error')
                return redirect(request.url)
            
            # Hesap kilidi kontrolü
            if locked_until:
                try:
                    if datetime.now() < datetime.fromisoformat(locked_until):
                        flash('Hesabınız geçici olarak kilitlenmiş.' if lang == 'tr' 
                            else 'Your account is temporarily locked.', 'error')
                        return redirect(request.url)
                except:
                    pass
            
            # Şifre doğrulama
            from werkzeug.security import check_password_hash
            if not check_password_hash(password_hash, password):
                UserManager.log_failed_login(email, 'Invalid password')
                flash('Hatalı email veya şifre.' if lang == 'tr' 
                    else 'Invalid email or password.', 'error')
                return redirect(request.url)
            
            # ✅ BAŞARILI GİRİŞ - Session'ları düzgün kur
            session['user_id'] = user_id
            session['user_email'] = user_email
            session['is_admin'] = bool(is_admin)
            session['is_verified'] = bool(is_verified)
            
            if remember_me:
                session.permanent = True
            
            # ✅ Session ID oluştur ve kaydet
            from database import SessionManager
            try:
                session_id = SessionManager.create_session(user_id)
                session['session_id'] = session_id
            except Exception as session_error:
                logger.warning(f"Session creation warning: {session_error}")
                # Session oluşturulamasa bile giriş başarılı olsun
            
            # Activity tracking
            try:
                ActivityTracker.log_user_activity(user_id, 'USER_LOGIN', 
                                                f'Login from {request.remote_addr}')
            except Exception as activity_error:
                logger.warning(f"Activity tracking warning: {activity_error}")
            
            # Başarısız deneme sayacını sıfırla
            try:
                UserManager.reset_failed_login_attempts(user_id)
            except:
                pass
            
            flash('Başarıyla giriş yaptınız!' if lang == 'tr' 
                else 'Successfully logged in!', 'success')
            
            # Yönlendirme
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            
            if is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
                
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            flash('Giriş sırasında bir hata oluştu.' if lang == 'tr' 
                else 'An error occurred during login.', 'error')
            return redirect(request.url)

    @app.route('/register', methods=['GET', 'POST'])
    @app.route('/tr/register', methods=['GET', 'POST'])
    @app.route('/en/register', methods=['GET', 'POST'])
    @limiter.limit("5 per minute")
    @security_check_decorator
    def register_page():
        lang = 'en' if '/en/' in request.path else 'tr'
        
        # ✅ Client IP'yi al
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
    
        user_agent = request.headers.get('User-Agent', '').lower()

        # Bot benzeri user-agent'ları tespit et
        suspicious_agents = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 
            'python-requests', 'java', 'go-http-client', 'okhttp'
        ]

        if any(agent in user_agent for agent in suspicious_agents):
            logger.warning(f"🤖 Suspicious User-Agent from {client_ip}: {user_agent[:100] if user_agent else 'Unknown'}")
            flash('Invalid browser detected.' if lang == 'en' 
                else 'Geçersiz tarayıcı tespit edildi.', 'error')
            return redirect(request.url)

        # Boş user-agent
        if not user_agent or len(user_agent) < 10:
            logger.warning(f"🤖 Empty/short User-Agent from {client_ip}")
            flash('Browser verification failed.' if lang == 'en' 
                else 'Tarayıcı doğrulaması başarısız.', 'error')
            return redirect(request.url)

    
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            form_timestamp = str(time.time())  # Timing kontrolü için
            return render_template(
                f'{lang}/register.html', 
                lang=lang, 
                csrf_token=csrf_token,
                form_timestamp=form_timestamp  # Template'e gönder
            )
        
        # POST - Bot koruması kontrolü
        try:
            client_ip = get_remote_address()
            print(f"🔄 Register POST request from {client_ip}")
            
            # 1. HONEYPOT KONTROLÜ
            honeypot = request.form.get('website_url', '').strip()
            if honeypot:
                logger.warning(f"🤖 Honeypot triggered from IP: {client_ip}, value: {honeypot}")
                
                # Database'e kaydet
                try:
                    conn = sqlite3.connect('bkty_consultancy.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO failed_registrations 
                        (ip_address, email, first_name, last_name, reason, form_data, user_agent)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        client_ip,
                        request.form.get('email', ''),
                        request.form.get('first_name', ''),
                        request.form.get('last_name', ''),
                        'honeypot_triggered',
                        json.dumps({'honeypot_value': honeypot}),
                        request.headers.get('User-Agent', '')
                    ))
                    conn.commit()
                    conn.close()
                except Exception as db_error:
                    logger.error(f"Failed to log honeypot attempt: {db_error}")
                
                # Sessizce reddet
                time.sleep(2)
                flash('Form validation failed.' if lang == 'en' else 'Form doğrulama hatası.', 'error')
                return redirect(request.url)
            
            # 2. CLOUDFLARE TURNSTILE KONTROLÜ - BURAYA EKLEYİN
            TURNSTILE_SECRET = os.getenv('TURNSTILE_SECRET_KEY')

            if TURNSTILE_SECRET:
                turnstile_token = request.form.get('cf-turnstile-response', '')
                
                if not turnstile_token:
                    logger.warning(f"🛡️ Missing Turnstile token from {client_ip}")
                    flash('Please complete the security verification.' if lang == 'en' 
                        else 'Lütfen güvenlik doğrulamasını tamamlayın.', 'error')
                    return redirect(request.url)
                
                try:
                    import requests
                    verify_response = requests.post(
                        'https://challenges.cloudflare.com/turnstile/v0/siteverify',
                        data={
                            'secret': TURNSTILE_SECRET,
                            'response': turnstile_token,
                            'remoteip': client_ip
                        },
                        timeout=5
                    )
                    
                    result = verify_response.json()
                    
                    if not result.get('success'):
                        error_codes = result.get('error-codes', [])
                        logger.warning(f"🛡️ Turnstile failed for {client_ip}: {error_codes}")
                        
                        try:
                            conn = sqlite3.connect('bkty_consultancy.db')
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO failed_registrations 
                                (ip_address, email, reason, form_data, user_agent)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (
                                client_ip,
                                request.form.get('email', ''),
                                'turnstile_failed',
                                json.dumps({'error_codes': error_codes}),
                                request.headers.get('User-Agent', '')
                            ))
                            conn.commit()
                            conn.close()
                        except:
                            pass
                        
                        flash('Security verification failed. Please try again.' if lang == 'en'
                            else 'Güvenlik doğrulaması başarısız. Lütfen tekrar deneyin.', 'error')
                        return redirect(request.url)
                        
                except Exception as e:
                    logger.error(f"Turnstile API error: {e}")
                    logger.warning(f"Turnstile verification skipped due to API error for {client_ip}")


            # 2. TIMING KONTROLÜ
            form_timestamp = request.form.get('form_timestamp', '')
            if form_timestamp:
                try:
                    submitted_time = float(form_timestamp)
                    elapsed = time.time() - submitted_time
                    
                    # Çok hızlı gönderim (3 saniyeden önce)
                    if elapsed < 3:
                        # Şüpheli aktiviteyi kaydet
                        if not hasattr(app, 'timing_violations'):
                            app.timing_violations = defaultdict(int)
                        
                        app.timing_violations[client_ip] += 1
                        
                        # 5 ihlalden sonra otomatik blokla
                        if app.timing_violations[client_ip] >= 5:
                            if hasattr(app.wsgi_app, 'blocked_ips'):
                                app.wsgi_app.blocked_ips.add(client_ip)
                                logger.critical(f"🚫 IP auto-blocked after repeated timing violations: {client_ip}")
                        
                        logger.warning(f"⚡ Form submitted too quickly: {elapsed:.2f}s from {client_ip} (violations: {app.timing_violations[client_ip]})")
                    
                    # Çok yavaş (1 saatten fazla)
                    if elapsed > 3600:
                        logger.warning(f"⏰ Form token expired: {elapsed:.2f}s from {client_ip}")
                        flash('Form session expired. Please try again.' if lang == 'en' 
                            else 'Form oturumu sona erdi. Lütfen tekrar deneyin.', 'error')
                        return redirect(request.url)
                        
                except (ValueError, TypeError):
                    logger.warning(f"❌ Invalid form timestamp from {client_ip}")
                    flash('Invalid form submission.' if lang == 'en' 
                        else 'Geçersiz form gönderimi.', 'error')
                    return redirect(request.url)
            
            # 3. IP RATE LIMITING (global değişken kullanarak)
            if not hasattr(app, 'ip_registrations'):
                app.ip_registrations = defaultdict(list)

            # Son 10 dakikadaki kayıtları kontrol et
            recent_regs = [
                reg_time for reg_time in app.ip_registrations[client_ip]
                if datetime.now() - reg_time < timedelta(minutes=10)  # 1 saatten 10 dakikaya düşürdük
            ]

            if len(recent_regs) >= 2:  # 3'ten 2'ye düşürdük - 10 dakikada max 2 kayıt
                logger.warning(f"🚫 Rate limit exceeded for IP: {client_ip} ({len(recent_regs)} attempts in 10 min)")
                
                # Database'e kaydet
                try:
                    conn = sqlite3.connect('bkty_consultancy.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO failed_registrations 
                        (ip_address, email, reason, form_data, user_agent)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        client_ip,
                        request.form.get('email', ''),
                        'rate_limit_exceeded',
                        json.dumps({'attempts_in_10min': len(recent_regs)}),
                        request.headers.get('User-Agent', '')
                    ))
                    conn.commit()
                    conn.close()
                except:
                    pass
                
                # IP'yi blokla
                if hasattr(app.wsgi_app, 'blocked_ips'):
                    app.wsgi_app.blocked_ips.add(client_ip)
                    logger.critical(f"🚫 IP auto-blocked: {client_ip}")
                
                flash('Too many registration attempts. Please try again later.' if lang == 'en'
                    else 'Çok fazla kayıt denemesi. Lütfen daha sonra tekrar deneyin.', 'error')
                return redirect(request.url)
            
            # Son 1 saatteki kayıtları kontrol et
            recent_regs = [
                reg_time for reg_time in app.ip_registrations[client_ip]
                if datetime.now() - reg_time < timedelta(hours=1)
            ]
            
            if len(recent_regs) >= 3:
                logger.warning(f"🚫 Rate limit exceeded for IP: {client_ip} ({len(recent_regs)} attempts)")
                flash('Too many registration attempts. Please try again later.' if lang == 'en'
                    else 'Çok fazla kayıt denemesi. Lütfen daha sonra tekrar deneyin.', 'error')
                return redirect(request.url)
            
            # CSRF kontrolü
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                logger.warning(f"🔐 CSRF mismatch from {client_ip}")
                flash('Security error. Please try again.' if lang == 'en' 
                    else 'Güvenlik hatası. Lütfen tekrar deneyin.', 'error')
                return redirect(request.url)
            
            # Form verilerini al ve validate et
            first_name = validate_and_sanitize_input(request.form.get('first_name', '').strip(), 50)
            last_name = validate_and_sanitize_input(request.form.get('last_name', '').strip(), 50)
            email = validate_email(request.form.get('email', '').strip())
            company = validate_and_sanitize_input(request.form.get('company', '').strip(), 100)
            phone = validate_and_sanitize_input(request.form.get('phone', '').strip(), 20)
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            print(f"📝 Form data: {first_name} {last_name}, {email}")
            
            # 4. ISIM PATTERN KONTROLÜ (Bot benzeri isimler)
            suspicious_name_pattern = r'^[A-Z][a-z]+[A-Z]{2,}[A-Z]{2}$'
            if re.match(suspicious_name_pattern, first_name) or re.match(suspicious_name_pattern, last_name):
                logger.warning(f"🤖 Suspicious name pattern from {client_ip}: {first_name} {last_name}")
                # Şüpheli aktiviteyi kaydet
                conn = sqlite3.connect('bkty_consultancy.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO failed_registrations (ip_address, email, reason, form_data)
                    VALUES (?, ?, ?, ?)
                ''', (client_ip, email, 'suspicious_name_pattern', 
                    json.dumps({'first_name': first_name, 'last_name': last_name})))
                conn.commit()
                conn.close()
                
                flash('Invalid name format. Please use your real name.' if lang == 'en'
                    else 'Geçersiz isim formatı. Lütfen gerçek isminizi kullanın.', 'error')
                return redirect(request.url)
            
            # 5. EMAIL DOMAIN KONTROLÜ
            suspicious_domains = [
                'trustreports.info', 'tempmail.com', 'guerrillamail.com',
                '10minutemail.com', 'throwaway.email', 'mailinator.com',
                'trashmail.com', 'getnada.com'
            ]
            
            email_domain = email.split('@')[-1].lower() if '@' in email else ''
            if email_domain in suspicious_domains:
                logger.warning(f"📧 Suspicious email domain: {email_domain} from {client_ip}")
                flash('Please use a valid business or personal email address.' if lang == 'en'
                    else 'Lütfen geçerli bir iş veya kişisel email adresi kullanın.', 'error')
                return redirect(request.url)
            
            # Gerekli alan kontrolü
            if not first_name or not last_name or not email or not password:
                flash('Please fill all required fields.' if lang == 'en'
                    else 'Lütfen tüm zorunlu alanları doldurun.', 'error')
                return redirect(request.url)
            
            # Email format kontrolü
            if not email:
                flash('Please enter a valid email address.' if lang == 'en'
                    else 'Geçerli bir email adresi girin.', 'error')
                return redirect(request.url)
            
            # Şifre kontrolü
            if password != confirm_password:
                flash('Passwords do not match.' if lang == 'en'
                    else 'Şifreler eşleşmiyor.', 'error')
                return redirect(request.url)
            
            # Şifre güçlülük kontrolü
            is_strong, password_errors = validate_password_strength(password)
            if not is_strong:
                for error in password_errors:
                    flash(error, 'error')
                return redirect(request.url)
            
            # Onay kontrolları
            privacy_accepted = request.form.get('privacy_accepted') == 'on'
            terms_accepted = request.form.get('terms_accepted') == 'on'
            
            if not privacy_accepted or not terms_accepted:
                flash('You must accept privacy policy and terms of service.' if lang == 'en'
                    else 'Gizlilik politikası ve kullanım şartlarını kabul etmelisiniz.', 'error')
                return redirect(request.url)
            
            # İsteğe bağlı onaylar
            data_processing_consent = request.form.get('data_processing_consent') == 'on'
            marketing_consent = request.form.get('marketing_consent') == 'on'
            
            # Database işlemi
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            try:
                # Email zaten kullanımda mı kontrol et
                cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    conn.close()
                    flash('This email address is already in use.' if lang == 'en'
                        else 'Bu email adresi zaten kullanılıyor.', 'error')
                    return redirect(request.url)
                
                # Şifreyi hash'le ve token oluştur
                from werkzeug.security import generate_password_hash
                import secrets
                
                password_hash = generate_password_hash(password)
                verification_token = secrets.token_urlsafe(32)
                
                print(f"🔐 Creating user with hashed password and token")
                
                # Kullanıcıyı oluştur
                cursor.execute('''
                    INSERT INTO users (
                        first_name, last_name, email, company, phone, 
                        password_hash, preferred_language, 
                        privacy_accepted, terms_accepted, 
                        data_processing_consent, marketing_consent, ai_data_consent,
                        verification_token, created_at, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    first_name, last_name, email, 
                    company if company else None, 
                    phone if phone else None,
                    password_hash, lang,
                    privacy_accepted, terms_accepted,
                    data_processing_consent, marketing_consent, data_processing_consent,
                    verification_token, datetime.now(), True
                ))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                print(f"✅ User created successfully with ID: {user_id}")
                
                # IP kaydı ekle (başarılı kayıt)
                app.ip_registrations[client_ip].append(datetime.now())
                
                # Activity tracking
                try:
                    log_user_activity(user_id, 'USER_REGISTERED', f'New user registration from {client_ip}')
                except Exception as activity_error:
                    print(f"⚠️ Activity tracking failed: {activity_error}")
                
                # Doğrulama emaili gönder
                email_sent = False
                try:
                    email_sent = send_verification_email(user_id, email, verification_token, lang)
                    if email_sent:
                        print(f"📧 Verification email sent to {email}")
                    else:
                        print(f"❌ Failed to send verification email")
                except Exception as email_error:
                    print(f"❌ Email sending error: {email_error}")
                
                # Başarı mesajı
                if email_sent:
                    flash('Account created! Please check your email for verification.' if lang == 'en'
                        else 'Hesabınız oluşturuldu! Lütfen email adresinizi kontrol edin.', 'success')
                else:
                    flash('Account created but verification email failed. Please try again later.' if lang == 'en'
                        else 'Hesap oluşturuldu ancak doğrulama emaili gönderilemedi.', 'warning')
                
                conn.close()
                return redirect(url_for('login_page'))
                
            except sqlite3.IntegrityError as db_error:
                conn.rollback()
                conn.close()
                print(f"❌ Database integrity error: {db_error}")
                flash('This email address is already in use.' if lang == 'en'
                    else 'Bu email adresi zaten kullanılıyor.', 'error')
                return redirect(request.url)
                
            except Exception as db_error:
                conn.rollback()
                conn.close()
                logger.error(f"Database error during registration: {db_error}")
                print(f"❌ Database error: {db_error}")
                flash('Database error. Please try again.' if lang == 'en'
                    else 'Veritabanı hatası. Lütfen tekrar deneyin.', 'error')
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Registration error: {e}")
            print(f"❌ General registration error: {e}")
            flash('An error occurred during registration.' if lang == 'en'
                else 'Kayıt sırasında bir hata oluştu.', 'error')
            return redirect(request.url)
    
    # =============================================================================
    # Şifre Sıfırlama Talebi
    # =============================================================================
    @app.route('/forgot-password', methods=['GET', 'POST'])
    @app.route('/tr/forgot-password', methods=['GET', 'POST'])
    @app.route('/en/forgot-password', methods=['GET', 'POST'])
    @limiter.limit("5 per minute")
    @security_check_decorator
    def forgot_password():
        lang = 'en' if '/en/' in request.path else 'tr'
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            # Template yolunu düzelt
            return render_template(f'{lang}/forgot_password.html', lang=lang, csrf_token=csrf_token)
    
        
        try:
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                flash('Güvenlik hatası. Lütfen tekrar deneyin.' if lang == 'tr' 
                      else 'Security error. Please try again.', 'error')
                return redirect(request.url)
            
            email = validate_email(request.form.get('email', '').strip())
            
            if not email:
                flash('Geçerli bir email adresi girin.' if lang == 'tr' 
                      else 'Please enter a valid email address.', 'error')
                return redirect(request.url)
            
            # Şifre sıfırlama tokeni oluştur
            reset_token = create_password_reset_token(email)
            
            if reset_token:
                # Email gönder
                send_password_reset_email(email, reset_token, lang)
                
                # Activity tracking
                conn = sqlite3.connect('bkty_consultancy.db')
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
                user = cursor.fetchone()
                if user:
                    ActivityTracker.log_user_activity(user[0], 'PASSWORD_RESET_REQUESTED', 'User requested password reset')
                conn.close()
                
                flash('Şifre sıfırlama linki email adresinize gönderildi.' if lang == 'tr' 
                      else 'Password reset link has been sent to your email.', 'success')
            else:
                # Güvenlik nedeniyle her durumda aynı mesajı göster
                flash('Şifre sıfırlama linki email adresinize gönderildi.' if lang == 'tr' 
                      else 'Password reset link has been sent to your email.', 'success')
            
            return redirect(url_for('login_page'))
            
        except Exception as e:
            logger.error(f"Forgot password error: {e}")
            flash('İşlem sırasında bir hata oluştu.' if lang == 'tr' 
                  else 'An error occurred during the process.', 'error')
            return redirect(request.url)
    
    # =============================================================================
    # Şifre Sıfırlama
    # =============================================================================
    @app.route('/reset-password/<token>', methods=['GET', 'POST'])
    @limiter.limit("5 per minute")
    @security_check_decorator
    def reset_password(token):
        # Dil algılaması ekle
        lang = session.get('lang', 'tr')
        
        if request.method == 'GET':
            # Token geçerliliğini kontrol et
            token_data = validate_reset_token(token)
            
            if not token_data['valid']:
                flash('Geçersiz veya süresi dolmuş şifre sıfırlama linki.' if lang == 'tr' 
                    else 'Invalid or expired password reset link.', 'error')
                return redirect(url_for('login_page'))
            
            csrf_token = generate_csrf_token()
            # Dil parametresi ile template'i render et
            return render_template(f'{lang}/reset_password.html', 
                                token=token, 
                                csrf_token=csrf_token,
                                lang=lang)
        
        # POST request
        try:
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                flash('Güvenlik hatası. Lütfen tekrar deneyin.' if lang == 'tr'
                    else 'Security error. Please try again.', 'error')
                return redirect(request.url)
            
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if password != confirm_password:
                flash('Şifreler eşleşmiyor.' if lang == 'tr'
                    else 'Passwords do not match.', 'error')
                return redirect(request.url)
            
            # Şifre güçlülüğü kontrolü
            is_strong, password_errors = validate_password_strength(password)
            if not is_strong:
                for error in password_errors:
                    flash(error, 'error')
                return redirect(request.url)
            
            # Token doğrulama
            token_data = validate_reset_token(token)
            if not token_data['valid']:
                flash('Geçersiz veya süresi dolmuş şifre sıfırlama linki.' if lang == 'tr'
                    else 'Invalid or expired password reset link.', 'error')
                return redirect(url_for('login_page'))
            
            # Şifreyi sıfırla
            reset_user_password(token_data['user_id'], password)
            
            # Activity tracking
            try:
                ActivityTracker.log_user_activity(token_data['user_id'], 
                                                'PASSWORD_RESET_COMPLETED', 
                                                'User successfully reset password')
            except:
                pass  # Activity tracking hatası ana işlemi durdurmasın
            
            flash('Şifreniz başarıyla güncellendi!' if lang == 'tr'
                else 'Your password has been successfully updated!', 'success')
            return redirect(url_for('login_page'))
            
        except Exception as e:
            logger.error(f"Reset password error: {e}")
            flash('Şifre sıfırlama sırasında bir hata oluştu.' if lang == 'tr'
                else 'An error occurred during password reset.', 'error')
            return redirect(request.url)
    
    # =============================================================================
    # Çıkış
    # =============================================================================
    @app.route('/logout')
    def logout():
        try:
            user_id = session.get('user_id')
            
            if user_id:
                ActivityTracker.end_user_session(user_id)
            
            session.clear()
            flash('Başarıyla çıkış yaptınız.', 'success')
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            session.clear()
        
        return redirect(url_for('home'))

    print("Auth routes registered successfully")
    
    # =============================================================================
    # Yeniden Doğrulama Maili Gönder
    # =============================================================================

    @app.route('/verify-email/<string:token>')
    def verify_email(token):
        """Email doğrulama route'u"""
        try:
            print(f"Verification attempt with token: {token}")
            
            # Token uzunluğu ve format kontrolü
            if not token or len(token) < 10:
                flash('Geçersiz doğrulama linki.', 'error')
                return redirect(url_for('login_page'))
            
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, email, preferred_language, first_name, last_name 
                FROM users 
                WHERE verification_token = ? AND is_active = TRUE
            ''', (token,))
            
            user = cursor.fetchone()
            
            if user:
                user_id, email, lang, first_name, last_name = user
                
                # Kullanıcıyı doğrulanmış olarak işaretle
                cursor.execute('''
                    UPDATE users SET 
                        is_verified = TRUE, 
                        email_verified_at = ?, 
                        verification_token = NULL
                    WHERE id = ?
                ''', (datetime.now(), user_id))
                
                conn.commit()
                conn.close()
                
                lang = lang if lang else 'tr'
                if lang == 'tr':
                    flash('Email adresiniz başarıyla doğrulandı!', 'success')
                else:
                    flash('Your email has been successfully verified!', 'success')
                
                return redirect(url_for('login_page'))
            
            else:
                conn.close()
                flash('Geçersiz veya süresi dolmuş doğrulama linki.', 'error')
                return redirect(url_for('login_page'))
                    
        except Exception as e:
            logger.error(f"Email verification error: {e}")
            flash('Doğrulama sırasında bir hata oluştu.', 'error')
            return redirect(url_for('login_page'))
    
    @app.route('/resend-verification', methods=['POST'])
    @limiter.limit("2 per minute")
    @security_check_decorator
    def resend_verification():
        try:
            email = validate_email(request.form.get('email', '').strip())
            
            if not email:
                return jsonify({'success': False, 'error': 'Geçerli email gerekli'})
            
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, is_verified, preferred_language FROM users 
                WHERE email = ? AND is_active = TRUE
            ''', (email,))
            
            user = cursor.fetchone()
            
            if user and not user[1]:  # Kullanıcı var ama doğrulanmamış
                # Yeni token oluştur
                verification_token = secrets.token_urlsafe(32)
                
                cursor.execute('''
                    UPDATE users SET verification_token = ? WHERE id = ?
                ''', (verification_token, user[0]))
                
                conn.commit()
                conn.close()
                
                # Activity tracking
                ActivityTracker.log_user_activity(user[0], 'VERIFICATION_EMAIL_RESENT', 'User requested new verification email')
                
                # Email gönder
                lang = user[2] if user[2] else 'tr'
                send_verification_email(user[0], email, verification_token, lang)
                
                return jsonify({'success': True})
            
            else:
                conn.close()
                return jsonify({'success': True})  # Güvenlik nedeniyle her durumda success
                
        except Exception as e:
            logger.error(f"Resend verification error: {e}")
            return jsonify({'success': False, 'error': 'Sunucu hatası'})

    @app.route('/test-verify/<string:token>')
    def test_verify(token):
        return f"Token alındı: {token}<br>Uzunluk: {len(token)}<br>Route çalışıyor!"