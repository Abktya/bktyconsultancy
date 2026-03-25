# api_integration_routes.py - Flask routes for external API integration
from flask import Blueprint, request, jsonify
from external_api_service import (
    external_api_service,
    format_exchange_rate_response,
    format_news_response,
    format_movie_response
)
import logging

logger = logging.getLogger(__name__)

# Blueprint oluştur
api_integration_bp = Blueprint('api_integration', __name__, url_prefix='/api/external')


# =============================================================================
# EXCHANGE RATE ENDPOINTS
# =============================================================================

@api_integration_bp.route('/exchange-rates', methods=['GET'])
def get_exchange_rates():
    """
    Döviz kurlarını getir
    
    Query params:
        base: Ana para birimi (USD, EUR, GBP, TRY, etc.) - default: USD
    """
    try:
        base_currency = request.args.get('base', 'USD').upper()
        
        result = external_api_service.get_exchange_rates(base_currency)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Exchange rates endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@api_integration_bp.route('/exchange-rates/popular', methods=['GET'])
def get_popular_rates():
    """
    Popüler döviz kurlarını getir
    
    Query params:
        base: Ana para birimi - default: USD
    """
    try:
        base_currency = request.args.get('base', 'USD').upper()
        
        result = external_api_service.get_popular_currency_rates(base_currency)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Popular rates endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@api_integration_bp.route('/exchange-rates/convert', methods=['POST'])
def convert_currency():
    """
    Para birimi çevirme
    
    JSON body:
        {
            "amount": 100,
            "from": "USD",
            "to": "EUR"
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "JSON data required"}), 400
        
        amount = data.get('amount')
        from_currency = data.get('from', '').upper()
        to_currency = data.get('to', '').upper()
        
        if not all([amount, from_currency, to_currency]):
            return jsonify({"error": "Missing required fields: amount, from, to"}), 400
        
        try:
            amount = float(amount)
        except ValueError:
            return jsonify({"error": "Invalid amount value"}), 400
        
        result = external_api_service.convert_currency(amount, from_currency, to_currency)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Currency conversion endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# NEWS API ENDPOINTS
# =============================================================================

@api_integration_bp.route('/news/search', methods=['GET'])
def search_news():
    """
    Haberleri ara
    
    Query params:
        query: Arama terimi
        language: Dil kodu (en, tr, etc.) - default: en
        categories: Kategori (general,business,sports gibi virgülle ayrılmış)
        limit: Maksimum sonuç sayısı - default: 10
    """
    try:
        query = request.args.get('query', '').strip()
        language = request.args.get('language', 'en')
        categories_str = request.args.get('categories', '')
        limit = int(request.args.get('limit', 10))
        
        categories = [c.strip() for c in categories_str.split(',')] if categories_str else None
        
        result = external_api_service.get_news(
            query=query if query else None,
            language=language,
            categories=categories,
            limit=limit
        )
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"News search endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@api_integration_bp.route('/news/top-headlines', methods=['GET'])
def get_top_headlines():
    """
    Top headlines getir
    
    Query params:
        language: Dil kodu - default: en
        category: Kategori (general, business, technology, etc.)
        limit: Maksimum sonuç sayısı - default: 10
    """
    try:
        language = request.args.get('language', 'en')
        category = request.args.get('category', None)
        limit = int(request.args.get('limit', 10))
        
        result = external_api_service.get_top_headlines(
            language=language,
            category=category,
            limit=limit
        )
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Top headlines endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# TMDB (MOVIES) ENDPOINTS
# =============================================================================

@api_integration_bp.route('/movies/search', methods=['GET'])
def search_movies():
    """
    Film ara
    
    Query params:
        query: Arama terimi (zorunlu)
        language: Dil kodu - default: en-US
        page: Sayfa numarası - default: 1
    """
    try:
        query = request.args.get('query', '').strip()
        language = request.args.get('language', 'en-US')
        page = int(request.args.get('page', 1))
        
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400
        
        result = external_api_service.search_movies(query, language, page)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Movie search endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@api_integration_bp.route('/movies/<int:movie_id>', methods=['GET'])
def get_movie_details(movie_id):
    """
    Film detaylarını getir
    
    Query params:
        language: Dil kodu - default: en-US
    """
    try:
        language = request.args.get('language', 'en-US')
        
        result = external_api_service.get_movie_details(movie_id, language)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Movie details endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@api_integration_bp.route('/movies/popular', methods=['GET'])
def get_popular_movies():
    """
    Popüler filmleri getir
    
    Query params:
        language: Dil kodu - default: en-US
        page: Sayfa numarası - default: 1
    """
    try:
        language = request.args.get('language', 'en-US')
        page = int(request.args.get('page', 1))
        
        result = external_api_service.get_popular_movies(language, page)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Popular movies endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# AI-FORMATTED RESPONSES
# =============================================================================

@api_integration_bp.route('/ai-format/exchange-rates', methods=['GET'])
def ai_format_exchange_rates():
    """AI modeli için formatlanmış döviz kuru yanıtı"""
    try:
        base_currency = request.args.get('base', 'USD').upper()
        result = external_api_service.get_popular_currency_rates(base_currency)
        
        formatted = format_exchange_rate_response(result)
        
        return jsonify({
            "success": result.get("success", False),
            "formatted_response": formatted,
            "raw_data": result
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_integration_bp.route('/ai-format/news', methods=['GET'])
def ai_format_news():
    """AI modeli için formatlanmış haber yanıtı"""
    try:
        query = request.args.get('query', '').strip()
        language = request.args.get('language', 'en')
        limit = int(request.args.get('limit', 5))
        
        result = external_api_service.get_news(
            query=query if query else None,
            language=language,
            limit=limit
        )
        
        formatted = format_news_response(result)
        
        return jsonify({
            "success": result.get("success", False),
            "formatted_response": formatted,
            "raw_data": result
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_integration_bp.route('/ai-format/movies', methods=['GET'])
def ai_format_movies():
    """AI modeli için formatlanmış film yanıtı"""
    try:
        query = request.args.get('query', '').strip()
        movie_id = request.args.get('movie_id', '').strip()
        language = request.args.get('language', 'en-US')
        
        if movie_id:
            # Film detayı
            try:
                result = external_api_service.get_movie_details(int(movie_id), language)
            except ValueError:
                return jsonify({"error": "Invalid movie_id"}), 400
        elif query:
            # Film arama
            result = external_api_service.search_movies(query, language)
        else:
            return jsonify({"error": "Either query or movie_id is required"}), 400
        
        formatted = format_movie_response(result)
        
        return jsonify({
            "success": result.get("success", False),
            "formatted_response": formatted,
            "raw_data": result
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@api_integration_bp.route('/status', methods=['GET'])
def get_service_status():
    """Tüm API servislerinin durumunu kontrol et"""
    try:
        status = external_api_service.get_service_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_integration_bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Cache'i temizle"""
    try:
        result = external_api_service.clear_cache()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Blueprint Registration Helper
# =============================================================================

def register_api_integration_routes(app):
    """Blueprint'i Flask app'e kaydet"""
    app.register_blueprint(api_integration_bp)
    print("✅ External API integration routes registered")