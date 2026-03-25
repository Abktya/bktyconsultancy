#!/usr/bin/env python3
"""
BKTY Consultancy - Güvenlik Yamaları
Çalıştır: python3 bkty_security_patch.py
"""
import os
import sys
import shutil
from datetime import datetime

# ── Renkli çıktı ──────────────────────────────────────────────────────────────
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; B = "\033[94m"; E = "\033[0m"
ok  = lambda s: print(f"{G}✅ {s}{E}")
err = lambda s: print(f"{R}❌ {s}{E}")
inf = lambda s: print(f"{B}ℹ  {s}{E}")
wrn = lambda s: print(f"{Y}⚠  {s}{E}")

# ── Yedek al ──────────────────────────────────────────────────────────────────
def backup(path):
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{path}.bak_{ts}"
    shutil.copy2(path, dst)
    ok(f"Yedek alındı: {dst}")
    return dst

# ── Metin değiştir ────────────────────────────────────────────────────────────
def replace_in_file(path, old, new, label):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if old not in content:
        err(f"[{label}] Hedef metin bulunamadı — patch atlandı!")
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.replace(old, new, 1))
    ok(f"[{label}] Patch uygulandı")
    return True

# ── 1. database.py — hardcoded admin şifresi ─────────────────────────────────
DB_OLD = '''    if admin_count == 0:
        admin_password = "Mercan.2018"
        password_hash = generate_password_hash(admin_password)
        
        cursor.execute(\'\'\'
            INSERT INTO users (
                email, password_hash, first_name, last_name, 
                is_active, is_admin, is_verified, 
                privacy_accepted, terms_accepted, data_processing_consent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        \'\'\', (
            \'info@bktyconsultancy.co.uk\',
            password_hash, 
            \'Admin\', 
            \'User\',
            True, True, True, True, True, True
        ))
        
        print(f"Admin user created - Email: info@bktyconsultancy.co.uk, Password: {admin_password}")'''

DB_NEW = '''    if admin_count == 0:
        # Şifreyi env'den al, yoksa güçlü random üret
        admin_password = os.environ.get("BKTY_ADMIN_PASSWORD")
        if not admin_password:
            admin_password = secrets.token_urlsafe(16)
            creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".admin_init_creds")
            with open(creds_path, "w") as _f:
                _f.write(f"Email: info@bktyconsultancy.co.uk\\nPassword: {admin_password}\\n")
            os.chmod(creds_path, 0o600)
            print(f"[!] Admin şifresi .admin_init_creds dosyasına kaydedildi (chmod 600)")

        password_hash = generate_password_hash(admin_password)

        cursor.execute(\'\'\'
            INSERT INTO users (
                email, password_hash, first_name, last_name,
                is_active, is_admin, is_verified,
                privacy_accepted, terms_accepted, data_processing_consent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        \'\'\', (
            "info@bktyconsultancy.co.uk",
            password_hash,
            "Admin",
            "User",
            True, True, True, True, True, True
        ))

        # Şifreyi ASLA loglama
        print("Admin kullanıcı oluşturuldu — kimlik bilgileri için .admin_init_creds dosyasına bakın")'''

# ── 2. app.py — CSRF bypass düzelt ───────────────────────────────────────────
CSRF_OLD = '''def csrf_protect():
    if request.method == "POST":
        # API, VOICE ve ADMIN endpoint'leri için CSRF kontrolü YAPMA
        if (request.path.startswith('/api/') or 
            request.path.startswith('/voice/') or 
            request.path.startswith('/admin/api/') or
            request.path.startswith('/admin/') or  
            request.path.startswith('/en/admin/') or 
            request.path.startswith('/tr/admin/')):
            return
            
        token = session.get('csrf_token')
        form_token = request.form.get('csrf_token')
        if not token or token != form_token:
            abort(403)'''

CSRF_NEW = '''def csrf_protect():
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
            abort(403)'''

# ── 3. app.py — AI endpoint'leri için login zorunlu ──────────────────────────
AI_CHAT_OLD = '''@app.route('/api/ask-ai-with-code', methods=['POST'])
def ask_ai_with_code_main():
    """Ana AI chat endpoint"""'''

AI_CHAT_NEW = '''@app.route('/api/ask-ai-with-code', methods=['POST'])
@login_required
def ask_ai_with_code_main():
    """Ana AI chat endpoint — login gerektirir"""'''

GEN_IMG_OLD = '''@app.route('/api/generate-image', methods=['POST'])
def generate_image_async():
    """Asenkron görüntü üretimi - frontend uyumlu"""'''

GEN_IMG_NEW = '''@app.route('/api/generate-image', methods=['POST'])
@login_required
def generate_image_async():
    """Asenkron görüntü üretimi — login gerektirir"""'''

RESEARCH_OLD = '''@app.route('/api/research/search', methods=['POST'])
def research_search_endpoint():'''

RESEARCH_NEW = '''@app.route('/api/research/search', methods=['POST'])
@login_required
def research_search_endpoint():'''

ANALYZE_OLD = '''@app.route('/api/research/analyze', methods=['POST'])
def research_analyze_endpoint():
    """Direct webpage analysis endpoint - düzeltilmiş\"\"\"'''

ANALYZE_NEW = '''@app.route('/api/research/analyze', methods=['POST'])
@login_required
def research_analyze_endpoint():
    """Direct webpage analysis endpoint — login gerektirir — SSRF korumalı\"\"\"'''

# ── 4. app.py — SSRF koruması (analyze endpoint içi) ─────────────────────────
SSRF_OLD = '''        # Protocol ekle
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Content extractor'ı kullan'''

SSRF_NEW = '''        # Protocol ekle
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

        # Content extractor\'ı kullan'''

# ── 5. app.py — active-tasks sızıntısını kapat ───────────────────────────────
TASKS_OLD = '''@app.route('/api/active-tasks', methods=['GET'])
def get_active_tasks():
    """Aktif task'ları listele"""
    current_time = time.time()
    task_info = {}
    
    for task_id, task in active_tasks.items():
        task_info[task_id] = {
            "status": task["status"],
            "elapsed": current_time - task["started_at"],
            "prompt": task.get("prompt", "")[:50] + "..." if len(task.get("prompt", "")) > 50 else task.get("prompt", ""),
            "user_id": task.get("user_id", "unknown")
        }
    
    return jsonify({
        "total_tasks": len(active_tasks),
        "tasks": task_info
    })'''

TASKS_NEW = '''@app.route('/api/active-tasks', methods=['GET'])
@login_required
def get_active_tasks():
    """Aktif task\'ları listele — yalnızca kendi task\'larını göster"""
    current_time = time.time()
    task_info = {}
    current_uid = str(session.get("user_id", request.remote_addr))

    for task_id, task in active_tasks.items():
        # Başkasının task\'ını gösterme
        if task.get("user_id") != current_uid:
            continue
        task_info[task_id] = {
            "status": task["status"],
            "elapsed": current_time - task["started_at"],
        }

    return jsonify({
        "total_tasks": len(task_info),
        "tasks": task_info
    })'''

# ── Çalıştır ──────────────────────────────────────────────────────────────────
def main():
    base = os.path.dirname(os.path.abspath(__file__))
    db_path  = os.path.join(base, "database.py")
    app_path = os.path.join(base, "app.py")

    # Dosyaların varlığını kontrol et
    for p in [db_path, app_path]:
        if not os.path.exists(p):
            err(f"Dosya bulunamadı: {p}")
            err("Bu scripti ~/bktyconsultancy/ dizininde çalıştırın!")
            sys.exit(1)

    print(f"\n{'='*60}")
    print(f"{B}BKTY Consultancy — Güvenlik Yamaları{E}")
    print(f"{'='*60}\n")

    # Yedekler
    backup(db_path)
    backup(app_path)
    print()

    results = []

    # 1 — database.py
    inf("Patch 1/5: database.py — hardcoded admin şifresi kaldırılıyor...")
    results.append(replace_in_file(db_path, DB_OLD, DB_NEW, "DB-AdminPassword"))

    # 2 — CSRF
    inf("Patch 2/5: app.py — CSRF bypass düzeltiliyor...")
    results.append(replace_in_file(app_path, CSRF_OLD, CSRF_NEW, "CSRF-Bypass"))

    # 3a — AI chat
    inf("Patch 3a/5: app.py — AI chat endpoint login koruması...")
    results.append(replace_in_file(app_path, AI_CHAT_OLD, AI_CHAT_NEW, "AI-Chat-Auth"))

    # 3b — Image gen
    inf("Patch 3b/5: app.py — Image gen endpoint login koruması...")
    results.append(replace_in_file(app_path, GEN_IMG_OLD, GEN_IMG_NEW, "Image-Gen-Auth"))

    # 3c — Research search
    inf("Patch 3c/5: app.py — Research search endpoint login koruması...")
    results.append(replace_in_file(app_path, RESEARCH_OLD, RESEARCH_NEW, "Research-Search-Auth"))

    # 3d — Research analyze
    inf("Patch 3d/5: app.py — Research analyze endpoint login koruması...")
    results.append(replace_in_file(app_path, ANALYZE_OLD, ANALYZE_NEW, "Research-Analyze-Auth"))

    # 4 — SSRF
    inf("Patch 4/5: app.py — SSRF koruması ekleniyor...")
    results.append(replace_in_file(app_path, SSRF_OLD, SSRF_NEW, "SSRF-Protection"))

    # 5 — Tasks
    inf("Patch 5/5: app.py — active-tasks sızıntısı kapatılıyor...")
    results.append(replace_in_file(app_path, TASKS_OLD, TASKS_NEW, "Tasks-Leak"))

    # Özet
    passed = sum(results)
    total  = len(results)
    print(f"\n{'='*60}")
    if passed == total:
        ok(f"Tüm yamalar başarıyla uygulandı ({passed}/{total})")
        print(f"\n{Y}Sonraki adımlar:{E}")
        print("  1. .env dosyasına BKTY_ADMIN_PASSWORD ekleyin:")
        print("     echo \"BKTY_ADMIN_PASSWORD=$(openssl rand -base64 18)\" >> .env")
        print("  2. app_backup.py dosyasını silin:")
        print("     git rm app_backup.py && rm app_backup.py")
        print("  3. .gitignore güncellemesini yapın (ayrıca gönderdim)")
        print("  4. Servisi yeniden başlatın:")
        print("     sudo systemctl restart bktyconsultancy")
    else:
        wrn(f"{passed}/{total} patch uygulandı — bazı yamalar atlandı")
        wrn("Yukarıdaki ❌ satırlarını kontrol edin")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
