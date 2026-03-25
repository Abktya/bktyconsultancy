# legal_pages.py - Yasal sayfalar ve onay yönetimi

from flask import request, render_template, redirect, url_for, flash, session, jsonify
from auth_helpers import login_required, get_current_user, log_user_activity
from database import UserManager
import sqlite3
import json
import logging
from datetime import datetime
import secrets

logger = logging.getLogger(__name__)

def register_legal_routes(app, limiter, security_check_decorator, 
                         validate_and_sanitize_input, generate_csrf_token, 
                         verify_csrf_token, generate_nonce):
    """Yasal sayfalar route'larını kaydet"""
    
    # =============================================================================
    # Kullanım Şartları
    # =============================================================================
    @app.route('/terms')
    @app.route('/tr/terms')
    @app.route('/en/terms')
    def terms_page():
        lang = 'en' if '/en/' in request.path else 'tr'
        nonce = generate_nonce()
        session['csp_nonce'] = nonce
        
        return render_template(f'{lang}/terms.html', lang=lang, nonce=nonce)
    
    # =============================================================================
    # Gizlilik Politikası
    # =============================================================================
    @app.route('/privacy')
    @app.route('/tr/privacy')
    @app.route('/en/privacy')
    def privacy_page():
        lang = 'en' if '/en/' in request.path else 'tr'
        nonce = generate_nonce()
        session['csp_nonce'] = nonce
        
        return render_template(f'{lang}/privacy.html', lang=lang, nonce=nonce)
    
    # =============================================================================
    # Çerez Politikası
    # =============================================================================
    @app.route('/cookies')
    @app.route('/tr/cookies')
    @app.route('/en/cookies')
    def cookie_policy():
        lang = 'en' if '/en/' in request.path else 'tr'
        nonce = generate_nonce()
        session['csp_nonce'] = nonce
        
        return render_template(f'{lang}/cookie_policy.html', lang=lang, nonce=nonce)
    
    # =============================================================================
    # Çerez Ayarları
    # =============================================================================
    @app.route('/cookie-settings', methods=['GET', 'POST'])
    @app.route('/tr/cookie-settings', methods=['GET', 'POST'])
    @app.route('/en/cookie-settings', methods=['GET', 'POST'])
    def cookie_settings():
        lang = 'en' if '/en/' in request.path else 'tr'
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            nonce = secrets.token_urlsafe(16)  
            
            # Mevcut çerez ayarlarını al
            current_settings = session.get('cookie_preferences', {
                'essential': True,
                'analytics': False,
                'marketing': False,
                'functional': False
            })
            
            return render_template(f'{lang}/cookie_settings.html', 
                                lang=lang, csrf_token=csrf_token, nonce=nonce,
                                current_settings=current_settings)
            
        try:
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                flash('Güvenlik hatası. Lütfen tekrar deneyin.' if lang == 'tr' 
                      else 'Security error. Please try again.', 'error')
                return redirect(request.url)
            
            # Çerez tercihlerini al
            cookie_preferences = {
                'essential': True,  # Her zaman zorunlu
                'analytics': request.form.get('analytics') == 'on',
                'marketing': request.form.get('marketing') == 'on',
                'functional': request.form.get('functional') == 'on',
                'updated_at': datetime.now().isoformat()
            }
            
            # Session'a kaydet
            session['cookie_preferences'] = cookie_preferences
            session['cookie_consent_given'] = True
            
            # Kullanıcı giriş yapmışsa veritabanına da kaydet
            if 'user_id' in session:
                user = get_current_user()
                if user:
                    UserManager.update_user_consents(user['id'], {
                        'privacy_accepted': user.get('privacy_accepted', False),
                        'terms_accepted': user.get('terms_accepted', False),
                        'data_processing_consent': user.get('data_processing_consent', False),
                        'marketing_consent': user.get('marketing_consent', False),
                        'ai_data_consent': user.get('ai_data_consent', False),
                        'ai_data_retention_days': user.get('ai_data_retention_days', 30),
                        'cookie_consent': cookie_preferences
                    })
                    
                    log_user_activity("cookie_preferences_updated", 
                                    f"Cookie preferences updated: {cookie_preferences}")
            
            flash('Çerez tercihleriniz kaydedildi.' if lang == 'tr' 
                  else 'Your cookie preferences have been saved.', 'success')
            
            return redirect(request.referrer or url_for('home'))
            
        except Exception as e:
            logger.error(f"Cookie settings error: {e}")
            flash('Ayarlar kaydedilirken bir hata oluştu.' if lang == 'tr' 
                  else 'An error occurred while saving settings.', 'error')
            return redirect(request.url)
    
    # =============================================================================
    # AI Veri İşleme Onayı
    # =============================================================================
    @app.route('/ai-consent', methods=['GET', 'POST'])
    @app.route('/tr/ai-consent', methods=['GET', 'POST'])
    @app.route('/en/ai-consent', methods=['GET', 'POST'])
    @login_required
    def ai_consent_page():
        lang = 'en' if '/en/' in request.path else 'tr'
        user = get_current_user()
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            nonce = generate_nonce()  # Ekleyin
            return render_template(f'{lang}/ai_consent.html', 
                                lang=lang, csrf_token=csrf_token, nonce=nonce, user=user)
        
        try:
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                flash('Güvenlik hatası. Lütfen tekrar deneyin.' if lang == 'tr' 
                      else 'Security error. Please try again.', 'error')
                return redirect(request.url)
            
            # AI veri işleme onayları
            ai_data_consent = request.form.get('ai_data_consent') == 'on'
            ai_data_retention_days = int(request.form.get('ai_data_retention_days', 30))
            
            # Güncelle
            consents = {
                'privacy_accepted': user.get('privacy_accepted', False),
                'terms_accepted': user.get('terms_accepted', False),
                'data_processing_consent': user.get('data_processing_consent', False),
                'marketing_consent': user.get('marketing_consent', False),
                'ai_data_consent': ai_data_consent,
                'ai_data_retention_days': ai_data_retention_days,
                'cookie_consent': user.get('cookie_consent', {})
            }
            
            UserManager.update_user_consents(user['id'], consents)
            
            log_user_activity("ai_consent_updated", 
                            f"AI data consent: {ai_data_consent}, retention: {ai_data_retention_days} days")
            
            flash('AI veri işleme tercihleriniz güncellendi.' if lang == 'tr' 
                  else 'Your AI data processing preferences have been updated.', 'success')
            
            # Yönlendirme
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            return redirect(url_for('user_dashboard'))
            
        except Exception as e:
            logger.error(f"AI consent error: {e}")
            flash('Onaylar güncellenirken bir hata oluştu.' if lang == 'tr' 
                  else 'An error occurred while updating consents.', 'error')
            return redirect(request.url)
    
    # =============================================================================
    # Genel Onay Sayfası
    # =============================================================================
    @app.route('/consent', methods=['GET', 'POST'])
    @app.route('/tr/consent', methods=['GET', 'POST'])
    @app.route('/en/consent', methods=['GET', 'POST'])
    @login_required
    def consent_page():
        lang = 'en' if '/en/' in request.path else 'tr'
        user = get_current_user()
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            nonce = generate_nonce()  # Ekleyin
            return render_template(f'{lang}/consent.html', 
                                lang=lang, csrf_token=csrf_token, nonce=nonce, user=user)
        
        try:
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                flash('Güvenlik hatası. Lütfen tekrar deneyin.' if lang == 'tr' 
                      else 'Security error. Please try again.', 'error')
                return redirect(request.url)
            
            # Tüm onayları al
            privacy_accepted = request.form.get('privacy_accepted') == 'on'
            terms_accepted = request.form.get('terms_accepted') == 'on'
            data_processing_consent = request.form.get('data_processing_consent') == 'on'
            marketing_consent = request.form.get('marketing_consent') == 'on'
            ai_data_consent = request.form.get('ai_data_consent') == 'on'
            ai_data_retention_days = int(request.form.get('ai_data_retention_days', 30))
            
            # Çerez onayları
            cookie_consent = {
                'essential': True,
                'analytics': request.form.get('cookie_analytics') == 'on',
                'marketing': request.form.get('cookie_marketing') == 'on',
                'functional': request.form.get('cookie_functional') == 'on',
                'updated_at': datetime.now().isoformat()
            }
            
            # Zorunlu onayları kontrol et
            if not privacy_accepted or not terms_accepted:
                flash('Gizlilik politikası ve kullanım şartları kabul edilmelidir.' if lang == 'tr' 
                      else 'Privacy policy and terms of service must be accepted.', 'error')
                return redirect(request.url)
            
            # Güncelle
            consents = {
                'privacy_accepted': privacy_accepted,
                'terms_accepted': terms_accepted,
                'data_processing_consent': data_processing_consent,
                'marketing_consent': marketing_consent,
                'ai_data_consent': ai_data_consent,
                'ai_data_retention_days': ai_data_retention_days,
                'cookie_consent': cookie_consent
            }
            
            UserManager.update_user_consents(user['id'], consents)
            
            # Session'a da çerez tercihlerini kaydet
            session['cookie_preferences'] = cookie_consent
            session['cookie_consent_given'] = True
            
            log_user_activity("all_consents_updated", "All user consents updated")
            
            flash('Tüm tercihleriniz güncellendi.' if lang == 'tr' 
                  else 'All your preferences have been updated.', 'success')
            
            return redirect(url_for('user_dashboard'))
            
        except Exception as e:
            logger.error(f"Consent page error: {e}")
            flash('Tercihler güncellenirken bir hata oluştu.' if lang == 'tr' 
                  else 'An error occurred while updating preferences.', 'error')
            return redirect(request.url)
    
    # =============================================================================
    # GDPR Veri Talepleri
    # =============================================================================
    @app.route('/gdpr-request', methods=['GET', 'POST'])
    @app.route('/tr/gdpr-request', methods=['GET', 'POST'])
    @app.route('/en/gdpr-request', methods=['GET', 'POST'])
    def gdpr_request():
        lang = 'en' if '/en/' in request.path else 'tr'
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            nonce = generate_nonce()
            return render_template(f'{lang}/gdpr_request.html', 
                                lang=lang, csrf_token=csrf_token, nonce=nonce)

        
        try:
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                flash('Güvenlik hatası. Lütfen tekrar deneyin.' if lang == 'tr' 
                      else 'Security error. Please try again.', 'error')
                return redirect(request.url)
            
            email = validate_and_sanitize_input(request.form.get('email', ''), 100)
            request_type = request.form.get('request_type')  # access, delete, portability, rectification
            description = validate_and_sanitize_input(request.form.get('description', ''), 2000)
            
            if not email or not request_type:
                flash('Email ve talep türü zorunludur.' if lang == 'tr' 
                      else 'Email and request type are required.', 'error')
                return redirect(request.url)
            
            # GDPR talebini kaydet
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            # GDPR requests tablosu yoksa oluştur
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gdpr_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    request_type TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    ip_address TEXT,
                    user_agent TEXT
                )
            ''')
            
            cursor.execute('''
                INSERT INTO gdpr_requests 
                (email, request_type, description, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (email, request_type, description, 
                  request.remote_addr, request.headers.get('User-Agent', '')))
            
            conn.commit()
            conn.close()
            
            # Admin'e bildirim email'i gönder
            try:
                from flask_mail import Message
                from app import mail
                
                request_types = {
                    'access': 'Veri Erişim Talebi' if lang == 'tr' else 'Data Access Request',
                    'delete': 'Veri Silme Talebi' if lang == 'tr' else 'Data Deletion Request',
                    'portability': 'Veri Taşınabilirlik Talebi' if lang == 'tr' else 'Data Portability Request',
                    'rectification': 'Veri Düzeltme Talebi' if lang == 'tr' else 'Data Rectification Request'
                }
                
                subject = f'GDPR Talebi - {request_types.get(request_type, request_type)}'
                body = f"""
Yeni GDPR Talebi / New GDPR Request

Email: {email}
Talep Türü / Request Type: {request_types.get(request_type, request_type)}
IP: {request.remote_addr}
Zaman / Time: {datetime.now()}

Açıklama / Description:
{description}

Bu talep 30 gün içinde işlenmelidir.
This request must be processed within 30 days.
"""
                
                msg = Message(
                    subject=subject,
                    recipients=['privacy@bktyconsultancy.co.uk'],
                    body=body
                )
                mail.send(msg)
                
            except Exception as e:
                logger.error(f"GDPR request notification email error: {e}")
            
            log_user_activity("gdpr_request_submitted", 
                            f"GDPR request submitted: {request_type} for {email}")
            
            flash('GDPR talebiniz alındı. 30 gün içinde yanıtlanacaktır.' if lang == 'tr' 
                  else 'Your GDPR request has been received. It will be processed within 30 days.', 'success')
            
            return redirect(url_for('home'))
            
        except Exception as e:
            logger.error(f"GDPR request error: {e}")
            flash('Talep gönderilirken bir hata oluştu.' if lang == 'tr' 
                  else 'An error occurred while submitting the request.', 'error')
            return redirect(request.url)
    
    # =============================================================================
    # Email Tercih Merkezi
    # =============================================================================
    @app.route('/email-preferences', methods=['GET', 'POST'])
    @app.route('/tr/email-preferences', methods=['GET', 'POST'])
    @app.route('/en/email-preferences', methods=['GET', 'POST'])
    def email_preferences():
        lang = 'en' if '/en/' in request.path else 'tr'
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            email = request.args.get('email', '')
            
            # Email ile kullanıcı bilgilerini al
            user_prefs = None
            if email:
                conn = sqlite3.connect('bkty_consultancy.db')
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT marketing_consent, preferred_language 
                    FROM users WHERE email = ? AND is_active = TRUE
                ''', (email,))
                
                result = cursor.fetchone()
                if result:
                    user_prefs = {
                        'marketing_consent': result[0],
                        'preferred_language': result[1]
                    }
                
                conn.close()
            
            return render_template(f'{lang}/email_preferences.html', 
                                lang=lang, csrf_token=csrf_token,
                                email=email, user_prefs=user_prefs)
        
        try:
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                flash('Güvenlik hatası. Lütfen tekrar deneyin.' if lang == 'tr' 
                      else 'Security error. Please try again.', 'error')
                return redirect(request.url)
            
            email = validate_and_sanitize_input(request.form.get('email', ''), 100)
            marketing_consent = request.form.get('marketing_consent') == 'on'
            
            if not email:
                flash('Email adresi gereklidir.' if lang == 'tr' 
                      else 'Email address is required.', 'error')
                return redirect(request.url)
            
            # Email tercihlerini güncelle
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET marketing_consent = ? 
                WHERE email = ? AND is_active = TRUE
            ''', (marketing_consent, email))
            
            if cursor.rowcount > 0:
                conn.commit()
                
                log_user_activity("email_preferences_updated", 
                                f"Email preferences updated for {email}: marketing={marketing_consent}")
                
                flash('Email tercihleriniz güncellendi.' if lang == 'tr' 
                      else 'Your email preferences have been updated.', 'success')
            else:
                flash('Email adresi bulunamadı.' if lang == 'tr' 
                      else 'Email address not found.', 'error')
            
            conn.close()
            
            return redirect(request.url)
            
        except Exception as e:
            logger.error(f"Email preferences error: {e}")
            flash('Tercihler güncellenirken bir hata oluştu.' if lang == 'tr' 
                  else 'An error occurred while updating preferences.', 'error')
            return redirect(request.url)
    
    # =============================================================================
    # Cookie Banner API
    # =============================================================================
    @app.route('/api/cookie-consent', methods=['POST'])
    def api_cookie_consent():
        try:
            data = request.get_json() or {}
            
            cookie_preferences = {
                'essential': True,  # Her zaman zorunlu
                'analytics': data.get('analytics', False),
                'marketing': data.get('marketing', False),
                'functional': data.get('functional', False),
                'updated_at': datetime.now().isoformat()
            }
            
            # Session'a kaydet
            session['cookie_preferences'] = cookie_preferences
            session['cookie_consent_given'] = True
            
            # Kullanıcı giriş yapmışsa veritabanına da kaydet
            if 'user_id' in session:
                try:
                    user = get_current_user()
                    if user:
                        conn = sqlite3.connect('bkty_consultancy.db')
                        cursor = conn.cursor()
                        
                        import json
                        cursor.execute("""
                            UPDATE users 
                            SET cookie_consent = ?
                            WHERE id = ?
                        """, (json.dumps(cookie_preferences), user['id']))
                        
                        conn.commit()
                        conn.close()
                        
                except Exception as e:
                    logger.error(f"Cookie consent user update error: {e}")
            
            return jsonify({'success': True})
            
        except Exception as e:
            logger.error(f"Cookie consent API error: {e}")
            return jsonify({'success': False, 'error': 'Sunucu hatası'})
    
    # =============================================================================
    # Yasal Sayfalar İndex
    # =============================================================================
    @app.route('/legal')
    @app.route('/tr/legal')
    @app.route('/en/legal')
    def legal_index():
        lang = 'en' if '/en/' in request.path else 'tr'
        nonce = generate_nonce()
        session['csp_nonce'] = nonce
        
        return render_template(f'{lang}/legal_index.html', lang=lang, nonce=nonce)
    
    # =============================================================================
    # Veri İşleme Bildirimi
    # =============================================================================
    @app.route('/data-processing')
    @app.route('/tr/data-processing')
    @app.route('/en/data-processing')
    def data_processing():
        lang = 'en' if '/en/' in request.path else 'tr'
        nonce = generate_nonce()
        session['csp_nonce'] = nonce
        
        return render_template(f'{lang}/data_processing.html', lang=lang, nonce=nonce)
    
    # =============================================================================
    # Kullanıcı Hakları Bildirimi
    # =============================================================================
    @app.route('/user-rights')
    @app.route('/tr/user-rights')
    @app.route('/en/user-rights')
    def user_rights():
        lang = 'en' if '/en/' in request.path else 'tr'
        nonce = generate_nonce()
        session['csp_nonce'] = nonce
        
        return render_template(f'{lang}/user_rights.html', lang=lang, nonce=nonce)
    
    # =============================================================================
    # AI Kullanım Politikası
    # =============================================================================
    @app.route('/ai-policy')
    @app.route('/tr/ai-policy')
    @app.route('/en/ai-policy')
    def ai_policy():
        lang = 'en' if '/en/' in request.path else 'tr'
        nonce = generate_nonce()
        session['csp_nonce'] = nonce
        
        return render_template(f'{lang}/ai_policy.html', lang=lang, nonce=nonce)
    
    # =============================================================================
    # İletişim ve Şikayet
    # =============================================================================
    @app.route('/complaints', methods=['GET', 'POST'])
    @app.route('/tr/complaints', methods=['GET', 'POST'])
    @app.route('/en/complaints', methods=['GET', 'POST'])
    @limiter.limit("3 per minute")
    @security_check_decorator
    def complaints_page():
        lang = 'en' if '/en/' in request.path else 'tr'
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            nonce = generate_nonce()  # Bu satır eksik
            return render_template(f'{lang}/complaints.html', 
                             lang=lang, csrf_token=csrf_token, nonce=nonce)
        
        try:
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                flash('Güvenlik hatası. Lütfen tekrar deneyin.' if lang == 'tr' 
                      else 'Security error. Please try again.', 'error')
                return redirect(request.url)
            
            name = validate_and_sanitize_input(request.form.get('name', ''), 100)
            email = validate_and_sanitize_input(request.form.get('email', ''), 100)
            complaint_type = request.form.get('complaint_type')  # privacy, service, data, other
            subject = validate_and_sanitize_input(request.form.get('subject', ''), 200)
            message = validate_and_sanitize_input(request.form.get('message', ''), 2000)
            
            if not all([name, email, complaint_type, subject, message]):
                flash('Tüm alanları doldurun.' if lang == 'tr' 
                      else 'Please fill in all fields.', 'error')
                return redirect(request.url)
            
            # Şikayeti kaydet
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            # Complaints tablosu yoksa oluştur
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS complaints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    complaint_type TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'new',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    ip_address TEXT,
                    user_agent TEXT,
                    admin_response TEXT
                )
            ''')
            
            cursor.execute('''
                INSERT INTO complaints 
                (name, email, complaint_type, subject, message, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, complaint_type, subject, message,
                  request.remote_addr, request.headers.get('User-Agent', '')))
            
            complaint_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Admin'e bildirim
            try:
                from flask_mail import Message
                from app import mail
                
                complaint_types = {
                    'privacy': 'Gizlilik Şikayeti' if lang == 'tr' else 'Privacy Complaint',
                    'service': 'Hizmet Şikayeti' if lang == 'tr' else 'Service Complaint',
                    'data': 'Veri İşleme Şikayeti' if lang == 'tr' else 'Data Processing Complaint',
                    'other': 'Diğer Şikayet' if lang == 'tr' else 'Other Complaint'
                }
                
                subject_line = f'Şikayet #{complaint_id} - {complaint_types.get(complaint_type, complaint_type)}'
                body = f"""
Yeni Şikayet / New Complaint

ID: {complaint_id}
Ad / Name: {name}
Email: {email}
Tür / Type: {complaint_types.get(complaint_type, complaint_type)}
Konu / Subject: {subject}

Mesaj / Message:
{message}

IP: {request.remote_addr}
Zaman / Time: {datetime.now()}
"""
                
                msg = Message(
                    subject=subject_line,
                    recipients=['complaints@bktyconsultancy.co.uk'],
                    body=body
                )
                mail.send(msg)
                
            except Exception as e:
                logger.error(f"Complaint notification email error: {e}")
            
            log_user_activity("complaint_submitted", 
                            f"Complaint submitted: #{complaint_id} by {email}")
            
            flash(f'Şikayetiniz alındı. (Referans: #{complaint_id})' if lang == 'tr' 
                  else f'Your complaint has been received. (Reference: #{complaint_id})', 'success')
            
            return redirect(url_for('home'))
            
        except Exception as e:
            logger.error(f"Complaint submission error: {e}")
            flash('Şikayet gönderilirken bir hata oluştu.' if lang == 'tr' 
                  else 'An error occurred while submitting the complaint.', 'error')
            return redirect(request.url)
    # =============================================================================
    # API Endpoint'leri (Fonksiyon içinde tanımlanmalı)
    # =============================================================================
    
    @app.route('/api/submit-gdpr-request', methods=['POST'])
    @limiter.limit("3 per hour")
    def api_submit_gdpr_request():
        try:
            request_type = request.form.get('request_type')
            request_details = validate_and_sanitize_input(request.form.get('request_details', ''), 2000)
            identity_verification = validate_and_sanitize_input(request.form.get('identity_verification', ''), 500)
            
            # Referans numarası üret
            import uuid
            request_id = f"GDPR-{str(uuid.uuid4())[:8].upper()}"
            
            # Email adresi - kullanıcı giriş yapmışsa
            email = None
            user_id = None
            if 'user_id' in session:
                user = get_current_user()
                if user:
                    email = user['email']
                    user_id = user['id']
            
            if not email:
                email = validate_and_sanitize_input(request.form.get('email', ''), 100)
            
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            # GDPR requests tablosunu oluştur (yoksa)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gdpr_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    email TEXT NOT NULL,
                    request_id TEXT UNIQUE NOT NULL,
                    request_type TEXT NOT NULL,
                    request_details TEXT,
                    identity_verification TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            cursor.execute('''
                INSERT INTO gdpr_requests 
                (user_id, email, request_id, request_type, request_details, 
                 identity_verification, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, email, request_id, request_type, request_details,
                  identity_verification, request.remote_addr, 
                  request.headers.get('User-Agent', '')))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'request_id': request_id,
                'message': 'GDPR talebi başarıyla gönderildi'
            })
            
        except Exception as e:
            logger.error(f"GDPR request API error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/submit-complaint', methods=['POST'])
    @limiter.limit("5 per hour")
    def api_submit_complaint():
        try:
            complaint_type = request.form.get('complaint_type')
            subject = validate_and_sanitize_input(request.form.get('subject', ''), 200)
            message = validate_and_sanitize_input(request.form.get('message', ''), 2000)
            contact_info = validate_and_sanitize_input(request.form.get('contact_info', ''), 100)
            
            # Ticket ID üret
            import uuid
            ticket_id = f"CMP-{str(uuid.uuid4())[:8].upper()}"
            
            # Kullanıcı bilgileri
            user_id = None
            if 'user_id' in session:
                user = get_current_user()
                if user:
                    user_id = user['id']
            
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            # Complaints tablosunu oluştur (yoksa)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS complaints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    ticket_id TEXT UNIQUE NOT NULL,
                    complaint_type TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    message TEXT NOT NULL,
                    contact_info TEXT,
                    status TEXT DEFAULT 'new',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TIMESTAMP,
                    ip_address TEXT,
                    user_agent TEXT,
                    admin_response TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            cursor.execute('''
                INSERT INTO complaints 
                (user_id, ticket_id, complaint_type, subject, message, 
                 contact_info, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, ticket_id, complaint_type, subject, message,
                  contact_info, request.remote_addr, 
                  request.headers.get('User-Agent', '')))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'ticket_id': ticket_id,
                'message': 'Şikayet başarıyla gönderildi'
            })
            
        except Exception as e:
            logger.error(f"Complaint API error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500