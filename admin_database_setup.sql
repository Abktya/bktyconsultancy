-- admin_database_setup.sql

-- 1. Mevcut users tablosuna yeni sütunlar ekle
ALTER TABLE users ADD COLUMN email_verified_at DATETIME NULL;
ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN locked_until DATETIME NULL;
ALTER TABLE users ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN deleted_at DATETIME NULL;
ALTER TABLE users ADD COLUMN deleted_by INTEGER NULL;

-- 2. Kullanıcı aktiviteleri tablosu
CREATE TABLE IF NOT EXISTS user_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    admin_user_id INTEGER NULL, -- Hangi admin bu işlemi yaptı
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (admin_user_id) REFERENCES users(id)
);

-- 3. Kullanıcı session geçmişi
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token VARCHAR(255) NOT NULL,
    login_time DATETIME NOT NULL,
    logout_time DATETIME NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    session_duration INTEGER NULL, -- dakika cinsinden
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 4. Sistem logları (admin işlemleri)
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NULL, -- Hangi kullanıcı bu işlemi yaptı
    action VARCHAR(100) NOT NULL,
    details TEXT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    severity VARCHAR(20) DEFAULT 'INFO', -- INFO, WARNING, ERROR, CRITICAL
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 5. Hata raporları
CREATE TABLE IF NOT EXISTS error_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NULL,
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    error_trace TEXT NULL,
    url VARCHAR(500) NULL,
    status VARCHAR(20) DEFAULT 'open', -- open, investigating, resolved, closed
    assigned_to INTEGER NULL,
    resolved_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (assigned_to) REFERENCES users(id)
);

-- 6. AI sohbet geçmişi (daha detaylı)
CREATE TABLE IF NOT EXISTS ai_chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id VARCHAR(255) NULL,
    message_type VARCHAR(20) NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    response_time REAL NULL, -- saniye cinsinden
    tokens_used INTEGER NULL,
    model_used VARCHAR(50) NULL,
    rating INTEGER NULL, -- 1-5 arası kullanıcı değerlendirmesi
    feedback TEXT NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 7. İletişim form mesajları
CREATE TABLE IF NOT EXISTS contact_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'new', -- new, read, replied, closed
    assigned_to INTEGER NULL,
    replied_at DATETIME NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_to) REFERENCES users(id)
);

-- 8. Admin bildirimler
CREATE TABLE IF NOT EXISTS admin_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'info', -- info, warning, error, success
    is_read BOOLEAN DEFAULT FALSE,
    user_id INTEGER NULL, -- Hangi admin için
    action_url VARCHAR(500) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 9. Sistem ayarları
CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT NULL,
    setting_type VARCHAR(20) DEFAULT 'string', -- string, integer, boolean, json
    description TEXT NULL,
    updated_by INTEGER NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES users(id)
);

-- İndeksler - Performans için
CREATE INDEX IF NOT EXISTS idx_user_activities_user_id ON user_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_user_activities_created_at ON user_activities(created_at);
CREATE INDEX IF NOT EXISTS idx_user_activities_action ON user_activities(action);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_user_sessions_login_time ON user_sessions(login_time);

CREATE INDEX IF NOT EXISTS idx_system_logs_user_id ON system_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_system_logs_action ON system_logs(action);

CREATE INDEX IF NOT EXISTS idx_ai_chat_user_id ON ai_chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_created_at ON ai_chat_history(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_chat_session_id ON ai_chat_history(session_id);

CREATE INDEX IF NOT EXISTS idx_error_reports_user_id ON error_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_error_reports_status ON error_reports(status);
CREATE INDEX IF NOT EXISTS idx_error_reports_created_at ON error_reports(created_at);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_is_verified ON users(is_verified);
CREATE INDEX IF NOT EXISTS idx_users_is_deleted ON users(is_deleted);

-- Başlangıç verileri
INSERT OR IGNORE INTO system_settings (setting_key, setting_value, setting_type, description) VALUES
('site_maintenance', 'false', 'boolean', 'Site bakım modunda mı?'),
('max_login_attempts', '5', 'integer', 'Maksimum başarısız giriş denemesi'),
('session_timeout', '1440', 'integer', 'Session timeout (dakika)'),
('ai_rate_limit', '100', 'integer', 'Günlük AI sorgu limiti'),
('new_user_approval', 'false', 'boolean', 'Yeni kullanıcılar admin onayı gerektirsin mi?');

-- Örnek admin bildirimleri
INSERT OR IGNORE INTO admin_notifications (title, message, type) VALUES
('System Started', 'Admin dashboard successfully initialized', 'success'),
('Database Updated', 'New database tables created for enhanced admin features', 'info');