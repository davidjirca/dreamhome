"""
Unified enums for the dreamhome platform
Consolidates enums used across multiple modules
"""
import enum


class NotificationFrequency(str, enum.Enum):
    """
    Notification frequency for alerts and saved searches
    Used in both SavedSearch and Alert models
    """
    IMMEDIATE = "immediate"  # Real-time notifications
    INSTANT = "instant"      # Alias for immediate (for backwards compatibility)
    DAILY = "daily"          # Once per day digest
    WEEKLY = "weekly"        # Once per week digest
    DISABLED = "disabled"    # No notifications