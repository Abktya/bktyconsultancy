# activity_tracking.py
import sqlite3
from datetime import datetime, timedelta
from flask import request, session
import uuid
import logging

DATABASE_PATH = 'bkty_consultancy.db'
logger = logging.getLogger(__name__)


def get_connection():
    """DB bağlantısı (timeout + WAL mod aktif)"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


class ActivityTracker:
    @staticmethod
    def log_user_activity(user_id, action, details=None, admin_user_id=None):
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO system_logs (user_id, action, details, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                action,
                details,
                request.environ.get('REMOTE_ADDR', 'unknown'),
                request.environ.get('HTTP_USER_AGENT', 'unknown')[:500]
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Activity logging error: {str(e)}")

    @staticmethod
    def create_user_session(user_id):
        try:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
            session['login_time'] = datetime.now().isoformat()

            expires_at = datetime.now() + timedelta(hours=2)

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_sessions (user_id, session_id, created_at, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                session_id,
                datetime.now(),
                expires_at,
                request.environ.get('REMOTE_ADDR', 'unknown'),
                request.environ.get('HTTP_USER_AGENT', 'unknown')
            ))

            conn.commit()
            conn.close()

            ActivityTracker.log_user_activity(user_id, 'USER_LOGIN', 'User logged in successfully')
            return session_id

        except Exception as e:
            logger.error(f"Session creation error: {str(e)}")
            return None

    @staticmethod
    def end_user_session(user_id):
        try:
            session_id = session.get('session_id')
            login_time_str = session.get('login_time')

            if not session_id:
                return

            logout_time = datetime.now()
            session_duration = None

            if login_time_str:
                try:
                    login_time = datetime.fromisoformat(login_time_str)
                    duration = logout_time - login_time
                    session_duration = int(duration.total_seconds() / 60)
                except:
                    pass

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_sessions
                SET logout_time = ?, session_duration = ?, is_active = FALSE
                WHERE session_id = ? AND user_id = ?
            ''', (logout_time, session_duration, session_id, user_id))

            conn.commit()
            conn.close()

            session.pop('session_id', None)
            session.pop('login_time', None)

            ActivityTracker.log_user_activity(
                user_id,
                'USER_LOGOUT',
                f'User logged out. Session duration: {session_duration} minutes'
                if session_duration else 'User logged out'
            )

        except Exception as e:
            logger.error(f"Session ending error: {str(e)}")
