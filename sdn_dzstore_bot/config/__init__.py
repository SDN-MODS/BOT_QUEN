"""
Configuration Manager for SDN_DZSTORE_BOT
Handles loading and accessing configuration settings
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    """Manages bot configuration from JSON and environment variables"""
    
    def __init__(self, config_path: str = "config/config.json"):
        self.config_path = Path(config_path)
        self.config = {}
        self.env = {}
        self.load()
    
    def load(self):
        """Load configuration from files"""
        # Load environment variables
        env_file = Path("config/.env")
        if env_file.exists():
            load_dotenv(env_file)
        
        # Load config JSON
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        
        # Store environment variables
        self.env = {
            'DISCORD_TOKEN': os.getenv('DISCORD_TOKEN', ''),
            'CLIENT_ID': os.getenv('CLIENT_ID', ''),
            'GUILD_ID': os.getenv('GUILD_ID', ''),
            'DATABASE_PATH': os.getenv('DATABASE_PATH', './database/store.db'),
        }
    
    def get(self, *keys, default=None):
        """Get nested configuration value"""
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def get_env(self, key: str, default=None):
        """Get environment variable"""
        return self.env.get(key, default)
    
    @property
    def token(self) -> str:
        """Get Discord bot token"""
        return self.get_env('DISCORD_TOKEN') or self.get('bot', 'token', default='')
    
    @property
    def client_id(self) -> str:
        """Get Discord client ID"""
        return self.get_env('CLIENT_ID') or self.get('bot', 'client_id', default='')
    
    @property
    def guild_id(self) -> str:
        """Get Discord guild ID"""
        return self.get_env('GUILD_ID') or self.get('bot', 'guild_id', default='')
    
    @property
    def database_path(self) -> str:
        """Get database path"""
        return self.get_env('DATABASE_PATH', './database/store.db')
    
    @property
    def store_name(self) -> str:
        """Get store name"""
        return self.get('store', 'name', default='SDN DayZ Store')
    
    @property
    def server_name(self) -> str:
        """Get server name"""
        return self.get('store', 'server_name', default='SDN DayZ Server')
    
    @property
    def currency_name(self) -> str:
        """Get currency name"""
        return self.get('store', 'currency_name', default='Coins')
    
    @property
    def currency_symbol(self) -> str:
        """Get currency symbol"""
        return self.get('store', 'currency_symbol', default='🪙')
    
    @property
    def colors(self) -> dict:
        """Get color configuration"""
        return self.get('colors', default={
            'primary': '#5865F2',
            'success': '#57F287',
            'warning': '#FEE75C',
            'error': '#ED4245',
            'info': '#5865F2'
        })
    
    @property
    def admin_roles(self) -> list:
        """Get admin role IDs"""
        return self.get('roles', 'admin', default=[])
    
    @property
    def moderator_roles(self) -> list:
        """Get moderator role IDs"""
        return self.get('roles', 'moderator', default=[])
    
    @property
    def log_channel_id(self) -> str:
        """Get logs channel ID"""
        return self.get('channels', 'logs', default='')
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.get('features', feature, default=False)


# Global config instance
config = Config()
