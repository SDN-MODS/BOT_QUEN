"""
Logging Service for SDN_DZSTORE_BOT
Handles admin logs and audit trail
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from database import db


class LogService:
    """Manages administrative logs and audit trail"""
    
    @staticmethod
    async def log_action(
        admin_id: str,
        admin_username: str,
        action: str,
        target_type: str = None,
        target_id: str = None,
        old_data: Dict = None,
        new_data: Dict = None
    ):
        """Log an administrative action"""
        old_data_json = json.dumps(old_data) if old_data else None
        new_data_json = json.dumps(new_data) if new_data else None
        
        await db.execute(
            """
            INSERT INTO admin_logs 
            (admin_id, admin_username, action, target_type, target_id, old_data, new_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (admin_id, admin_username, action, target_type, target_id, old_data_json, new_data_json)
        )
    
    @staticmethod
    async def get_logs(limit: int = 50) -> List[Dict]:
        """Get recent logs"""
        rows = await db.fetchall(
            "SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        
        logs = []
        for row in rows:
            log = dict(row)
            # Parse JSON data
            if log.get('old_data'):
                try:
                    log['old_data'] = json.loads(log['old_data'])
                except:
                    pass
            if log.get('new_data'):
                try:
                    log['new_data'] = json.loads(log['new_data'])
                except:
                    pass
            logs.append(log)
        
        return logs
    
    @staticmethod
    async def get_logs_by_admin(admin_id: str, limit: int = 50) -> List[Dict]:
        """Get logs for a specific admin"""
        rows = await db.fetchall(
            """
            SELECT * FROM admin_logs 
            WHERE admin_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (admin_id, limit)
        )
        
        logs = []
        for row in rows:
            log = dict(row)
            if log.get('old_data'):
                try:
                    log['old_data'] = json.loads(log['old_data'])
                except:
                    pass
            if log.get('new_data'):
                try:
                    log['new_data'] = json.loads(log['new_data'])
                except:
                    pass
            logs.append(log)
        
        return logs
    
    @staticmethod
    async def get_logs_by_action(action: str, limit: int = 50) -> List[Dict]:
        """Get logs for a specific action type"""
        rows = await db.fetchall(
            """
            SELECT * FROM admin_logs 
            WHERE action = ? 
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (action, limit)
        )
        
        logs = []
        for row in rows:
            log = dict(row)
            if log.get('old_data'):
                try:
                    log['old_data'] = json.loads(log['old_data'])
                except:
                    pass
            if log.get('new_data'):
                try:
                    log['new_data'] = json.loads(log['new_data'])
                except:
                    pass
            logs.append(log)
        
        return logs
    
    @staticmethod
    async def search_logs(query: str, limit: int = 50) -> List[Dict]:
        """Search logs by action or target"""
        rows = await db.fetchall(
            """
            SELECT * FROM admin_logs 
            WHERE action LIKE ? OR target_id LIKE ? OR admin_username LIKE ?
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%", limit)
        )
        
        logs = []
        for row in rows:
            log = dict(row)
            if log.get('old_data'):
                try:
                    log['old_data'] = json.loads(log['old_data'])
                except:
                    pass
            if log.get('new_data'):
                try:
                    log['new_data'] = json.loads(log['new_data'])
                except:
                    pass
            logs.append(log)
        
        return logs
    
    # Convenience methods for common actions
    
    @staticmethod
    async def log_coin_add(
        admin_id: str,
        admin_username: str,
        player_id: str,
        amount: int,
        reason: str = ""
    ):
        """Log coin addition by admin"""
        await LogService.log_action(
            admin_id=admin_id,
            admin_username=admin_username,
            action="ADMIN_ADDED_COINS",
            target_type="player",
            target_id=player_id,
            new_data={"amount": amount, "reason": reason}
        )
    
    @staticmethod
    async def log_coin_remove(
        admin_id: str,
        admin_username: str,
        player_id: str,
        amount: int,
        reason: str = ""
    ):
        """Log coin removal by admin"""
        await LogService.log_action(
            admin_id=admin_id,
            admin_username=admin_username,
            action="ADMIN_REMOVED_COINS",
            target_type="player",
            target_id=player_id,
            new_data={"amount": amount, "reason": reason}
        )
    
    @staticmethod
    async def log_product_created(
        admin_id: str,
        admin_username: str,
        product_id: int,
        product_data: Dict
    ):
        """Log product creation"""
        await LogService.log_action(
            admin_id=admin_id,
            admin_username=admin_username,
            action="PRODUCT_CREATED",
            target_type="product",
            target_id=str(product_id),
            new_data=product_data
        )
    
    @staticmethod
    async def log_product_updated(
        admin_id: str,
        admin_username: str,
        product_id: int,
        old_data: Dict,
        new_data: Dict
    ):
        """Log product update"""
        await LogService.log_action(
            admin_id=admin_id,
            admin_username=admin_username,
            action="PRODUCT_UPDATED",
            target_type="product",
            target_id=str(product_id),
            old_data=old_data,
            new_data=new_data
        )
    
    @staticmethod
    async def log_product_deleted(
        admin_id: str,
        admin_username: str,
        product_id: int,
        product_name: str
    ):
        """Log product deletion"""
        await LogService.log_action(
            admin_id=admin_id,
            admin_username=admin_username,
            action="PRODUCT_DELETED",
            target_type="product",
            target_id=str(product_id),
            old_data={"name": product_name}
        )
    
    @staticmethod
    async def log_order_cancelled(
        admin_id: str,
        admin_username: str,
        order_id: int,
        order_number: str,
        reason: str
    ):
        """Log order cancellation"""
        await LogService.log_action(
            admin_id=admin_id,
            admin_username=admin_username,
            action="ORDER_CANCELLED",
            target_type="order",
            target_id=str(order_id),
            new_data={"order_number": order_number, "reason": reason}
        )
    
    @staticmethod
    async def log_order_refunded(
        admin_id: str,
        admin_username: str,
        order_id: int,
        order_number: str,
        amount: int
    ):
        """Log order refund"""
        await LogService.log_action(
            admin_id=admin_id,
            admin_username=admin_username,
            action="ORDER_REFUNDED",
            target_type="order",
            target_id=str(order_id),
            new_data={"order_number": order_number, "refunded_amount": amount}
        )
    
    @staticmethod
    async def log_player_blocked(
        admin_id: str,
        admin_username: str,
        player_id: str,
        reason: str = ""
    ):
        """Log player block"""
        await LogService.log_action(
            admin_id=admin_id,
            admin_username=admin_username,
            action="PLAYER_BLOCKED",
            target_type="player",
            target_id=player_id,
            new_data={"reason": reason}
        )
    
    @staticmethod
    async def log_player_unblocked(
        admin_id: str,
        admin_username: str,
        player_id: str
    ):
        """Log player unblock"""
        await LogService.log_action(
            admin_id=admin_id,
            admin_username=admin_username,
            action="PLAYER_UNBLOCKED",
            target_type="player",
            target_id=player_id
        )
    
    @staticmethod
    async def log_coupon_created(
        admin_id: str,
        admin_username: str,
        coupon_code: str,
        coupon_data: Dict
    ):
        """Log coupon creation"""
        await LogService.log_action(
            admin_id=admin_id,
            admin_username=admin_username,
            action="COUPON_CREATED",
            target_type="coupon",
            target_id=coupon_code,
            new_data=coupon_data
        )
    
    @staticmethod
    async def log_config_changed(
        admin_id: str,
        admin_username: str,
        config_key: str,
        old_value: Any,
        new_value: Any
    ):
        """Log configuration change"""
        await LogService.log_action(
            admin_id=admin_id,
            admin_username=admin_username,
            action="CONFIG_CHANGED",
            target_type="config",
            target_id=config_key,
            old_data={"value": old_value},
            new_data={"value": new_value}
        )
