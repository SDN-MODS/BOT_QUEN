"""
Player Service for SDN_DZSTORE_BOT
Handles player registration, account management, and data operations
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from database import db


class PlayerService:
    """Manages player accounts and operations"""
    
    @staticmethod
    async def get_player_by_discord(discord_id: str) -> Optional[Dict]:
        """Get player by Discord ID"""
        row = await db.fetchone(
            "SELECT * FROM players WHERE discord_id = ?",
            (discord_id,)
        )
        if row:
            return dict(row)
        return None
    
    @staticmethod
    async def get_player_by_steam(steam_id: str) -> Optional[Dict]:
        """Get player by Steam ID"""
        row = await db.fetchone(
            "SELECT * FROM players WHERE steam_id = ?",
            (steam_id,)
        )
        if row:
            return dict(row)
        return None
    
    @staticmethod
    async def get_player_by_id(player_id: int) -> Optional[Dict]:
        """Get player by internal ID"""
        row = await db.fetchone(
            "SELECT * FROM players WHERE id = ?",
            (player_id,)
        )
        if row:
            return dict(row)
        return None
    
    @staticmethod
    async def player_exists(discord_id: str) -> bool:
        """Check if player exists"""
        row = await db.fetchone(
            "SELECT 1 FROM players WHERE discord_id = ?",
            (discord_id,)
        )
        return row is not None
    
    @staticmethod
    async def steam_exists(steam_id: str) -> bool:
        """Check if Steam ID is already registered"""
        row = await db.fetchone(
            "SELECT 1 FROM players WHERE steam_id = ?",
            (steam_id,)
        )
        return row is not None
    
    @staticmethod
    async def create_player(
        discord_id: str,
        discord_username: str,
        steam_id: str,
        player_name: str
    ) -> Dict:
        """Create a new player account"""
        cursor = await db.execute(
            """
            INSERT INTO players (discord_id, discord_username, steam_id, player_name, coin_balance)
            VALUES (?, ?, ?, ?, 0)
            """,
            (discord_id, discord_username, steam_id, player_name)
        )
        
        player = await PlayerService.get_player_by_discord(discord_id)
        return player
    
    @staticmethod
    async def update_player(discord_id: str, **kwargs) -> Optional[Dict]:
        """Update player information"""
        allowed_fields = ['discord_username', 'steam_id', 'player_name', 'status']
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return await PlayerService.get_player_by_discord(discord_id)
        
        updates.append("updated_at = ?")
        values.append(datetime.now())
        
        values.append(discord_id)
        
        await db.execute(
            f"UPDATE players SET {', '.join(updates)} WHERE discord_id = ?",
            tuple(values)
        )
        
        return await PlayerService.get_player_by_discord(discord_id)
    
    @staticmethod
    async def update_last_access(discord_id: str):
        """Update player's last access time"""
        await db.execute(
            "UPDATE players SET last_access = ? WHERE discord_id = ?",
            (datetime.now(), discord_id)
        )
    
    @staticmethod
    async def get_coin_balance(discord_id: str) -> int:
        """Get player's coin balance"""
        player = await PlayerService.get_player_by_discord(discord_id)
        if player:
            return player['coin_balance']
        return 0
    
    @staticmethod
    async def add_coins(
        discord_id: str,
        amount: int,
        reason: str = "",
        admin_id: str = None
    ) -> bool:
        """Add coins to player account"""
        if amount <= 0:
            return False
        
        player = await PlayerService.get_player_by_discord(discord_id)
        if not player:
            return False
        
        balance_before = player['coin_balance']
        balance_after = balance_before + amount
        
        # Update balance
        await db.execute(
            "UPDATE players SET coin_balance = ?, updated_at = ? WHERE discord_id = ?",
            (balance_after, datetime.now(), discord_id)
        )
        
        # Record transaction
        await TransactionService.create_transaction(
            player_id=player['id'],
            discord_id=discord_id,
            transaction_type="bonus" if not admin_id else "admin_add",
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason,
            admin_id=admin_id
        )
        
        return True
    
    @staticmethod
    async def remove_coins(
        discord_id: str,
        amount: int,
        reason: str = "",
        admin_id: str = None
    ) -> bool:
        """Remove coins from player account"""
        if amount <= 0:
            return False
        
        player = await PlayerService.get_player_by_discord(discord_id)
        if not player:
            return False
        
        balance_before = player['coin_balance']
        
        # Prevent negative balance
        if balance_before < amount:
            return False
        
        balance_after = balance_before - amount
        
        # Update balance
        await db.execute(
            "UPDATE players SET coin_balance = ?, updated_at = ? WHERE discord_id = ?",
            (balance_after, datetime.now(), discord_id)
        )
        
        # Record transaction
        await TransactionService.create_transaction(
            player_id=player['id'],
            discord_id=discord_id,
            transaction_type="removal" if not admin_id else "admin_remove",
            amount=-amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason,
            admin_id=admin_id
        )
        
        return True
    
    @staticmethod
    async def spend_coins(
        discord_id: str,
        amount: int,
        reason: str = "",
        order_id: int = None
    ) -> bool:
        """Spend coins from player account (for purchases)"""
        if amount <= 0:
            return False
        
        player = await PlayerService.get_player_by_discord(discord_id)
        if not player:
            return False
        
        balance_before = player['coin_balance']
        
        # Prevent negative balance
        if balance_before < amount:
            return False
        
        balance_after = balance_before - amount
        
        # Update balance
        await db.execute(
            "UPDATE players SET coin_balance = ?, updated_at = ? WHERE discord_id = ?",
            (balance_after, datetime.now(), discord_id)
        )
        
        # Record transaction
        await TransactionService.create_transaction(
            player_id=player['id'],
            discord_id=discord_id,
            transaction_type="purchase",
            amount=-amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason,
            order_id=order_id
        )
        
        return True
    
    @staticmethod
    async def refund_coins(
        discord_id: str,
        amount: int,
        reason: str = "",
        order_id: int = None
    ) -> bool:
        """Refund coins to player account"""
        return await PlayerService.add_coins(
            discord_id=discord_id,
            amount=amount,
            reason=reason or "Reembolso",
            admin_id=None
        )
    
    @staticmethod
    async def search_players(query: str) -> List[Dict]:
        """Search players by name, Discord ID, or Steam ID"""
        rows = await db.fetchall(
            """
            SELECT * FROM players 
            WHERE player_name LIKE ? OR discord_id LIKE ? OR steam_id LIKE ?
            LIMIT 50
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%")
        )
        return [dict(row) for row in rows]
    
    @staticmethod
    async def get_all_players(limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get all players with pagination"""
        rows = await db.fetchall(
            "SELECT * FROM players ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        return [dict(row) for row in rows]
    
    @staticmethod
    async def block_player(discord_id: str) -> bool:
        """Block player account"""
        await PlayerService.update_player(discord_id, status='blocked')
        return True
    
    @staticmethod
    async def unblock_player(discord_id: str) -> bool:
        """Unblock player account"""
        await PlayerService.update_player(discord_id, status='active')
        return True
    
    @staticmethod
    async def get_transaction_history(discord_id: str, limit: int = 20) -> List[Dict]:
        """Get player's transaction history"""
        rows = await db.fetchall(
            """
            SELECT * FROM coin_transactions 
            WHERE discord_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (discord_id, limit)
        )
        return [dict(row) for row in rows]


class TransactionService:
    """Manages coin transactions"""
    
    @staticmethod
    async def create_transaction(
        player_id: int,
        discord_id: str,
        transaction_type: str,
        amount: int,
        balance_before: int,
        balance_after: int,
        reason: str = "",
        order_id: int = None,
        admin_id: str = None
    ) -> Dict:
        """Create a new transaction record"""
        cursor = await db.execute(
            """
            INSERT INTO coin_transactions 
            (player_id, discord_id, transaction_type, amount, balance_before, balance_after, reason, order_id, admin_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (player_id, discord_id, transaction_type, amount, balance_before, balance_after, reason, order_id, admin_id)
        )
        
        return await TransactionService.get_transaction(cursor.lastrowid)
    
    @staticmethod
    async def get_transaction(transaction_id: int) -> Optional[Dict]:
        """Get transaction by ID"""
        row = await db.fetchone(
            "SELECT * FROM coin_transactions WHERE id = ?",
            (transaction_id,)
        )
        if row:
            return dict(row)
        return None
    
    @staticmethod
    async def get_all_transactions(limit: int = 50) -> List[Dict]:
        """Get recent transactions"""
        rows = await db.fetchall(
            "SELECT * FROM coin_transactions ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in rows]
    
    @staticmethod
    async def get_player_transactions(discord_id: str, limit: int = 50) -> List[Dict]:
        """Get transactions for a specific player"""
        rows = await db.fetchall(
            """
            SELECT * FROM coin_transactions 
            WHERE discord_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (discord_id, limit)
        )
        return [dict(row) for row in rows]
