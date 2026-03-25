# admin_dashboard.py - COMPLETE VERSION - Tüm Fonksiyonlar Dahil

from flask import request, render_template, redirect, url_for, flash, session, jsonify
from auth_helpers import admin_required, get_current_user, log_user_activity
from database import UserManager
import sqlite3
import json
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def get_admin_template_path(template_name, lang):
    """Admin template path helper"""
    return f'admin/{template_name}'

def register_admin_routes(app, limiter, security_check_decorator, 
                         validate_and_sanitize_input, validate_email,
                         generate_csrf_token, verify_csrf_token, generate_nonce):
    """Complete admin dashboard routes with all features"""
    
    # =============================================================================
    # ADMIN DASHBOARD ANA SAYFA - ENHANCED
    # =============================================================================
    @app.route('/admin')
    @app.route('/admin/dashboard')
    @app.route('/en/admin/dashboard')
    @app.route('/tr/admin/dashboard')
    @admin_required
    def admin_dashboard():
        nonce = generate_nonce()
        lang = 'en' if '/en/' in request.path else 'tr'
        session['csp_nonce'] = nonce
        csrf_token = generate_csrf_token()
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        # Genel istatistikler
        stats = {}
        
        # Kullanıcı sayıları
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        stats['total_users'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_verified = 1 AND is_active = 1')
        stats['verified_users'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE created_at >= date("now", "-30 days")')
        stats['new_users_month'] = cursor.fetchone()[0]
        
        # AI kullanım istatistikleri (tablolar varsa)
        try:
            cursor.execute('SELECT COUNT(*) FROM ai_chat_history WHERE created_at >= date("now", "-1 day")')
            stats['chats_today'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM ai_chat_history WHERE created_at >= date("now", "-7 days")')
            stats['chats_week'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT AVG(response_time) FROM ai_chat_history WHERE created_at >= date("now", "-1 day")')
            avg_response = cursor.fetchone()[0]
            stats['avg_response_time'] = round(avg_response, 2) if avg_response else 0
        except sqlite3.OperationalError:
            stats['chats_today'] = 0
            stats['chats_week'] = 0
            stats['avg_response_time'] = 0
        
        # Hata raporları (tablolar varsa)
        try:
            cursor.execute('SELECT COUNT(*) FROM error_reports WHERE status = "open"')
            stats['open_reports'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM error_reports WHERE created_at >= date("now", "-1 day")')
            stats['reports_today'] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            stats['open_reports'] = 0
            stats['reports_today'] = 0
        
        # İletişim formları (tablolar varsa)
        try:
            cursor.execute('SELECT COUNT(*) FROM contact_submissions WHERE status = "new"')
            stats['new_contacts'] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            stats['new_contacts'] = 0
        
        # Son aktiviteler (tablolar varsa)
        try:
            cursor.execute('''
                SELECT u.first_name, u.last_name, ua.action, ua.created_at
                FROM user_activities ua
                LEFT JOIN users u ON ua.user_id = u.id
                ORDER BY ua.created_at DESC
                LIMIT 10
            ''')
            recent_activities = cursor.fetchall()
        except sqlite3.OperationalError:
            recent_activities = []
        
        conn.close()
        
        stats['recent_activities'] = recent_activities
        
        template_path = get_admin_template_path('dashboard.html', lang)
        return render_template(template_path,
                            stats=stats,
                            csrf_token=csrf_token,
                            nonce=nonce,
                            lang=lang)
    
    # =============================================================================
    # KULLANICI LİSTESİ - ENHANCED
    # =============================================================================
    @app.route('/admin/users')
    @app.route('/en/admin/users')
    @app.route('/tr/admin/users')
    @admin_required
    def admin_users():
        lang = 'en' if '/en/' in request.path else 'tr'
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '').strip()
        status_filter = request.args.get('status', 'all')
        per_page = 20
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        # Base query
        where_conditions = []
        params = []
        
        if search:
            where_conditions.append('''
                (email LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR company LIKE ?)
            ''')
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param, search_param])
        
        if status_filter == 'active':
            where_conditions.append('is_active = 1')
        elif status_filter == 'inactive':
            where_conditions.append('is_active = 0')
        elif status_filter == 'unverified':
            where_conditions.append('is_verified = 0 AND is_active = 1')
        elif status_filter == 'admin':
            where_conditions.append('is_admin = 1')
        
        where_clause = 'WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
        
        # Toplam sayı
        count_query = f'SELECT COUNT(*) FROM users {where_clause}'
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Sayfalı veri
        offset = (page - 1) * per_page
        data_query = f'''
            SELECT id, email, first_name, last_name, company, 
                   is_active, is_verified, is_admin, created_at, last_login
            FROM users {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        '''
        cursor.execute(data_query, params + [per_page, offset])
        users = cursor.fetchall()
        
        conn.close()
        
        # Sayfalama
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
        
        template_path = get_admin_template_path('users.html', lang)
        return render_template(template_path,
                            users=users,
                            pagination=pagination,
                            search=search,
                            status_filter=status_filter,
                            csrf_token=generate_csrf_token(),
                            lang=lang)
    
    # =============================================================================
    # SISTEM DURUMU - NEW
    # =============================================================================
    @app.route('/admin/system-status')
    @app.route('/en/admin/system-status')
    @app.route('/tr/admin/system-status')
    @admin_required
    def admin_system_status():
        lang = 'en' if '/en/' in request.path else 'tr'
        
        system_info = {
            'db_exists': os.path.exists('bkty_consultancy.db'),
            'db_size_mb': round(os.path.getsize('bkty_consultancy.db') / (1024 * 1024), 2) if os.path.exists('bkty_consultancy.db') else 0,
            'log_exists': os.path.exists('security.log'),
            'log_size_mb': round(os.path.getsize('security.log') / (1024 * 1024), 2) if os.path.exists('security.log') else 0,
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'uptime': 'N/A'  # Bu gerçek uptime için ayrı implementasyon gerekir
        }
        
        # Veritabanı tablo kontrolü
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            system_info['tables'] = tables
            system_info['table_count'] = len(tables)
            
            # Her tablo için kayıt sayısı
            table_counts = {}
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    table_counts[table] = cursor.fetchone()[0]
                except:
                    table_counts[table] = 'Error'
            system_info['table_counts'] = table_counts
            
        except Exception as e:
            system_info['db_error'] = str(e)
        finally:
            conn.close()
        
        template_path = get_admin_template_path('system_status.html', lang)
        return render_template(template_path,
                            system_info=system_info,
                            lang=lang)
    
    # =============================================================================
    # SISTEM LOGLARI - NEW
    # =============================================================================
    @app.route('/admin/system-logs')
    @app.route('/en/admin/system-logs')
    @app.route('/tr/admin/system-logs')
    @admin_required
    def admin_system_logs():
        lang = 'en' if '/en/' in request.path else 'tr'
        page = request.args.get('page', 1, type=int)
        action_filter = request.args.get('action', 'all')
        per_page = 50
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            # Base query
            where_conditions = []
            params = []
            
            if action_filter != 'all':
                where_conditions.append('sl.action LIKE ?')
                params.append(f'%{action_filter}%')
            
            where_clause = 'WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
            
            # Toplam sayı
            count_query = f'SELECT COUNT(*) FROM system_logs sl {where_clause}'
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Sayfalı veri
            offset = (page - 1) * per_page
            data_query = f'''
                SELECT sl.id, sl.user_id, sl.action, sl.details, sl.ip_address, sl.created_at,
                       u.email, u.first_name, u.last_name
                FROM system_logs sl
                LEFT JOIN users u ON sl.user_id = u.id
                {where_clause}
                ORDER BY sl.created_at DESC
                LIMIT ? OFFSET ?
            '''
            cursor.execute(data_query, params + [per_page, offset])
            logs = cursor.fetchall()
            
        except sqlite3.OperationalError:
            # system_logs tablosu yoksa
            total = 0
            logs = []
        
        conn.close()
        
        # Sayfalama
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
        
        template_path = get_admin_template_path('system_logs.html', lang)
        return render_template(template_path,
                            logs=logs,
                            pagination=pagination,
                            action_filter=action_filter,
                            lang=lang)
    
    # =============================================================================
    # HATA RAPORLARI YÖNETİMİ - NEW
    # =============================================================================
    @app.route('/admin/error-reports')
    @app.route('/en/admin/error-reports')
    @app.route('/tr/admin/error-reports')
    @admin_required
    def admin_error_reports():
        lang = 'en' if '/en/' in request.path else 'tr'
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status', 'all')
        category_filter = request.args.get('category', 'all')
        per_page = 20
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            # Base query
            where_conditions = []
            params = []
            
            if status_filter != 'all':
                where_conditions.append('er.status = ?')
                params.append(status_filter)
            
            if category_filter != 'all':
                where_conditions.append('er.error_category = ?')
                params.append(category_filter)
            
            where_clause = 'WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
            
            # Toplam sayı
            count_query = f'SELECT COUNT(*) FROM error_reports er {where_clause}'
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Sayfalı veri
            offset = (page - 1) * per_page
            data_query = f'''
                SELECT er.id, er.user_id, er.error_category, er.error_title, er.description, 
                       er.status, er.created_at, er.resolved_at,
                       u.email, u.first_name, u.last_name
                FROM error_reports er
                LEFT JOIN users u ON er.user_id = u.id
                {where_clause}
                ORDER BY er.created_at DESC
                LIMIT ? OFFSET ?
            '''
            cursor.execute(data_query, params + [per_page, offset])
            reports = cursor.fetchall()
            
            # Kategoriler listesi
            cursor.execute('SELECT DISTINCT error_category FROM error_reports WHERE error_category IS NOT NULL')
            categories = [row[0] for row in cursor.fetchall()]
            
        except sqlite3.OperationalError:
            # error_reports tablosu yoksa
            total = 0
            reports = []
            categories = []
        
        conn.close()
        
        # Sayfalama
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
        
        template_path = get_admin_template_path('error_reports.html', lang)
        return render_template(template_path,
                            reports=reports,
                            categories=categories,
                            pagination=pagination,
                            status_filter=status_filter,
                            category_filter=category_filter,
                            csrf_token=generate_csrf_token(),
                            lang=lang)
    
    # =============================================================================
    # HATA RAPORU DURUM DEĞİŞTİRME - NEW
    # =============================================================================
    @app.route('/admin/error-report/<int:report_id>/update-status', methods=['POST'])
    @app.route('/en/admin/error-report/<int:report_id>/update-status', methods=['POST'])
    @app.route('/tr/admin/error-report/<int:report_id>/update-status', methods=['POST'])
    @admin_required
    def update_error_report_status(report_id):
        if not verify_csrf_token(request.form.get('csrf_token')):
            flash('Güvenlik hatası', 'error')
            return redirect(url_for('admin_error_reports'))
        
        new_status = request.form.get('status')
        notes = request.form.get('notes', '').strip()
        
        if new_status not in ['open', 'in_progress', 'resolved', 'closed']:
            flash('Geçersiz durum', 'error')
            return redirect(url_for('admin_error_reports'))
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            # Durumu güncelle
            if new_status in ['resolved', 'closed']:
                cursor.execute('''
                    UPDATE error_reports 
                    SET status = ?, resolved_at = ?, admin_notes = ?
                    WHERE id = ?
                ''', (new_status, datetime.now(), notes, report_id))
            else:
                cursor.execute('''
                    UPDATE error_reports 
                    SET status = ?, admin_notes = ?
                    WHERE id = ?
                ''', (new_status, notes, report_id))
            
            # Sistem loguna ekle
            current_user = get_current_user()
            admin_id = current_user.get('id') if current_user else None
            if admin_id:
                cursor.execute('''
                    INSERT INTO system_logs (user_id, action, details, ip_address)
                    VALUES (?, ?, ?, ?)
                ''', (admin_id, 'ADMIN_UPDATE_ERROR_REPORT', 
                      f'Report ID: {report_id} status changed to {new_status}', 
                      request.environ.get('REMOTE_ADDR', 'unknown')))
            
            conn.commit()
            flash('Hata raporu durumu güncellendi', 'success')
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Update error report status error: {str(e)}")
            flash('Durum güncelleme sırasında hata oluştu', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('admin_error_reports'))
    
    # =============================================================================
    # İLETİŞİM FORMLARI YÖNETİMİ - NEW
    # =============================================================================
    @app.route('/admin/contact-submissions')
    @app.route('/en/admin/contact-submissions')
    @app.route('/tr/admin/contact-submissions')
    @admin_required
    def admin_contact_submissions():
        lang = 'en' if '/en/' in request.path else 'tr'
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status', 'all')
        per_page = 20
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            # Base query
            where_conditions = []
            params = []
            
            if status_filter != 'all':
                where_conditions.append('cs.status = ?')
                params.append(status_filter)
            
            where_clause = 'WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
            
            # Toplam sayı
            count_query = f'SELECT COUNT(*) FROM contact_submissions cs {where_clause}'
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Sayfalı veri
            offset = (page - 1) * per_page
            data_query = f'''
                SELECT cs.id, cs.name, cs.email, cs.subject, cs.message, 
                       cs.status, cs.created_at, cs.responded_at
                FROM contact_submissions cs
                {where_clause}
                ORDER BY cs.created_at DESC
                LIMIT ? OFFSET ?
            '''
            cursor.execute(data_query, params + [per_page, offset])
            submissions = cursor.fetchall()
            
        except sqlite3.OperationalError:
            # contact_submissions tablosu yoksa
            total = 0
            submissions = []
        
        conn.close()
        
        # Sayfalama
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
        
        template_path = get_admin_template_path('contact_submissions.html', lang)
        return render_template(template_path,
                            submissions=submissions,
                            pagination=pagination,
                            status_filter=status_filter,
                            csrf_token=generate_csrf_token(),
                            lang=lang)
    
    # =============================================================================
    # TEST ROUTES - DEBUG
    # =============================================================================
    @app.route('/admin/test-routes')
    @app.route('/admin-test')
    @admin_required
    def admin_test():
        return jsonify({
            "success": True,
            "message": "Complete admin routes working",
            "timestamp": datetime.now().isoformat(),
            "available_routes": [
                "/admin/dashboard",
                "/admin/users",
                "/admin/user/<id>",
                "/admin/user/<id>/approve",
                "/admin/user/<id>/toggle-status", 
                "/admin/user/<id>/delete",
                "/admin/users/bulk-action",
                "/admin/sessions",
                "/admin/session/<id>/terminate",
                "/admin/activity-logs",
                "/admin/system-status",
                "/admin/system-logs",
                "/admin/error-reports",
                "/admin/contact-submissions"
            ]
        })
    
    # =============================================================================
    # API ENDPOINTS
    # =============================================================================
    @app.route('/api/admin/user/<int:user_id>/recent-activities')
    @admin_required
    def get_user_recent_activities(user_id):
        """Kullanıcının son aktivitelerini JSON olarak döndür"""
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT action, details, ip_address, user_agent, created_at
                FROM user_activities 
                WHERE user_id = ? AND created_at >= datetime('now', '-1 hour')
                ORDER BY created_at DESC
                LIMIT 10
            ''', (user_id,))
            
            activities = cursor.fetchall()
            conn.close()
            
            return jsonify({
                'success': True,
                'activities': activities
            })
            
        except Exception as e:
            conn.close()
            logger.error(f"Error fetching recent activities: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/admin/stats/dashboard')
    @admin_required
    def get_dashboard_stats():
        """Dashboard için istatistikleri JSON olarak döndür"""
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # Kullanıcı istatistikleri
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
            stats['total_users'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE created_at >= date("now", "-1 day")')
            stats['new_users_today'] = cursor.fetchone()[0]
            
            # Session istatistikleri
            try:
                cursor.execute('SELECT COUNT(*) FROM user_sessions WHERE logout_time IS NULL')
                stats['active_sessions'] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                stats['active_sessions'] = 0
            
            # Hata raporları
            try:
                cursor.execute('SELECT COUNT(*) FROM error_reports WHERE status = "open"')
                stats['open_reports'] = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                stats['open_reports'] = 0
            
            conn.close()
            
            return jsonify({
                'success': True,
                'stats': stats
            })
            
        except Exception as e:
            conn.close()
            logger.error(f"Error fetching dashboard stats: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    print("✅ COMPLETE Admin routes registered successfully")
    print("📍 Available admin routes:")
    print("  🏠 Dashboard: /admin/dashboard")
    print("  👥 Users: /admin/users")
    print("  👤 User Detail: /admin/user/<id>")
    print("  ✅ User Actions: approve, toggle-status, delete")
    print("  📦 Bulk Actions: /admin/users/bulk-action")
    print("  🔒 Sessions: /admin/sessions")
    print("  📊 Activity Logs: /admin/activity-logs")
    print("  💻 System Status: /admin/system-status")
    print("  📋 System Logs: /admin/system-logs")
    print("  ❌ Error Reports: /admin/error-reports")
    print("  📧 Contact Forms: /admin/contact-submissions")
    print("  🧪 Test Routes: /admin/test-routes")
    print("  🔌 API Endpoints: /api/admin/*")

    # =============================================================================
    # KULLANICI DETAY SAYFASı - ENHANCED
    # =============================================================================
    @app.route('/admin/user/<int:user_id>')
    @app.route('/en/admin/user/<int:user_id>')
    @app.route('/tr/admin/user/<int:user_id>')
    @admin_required
    def admin_user_detail(user_id):
        lang = 'en' if '/en/' in request.path else 'tr'
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        # Kullanıcı bilgileri
        cursor.execute('''
            SELECT id, email, first_name, last_name, company, phone,
                   is_active, is_verified, is_admin, created_at, last_login,
                   email_verified_at, failed_login_attempts, locked_until
            FROM users WHERE id = ?
        ''', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash('Kullanıcı bulunamadı', 'error')
            return redirect(url_for('admin_users'))
        
        # Kullanıcı aktiviteleri
        cursor.execute('''
            SELECT action, details, ip_address, user_agent, created_at
            FROM user_activities 
            WHERE user_id = ? AND created_at >= date('now', '-30 days')
            ORDER BY created_at DESC
            LIMIT 50
        ''', (user_id,))
        activities = cursor.fetchall()
        
        # Giriş-çıkış geçmişi
        cursor.execute('''
            SELECT login_time, logout_time, ip_address, user_agent, session_duration
            FROM user_sessions 
            WHERE user_id = ? 
            ORDER BY login_time DESC
            LIMIT 20
        ''', (user_id,))
        sessions = cursor.fetchall()
        
        # AI sohbet istatistikleri
        try:
            cursor.execute('''
                SELECT COUNT(*) as total_chats,
                       AVG(response_time) as avg_response_time
                FROM ai_chat_history 
                WHERE user_id = ?
            ''', (user_id,))
            chat_stats = cursor.fetchone()
        except sqlite3.OperationalError:
            chat_stats = (0, 0)
        
        # Hata raporları
        try:
            cursor.execute('''
                SELECT error_category, error_title, description, created_at, status
                FROM error_reports 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            ''', (user_id,))
            error_reports = cursor.fetchall()
        except sqlite3.OperationalError:
            error_reports = []
        
        conn.close()
        
        template_path = get_admin_template_path('user_detail.html', lang)
        current_user = get_current_user()
        return render_template(template_path,
                            user=user,
                            current_user=current_user, 
                            activities=activities,
                            sessions=sessions,
                            chat_stats=chat_stats,
                            error_reports=error_reports,
                            csrf_token=generate_csrf_token(),
                            lang=lang)
    
    # =============================================================================
    # KULLANICI ONAYLAMA - ENHANCED
    # =============================================================================
    @app.route('/admin/user/<int:user_id>/approve', methods=['POST'])
    @app.route('/en/admin/user/<int:user_id>/approve', methods=['POST'])
    @app.route('/tr/admin/user/<int:user_id>/approve', methods=['POST'])
    @admin_required
    def approve_user(user_id):
        print(f"Approve user called for user_id: {user_id}")
        print(f"CSRF token received: {request.form.get('csrf_token')}")
        
        if not verify_csrf_token(request.form.get('csrf_token')):
            flash('Güvenlik hatası', 'error')
            return redirect(url_for('admin_user_detail', user_id=user_id))
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            # Kullanıcıyı onayla
            cursor.execute('''
                UPDATE users 
                SET is_verified = 1, is_active = 1, email_verified_at = ?
                WHERE id = ?
            ''', (datetime.now(), user_id))
            
            # Aktiviteyi logla
            try:
                current_user = get_current_user()
                admin_id = current_user.get('id') if current_user else None
                cursor.execute('''
                    INSERT INTO user_activities (user_id, action, details, admin_user_id)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, 'USER_APPROVED', 'Hesap admin tarafından onaylandı', admin_id))
                
                # Sistem loguna ekle
                if admin_id:
                    cursor.execute('''
                        INSERT INTO system_logs (user_id, action, details, ip_address)
                        VALUES (?, ?, ?, ?)
                    ''', (admin_id, 'ADMIN_APPROVE_USER', f'User ID: {user_id} approved', 
                          request.environ.get('REMOTE_ADDR', 'unknown')))
            except Exception as log_error:
                print(f"Logging error: {log_error}")
            
            conn.commit()
            flash('Kullanıcı başarıyla onaylandı', 'success')
            print(f"User {user_id} approved successfully")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"User approval error: {str(e)}")
            flash('Onaylama sırasında hata oluştu', 'error')
            print(f"Approval error: {e}")
        finally:
            conn.close()
        
        return redirect(url_for('admin_user_detail', user_id=user_id))
    
    # =============================================================================
    # KULLANICI DURUM DEĞİŞTİRME - ENHANCED
    # =============================================================================
    @app.route('/admin/user/<int:user_id>/toggle-status', methods=['POST'])
    @app.route('/en/admin/user/<int:user_id>/toggle-status', methods=['POST'])
    @app.route('/tr/admin/user/<int:user_id>/toggle-status', methods=['POST'])
    @admin_required
    def toggle_user_status(user_id):
        print(f"Toggle status called for user_id: {user_id}")
        print(f"CSRF token received: {request.form.get('csrf_token')}")
        
        if not verify_csrf_token(request.form.get('csrf_token')):
            flash('Güvenlik hatası', 'error')
            return redirect(url_for('admin_user_detail', user_id=user_id))
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            # Mevcut durumu kontrol et
            cursor.execute('SELECT is_active, email FROM users WHERE id = ?', (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                flash('Kullanıcı bulunamadı', 'error')
                return redirect(url_for('admin_users'))
            
            new_status = 1 if not user_data[0] else 0
            action = 'ACTIVATED' if new_status else 'DEACTIVATED'
            
            # Durumu değiştir
            cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
            
            # Eğer deaktif ediliyorsa, aktif sessionları sonlandır
            if not new_status:
                try:
                    cursor.execute('UPDATE user_sessions SET logout_time = ? WHERE user_id = ? AND logout_time IS NULL', 
                                 (datetime.now(), user_id))
                except sqlite3.OperationalError:
                    pass  # user_sessions tablosu yoksa
            
            # Aktiviteyi logla
            try:
                current_user = get_current_user()
                admin_id = current_user.get('id') if current_user else None
                cursor.execute('''
                    INSERT INTO user_activities (user_id, action, details, admin_user_id)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, f'USER_{action}', f'Hesap admin tarafından {action.lower()}', admin_id))
                
                # Sistem loguna ekle
                if admin_id:
                    cursor.execute('''
                        INSERT INTO system_logs (user_id, action, details, ip_address)
                        VALUES (?, ?, ?, ?)
                    ''', (admin_id, f'ADMIN_{action}_USER', f'User ID: {user_id} {action.lower()}', 
                          request.environ.get('REMOTE_ADDR', 'unknown')))
            except Exception as log_error:
                print(f"Logging error: {log_error}")
            
            conn.commit()
            flash(f'Kullanıcı {"aktif" if new_status else "pasif"} edildi', 'success')
            print(f"User {user_id} status changed to {new_status}")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Toggle user status error: {str(e)}")
            flash('Durum değiştirme sırasında hata oluştu', 'error')
            print(f"Toggle status error: {e}")
        finally:
            conn.close()
        
        return redirect(url_for('admin_user_detail', user_id=user_id))
    
    # =============================================================================
    # KULLANICI SİLME - ENHANCED
    # =============================================================================
    @app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
    @app.route('/en/admin/user/<int:user_id>/delete', methods=['POST'])
    @app.route('/tr/admin/user/<int:user_id>/delete', methods=['POST'])
    @admin_required
    def delete_user(user_id):
        print(f"Delete user called for user_id: {user_id}")
        
        if not verify_csrf_token(request.form.get('csrf_token')):
            flash('Güvenlik hatası', 'error')
            return redirect(url_for('admin_user_detail', user_id=user_id))
        
        # Kendi kendini silmeyi engelle
        current_user = get_current_user()
        if current_user and current_user.get('id') == user_id:
            flash('Kendi hesabınızı silemezsiniz', 'error')
            return redirect(url_for('admin_user_detail', user_id=user_id))
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            # Basit soft delete - sadece is_active = 0 yap
            cursor.execute('''
                UPDATE users 
                SET is_active = 0
                WHERE id = ?
            ''', (user_id,))
            
            # Sessionları sonlandır
            try:
                cursor.execute('UPDATE user_sessions SET logout_time = ? WHERE user_id = ? AND logout_time IS NULL', 
                            (datetime.now(), user_id))
            except sqlite3.OperationalError:
                pass  # user_sessions tablosu yoksa
            
            # Sistem loguna ekle
            admin_id = current_user.get('id') if current_user else None
            if admin_id:
                try:
                    cursor.execute('''
                        INSERT INTO system_logs (user_id, action, details, ip_address)
                        VALUES (?, ?, ?, ?)
                    ''', (admin_id, 'ADMIN_DELETE_USER', f'User ID: {user_id} deleted', 
                        request.environ.get('REMOTE_ADDR', 'unknown')))
                except sqlite3.OperationalError:
                    pass  # system_logs tablosu yoksa
            
            conn.commit()
            flash('Kullanıcı başarıyla silindi', 'success')
            print(f"User {user_id} deleted successfully")
            return redirect(url_for('admin_users'))
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Delete user error: {str(e)}")
            flash('Kullanıcı silme sırasında hata oluştu', 'error')
            print(f"Delete error: {e}")
        finally:
            conn.close()
        
        return redirect(url_for('admin_user_detail', user_id=user_id))
        
    # =============================================================================
    # TOPLU KULLANICI İŞLEMLERİ - NEW
    # =============================================================================
    @app.route('/admin/users/bulk-action', methods=['POST'])
    @app.route('/en/admin/users/bulk-action', methods=['POST'])
    @app.route('/tr/admin/users/bulk-action', methods=['POST'])
    @admin_required
    def bulk_user_action():
        if not verify_csrf_token(request.form.get('csrf_token')):
            flash('Güvenlik hatası', 'error')
            return redirect(url_for('admin_users'))
        
        action = request.form.get('action')
        user_ids = request.form.getlist('user_ids')
        
        if not user_ids:
            flash('Lütfen en az bir kullanıcı seçin', 'error')
            return redirect(url_for('admin_users'))
        
        user_ids = [int(uid) for uid in user_ids]
        current_user = get_current_user()
        admin_id = current_user.get('id') if current_user else None
        
        # Kendi kendini seçmeyi engelle
        if admin_id and admin_id in user_ids:
            user_ids.remove(admin_id)
            flash('Kendi hesabınız işlemden çıkarıldı', 'warning')
        
        if not user_ids:
            flash('İşlem yapılacak kullanıcı kalmadı', 'warning')
            return redirect(url_for('admin_users'))
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            if action == 'approve':
                cursor.executemany('''
                    UPDATE users 
                    SET is_verified = 1, is_active = 1, email_verified_at = ?
                    WHERE id = ?
                ''', [(datetime.now(), uid) for uid in user_ids])
                flash(f'{len(user_ids)} kullanıcı onaylandı', 'success')
                
            elif action == 'deactivate':
                cursor.executemany('UPDATE users SET is_active = 0 WHERE id = ?', 
                                 [(uid,) for uid in user_ids])
                # Sessionları sonlandır
                try:
                    cursor.executemany('UPDATE user_sessions SET logout_time = ? WHERE user_id = ? AND logout_time IS NULL', 
                                     [(datetime.now(), uid) for uid in user_ids])
                except sqlite3.OperationalError:
                    pass
                flash(f'{len(user_ids)} kullanıcı deaktif edildi', 'success')
                
            elif action == 'activate':
                cursor.executemany('UPDATE users SET is_active = 1 WHERE id = ?', 
                                 [(uid,) for uid in user_ids])
                flash(f'{len(user_ids)} kullanıcı aktif edildi', 'success')
            
            # Sistem loguna ekle
            if admin_id:
                try:
                    cursor.execute('''
                        INSERT INTO system_logs (user_id, action, details, ip_address)
                        VALUES (?, ?, ?, ?)
                    ''', (admin_id, f'ADMIN_BULK_{action.upper()}', 
                          f'Bulk {action} on {len(user_ids)} users: {user_ids}', 
                          request.environ.get('REMOTE_ADDR', 'unknown')))
                except sqlite3.OperationalError:
                    pass
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Bulk action error: {str(e)}")
            flash('Toplu işlem sırasında hata oluştu', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('admin_users'))
    
    # =============================================================================
    # SESSION YÖNETİMİ - NEW
    # =============================================================================
    @app.route('/admin/sessions')
    @app.route('/en/admin/sessions')
    @app.route('/tr/admin/sessions')
    @admin_required
    def admin_sessions():
        lang = 'en' if '/en/' in request.path else 'tr'
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            # Aktif sessionlar
            cursor.execute('''
                SELECT us.id, us.user_id, us.login_time, us.ip_address, us.user_agent,
                       u.email, u.first_name, u.last_name
                FROM user_sessions us
                JOIN users u ON us.user_id = u.id
                WHERE us.logout_time IS NULL AND us.login_time >= datetime('now', '-7 days')
                ORDER BY us.login_time DESC
            ''')
            active_sessions = cursor.fetchall()
            
            # Session istatistikleri
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(CASE WHEN logout_time IS NULL THEN 1 END) as active_sessions,
                    AVG(session_duration) as avg_duration
                FROM user_sessions
                WHERE login_time >= date('now', '-30 days')
            ''')
            session_stats = cursor.fetchone()
            
        except sqlite3.OperationalError:
            # user_sessions tablosu yoksa
            active_sessions = []
            session_stats = (0, 0, 0)
        
        conn.close()
        
        template_path = get_admin_template_path('sessions.html', lang)
        return render_template(template_path,
                            active_sessions=active_sessions,
                            session_stats=session_stats,
                            csrf_token=generate_csrf_token(),
                            lang=lang)
    
    # =============================================================================
    # SESSION SONLANDIRMA - NEW
    # =============================================================================
    @app.route('/admin/session/<int:session_id>/terminate', methods=['POST'])
    @app.route('/en/admin/session/<int:session_id>/terminate', methods=['POST'])
    @app.route('/tr/admin/session/<int:session_id>/terminate', methods=['POST'])
    @admin_required
    def terminate_session(session_id):
        if not verify_csrf_token(request.form.get('csrf_token')):
            flash('Güvenlik hatası', 'error')
            return redirect(url_for('admin_sessions'))
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            # Session'ı sonlandır
            cursor.execute('UPDATE user_sessions SET logout_time = ? WHERE id = ?', 
                         (datetime.now(), session_id))
            
            # Sistem loguna ekle
            current_user = get_current_user()
            admin_id = current_user.get('id') if current_user else None
            if admin_id:
                cursor.execute('''
                    INSERT INTO system_logs (user_id, action, details, ip_address)
                    VALUES (?, ?, ?, ?)
                ''', (admin_id, 'ADMIN_TERMINATE_SESSION', 
                      f'Session ID: {session_id} terminated', 
                      request.environ.get('REMOTE_ADDR', 'unknown')))
            
            conn.commit()
            flash('Session başarıyla sonlandırıldı', 'success')
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Terminate session error: {str(e)}")
            flash('Session sonlandırma sırasında hata oluştu', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('admin_sessions'))
    
    # =============================================================================
    # AKTİVİTE LOGLARI - NEW
    # =============================================================================
    @app.route('/admin/activity-logs')
    @app.route('/en/admin/activity-logs')
    @app.route('/tr/admin/activity-logs')
    @admin_required
    def admin_activity_logs():
        lang = 'en' if '/en/' in request.path else 'tr'
        page = request.args.get('page', 1, type=int)
        action_filter = request.args.get('action', 'all')
        date_filter = request.args.get('date', 'all')
        per_page = 50
        
        conn = sqlite3.connect('bkty_consultancy.db')
        cursor = conn.cursor()
        
        try:
            # Base query
            where_conditions = []
            params = []
            
            if action_filter != 'all':
                where_conditions.append('ua.action LIKE ?')
                params.append(f'%{action_filter}%')
            
            if date_filter == 'today':
                where_conditions.append('ua.created_at >= date("now")')
            elif date_filter == 'week':
                where_conditions.append('ua.created_at >= date("now", "-7 days")')
            elif date_filter == 'month':
                where_conditions.append('ua.created_at >= date("now", "-30 days")')
            
            where_clause = 'WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
            
            # Toplam sayı
            count_query = f'SELECT COUNT(*) FROM user_activities ua {where_clause}'
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Sayfalı veri
            offset = (page - 1) * per_page
            data_query = f'''
                SELECT ua.id, ua.user_id, ua.action, ua.details, ua.ip_address, ua.created_at,
                       u.email, u.first_name, u.last_name,
                       admin_u.email as admin_email
                FROM user_activities ua
                LEFT JOIN users u ON ua.user_id = u.id
                LEFT JOIN users admin_u ON ua.admin_user_id = admin_u.id
                {where_clause}
                ORDER BY ua.created_at DESC
                LIMIT ? OFFSET ?
            '''
            cursor.execute(data_query, params + [per_page, offset])
            activities = cursor.fetchall()
            
        except sqlite3.OperationalError:
            # user_activities tablosu yoksa
            total = 0
            activities = []
        
        conn.close()
        
        # Sayfalama
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
        
        template_path = get_admin_template_path('activity_logs.html', lang)
        return render_template(template_path,
                            activities=activities,
                            pagination=pagination,
                            action_filter=action_filter,
                            date_filter=date_filter,
                            lang=lang)

    @app.route('/admin/delete-user-permanent/<int:user_id>', methods=['POST'])
    @admin_required
    def delete_user_permanent(user_id):
        """Kullanıcıyı kalıcı olarak sil"""
        try:
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            # Önce kullanıcı bilgilerini al (log için)
            cursor.execute('SELECT email, first_name, last_name FROM users WHERE id = ?', (user_id,))
            user_info = cursor.fetchone()
            
            if not user_info:
                flash('Kullanıcı bulunamadı.', 'error')
                return redirect(url_for('admin_dashboard'))
            
            # İlişkili verileri sil (cascade delete)
            cursor.execute('DELETE FROM user_sessions WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM system_logs WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM user_activities WHERE user_id = ?', (user_id,))
            
            # Kullanıcıyı sil
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            
            conn.commit()
            conn.close()
            
            # Admin activity log
            log_user_activity("USER_PERMANENTLY_DELETED", 
                            f"User {user_info[0]} permanently deleted by admin")
            
            flash(f'Kullanıcı {user_info[0]} kalıcı olarak silindi.', 'success')
            
        except Exception as e:
            logger.error(f"Permanent delete error: {e}")
            flash('Silme işlemi sırasında hata oluştu.', 'error')
        
        return redirect(url_for('admin_dashboard'))

    # admin_dashboard.py'ye ekleyin

    @app.route('/admin/security-live')
    @admin_required
    def admin_security_live():
        """Security monitoring sayfası"""
        return render_template('admin/security_live.html', lang=session.get('lang', 'tr'))

    @app.route('/admin/api/security-stats')
    @admin_required
    def admin_security_stats_api():
        """Security monitor için real-time stats"""
        try:
            from app import app as flask_app
            
            # SimpleSecurityMiddleware instance'ını al
            middleware = flask_app.wsgi_app
            
            stats = {
                'blocked_ips': len(middleware.blocked_ips),
                'threats_last_hour': 0,
                'requests_last_minute': len(middleware.ip_data),
                'avg_threat_score': 0
            }
            
            recent_attacks = []
            blocked_list = []
            
            # IP data'dan şüpheli aktiviteleri topla
            for ip, data in list(middleware.ip_data.items())[:20]:
                if data['suspicious_count'] > 0:
                    recent_attacks.append({
                        'ip': ip,
                        'score': data['suspicious_count'] * 5,
                        'count_404': data.get('404_count', 0),
                        'suspicious': data['suspicious_count']
                    })
            
            # Bloklu IP'leri formatla
            for ip in list(middleware.blocked_ips)[:50]:
                if ip in middleware.ip_data:
                    data = middleware.ip_data[ip]
                    blocked_list.append({
                        'ip': ip,
                        'score': data['suspicious_count'] * 5,
                        'count_404': data.get('404_count', 0),
                        'suspicious': data['suspicious_count']
                    })
            
            # Saatlik tehdit grafiği
            hourly_threats = []
            for i in range(12):
                hourly_threats.append({
                    'time': f'{(datetime.now() - timedelta(hours=11-i)).strftime("%H:%M")}',
                    'count': len([a for a in recent_attacks if a['score'] > 20]) // max(i+1, 1)
                })
            
            if recent_attacks:
                stats['avg_threat_score'] = sum(a['score'] for a in recent_attacks) // len(recent_attacks)
                stats['threats_last_hour'] = len(recent_attacks)
            
            return jsonify({
                'success': True,
                'blocked_ips': stats['blocked_ips'],
                'threats_last_hour': stats['threats_last_hour'],
                'requests_last_minute': stats['requests_last_minute'],
                'avg_threat_score': stats['avg_threat_score'],
                'recent': recent_attacks,
                'blocked_list': blocked_list,
                'hourly_threats': hourly_threats
            })
            
        except Exception as e:
            logger.error(f"Security stats error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/admin/api/block-ip', methods=['POST'])
    @admin_required
    def admin_block_ip():
        """Manually block IP"""
        try:
            data = request.get_json()
            ip = data.get('ip')
            
            if not ip:
                return jsonify({'success': False, 'error': 'IP required'}), 400
            
            from app import app as flask_app
            middleware = flask_app.wsgi_app
            middleware.blocked_ips.add(ip)
            
            logger.warning(f"IP manually blocked by admin: {ip}")
            
            return jsonify({'success': True, 'message': f'IP {ip} blocked'})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/admin/api/unblock-ip', methods=['POST'])
    @admin_required
    def admin_unblock_ip():
        """Unblock IP"""
        try:
            data = request.get_json()
            ip = data.get('ip')
            
            if not ip:
                return jsonify({'success': False, 'error': 'IP required'}), 400
            
            from app import app as flask_app
            middleware = flask_app.wsgi_app
            middleware.blocked_ips.discard(ip)
            
            logger.info(f"IP unblocked by admin: {ip}")
            
            return jsonify({'success': True, 'message': f'IP {ip} unblocked'})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/admin/api/whitelist-ip', methods=['POST'])
    @admin_required
    def admin_whitelist_ip():
        """Whitelist IP (remove from monitoring)"""
        try:
            data = request.get_json()
            ip = data.get('ip')
            
            if not ip:
                return jsonify({'success': False, 'error': 'IP required'}), 400
            
            from app import app as flask_app
            middleware = flask_app.wsgi_app
            
            # IP'yi blocked listesinden çıkar
            middleware.blocked_ips.discard(ip)
            
            # IP data'sını temizle
            if ip in middleware.ip_data:
                del middleware.ip_data[ip]
            
            logger.info(f"IP whitelisted by admin: {ip}")
            
            return jsonify({'success': True, 'message': f'IP {ip} whitelisted'})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/admin/security/bot-attempts', methods=['GET'])
    @admin_required
    def admin_bot_attempts():
        """Bot girişimlerini listele"""
        try:
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            # Son 24 saatteki şüpheli kayıt denemeleri
            cursor.execute('''
                SELECT ip_address, COUNT(*) as attempts, 
                    GROUP_CONCAT(email) as emails,
                    MIN(attempted_at) as first_attempt,
                    MAX(attempted_at) as last_attempt
                FROM failed_registrations
                WHERE attempted_at > datetime('now', '-24 hours')
                GROUP BY ip_address
                HAVING attempts > 2
                ORDER BY attempts DESC
            ''')
            
            bot_attempts = cursor.fetchall()
            conn.close()
            
            return jsonify({
                'success': True,
                'bot_attempts': [
                    {
                        'ip': row[0],
                        'attempts': row[1],
                        'emails': row[2].split(',') if row[2] else [],
                        'first_attempt': row[3],
                        'last_attempt': row[4]
                    }
                    for row in bot_attempts
                ]
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500


# admin_dashboard.py'nin sonuna ekleyin

    @app.route('/admin/bot-monitoring', methods=['GET'])
    @admin_required
    def admin_bot_monitoring():
        """Bot girişimlerini izle"""
        try:
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            # Son 24 saatteki başarısız kayıt denemeleri
            cursor.execute('''
                SELECT 
                    ip_address,
                    first_name,
                    last_name,
                    email,
                    reason,
                    attempted_at
                FROM failed_registrations
                WHERE attempted_at > datetime('now', '-24 hours')
                ORDER BY attempted_at DESC
                LIMIT 100
            ''')
            
            failed_attempts = cursor.fetchall()
            
            # IP bazlı gruplandırma
            cursor.execute('''
                SELECT 
                    ip_address,
                    COUNT(*) as attempt_count,
                    GROUP_CONCAT(DISTINCT reason) as reasons,
                    MIN(attempted_at) as first_attempt,
                    MAX(attempted_at) as last_attempt
                FROM failed_registrations
                WHERE attempted_at > datetime('now', '-24 hours')
                GROUP BY ip_address
                HAVING attempt_count > 1
                ORDER BY attempt_count DESC
            ''')
            
            suspicious_ips = cursor.fetchall()
            conn.close()
            
            return render_template('admin/bot_monitoring.html',
                failed_attempts=failed_attempts,
                suspicious_ips=suspicious_ips,
                lang=session.get('lang', 'tr')
            )
            
        except Exception as e:
            logger.error(f"Bot monitoring error: {e}")
            return jsonify({'error': str(e)}), 500



    @app.route('/admin/users/delete-all-non-admin', methods=['POST'])
    @admin_required
    def delete_all_non_admin_users():
        """Admin olmayan tüm kullanıcıları sil"""
        
        # Debug - tokenleri yazdır
        received_token = request.form.get('csrf_token')
        session_token = session.get('csrf_token')
        
        print(f"Received token: {received_token}")
        print(f"Session token: {session_token}")
        print(f"Match: {received_token == session_token}")
        
        if not verify_csrf_token(received_token):
            return jsonify({
                'success': False, 
                'error': f'CSRF validation failed. Received: {received_token[:10]}..., Expected: {session_token[:10] if session_token else "None"}...'
            }), 403
        
        confirmation = request.form.get('confirmation', '').strip()
        if confirmation != 'DELETE_ALL_USERS':
            return jsonify({
                'success': False,
                'error': 'Confirmation text must be "DELETE_ALL_USERS"'
            }), 400

        
        try:
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            # Silinecek kullanıcı sayısını al
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0')
            count = cursor.fetchone()[0]
            
            if count == 0:
                conn.close()
                return jsonify({
                    'success': True,
                    'message': 'Silinecek kullanıcı yok',
                    'deleted': 0
                })
            
            # İlişkili verileri temizle
            cursor.execute('DELETE FROM user_sessions WHERE user_id IN (SELECT id FROM users WHERE is_admin = 0)')
            cursor.execute('DELETE FROM user_activities WHERE user_id IN (SELECT id FROM users WHERE is_admin = 0)')
            cursor.execute('DELETE FROM ai_chat_history WHERE user_id IN (SELECT id FROM users WHERE is_admin = 0)')
            cursor.execute('DELETE FROM error_reports WHERE user_id IN (SELECT id FROM users WHERE is_admin = 0)')
            
            # Kullanıcıları sil
            cursor.execute('DELETE FROM users WHERE is_admin = 0')
            
            conn.commit()
            conn.close()
            
            # Log
            current_user = get_current_user()
            logger.warning(f"Admin {current_user.get('email')} deleted {count} non-admin users")
            
            return jsonify({
                'success': True,
                'message': f'{count} kullanıcı başarıyla silindi',
                'deleted': count
            })
            
        except Exception as e:
            logger.error(f"Bulk delete error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/admin/api-services', methods=['GET'])
    @admin_required
    def admin_api_services():
        """Admin için external API servisleri durumu"""
        try:
            from external_api_service import external_api_service
            
            status = external_api_service.get_service_status()
            
            # Cache istatistikleri
            cache_info = {
                "size": status.get("cache_size", 0),
                "items": []
            }
            
            if hasattr(external_api_service, '_cache'):
                for key, (data, timestamp) in list(external_api_service._cache.items())[:10]:
                    cache_info["items"].append({
                        "key": key[:50],
                        "timestamp": timestamp.isoformat(),
                        "age_seconds": (datetime.now() - timestamp).total_seconds()
                    })
            
            return jsonify({
                "success": True,
                "services": status,
                "cache": cache_info
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500


    @app.route('/admin/api-services/clear-cache', methods=['POST'])
    @admin_required
    def admin_clear_api_cache():
        """Admin cache temizleme"""
        try:
            from external_api_service import external_api_service
            result = external_api_service.clear_cache()
            return jsonify({"success": True, "message": "Cache cleared"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500