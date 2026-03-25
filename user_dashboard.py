# user_dashboard.py - Kullanıcı paneli ve profil yönetimi

from flask import request, render_template, redirect, url_for, flash, session, jsonify, send_file
from auth_helpers import login_required, verified_required, get_current_user, log_user_activity
from database import UserManager
import sqlite3
import json
import csv
import io
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def get_user_template_path(template_name, lang):
    """User template path'ini dil bazında döndürür"""
    if lang == 'en':
        return f'en/user/{template_name}'
    else:
        return f'user/{template_name}'

def register_user_routes(app, limiter, security_check_decorator, 
                        validate_and_sanitize_input, validate_email,
                        generate_csrf_token, verify_csrf_token, generate_nonce):
    """Kullanıcı dashboard route'larını kaydet"""
    
    # =============================================================================
    # Ana Dashboard
    # =============================================================================
    @app.route('/dashboard')
    @app.route('/tr/dashboard') 
    @app.route('/en/dashboard')
    @login_required
    def user_dashboard():
        lang = 'en' if '/en/' in request.path else 'tr'
        nonce = generate_nonce()
        session['csp_nonce'] = nonce
        
        user = get_current_user()
        
        # Kullanıcı istatistikleri
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        # AI sohbet sayısı
        cursor.execute('''
            SELECT COUNT(*) FROM ai_chat_history 
            WHERE user_id = ? AND is_deleted = FALSE
        ''', (user['id'],))
        chat_count = cursor.fetchone()[0]
        
        # Son sohbetler
        cursor.execute('''
            SELECT question, response, model_used, created_at, response_time
            FROM ai_chat_history 
            WHERE user_id = ? AND is_deleted = FALSE
            ORDER BY created_at DESC
            LIMIT 5
        ''', (user['id'],))
        recent_chats = cursor.fetchall()
        
        # Hata raporları
        cursor.execute('''
            SELECT COUNT(*) FROM error_reports 
            WHERE user_id = ? AND status != 'closed'
        ''', (user['id'],))
        open_reports = cursor.fetchone()[0]
        
        conn.close()
        
        stats = {
            'chat_count': chat_count,
            'recent_chats': recent_chats,
            'open_reports': open_reports,
            'member_since': user['created_at']
        }
        
        template_path = get_user_template_path('dashboard.html', lang)
        return render_template(template_path, user=user, stats=stats, nonce=nonce)
    
    # =============================================================================
    # Profil Yönetimi
    # =============================================================================
    @app.route('/profile', methods=['GET', 'POST'])
    @app.route('/tr/profile', methods=['GET', 'POST'])
    @app.route('/en/profile', methods=['GET', 'POST'])
    @login_required
    def user_profile():
        lang = 'en' if '/en/' in request.path else 'tr'
        user = get_current_user()
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            template_path = get_user_template_path('profile.html', lang)
            return render_template(template_path, user=user, csrf_token=csrf_token)
        
        try:
            # CSRF kontrolü
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                error_msg = 'Security error. Please try again.' if lang == 'en' else 'Güvenlik hatası. Lütfen tekrar deneyin.'
                flash(error_msg, 'error')
                return redirect(request.url)
            
            # Form verilerini al
            first_name = validate_and_sanitize_input(request.form.get('first_name', ''), 50)
            last_name = validate_and_sanitize_input(request.form.get('last_name', ''), 50)
            company = validate_and_sanitize_input(request.form.get('company', ''), 100)
            phone = validate_and_sanitize_input(request.form.get('phone', ''), 20)
            preferred_language = request.form.get('preferred_language', 'tr')
            
            if not first_name or not last_name:
                error_msg = 'First name and last name are required.' if lang == 'en' else 'Ad ve soyad zorunludur.'
                flash(error_msg, 'error')
                return redirect(request.url)
            
            # Profil güncelle
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET 
                    first_name = ?, last_name = ?, company = ?, 
                    phone = ?, preferred_language = ?
                WHERE id = ?
            ''', (first_name, last_name, company, phone, preferred_language, user['id']))
            
            conn.commit()
            conn.close()
            
            log_user_activity("profile_updated", f"User profile information updated (lang: {lang})")
            success_msg = 'Profile updated successfully.' if lang == 'en' else 'Profil bilgileriniz güncellendi.'
            flash(success_msg, 'success')
            
            return redirect(url_for('user_profile'))
            
        except Exception as e:
            logger.error(f"Profile update error: {e}")
            error_msg = 'An error occurred while updating profile.' if lang == 'en' else 'Profil güncellenirken bir hata oluştu.'
            flash(error_msg, 'error')
            return redirect(request.url)
    
    # =============================================================================
    # Şifre Değiştirme
    # =============================================================================
    @app.route('/change-password', methods=['GET', 'POST'])
    @app.route('/tr/change-password', methods=['GET', 'POST'])
    @app.route('/en/change-password', methods=['GET', 'POST'])
    @login_required
    def change_password():
        lang = 'en' if '/en/' in request.path else 'tr'
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            template_path = get_user_template_path('change_password.html', lang)
            return render_template(template_path, csrf_token=csrf_token)
        
        try:
            from auth_helpers import validate_password_strength
            from werkzeug.security import check_password_hash, generate_password_hash
            
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                error_msg = 'Security error. Please try again.' if lang == 'en' else 'Güvenlik hatası. Lütfen tekrar deneyin.'
                flash(error_msg, 'error')
                return redirect(request.url)
            
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if not all([current_password, new_password, confirm_password]):
                error_msg = 'Please fill in all fields.' if lang == 'en' else 'Tüm alanları doldurun.'
                flash(error_msg, 'error')
                return redirect(request.url)
            
            if new_password != confirm_password:
                error_msg = 'New passwords do not match.' if lang == 'en' else 'Yeni şifreler eşleşmiyor.'
                flash(error_msg, 'error')
                return redirect(request.url)
            
            # Mevcut şifre kontrolü
            user = get_current_user()
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user['id'],))
            stored_hash = cursor.fetchone()[0]
            
            if not check_password_hash(stored_hash, current_password):
                error_msg = 'Current password is incorrect.' if lang == 'en' else 'Mevcut şifre yanlış.'
                flash(error_msg, 'error')
                conn.close()
                return redirect(request.url)
            
            # Yeni şifre güçlülük kontrolü
            is_strong, password_errors = validate_password_strength(new_password)
            if not is_strong:
                for error in password_errors:
                    flash(error, 'error')
                conn.close()
                return redirect(request.url)
            
            # Şifreyi güncelle
            new_hash = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', 
                        (new_hash, user['id']))
            
            conn.commit()
            conn.close()
            
            log_user_activity("password_changed", f"User changed password (lang: {lang})")
            
            success_msg = 'Your password has been successfully changed.' if lang == 'en' else 'Şifreniz başarıyla değiştirildi.'
            flash(success_msg, 'success')
            
            return redirect(url_for('user_profile'))
            
        except Exception as e:
            logger.error(f"Change password error: {e}")
            error_msg = 'An error occurred while changing password.' if lang == 'en' else 'Şifre değiştirirken bir hata oluştu.'
            flash(error_msg, 'error')
            return redirect(request.url)
    
    # =============================================================================
    # Gizlilik ve Onay Ayarları
    # =============================================================================
    @app.route('/privacy-settings', methods=['GET', 'POST'])
    @app.route('/tr/privacy-settings', methods=['GET', 'POST'])
    @app.route('/en/privacy-settings', methods=['GET', 'POST'])
    @login_required
    def privacy_settings():
        lang = 'en' if '/en/' in request.path else 'tr'
        user = get_current_user()
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            template_path = get_user_template_path('privacy_settings.html', lang)
            return render_template(template_path, user=user, csrf_token=csrf_token)
        
        # POST request handling
        try:
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                error_msg = 'Security error. Please try again.' if lang == 'en' else 'Güvenlik hatası. Lütfen tekrar deneyin.'
                flash(error_msg, 'error')
                return redirect(request.url)
            
            # Form verilerini al
            data_processing_consent = request.form.get('data_processing_consent') == 'on'
            marketing_consent = request.form.get('marketing_consent') == 'on'
            ai_data_consent = request.form.get('ai_data_consent') == 'on'
            ai_data_retention_days = int(request.form.get('ai_data_retention_days', 30))
            
            # Çerez ayarları (eğer form'da varsa)
            cookie_settings = {
                'essential': True,  # Her zaman true
                'analytics': request.form.get('cookie_analytics') == 'on',
                'marketing': request.form.get('cookie_marketing') == 'on',
                'functional': request.form.get('cookie_functional') == 'on'
            }
            
            # Consent verilerini hazırla
            consents = {
                'privacy_accepted': user.get('privacy_accepted', True),
                'terms_accepted': user.get('terms_accepted', True),
                'data_processing_consent': data_processing_consent,
                'marketing_consent': marketing_consent,
                'ai_data_consent': ai_data_consent,
                'ai_data_retention_days': ai_data_retention_days,
                'cookie_consent': cookie_settings
            }
            
            # Veritabanını güncelle
            UserManager.update_user_consents(user['id'], consents)
            
            # Activity log
            log_user_activity("privacy_settings_updated", f"Updated privacy settings (lang: {lang})")
            
            # Başarı mesajını dile göre ayarla
            success_msg = 'Your privacy settings have been updated.' if lang == 'en' else 'Gizlilik ayarlarınız güncellendi.'
            flash(success_msg, 'success')
            
            return redirect(url_for('privacy_settings'))
            
        except Exception as e:
            logger.error(f"Privacy settings error: {e}")
            
            # Hata mesajını dile göre ayarla
            error_msg = 'An error occurred while updating settings.' if lang == 'en' else 'Ayarlar güncellenirken bir hata oluştu.'
            flash(error_msg, 'error')
            return redirect(request.url)
    
    # =============================================================================
    # AI Sohbet Geçmişi
    # =============================================================================
    @app.route('/chat-history')
    @app.route('/tr/chat-history')
    @app.route('/en/chat-history')
    @login_required
    @verified_required
    def chat_history():
        lang = 'en' if '/en/' in request.path else 'tr'
        user = get_current_user()
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        # Toplam sayı
        cursor.execute('''
            SELECT COUNT(*) FROM ai_chat_history 
            WHERE user_id = ? AND is_deleted = FALSE
        ''', (user['id'],))
        total = cursor.fetchone()[0]
        
        # Sayfalı veri
        offset = (page - 1) * per_page
        cursor.execute('''
            SELECT id, question, response, model_used, created_at, response_time
            FROM ai_chat_history 
            WHERE user_id = ? AND is_deleted = FALSE
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (user['id'], per_page, offset))
        
        chats = cursor.fetchall()
        conn.close()
        
        # Sayfalama bilgileri
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
        
        template_path = get_user_template_path('chat_history.html', lang)
        return render_template(template_path, chats=chats, pagination=pagination)
    
    # =============================================================================
    # Sohbet Silme
    # =============================================================================
    @app.route('/delete-chat/<int:chat_id>', methods=['POST'])
    @login_required
    def delete_chat(chat_id):
        try:
            user = get_current_user()
            
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            # Kullanıcının sohbeti olduğunu kontrol et
            cursor.execute('''
                UPDATE ai_chat_history SET is_deleted = TRUE 
                WHERE id = ? AND user_id = ?
            ''', (chat_id, user['id']))
            
            if cursor.rowcount > 0:
                conn.commit()
                log_user_activity("chat_deleted", f"Deleted chat ID: {chat_id}")
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Chat not found'})
            
        except Exception as e:
            logger.error(f"Delete chat error: {e}")
            return jsonify({'success': False, 'error': 'Server error'})
        finally:
            conn.close()
    
    # =============================================================================
    # Veri İndirme (GDPR)
    # =============================================================================
    @app.route('/download-data')
    @app.route('/tr/download-data')
    @app.route('/en/download-data')
    @login_required
    def download_data():
        lang = 'en' if '/en/' in request.path else 'tr'
        try:
            user = get_current_user()
            
            if not user['data_processing_consent']:
                error_msg = 'Data processing consent is required for data download.' if lang == 'en' else 'Veri indirme için veri işleme onayı gereklidir.'
                flash(error_msg, 'error')
                return redirect(url_for('privacy_settings'))
            
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            # Kullanıcı verileri
            user_data = {
                'profile': {
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'company': user['company'],
                    'phone': user['phone'],
                    'created_at': user['created_at'],
                    'preferred_language': user['preferred_language']
                }
            }
            
            # AI sohbet geçmişi
            if user['ai_data_consent']:
                cursor.execute('''
                    SELECT question, response, model_used, created_at, response_time
                    FROM ai_chat_history 
                    WHERE user_id = ? AND is_deleted = FALSE
                    ORDER BY created_at DESC
                ''', (user['id'],))
                
                chats = cursor.fetchall()
                user_data['ai_chat_history'] = [
                    {
                        'question': chat[0],
                        'response': chat[1],
                        'model_used': chat[2],
                        'created_at': chat[3],
                        'response_time': chat[4]
                    } for chat in chats
                ]
            
            # Hata raporları
            cursor.execute('''
                SELECT error_type, description, page_url, created_at, status
                FROM error_reports 
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user['id'],))
            
            reports = cursor.fetchall()
            user_data['error_reports'] = [
                {
                    'error_type': report[0],
                    'description': report[1],
                    'page_url': report[2],
                    'created_at': report[3],
                    'status': report[4]
                } for report in reports
            ]
            
            # Sistem logları
            cursor.execute('''
                SELECT action, details, created_at
                FROM system_logs 
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user['id'],))
            
            logs = cursor.fetchall()
            user_data['activity_logs'] = [
                {
                    'action': log[0],
                    'details': log[1],
                    'created_at': log[2]
                } for log in logs
            ]
            
            conn.close()
            
            # JSON dosyası oluştur
            json_data = json.dumps(user_data, indent=2, ensure_ascii=False)
            
            # BytesIO'ya çevir
            bytes_output = io.BytesIO()
            bytes_output.write(json_data.encode('utf-8'))
            bytes_output.seek(0)
            
            log_user_activity("data_download", f"User downloaded personal data (lang: {lang})")
            
            return send_file(
                bytes_output,
                as_attachment=True,
                download_name=f'bkty_data_{user["id"]}_{datetime.now().strftime("%Y%m%d")}.json',
                mimetype='application/json'
            )
            
        except Exception as e:
            logger.error(f"Data download error: {e}")
            error_msg = 'An error occurred during data download.' if lang == 'en' else 'Veri indirme sırasında bir hata oluştu.'
            flash(error_msg, 'error')
            return redirect(url_for('user_dashboard'))
    
    # =============================================================================
    # Hesap Silme Talebi
    # =============================================================================
    @app.route('/delete-account', methods=['GET', 'POST'])
    @app.route('/tr/delete-account', methods=['GET', 'POST'])
    @app.route('/en/delete-account', methods=['GET', 'POST'])
    @login_required
    def delete_account():
        lang = 'en' if '/en/' in request.path else 'tr'
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            template_path = get_user_template_path('delete_account.html', lang)
            return render_template(template_path, csrf_token=csrf_token)
        
        try:
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                error_msg = 'Security error. Please try again.' if lang == 'en' else 'Güvenlik hatası. Lütfen tekrar deneyin.'
                flash(error_msg, 'error')
                return redirect(request.url)
            
            password = request.form.get('password', '')
            confirmation = request.form.get('confirmation', '')
            
            expected_confirmation = 'DELETE MY ACCOUNT' if lang == 'en' else 'HESABIMI SIL'
            if confirmation != expected_confirmation:
                error_msg = f'Deletion confirmation is incorrect. You must type "{expected_confirmation}".' if lang == 'en' else f'Silme onayı yanlış. "{expected_confirmation}" yazmalısınız.'
                flash(error_msg, 'error')
                return redirect(request.url)
            
            # Şifre kontrolü
            from werkzeug.security import check_password_hash
            user = get_current_user()
            
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user['id'],))
            stored_hash = cursor.fetchone()[0]
            
            if not check_password_hash(stored_hash, password):
                error_msg = 'Password is incorrect.' if lang == 'en' else 'Şifre yanlış.'
                flash(error_msg, 'error')
                conn.close()
                return redirect(request.url)
            
            # Hesabı deaktive et (GDPR uyumlu)
            cursor.execute('''
                UPDATE users SET 
                    is_active = FALSE,
                    email = 'deleted_' || id || '@deleted.local',
                    first_name = 'Deleted',
                    last_name = 'User',
                    company = NULL,
                    phone = NULL,
                    verification_token = NULL,
                    reset_token = NULL
                WHERE id = ?
            ''', (user['id'],))
            
            # AI sohbet verilerini anonimleştir
            cursor.execute('''
                UPDATE ai_chat_history SET is_deleted = TRUE 
                WHERE user_id = ?
            ''', (user['id'],))
            
            # Oturumları sonlandır
            cursor.execute('''
                UPDATE user_sessions SET is_active = FALSE 
                WHERE user_id = ?
            ''', (user['id'],))
            
            conn.commit()
            conn.close()
            
            log_user_activity("account_deleted", f"User account deleted/deactivated (lang: {lang})")
            
            # Oturumu temizle
            session.clear()
            
            success_msg = 'Your account has been successfully deleted.' if lang == 'en' else 'Hesabınız başarıyla silindi.'
            flash(success_msg, 'success')
            return redirect(url_for('home'))
            
        except Exception as e:
            logger.error(f"Account deletion error: {e}")
            error_msg = 'An error occurred during account deletion.' if lang == 'en' else 'Hesap silme sırasında bir hata oluştu.'
            flash(error_msg, 'error')
            return redirect(request.url)
    
    # =============================================================================
    # Hata Bildirimi
    # =============================================================================
    @app.route('/report-error', methods=['GET', 'POST'])
    @app.route('/tr/report-error', methods=['GET', 'POST'])
    @app.route('/en/report-error', methods=['GET', 'POST'])
    @login_required
    def report_error():
        lang = 'en' if '/en/' in request.path else 'tr'
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            template_path = get_user_template_path('report_error.html', lang)
            return render_template(template_path, csrf_token=csrf_token)
        
        try:
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                error_msg = 'Security error. Please try again.' if lang == 'en' else 'Güvenlik hatası. Lütfen tekrar deneyin.'
                flash(error_msg, 'error')
                return redirect(request.url)
            
            error_type = validate_and_sanitize_input(request.form.get('error_type', ''), 50)
            description = validate_and_sanitize_input(request.form.get('description', ''), 2000)
            page_url = validate_and_sanitize_input(request.form.get('page_url', ''), 500)
            
            if not error_type or not description:
                error_msg = 'Error type and description are required.' if lang == 'en' else 'Hata türü ve açıklama zorunludur.'
                flash(error_msg, 'error')
                return redirect(request.url)
            
            user = get_current_user()
            
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO error_reports 
                (user_id, error_type, description, page_url, user_agent, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user['id'], error_type, description, page_url,
                request.headers.get('User-Agent', ''),
                request.remote_addr
            ))
            
            report_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            log_user_activity("error_reported", f"Error report submitted: ID {report_id} (lang: {lang})")
            
            success_msg = 'Error report submitted. Thank you!' if lang == 'en' else 'Hata raporu gönderildi. Teşekkür ederiz!'
            flash(success_msg, 'success')
            return redirect(url_for('user_dashboard'))
            
        except Exception as e:
            logger.error(f"Error report submission error: {e}")
            error_msg = 'An error occurred while submitting the report.' if lang == 'en' else 'Hata raporu gönderilirken bir hata oluştu.'
            flash(error_msg, 'error')
            return redirect(request.url)
    
    # =============================================================================
    # Bildirimler
    # =============================================================================
    @app.route('/notifications')
    @app.route('/tr/notifications')
    @app.route('/en/notifications')
    @login_required
    def notifications():
        lang = 'en' if '/en/' in request.path else 'tr'
        user = get_current_user()
        
        # Örnek bildirimler - gerçek sistemde veritabanından gelecek
        notifications_list = [
            {
                'id': 1,
                'type': 'info',
                'title': 'Welcome!' if lang == 'en' else 'Hoş Geldiniz!',
                'message': 'Welcome to BKTY Consultancy platform.' if lang == 'en' else 'BKTY Consultancy platformuna hoş geldiniz.',
                'created_at': datetime.now() - timedelta(days=1),
                'is_read': False
            }
        ]
        
        # Email doğrulaması kontrolü
        if not user['is_verified']:
            notifications_list.append({
                'id': 2,
                'type': 'warning',
                'title': 'Email Verification' if lang == 'en' else 'Email Doğrulama',
                'message': 'Don\'t forget to verify your email address.' if lang == 'en' else 'Email adresinizi doğrulamayı unutmayın.',
                'created_at': datetime.now(),
                'is_read': False
            })
        
        template_path = get_user_template_path('notifications.html', lang)
        return render_template(template_path, notifications=notifications_list)
    
    # =============================================================================
    # API Anahtarları (Gelecek özellik)
    # =============================================================================
    @app.route('/api-keys')
    @app.route('/tr/api-keys')
    @app.route('/en/api-keys')
    @login_required
    @verified_required
    def api_keys():
        lang = 'en' if '/en/' in request.path else 'tr'
        user = get_current_user()
        
        # API anahtarları (şimdilik boş)
        api_keys = []
        
        template_path = get_user_template_path('api_keys.html', lang)
        return render_template(template_path, api_keys=api_keys, user=user)
    
    # =============================================================================
    # Kullanım İstatistikleri
    # =============================================================================
    @app.route('/usage-stats')
    @app.route('/tr/usage-stats')
    @app.route('/en/usage-stats')
    @login_required
    def usage_stats():
        lang = 'en' if '/en/' in request.path else 'tr'
        user = get_current_user()
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        # Aylık kullanım
        cursor.execute('''
            SELECT 
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as chat_count,
                AVG(response_time) as avg_response_time
            FROM ai_chat_history 
            WHERE user_id = ? AND is_deleted = FALSE
            GROUP BY strftime('%Y-%m', created_at)
            ORDER BY month DESC
            LIMIT 12
        ''', (user['id'],))
        
        monthly_stats = cursor.fetchall()
        
        # Model kullanım istatistikleri
        cursor.execute('''
            SELECT 
                model_used,
                COUNT(*) as usage_count,
                AVG(response_time) as avg_response_time
            FROM ai_chat_history 
            WHERE user_id = ? AND is_deleted = FALSE AND model_used IS NOT NULL
            GROUP BY model_used
            ORDER BY usage_count DESC
        ''', (user['id'],))
        
        model_stats = cursor.fetchall()
        
        conn.close()
        
        stats = {
            'monthly': monthly_stats,
            'models': model_stats
        }
        
        template_path = get_user_template_path('usage_stats.html', lang)
        return render_template(template_path, stats=stats, user=user)

    # =============================================================================
    # API Endpoint'leri
    # =============================================================================

    @app.route('/api/submit-error-report', methods=['POST'])
    @login_required
    @limiter.limit("5 per hour")
    def api_submit_error_report():
        try:
            user = get_current_user()
            
            # Form verilerini al
            error_category = request.form.get('error_category', '')
            error_title = validate_and_sanitize_input(request.form.get('error_title', ''), 200)
            error_description = validate_and_sanitize_input(request.form.get('error_description', ''), 2000)
            priority = request.form.get('priority', 'medium')
            browser_info = validate_and_sanitize_input(request.form.get('browser_info', ''), 100)
            error_url = validate_and_sanitize_input(request.form.get('error_url', ''), 500)
            
            # Ticket ID üret
            import uuid
            ticket_id = f"ERR-{str(uuid.uuid4())[:8].upper()}"
            
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO error_reports 
                (user_id, ticket_id, error_category, error_title, description, priority, 
                browser_info, error_url, status, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
            ''', (user['id'], ticket_id, error_category, error_title, 
                error_description, priority, browser_info, error_url,
                request.remote_addr, request.headers.get('User-Agent', '')))
            
            conn.commit()
            conn.close()
            
            log_user_activity("error_report_submitted", f"Error report: {ticket_id}")
            
            return jsonify({
                'success': True,
                'ticket_id': ticket_id,
                'message': 'Error report submitted successfully'
            })
            
        except Exception as e:
            logger.error(f"API error report submission: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/update-email-preferences', methods=['POST'])
    @login_required
    def api_update_email_preferences():
        try:
            user = get_current_user()
            
            preferences = {
                'system_notifications': request.form.get('system_notifications') == '1',
                'newsletter': request.form.get('newsletter') == '1',
                'marketing_emails': request.form.get('marketing_emails') == '1',
                'ai_notifications': request.form.get('ai_notifications') == '1',
                'weekly_report': request.form.get('weekly_report') == '1'
            }
            
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO email_preferences 
                (user_id, system_notifications, newsletter, marketing_emails, 
                ai_notifications, weekly_report, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (user['id'], preferences['system_notifications'], 
                preferences['newsletter'], preferences['marketing_emails'],
                preferences['ai_notifications'], preferences['weekly_report']))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True})
            
        except Exception as e:
            logger.error(f"Email preferences update error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # =============================================================================
    # Email Preferences
    # =============================================================================
    @app.route('/email-preferences', methods=['GET', 'POST'])
    @app.route('/tr/email-preferences', methods=['GET', 'POST'])
    @app.route('/en/email-preferences', methods=['GET', 'POST'])
    @login_required
    def user_email_preferences():
        lang = 'en' if '/en/' in request.path else 'tr'
        user = get_current_user()
        
        if request.method == 'GET':
            csrf_token = generate_csrf_token()
            
            # Mevcut tercihleri getir
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM email_preferences WHERE user_id = ?
            ''', (user['id'],))
            
            prefs = cursor.fetchone()
            conn.close()
            
            # Default değerler
            if not prefs:
                prefs = {
                    'system_notifications': True,
                    'newsletter': False,
                    'marketing_emails': False,
                    'ai_notifications': False,
                    'weekly_report': False
                }
            else:
                prefs = {
                    'system_notifications': bool(prefs[2]),
                    'newsletter': bool(prefs[3]),
                    'marketing_emails': bool(prefs[4]),
                    'ai_notifications': bool(prefs[5]),
                    'weekly_report': bool(prefs[6])
                }
            
            template_path = get_user_template_path('email_preferences.html', lang)
            return render_template(template_path, user=user, preferences=prefs, csrf_token=csrf_token)
        
        # POST işlemi
        try:
            csrf_token = request.form.get('csrf_token', '')
            if not verify_csrf_token(csrf_token):
                error_msg = 'Security error. Please try again.' if lang == 'en' else 'Güvenlik hatası. Lütfen tekrar deneyin.'
                flash(error_msg, 'error')
                return redirect(request.url)
            
            # Form verilerini al
            preferences = {
                'system_notifications': request.form.get('system_notifications') == 'on',
                'newsletter': request.form.get('newsletter') == 'on',
                'marketing_emails': request.form.get('marketing_emails') == 'on',
                'ai_notifications': request.form.get('ai_notifications') == 'on',
                'weekly_report': request.form.get('weekly_report') == 'on'
            }
            
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO email_preferences 
                (user_id, system_notifications, newsletter, marketing_emails, 
                ai_notifications, weekly_report, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (user['id'], preferences['system_notifications'], 
                preferences['newsletter'], preferences['marketing_emails'],
                preferences['ai_notifications'], preferences['weekly_report']))
            
            conn.commit()
            conn.close()
            
            log_user_activity("email_preferences_updated", f"Updated email preferences (lang: {lang})")
            
            success_msg = 'Email preferences updated successfully.' if lang == 'en' else 'Email tercihleri başarıyla güncellendi.'
            flash(success_msg, 'success')
            
            return redirect(url_for('user_email_preferences'))
            
        except Exception as e:
            logger.error(f"Email preferences update error: {e}")
            error_msg = 'An error occurred while updating preferences.' if lang == 'en' else 'Tercihler güncellenirken bir hata oluştu.'
            flash(error_msg, 'error')
            return redirect(request.url)