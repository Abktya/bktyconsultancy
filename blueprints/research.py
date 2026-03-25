# blueprints/research.py - AI Web Research Blueprint

from flask import Blueprint, request, jsonify, send_from_directory, current_app, session
import asyncio
import os
import traceback
import time
from datetime import datetime
from typing import Dict, Any
import logging

# Research agent'ı import et
try:
    from ai_web_research_agent import WebResearchAgent, EnhancedMultiUserOllamaRunner
    RESEARCH_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ AI Web Research Agent import error: {e}")
    RESEARCH_AVAILABLE = False
    WebResearchAgent = None

# Blueprint oluştur
research_bp = Blueprint('research', __name__, url_prefix='/api/research')

# Global research agent - Flask app context'inde başlatılacak
research_agent = None

logger = logging.getLogger(__name__)

def init_research_agent(ollama_runner):
    """Research agent'ı başlat"""
    global research_agent
    if RESEARCH_AVAILABLE and ollama_runner:
        try:
            research_agent = WebResearchAgent(ollama_runner)
            logger.info("Research agent initialized successfully")
            return research_agent
        except Exception as e:
            logger.error(f"Research agent initialization failed: {e}")
            return None
    else:
        logger.warning("Research agent not available - dependencies missing")
        return None

def get_research_agent():
    """Research agent'ı al"""
    if not RESEARCH_AVAILABLE:
        raise RuntimeError("Research functionality not available. Missing dependencies.")
    if research_agent is None:
        raise RuntimeError("Research agent başlatılmamış. init_research_agent() çağrılmalı.")
    return research_agent

def require_research_agent(f):
    """Research agent gerekli olan endpoint'ler için decorator"""
    def decorated_function(*args, **kwargs):
        try:
            get_research_agent()
            return f(*args, **kwargs)
        except RuntimeError as e:
            return jsonify({
                "success": False,
                "error": str(e),
                "available": RESEARCH_AVAILABLE
            }), 503
    decorated_function.__name__ = f.__name__
    return decorated_function

@research_bp.route('/status', methods=['GET'])
def research_status():
    """Research system durumu"""
    return jsonify({
        "success": True,
        "research_available": RESEARCH_AVAILABLE,
        "agent_initialized": research_agent is not None,
        "timestamp": datetime.now().isoformat()
    })

@research_bp.route('/search', methods=['POST'])
@require_research_agent
def web_search():
    """Web araması endpoint'i"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        max_results = data.get('max_results', 10)
        user_id = data.get('user_id', f"user_{request.remote_addr}")
        
        if not query:
            return jsonify({
                "success": False,
                "error": "Arama sorgusu gerekli"
            }), 400
        
        # User activity tracking
        if 'user_id' in session:
            try:
                from activity_tracking import ActivityTracker
                ActivityTracker.log_user_activity(
                    session['user_id'], 
                    'WEB_SEARCH', 
                    f'Web search: {query[:50]}'
                )
            except:
                pass
        
        agent = get_research_agent()
        
        # Async search'i senkron olarak çalıştır
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                agent.perform_web_search(query, max_results)
            )
        finally:
            loop.close()
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "action": "web_search",
                "query": query,
                "results": result["results"],
                "total_results": result["total_results"],
                "search_time": result.get("search_time", 0),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Arama başarısız")
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Web search error: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Arama hatası: {str(e)}"
        }), 500

@research_bp.route('/analyze', methods=['POST'])
@require_research_agent
def analyze_webpage():
    """Web sayfası analizi endpoint'i"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        user_id = data.get('user_id', f"user_{request.remote_addr}")
        
        if not url:
            return jsonify({
                "success": False,
                "error": "URL gerekli"
            }), 400
        
        # URL validasyonu
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # User activity tracking
        if 'user_id' in session:
            try:
                from activity_tracking import ActivityTracker
                ActivityTracker.log_user_activity(
                    session['user_id'], 
                    'WEBPAGE_ANALYSIS', 
                    f'Analyzed: {url}'
                )
            except:
                pass
        
        agent = get_research_agent()
        
        # Async analyze'i senkron olarak çalıştır
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                agent.analyze_webpage(url)
            )
        finally:
            loop.close()
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "action": "analyze_webpage",
                "url": url,
                "title": result.get("title", ""),
                "description": result.get("description", ""),
                "content_summary": result.get("content_summary", ""),
                "word_count": result.get("word_count", 0),
                "domain": result.get("domain", ""),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Sayfa analizi başarısız")
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Webpage analysis error: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Sayfa analizi hatası: {str(e)}"
        }), 500

@research_bp.route('/screenshot', methods=['POST'])
@require_research_agent
def take_screenshot():
    """Web sayfası screenshot endpoint'i"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        full_page = data.get('full_page', True)
        wait_time = data.get('wait_time', 3)
        user_id = data.get('user_id', f"user_{request.remote_addr}")
        
        if not url:
            return jsonify({
                "success": False,
                "error": "URL gerekli"
            }), 400
        
        # URL validasyonu
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # User activity tracking
        if 'user_id' in session:
            try:
                from activity_tracking import ActivityTracker
                ActivityTracker.log_user_activity(
                    session['user_id'], 
                    'SCREENSHOT', 
                    f'Screenshot: {url}'
                )
            except:
                pass
        
        agent = get_research_agent()
        
        # Screenshot al
        screenshot_result = agent.web_module.screenshot_agent.take_screenshot(
            url=url,
            wait_time=wait_time,
            full_page=full_page
        )
        
        if screenshot_result.get("success"):
            # Screenshot'ı static dizine taşı
            screenshot_path = screenshot_result["screenshot_path"]
            static_screenshots = os.path.join(current_app.static_folder, "screenshots")
            os.makedirs(static_screenshots, exist_ok=True)
            
            filename = os.path.basename(screenshot_path)
            new_path = os.path.join(static_screenshots, filename)
            
            try:
                if os.path.exists(screenshot_path):
                    if screenshot_path != new_path:
                        os.rename(screenshot_path, new_path)
                    
                    return jsonify({
                        "success": True,
                        "action": "take_screenshot",
                        "url": url,
                        "screenshot_path": new_path,
                        "screenshot_url": f"/static/screenshots/{filename}",
                        "file_size": screenshot_result.get("file_size", 0),
                        "full_page": full_page,
                        "processing_time": screenshot_result.get("processing_time", 0),
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Screenshot dosyası oluşturulamadı"
                    }), 500
            except Exception as file_error:
                current_app.logger.error(f"Screenshot file handling error: {file_error}")
                return jsonify({
                    "success": False,
                    "error": f"Dosya işleme hatası: {str(file_error)}"
                }), 500
        else:
            return jsonify({
                "success": False,
                "error": screenshot_result.get("error", "Screenshot alınamadı")
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Screenshot error: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Screenshot hatası: {str(e)}"
        }), 500

@research_bp.route('/comprehensive', methods=['POST'])
@require_research_agent
def comprehensive_research():
    """Kapsamlı araştırma endpoint'i"""
    try:
        data = request.get_json()
        topic = data.get('topic', '').strip()
        depth = data.get('depth', 'detailed')  # basic, detailed, comprehensive
        user_id = data.get('user_id', f"user_{request.remote_addr}")
        
        if not topic:
            return jsonify({
                "success": False,
                "error": "Araştırma konusu gerekli"
            }), 400
        
        if depth not in ['basic', 'detailed', 'comprehensive']:
            depth = 'detailed'
        
        # User activity tracking
        if 'user_id' in session:
            try:
                from activity_tracking import ActivityTracker
                ActivityTracker.log_user_activity(
                    session['user_id'], 
                    'COMPREHENSIVE_RESEARCH', 
                    f'Research: {topic} ({depth})'
                )
            except:
                pass
        
        agent = get_research_agent()
        
        # Async comprehensive research'i senkron olarak çalıştır
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                agent.comprehensive_research(topic, depth)
            )
        finally:
            loop.close()
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "action": "comprehensive_research",
                "topic": topic,
                "depth": depth,
                "session_id": result.get("session_id", ""),
                "results": result["results"],
                "total_results": result["total_results"],
                "research_queries": result.get("research_queries", []),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Kapsamlı araştırma başarısız")
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Comprehensive research error: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Kapsamlı araştırma hatası: {str(e)}"
        }), 500

@research_bp.route('/intent', methods=['POST'])
@require_research_agent
def detect_intent():
    """Araştırma isteği algılama endpoint'i"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            return jsonify({
                "success": False,
                "error": "Prompt gerekli"
            }), 400
        
        agent = get_research_agent()
        intent = agent.detect_research_intent(prompt)
        
        return jsonify({
            "success": True,
            "prompt": prompt,
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Intent detection error: {e}")
        return jsonify({
            "success": False,
            "error": f"Intent algılama hatası: {str(e)}"
        }), 500

@research_bp.route('/tools', methods=['GET'])
@require_research_agent
def get_available_tools():
    """Mevcut araştırma araçlarını listele"""
    try:
        agent = get_research_agent()
        
        return jsonify({
            "success": True,
            "tools": agent.available_tools,
            "total_tools": len(agent.available_tools),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Tools listing error: {e}")
        return jsonify({
            "success": False,
            "error": f"Araç listesi alınamadı: {str(e)}"
        }), 500

@research_bp.route('/stats', methods=['GET'])
@require_research_agent
def get_research_stats():
    """Araştırma istatistikleri"""
    try:
        agent = get_research_agent()
        web_stats = agent.web_module.get_stats()
        
        return jsonify({
            "success": True,
            "stats": web_stats,
            "active_sessions": len(agent.active_research_sessions),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Stats error: {e}")
        return jsonify({
            "success": False,
            "error": f"İstatistik alınamadı: {str(e)}"
        }), 500

@research_bp.route('/test', methods=['GET'])
def test_research_capabilities():
    """Araştırma yeteneklerini test et"""
    try:
        if not RESEARCH_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Research dependencies not available",
                "research_available": False
            })
        
        if research_agent is None:
            return jsonify({
                "success": False,
                "error": "Research agent not initialized",
                "research_available": True,
                "agent_initialized": False
            })
        
        agent = get_research_agent()
        
        # Test sonuçları
        test_results = {
            "selenium_available": hasattr(agent.web_module.screenshot_agent, 'driver_options'),
            "search_engines": list(agent.web_module.search_agent.search_engines.keys()),
            "tools_available": list(agent.available_tools.keys()),
            "web_module_stats": agent.web_module.get_stats()
        }
        
        return jsonify({
            "success": True,
            "test_results": test_results,
            "research_available": RESEARCH_AVAILABLE,
            "agent_initialized": True,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Test error: {e}")
        return jsonify({
            "success": False,
            "error": f"Test hatası: {str(e)}"
        }), 500

# Screenshot dosyalarını servis etmek için yardımcı route
@research_bp.route('/screenshot/<filename>')
def serve_screenshot(filename):
    """Screenshot dosyalarını servis et"""
    try:
        screenshots_dir = os.path.join(current_app.static_folder, "screenshots")
        if not os.path.exists(screenshots_dir):
            return jsonify({"error": "Screenshot dizini bulunamadı"}), 404
        
        return send_from_directory(screenshots_dir, filename)
    except Exception as e:
        current_app.logger.error(f"Screenshot serve error: {e}")
        return jsonify({"error": "Dosya servis edilemedi"}), 500

# Blueprint cleanup fonksiyonu
def cleanup_research_blueprint():
    """Blueprint temizlik işlemleri"""
    global research_agent
    if research_agent:
        try:
            research_agent.cleanup()
        except Exception as e:
            logger.error(f"Research agent cleanup error: {e}")
        finally:
            research_agent = None