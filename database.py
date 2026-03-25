# database.py - Veritabanı şeması ve kullanıcı yönetimi
import sqlite3
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_PATH = 'bkty_consultancy.db'

def get_connection():
    """SQLite bağlantısı aç, WAL modu ve timeout ile"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_database():
    """Veritabanını başlat ve tabloları oluştur"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Users tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            company TEXT,
            phone TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            is_admin BOOLEAN DEFAULT FALSE,
            is_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            verification_token TEXT,
            reset_token TEXT,
            reset_token_expires TIMESTAMP,
            preferred_language TEXT DEFAULT 'tr',
            privacy_accepted BOOLEAN DEFAULT FALSE,
            terms_accepted BOOLEAN DEFAULT FALSE,
            data_processing_consent BOOLEAN DEFAULT FALSE,
            marketing_consent BOOLEAN DEFAULT FALSE,
            cookie_consent TEXT,
            ai_data_consent BOOLEAN DEFAULT FALSE,
            ai_data_retention_days INTEGER DEFAULT 30,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            email_verified_at TIMESTAMP
        )
    ''')
    
    # User sessions tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id TEXT UNIQUE NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            logout_time TIMESTAMP,
            session_duration INTEGER,
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    # AI chat history tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id TEXT,
            question TEXT NOT NULL,
            response TEXT,
            model_used TEXT,
            response_time REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            is_deleted BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        )
    ''')
    
    # Error reports tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS error_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            ticket_id TEXT UNIQUE,
            error_category TEXT,
            error_title TEXT,
            description TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            browser_info TEXT,
            error_url TEXT,
            file_path TEXT,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            admin_notes TEXT,
            ip_address TEXT,
            user_agent TEXT
        )
    ''')

    # Contact form submissions tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            company TEXT,
            service_type TEXT,
            message TEXT NOT NULL,
            ip_address TEXT,
            language TEXT DEFAULT 'tr',
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            replied_at TIMESTAMP,
            admin_notes TEXT
        )
    ''')
    
    # System logs tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        )
    ''')

    # Email preferences tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            system_notifications BOOLEAN DEFAULT 1,
            newsletter BOOLEAN DEFAULT 0,
            marketing_emails BOOLEAN DEFAULT 0,
            ai_notifications BOOLEAN DEFAULT 0,
            weekly_report BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # User activities tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            admin_user_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (admin_user_id) REFERENCES users (id) ON DELETE SET NULL
        )
    ''')
    
    # Failed registrations tablosu - BOT KORUMASI İÇİN
    # Failed registrations tablosu - BOT KORUMASI İÇİN
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS failed_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            email TEXT,
            first_name TEXT,
            last_name TEXT,
            reason TEXT NOT NULL,
            form_data TEXT,
            user_agent TEXT,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 🔹 Index’leri ayrı oluştur
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_failed_ip_address ON failed_registrations (ip_address)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_failed_attempted_at ON failed_registrations (attempted_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_failed_reason ON failed_registrations (reason)')

        
    # Admin user oluştur (eğer yoksa)
    # database.py - init_database() içinde değiştirilecek kısım

    import os

    # Admin user oluştur (eğer yoksa)
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = TRUE')
    admin_count = cursor.fetchone()[0]

    if admin_count == 0:
        # Önce env'den al, yoksa güçlü random şifre üret
        admin_password = os.environ.get('BKTY_ADMIN_PASSWORD')
        
        if not admin_password:
            admin_password = secrets.token_urlsafe(16)  # 22 karakterlik random
            # Şifreyi güvenli bir dosyaya yaz (bir kez, sadece okunabilir)
            creds_path = os.path.join(os.path.dirname(__file__), '.admin_init_creds')
            with open(creds_path, 'w') as f:
                f.write(f"Email: info@bktyconsultancy.co.uk\nPassword: {admin_password}\n")
            os.chmod(creds_path, 0o600)  # sadece owner okuyabilir
            print(f"[!] Admin credentials saved to: {creds_path}")
        
        password_hash = generate_password_hash(admin_password)
        
        cursor.execute('''
            INSERT INTO users (
                email, password_hash, first_name, last_name, 
                is_active, is_admin, is_verified, 
                privacy_accepted, terms_accepted, data_processing_consent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'info@bktyconsultancy.co.uk',
            password_hash, 
            'Admin', 
            'User',
            True, True, True, True, True, True
        ))
        
        # Şifreyi ASLA loglama
        print("Admin user created - check .admin_init_creds for credentials")

class UserManager:
    """Kullanıcı yönetimi sınıfı"""
    
    @staticmethod
    def create_user(email, password, first_name, last_name, company=None, phone=None, language='tr'):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                return {'success': False, 'error': 'Bu email adresi zaten kullanılıyor'}

            password_hash = generate_password_hash(password)
            verification_token = secrets.token_urlsafe(32)

            cursor.execute('''
                INSERT INTO users (
                    email, password_hash, first_name, last_name,
                    company, phone, verification_token, preferred_language
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (email, password_hash, first_name, last_name, company, phone, verification_token, language))

            user_id = cursor.lastrowid
            conn.commit()
            return {'success': True, 'user_id': user_id, 'verification_token': verification_token}
        except Exception as e:
            conn.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    @staticmethod
    def authenticate_user(email, password):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, password_hash, is_active, is_verified, first_name, last_name, is_admin
            FROM users WHERE email = ?
        ''', (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            if not user[2]:
                return {'success': False, 'error': 'Hesabınız deaktif edilmiştir'}
            return {
                'success': True,
                'user_id': user[0],
                'is_verified': user[3],
                'first_name': user[4],
                'last_name': user[5],
                'is_admin': user[6]
            }
        return {'success': False, 'error': 'Geçersiz email veya şifre'}
    
    @staticmethod
    def get_user(user_id):
        """Kullanıcı bilgilerini getir"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, email, first_name, last_name, company, phone, 
                   is_active, is_admin, is_verified, created_at, last_login,
                   preferred_language, privacy_accepted, terms_accepted,
                   data_processing_consent, marketing_consent, ai_data_consent,
                   ai_data_retention_days, cookie_consent
            FROM users WHERE id = ?
        ''', (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'email': user[1],
                'first_name': user[2],
                'last_name': user[3],
                'company': user[4],
                'phone': user[5],
                'is_active': user[6],
                'is_admin': user[7],
                'is_verified': user[8],
                'created_at': user[9],
                'last_login': user[10],
                'preferred_language': user[11],
                'privacy_accepted': user[12],
                'terms_accepted': user[13],
                'data_processing_consent': user[14],
                'marketing_consent': user[15],
                'ai_data_consent': user[16],
                'ai_data_retention_days': user[17],
                'cookie_consent': json.loads(user[18]) if user[18] else None
            }
        return None
    
    @staticmethod
    def update_user_activity(user_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET last_activity = CURRENT_TIMESTAMP, last_login = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def update_user_consents(user_id, consents):
        """Kullanıcı onaylarını güncelle"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET 
                privacy_accepted = ?, 
                terms_accepted = ?, 
                data_processing_consent = ?,
                marketing_consent = ?,
                ai_data_consent = ?,
                ai_data_retention_days = ?,
                cookie_consent = ?
            WHERE id = ?
        ''', (
            consents.get('privacy_accepted', False),
            consents.get('terms_accepted', False),
            consents.get('data_processing_consent', False),
            consents.get('marketing_consent', False),
            consents.get('ai_data_consent', False),
            consents.get('ai_data_retention_days', 30),
            json.dumps(consents.get('cookie_consent', {})),
            user_id
        ))
        
        conn.commit()
        conn.close()


    @staticmethod
    def reset_failed_login_attempts(user_id):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = ?', (user_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Reset failed attempts error: {e}")


    @staticmethod
    def log_failed_login(email, reason='Invalid credentials'):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, failed_login_attempts FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            if user:
                new_attempts = (user[1] or 0) + 1
                cursor.execute('UPDATE users SET failed_login_attempts = ? WHERE id = ?', (new_attempts, user[0]))
                conn.commit()
            conn.close()
        except Exception as e:
            print(f"Log failed login error: {e}")



class SessionManager:
    """Oturum yönetimi"""

    @staticmethod
    def create_session(user_id, ip_address, user_agent):
        conn = get_connection()
        cursor = conn.cursor()
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=2)
        cursor.execute('''
            INSERT INTO user_sessions (user_id, session_id, ip_address, user_agent, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, session_id, ip_address, user_agent, expires_at))
        conn.commit()
        conn.close()
        return session_id
    
    @staticmethod
    def validate_session(session_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, expires_at FROM user_sessions
            WHERE session_id = ? AND is_active = TRUE
        ''', (session_id,))
        session = cursor.fetchone()
        conn.close()
        if session and datetime.fromisoformat(session[1]) > datetime.now():
            return {'valid': True, 'user_id': session[0]}
        return {'valid': False}
    
    @staticmethod
    def destroy_session(session_id):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_sessions SET is_active = FALSE WHERE session_id = ?
        ''', (session_id,))
        conn.commit()
        conn.close()


    @staticmethod
    def update_user_consents(user_id, consents):
        """Kullanıcı onaylarını güncelle"""
        try:
            conn = sqlite3.connect('bkty_consultancy.db')
            cursor = conn.cursor()
            
            # Consents tablosuna kaydet (tablo varsa)
            cursor.execute('''
                INSERT OR REPLACE INTO user_consents 
                (user_id, terms_accepted, privacy_accepted, data_processing_consent, 
                 marketing_consent, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, consents.get('terms_accepted', False),
                  consents.get('privacy_accepted', False),
                  consents.get('data_processing_consent', False),
                  consents.get('marketing_consent', False),
                  datetime.now()))
            
            conn.commit()
            conn.close()
            
        except sqlite3.OperationalError:
            # Tablo yoksa pas geç
            pass
        except Exception as e:
            logger.error(f"Update consents error: {str(e)}")

# Veritabanını başlat
if __name__ == "__main__":
    init_database()