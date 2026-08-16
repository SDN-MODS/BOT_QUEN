"""
Database Manager for SDN_DZSTORE_BOT
Handles SQLite database operations with async support
Prepared for future migration to PostgreSQL
"""

import aiosqlite
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class Database:
    """Manages SQLite database connections and operations"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Establish database connection"""
        self._connection = await aiosqlite.connect(str(self.db_path))
        self._connection.row_factory = aiosqlite.Row
        await self._init_tables()
    
    async def disconnect(self):
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def _init_tables(self):
        """Initialize all database tables"""
        await self._create_players_table()
        await self._create_coin_transactions_table()
        await self._create_coin_packages_table()
        await self._create_categories_table()
        await self._create_products_table()
        await self._create_cart_items_table()
        await self._create_orders_table()
        await self._create_order_items_table()
        await self._create_coupons_table()
        await self._create_payments_table()
        await self._create_admin_logs_table()
        await self._create_settings_table()
    
    async def _create_players_table(self):
        """Create players table"""
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT UNIQUE NOT NULL,
                discord_username TEXT NOT NULL,
                steam_id TEXT UNIQUE,
                player_name TEXT NOT NULL,
                coin_balance INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_access TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await self._connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_players_discord ON players(discord_id)
        ''')
        await self._connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_players_steam ON players(steam_id)
        ''')
        await self._connection.commit()
    
    async def _create_coin_transactions_table(self):
        """Create coin transactions table"""
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS coin_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                discord_id TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                amount INTEGER NOT NULL,
                balance_before INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                reason TEXT,
                order_id INTEGER,
                admin_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(id),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        ''')
        await self._connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_transactions_player ON coin_transactions(player_id)
        ''')
        await self._connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_transactions_discord ON coin_transactions(discord_id)
        ''')
        await self._connection.commit()
    
    async def _create_coin_packages_table(self):
        """Create coin packages table"""
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS coin_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                coin_amount INTEGER NOT NULL,
                bonus_amount INTEGER DEFAULT 0,
                price REAL NOT NULL,
                status TEXT DEFAULT 'active',
                display_order INTEGER DEFAULT 0,
                image_url TEXT,
                is_featured BOOLEAN DEFAULT FALSE,
                is_promotion BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await self._connection.commit()
    
    async def _create_categories_table(self):
        """Create categories table"""
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT,
                status TEXT DEFAULT 'active',
                display_order INTEGER DEFAULT 0,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await self._connection.commit()
    
    async def _create_products_table(self):
        """Create products table"""
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                category_id INTEGER,
                price INTEGER NOT NULL,
                stock INTEGER DEFAULT -1,
                image_url TEXT,
                status TEXT DEFAULT 'active',
                is_featured BOOLEAN DEFAULT FALSE,
                display_order INTEGER DEFAULT 0,
                delivery_type TEXT DEFAULT 'manual',
                delivery_data TEXT,
                discount_percent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')
        await self._connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id)
        ''')
        await self._connection.commit()
    
    async def _create_cart_items_table(self):
        """Create cart items table"""
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS cart_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        await self._connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_cart_discord ON cart_items(discord_id)
        ''')
        await self._connection.commit()
    
    async def _create_orders_table(self):
        """Create orders table"""
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL,
                discord_id TEXT NOT NULL,
                player_id INTEGER NOT NULL,
                steam_id TEXT,
                total_value INTEGER NOT NULL,
                coins_used INTEGER NOT NULL,
                coupon_code TEXT,
                discount_amount INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                payment_method TEXT,
                delivery_type TEXT,
                delivery_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(id)
            )
        ''')
        await self._connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_orders_discord ON orders(discord_id)
        ''')
        await self._connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)
        ''')
        await self._connection.commit()
    
    async def _create_order_items_table(self):
        """Create order items table"""
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price INTEGER NOT NULL,
                subtotal INTEGER NOT NULL,
                delivery_type TEXT,
                delivery_data TEXT,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        await self._connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)
        ''')
        await self._connection.commit()
    
    async def _create_coupons_table(self):
        """Create coupons table"""
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS coupons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                description TEXT,
                discount_type TEXT NOT NULL,
                discount_value INTEGER NOT NULL,
                min_purchase INTEGER DEFAULT 0,
                max_uses INTEGER,
                used_count INTEGER DEFAULT 0,
                max_uses_per_user INTEGER DEFAULT 1,
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                status TEXT DEFAULT 'active',
                applicable_products TEXT,
                applicable_categories TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await self._connection.commit()
    
    async def _create_payments_table(self):
        """Create payments table"""
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                discord_id TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_method TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                transaction_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        ''')
        await self._connection.commit()
    
    async def _create_admin_logs_table(self):
        """Create admin logs table"""
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id TEXT NOT NULL,
                admin_username TEXT,
                action TEXT NOT NULL,
                target_type TEXT,
                target_id TEXT,
                old_data TEXT,
                new_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await self._connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_logs_admin ON admin_logs(admin_id)
        ''')
        await self._connection.execute('''
            CREATE INDEX IF NOT EXISTS idx_logs_action ON admin_logs(action)
        ''')
        await self._connection.commit()
    
    async def _create_settings_table(self):
        """Create settings table"""
        await self._connection.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                type TEXT DEFAULT 'string',
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await self._connection.commit()
    
    async def execute(self, query: str, parameters: tuple = ()):
        """Execute a query and return cursor"""
        cursor = await self._connection.execute(query, parameters)
        await self._connection.commit()
        return cursor
    
    async def fetchone(self, query: str, parameters: tuple = ()) -> Optional[aiosqlite.Row]:
        """Fetch one row"""
        cursor = await self._connection.execute(query, parameters)
        return await cursor.fetchone()
    
    async def fetchall(self, query: str, parameters: tuple = ()) -> List[aiosqlite.Row]:
        """Fetch all rows"""
        cursor = await self._connection.execute(query, parameters)
        return await cursor.fetchall()
    
    async def fetchmany(self, query: str, parameters: tuple = (), size: int = 10) -> List[aiosqlite.Row]:
        """Fetch many rows"""
        cursor = await self._connection.execute(query, parameters)
        return await cursor.fetchmany(size)
    
    @property
    def connection(self) -> aiosqlite.Connection:
        """Get database connection"""
        return self._connection


# Global database instance
db = Database("./database/store.db")
