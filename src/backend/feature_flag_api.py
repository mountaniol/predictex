#!/usr/bin/env python3
"""
Feature Flag API endpoints for Flask server

Provides REST API for frontend feature flag client.
"""

from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any

from src.backend.feature_flag_manager import FeatureFlagManager, ClientMode

logger = logging.getLogger(__name__)

# Create Blueprint
feature_flag_bp = Blueprint('feature_flag', __name__)

# Initialize manager (singleton pattern)
_manager = None

def get_manager() -> FeatureFlagManager:
    """Get or create feature flag manager singleton"""
    global _manager
    if _manager is None:
        _manager = FeatureFlagManager()
    return _manager


@feature_flag_bp.route('/api/feature-flag/client-mode', methods=['POST'])
def get_client_mode():
    """
    Get client mode for a user
    
    Request body:
    {
        "userId": "user_123",
        "sessionId": "session_456"  
    }
    
    Response:
    {
        "mode": "thick" | "thin",
        "userId": "user_123",
        "sessionId": "session_456"
    }
    """
    try:
        data = request.json
        user_id = data.get('userId')
        session_id = data.get('sessionId')
        
        if not user_id:
            return jsonify({'error': 'userId required'}), 400
        
        manager = get_manager()
        mode = manager.get_user_mode(user_id, session_id)
        
        return jsonify({
            'mode': mode.value,
            'userId': user_id,
            'sessionId': session_id
        })
        
    except Exception as e:
        logger.error(f"Error getting client mode: {e}")
        return jsonify({'error': str(e)}), 500


@feature_flag_bp.route('/api/feature-flag/check', methods=['POST'])
def check_feature():
    """
    Check if a feature is enabled for a user
    
    Request body:
    {
        "userId": "user_123",
        "flagName": "new_feature"
    }
    
    Response:
    {
        "enabled": true | false,
        "userId": "user_123",
        "flagName": "new_feature"
    }
    """
    try:
        data = request.json
        user_id = data.get('userId')
        flag_name = data.get('flagName')
        
        if not user_id or not flag_name:
            return jsonify({'error': 'userId and flagName required'}), 400
        
        manager = get_manager()
        enabled = manager.is_enabled(user_id, flag_name)
        
        return jsonify({
            'enabled': enabled,
            'userId': user_id,
            'flagName': flag_name
        })
        
    except Exception as e:
        logger.error(f"Error checking feature: {e}")
        return jsonify({'error': str(e)}), 500


@feature_flag_bp.route('/api/feature-flag/ab-test', methods=['POST'])
def get_ab_test_group():
    """
    Get A/B test group for a user
    
    Request body:
    {
        "userId": "user_123",
        "testName": "new_ui_test"
    }
    
    Response:
    {
        "group": "A" | "B",
        "userId": "user_123",
        "testName": "new_ui_test"
    }
    """
    try:
        data = request.json
        user_id = data.get('userId')
        test_name = data.get('testName')
        
        if not user_id or not test_name:
            return jsonify({'error': 'userId and testName required'}), 400
        
        manager = get_manager()
        group = manager.get_ab_test_group(user_id, test_name)
        
        return jsonify({
            'group': group,
            'userId': user_id,
            'testName': test_name
        })
        
    except Exception as e:
        logger.error(f"Error getting A/B test group: {e}")
        return jsonify({'error': str(e)}), 500


# Admin endpoints (should be protected in production)

@feature_flag_bp.route('/api/feature-flag/admin/list', methods=['GET'])
def list_flags():
    """
    List all feature flags
    
    Response:
    {
        "flags": {
            "server_driven_ui": {
                "enabled": true,
                "percentage": 30,
                "description": "...",
                "userOverrides": ["user1"],
                "userExcludes": ["user2"]
            }
        }
    }
    """
    try:
        manager = get_manager()
        
        flags_data = {}
        for flag_name, flag in manager.flags.items():
            flags_data[flag_name] = {
                'enabled': flag.enabled,
                'percentage': flag.percentage,
                'description': flag.description,
                'userOverrides': list(flag.user_overrides),
                'userExcludes': list(flag.user_excludes)
            }
        
        return jsonify({'flags': flags_data})
        
    except Exception as e:
        logger.error(f"Error listing flags: {e}")
        return jsonify({'error': str(e)}), 500


@feature_flag_bp.route('/api/feature-flag/admin/update', methods=['POST'])
def update_flag():
    """
    Update a feature flag
    
    Request body:
    {
        "flagName": "server_driven_ui",
        "enabled": true,
        "percentage": 50,
        "userOverrides": ["user1"],
        "userExcludes": ["user2"]
    }
    
    Response:
    {
        "success": true,
        "flagName": "server_driven_ui"
    }
    """
    try:
        data = request.json
        flag_name = data.get('flagName')
        
        if not flag_name:
            return jsonify({'error': 'flagName required'}), 400
        
        manager = get_manager()
        
        # Build update kwargs
        updates = {}
        if 'enabled' in data:
            updates['enabled'] = data['enabled']
        if 'percentage' in data:
            updates['percentage'] = data['percentage']
        if 'userOverrides' in data:
            updates['user_overrides'] = data['userOverrides']
        if 'userExcludes' in data:
            updates['user_excludes'] = data['userExcludes']
        if 'description' in data:
            updates['description'] = data['description']
        
        success = manager.update_flag(flag_name, **updates)
        
        if success:
            return jsonify({
                'success': True,
                'flagName': flag_name
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Update failed'
            }), 400
        
    except Exception as e:
        logger.error(f"Error updating flag: {e}")
        return jsonify({'error': str(e)}), 500


@feature_flag_bp.route('/api/feature-flag/admin/rollback', methods=['POST'])
def emergency_rollback():
    """
    Emergency rollback a feature flag
    
    Request body:
    {
        "flagName": "server_driven_ui"
    }
    
    Response:
    {
        "success": true,
        "flagName": "server_driven_ui",
        "message": "Emergency rollback completed"
    }
    """
    try:
        data = request.json
        flag_name = data.get('flagName')
        
        if not flag_name:
            return jsonify({'error': 'flagName required'}), 400
        
        manager = get_manager()
        success = manager.emergency_rollback(flag_name)
        
        if success:
            return jsonify({
                'success': True,
                'flagName': flag_name,
                'message': 'Emergency rollback completed'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Rollback failed'
            }), 400
        
    except Exception as e:
        logger.error(f"Error during emergency rollback: {e}")
        return jsonify({'error': str(e)}), 500


@feature_flag_bp.route('/api/feature-flag/admin/stats', methods=['GET'])
def get_stats():
    """
    Get rollout statistics
    
    Query params:
    ?flagName=server_driven_ui
    
    Response:
    {
        "flagName": "server_driven_ui",
        "enabled": true,
        "percentage": 30,
        "overrideCount": 5,
        "excludeCount": 2,
        "thinSessions": 150,
        "thickSessions": 350,
        "totalSessions": 500
    }
    """
    try:
        flag_name = request.args.get('flagName', 'server_driven_ui')
        
        manager = get_manager()
        stats = manager.get_rollout_stats(flag_name)
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500


@feature_flag_bp.route('/api/feature-flag/admin/reload', methods=['POST'])
def reload_config():
    """
    Hot reload configuration from file
    
    Response:
    {
        "success": true,
        "message": "Configuration reloaded"
    }
    """
    try:
        manager = get_manager()
        manager.reload_config()
        
        return jsonify({
            'success': True,
            'message': 'Configuration reloaded'
        })
        
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        return jsonify({'error': str(e)}), 500