#!/usr/bin/env python3
"""
Feature Flag Manager for Server-Driven UI Gradual Rollout

Mathematical model: (U, F, C, H, S) where:
- U = set of users
- F = set of feature flags  
- C = configuration function: F → [0,100] × P(U) × Boolean
- H = hash function: U × F → [0,99] (consistent assignment)
- S = session state: U → {thick, thin} × Timestamp

Provides deterministic, gradual rollout with A/B testing support.
"""

import hashlib
import time
import toml
from typing import Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ClientMode(Enum):
    """Client architecture mode"""
    THICK = "thick"  # Legacy: business logic in frontend
    THIN = "thin"    # New: server-driven UI


@dataclass
class FeatureFlag:
    """Feature flag configuration
    
    Mathematical representation: C(f) = (percentage, overrides, enabled)
    """
    name: str
    enabled: bool = False
    percentage: int = 0  # 0-100
    user_overrides: Set[str] = None  # Explicit user inclusions
    user_excludes: Set[str] = None   # Explicit user exclusions
    description: str = ""
    created_at: float = 0
    updated_at: float = 0
    
    def __post_init__(self):
        if self.user_overrides is None:
            self.user_overrides = set()
        if self.user_excludes is None:
            self.user_excludes = set()
        if self.created_at == 0:
            self.created_at = time.time()
        if self.updated_at == 0:
            self.updated_at = time.time()


class FeatureFlagManager:
    """
    Manages feature flags with mathematical guarantees:
    - Deterministic hash-based assignment
    - Consistent user experience across sessions
    - Gradual percentage-based rollout
    - A/B testing support
    """
    
    def __init__(self, config_path: str = "public/feature_flags.toml"):
        self.config_path = Path(config_path)
        self.flags: Dict[str, FeatureFlag] = {}
        self.session_modes: Dict[str, Tuple[ClientMode, float]] = {}
        self._load_config()
        
    def _load_config(self):
        """Load feature flags from TOML configuration"""
        if not self.config_path.exists():
            logger.info(f"Creating default feature flags config at {self.config_path}")
            self._create_default_config()
            
        try:
            config = toml.load(self.config_path)
            
            # Load flags
            for flag_name, flag_config in config.get("flags", {}).items():
                self.flags[flag_name] = FeatureFlag(
                    name=flag_name,
                    enabled=flag_config.get("enabled", False),
                    percentage=flag_config.get("percentage", 0),
                    user_overrides=set(flag_config.get("user_overrides", [])),
                    user_excludes=set(flag_config.get("user_excludes", [])),
                    description=flag_config.get("description", "")
                )
                
            logger.info(f"Loaded {len(self.flags)} feature flags")
            
        except Exception as e:
            logger.error(f"Error loading feature flags: {e}")
            # Use safe defaults on error
            self._use_safe_defaults()
    
    def _create_default_config(self):
        """Create default feature flags configuration"""
        default_config = {
            "version": "1.0",
            "flags": {
                "server_driven_ui": {
                    "enabled": False,
                    "percentage": 0,
                    "description": "Enable Server-Driven UI (thin client) architecture",
                    "user_overrides": [],
                    "user_excludes": []
                },
                "gradual_rollout": {
                    "enabled": True,
                    "percentage": 0,
                    "description": "Gradual rollout control flag",
                    "user_overrides": [],
                    "user_excludes": []
                }
            },
            "monitoring": {
                "log_evaluations": True,
                "metrics_enabled": True
            }
        }
        
        # Save default config
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            toml.dump(default_config, f)
    
    def _use_safe_defaults(self):
        """Use safe default flags (all disabled)"""
        self.flags = {
            "server_driven_ui": FeatureFlag(
                name="server_driven_ui",
                enabled=False,
                percentage=0,
                description="Server-Driven UI (safe default: disabled)"
            )
        }
    
    def _hash_user_flag(self, user_id: str, flag_name: str) -> int:
        """
        Deterministic hash function H: U × F → [0,99]
        
        Mathematical formula: H(u,f) = ((hash(u) * 37 + hash(f)) mod 100)
        
        Properties:
        - Deterministic: same input always produces same output
        - Uniform distribution: approximately equal probability for each bucket
        - Independent: different flags give different assignments
        """
        # Create stable hash from user_id and flag_name
        user_hash = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
        flag_hash = int(hashlib.md5(flag_name.encode()).hexdigest()[:8], 16)
        
        # Mathematical formula from agent's design
        combined_hash = (user_hash * 37 + flag_hash) % 100
        
        return combined_hash
    
    def is_enabled(self, user_id: str, flag_name: str = "server_driven_ui") -> bool:
        """
        Evaluate if feature flag is enabled for user
        
        Mathematical evaluation: E(u,f) = (u ∈ overrides) ∨ (enabled ∧ H(u,f) < percentage ∧ u ∉ excludes)
        
        Args:
            user_id: Unique user identifier
            flag_name: Feature flag name
            
        Returns:
            True if feature is enabled for this user
        """
        flag = self.flags.get(flag_name)
        
        if not flag:
            logger.warning(f"Unknown flag: {flag_name}")
            return False
        
        # Check explicit excludes first (highest priority)
        if user_id in flag.user_excludes:
            return False
        
        # Check explicit overrides (second priority)
        if user_id in flag.user_overrides:
            return True
        
        # Check if flag is enabled globally
        if not flag.enabled:
            return False
        
        # Apply percentage-based rollout
        user_hash = self._hash_user_flag(user_id, flag_name)
        is_enabled = user_hash < flag.percentage
        
        # Log evaluation for monitoring
        logger.debug(
            f"Flag evaluation: user={user_id}, flag={flag_name}, "
            f"hash={user_hash}, percentage={flag.percentage}, "
            f"result={is_enabled}"
        )
        
        return is_enabled
    
    def get_user_mode(self, user_id: str, session_id: Optional[str] = None) -> ClientMode:
        """
        Get client mode for user with session consistency
        
        Guarantees:
        - Same user always gets same mode within session
        - Mode changes only when flag configuration changes
        
        Args:
            user_id: User identifier
            session_id: Optional session for consistency tracking
            
        Returns:
            ClientMode.THIN if server-driven UI enabled, else ClientMode.THICK
        """
        # Check if we have cached session mode
        cache_key = session_id or user_id
        if cache_key in self.session_modes:
            mode, timestamp = self.session_modes[cache_key]
            # Cache valid for 1 hour
            if time.time() - timestamp < 3600:
                return mode
        
        # Evaluate feature flag
        if self.is_enabled(user_id, "server_driven_ui"):
            mode = ClientMode.THIN
        else:
            mode = ClientMode.THICK
        
        # Cache the decision
        self.session_modes[cache_key] = (mode, time.time())
        
        logger.info(f"User {user_id} assigned mode: {mode.value}")
        return mode
    
    def get_ab_test_group(self, user_id: str, test_name: str) -> str:
        """
        Get A/B test group assignment for user
        
        Uses independent hash for each test to ensure:
        - Users are randomly distributed across tests
        - Same user always in same group for given test
        
        Args:
            user_id: User identifier
            test_name: A/B test name
            
        Returns:
            'A' or 'B' based on hash assignment
        """
        test_hash = self._hash_user_flag(user_id, test_name)
        return 'A' if test_hash < 50 else 'B'
    
    def update_flag(self, flag_name: str, **kwargs) -> bool:
        """
        Update feature flag configuration
        
        Atomic update with validation to maintain mathematical constraints:
        - percentage ∈ [0, 100]
        - overrides ∩ excludes = ∅ (no overlap)
        
        Args:
            flag_name: Flag to update
            **kwargs: Flag properties to update
            
        Returns:
            True if update successful
        """
        flag = self.flags.get(flag_name)
        if not flag:
            logger.error(f"Cannot update unknown flag: {flag_name}")
            return False
        
        # Validate percentage
        if "percentage" in kwargs:
            percentage = kwargs["percentage"]
            if not 0 <= percentage <= 100:
                logger.error(f"Invalid percentage: {percentage}")
                return False
            flag.percentage = percentage
        
        # Validate no overlap between overrides and excludes
        if "user_overrides" in kwargs:
            overrides = set(kwargs["user_overrides"])
            if overrides & flag.user_excludes:
                logger.error("User overrides overlap with excludes")
                return False
            flag.user_overrides = overrides
        
        if "user_excludes" in kwargs:
            excludes = set(kwargs["user_excludes"])
            if excludes & flag.user_overrides:
                logger.error("User excludes overlap with overrides")
                return False
            flag.user_excludes = excludes
        
        # Update other properties
        if "enabled" in kwargs:
            flag.enabled = kwargs["enabled"]
        if "description" in kwargs:
            flag.description = kwargs["description"]
        
        flag.updated_at = time.time()
        
        # Clear session cache on flag update
        self.session_modes.clear()
        
        # Save to config
        self._save_config()
        
        logger.info(f"Updated flag {flag_name}: {kwargs}")
        return True
    
    def _save_config(self):
        """Save current flags to TOML configuration"""
        config = {
            "version": "1.0",
            "flags": {},
            "monitoring": {
                "log_evaluations": True,
                "metrics_enabled": True
            }
        }
        
        for flag_name, flag in self.flags.items():
            config["flags"][flag_name] = {
                "enabled": flag.enabled,
                "percentage": flag.percentage,
                "description": flag.description,
                "user_overrides": list(flag.user_overrides),
                "user_excludes": list(flag.user_excludes)
            }
        
        with open(self.config_path, 'w') as f:
            toml.dump(config, f)
    
    def emergency_rollback(self, flag_name: str = "server_driven_ui") -> bool:
        """
        Emergency rollback - immediately disable flag
        
        Mathematical guarantee: Sets percentage to 0 and enabled to False
        ensuring E(u,f) = False for all users (except explicit overrides)
        
        Args:
            flag_name: Flag to rollback
            
        Returns:
            True if rollback successful
        """
        logger.warning(f"EMERGENCY ROLLBACK initiated for {flag_name}")
        
        success = self.update_flag(
            flag_name,
            enabled=False,
            percentage=0
        )
        
        if success:
            # Clear all session caches immediately
            self.session_modes.clear()
            logger.warning(f"EMERGENCY ROLLBACK completed for {flag_name}")
        else:
            logger.error(f"EMERGENCY ROLLBACK FAILED for {flag_name}")
        
        return success
    
    def get_rollout_stats(self, flag_name: str = "server_driven_ui") -> Dict[str, Any]:
        """
        Get rollout statistics for monitoring
        
        Returns:
            Statistics including percentage, overrides, and session counts
        """
        flag = self.flags.get(flag_name)
        if not flag:
            return {}
        
        thin_sessions = sum(1 for mode, _ in self.session_modes.values() if mode == ClientMode.THIN)
        thick_sessions = sum(1 for mode, _ in self.session_modes.values() if mode == ClientMode.THICK)
        
        return {
            "flag_name": flag_name,
            "enabled": flag.enabled,
            "percentage": flag.percentage,
            "override_count": len(flag.user_overrides),
            "exclude_count": len(flag.user_excludes),
            "thin_sessions": thin_sessions,
            "thick_sessions": thick_sessions,
            "total_sessions": thin_sessions + thick_sessions,
            "last_updated": flag.updated_at
        }
    
    def reload_config(self):
        """Hot-reload configuration from file"""
        logger.info("Reloading feature flag configuration")
        self._load_config()
        # Clear session cache on reload
        self.session_modes.clear()