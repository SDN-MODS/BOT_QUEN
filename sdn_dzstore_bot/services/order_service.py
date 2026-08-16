"""
Order Service for SDN_DZSTORE_BOT
Handles orders, cart management, and checkout process
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from database import db
from services.player_service import PlayerService
from services.product_service import ProductService


class CartService:
    """Manages shopping cart"""
    
    @staticmethod
    async def get_cart_items(discord_id: str) -> List[Dict]:
        """Get all items in player's cart"""
        rows = await db.fetchall(
            """
            SELECT ci.*, p.name as product_name, p.price, p.image_url, p.delivery_type, p.delivery_data
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.id
            WHERE ci.discord_id = ?
            ORDER BY ci.added_at DESC
            """,
            (discord_id,)
        )
        return [dict(row) for row in rows]
    
    @staticmethod
    async def add_to_cart(discord_id: str, product_id: int, quantity: int = 1) -> bool:
        """Add item to cart"""
        # Check if product exists and is available
        product = await ProductService.get_product(product_id)
        if not product or product['status'] != 'active':
            return False
        
        # Check stock
        if not await ProductService.has_stock(product_id, quantity):
            return False
        
        # Check if already in cart
        existing = await db.fetchone(
            "SELECT * FROM cart_items WHERE discord_id = ? AND product_id = ?",
            (discord_id, product_id)
        )
        
        if existing:
            # Update quantity
            new_quantity = existing['quantity'] + quantity
            await db.execute(
                "UPDATE cart_items SET quantity = ? WHERE discord_id = ? AND product_id = ?",
                (new_quantity, discord_id, product_id)
            )
        else:
            # Add new item
            await db.execute(
                "INSERT INTO cart_items (discord_id, product_id, quantity) VALUES (?, ?, ?)",
                (discord_id, product_id, quantity)
            )
        
        return True
    
    @staticmethod
    async def update_cart_item(discord_id: str, product_id: int, quantity: int) -> bool:
        """Update item quantity in cart"""
        if quantity <= 0:
            return await CartService.remove_from_cart(discord_id, product_id)
        
        # Check stock
        if not await ProductService.has_stock(product_id, quantity):
            return False
        
        await db.execute(
            "UPDATE cart_items SET quantity = ? WHERE discord_id = ? AND product_id = ?",
            (quantity, discord_id, product_id)
        )
        
        return True
    
    @staticmethod
    async def remove_from_cart(discord_id: str, product_id: int) -> bool:
        """Remove item from cart"""
        await db.execute(
            "DELETE FROM cart_items WHERE discord_id = ? AND product_id = ?",
            (discord_id, product_id)
        )
        return True
    
    @staticmethod
    async def clear_cart(discord_id: str) -> bool:
        """Clear entire cart"""
        await db.execute(
            "DELETE FROM cart_items WHERE discord_id = ?",
            (discord_id,)
        )
        return True
    
    @staticmethod
    async def get_cart_total(discord_id: str) -> Dict:
        """Calculate cart totals"""
        items = await CartService.get_cart_items(discord_id)
        
        total = 0
        item_count = 0
        
        for item in items:
            price = await ProductService.get_final_price(item)
            total += price * item['quantity']
            item_count += item['quantity']
        
        return {
            'items': items,
            'item_count': item_count,
            'total': total
        }


class OrderService:
    """Manages orders"""
    
    @staticmethod
    def generate_order_number() -> str:
        """Generate unique order number"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        import random
        suffix = f"{random.randint(0, 999):03d}"
        return f"DZ-{timestamp}-{suffix}"
    
    @staticmethod
    async def create_order(
        discord_id: str,
        player_id: int,
        steam_id: str,
        items: List[Dict],
        total_value: int,
        coins_used: int,
        coupon_code: str = None,
        discount_amount: int = 0
    ) -> Optional[Dict]:
        """Create a new order"""
        order_number = OrderService.generate_order_number()
        
        # Determine delivery type from items
        delivery_type = items[0].get('delivery_type', 'manual') if items else 'manual'
        delivery_data = items[0].get('delivery_data', '') if items else ''
        
        # Create order
        cursor = await db.execute(
            """
            INSERT INTO orders 
            (order_number, discord_id, player_id, steam_id, total_value, coins_used, coupon_code, discount_amount, status, delivery_type, delivery_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (order_number, discord_id, player_id, steam_id, total_value, coins_used, coupon_code, discount_amount, delivery_type, delivery_data)
        )
        
        order_id = cursor.lastrowid
        
        # Create order items
        for item in items:
            product = await ProductService.get_product(item['product_id'])
            unit_price = await ProductService.get_final_price(product) if product else item['price']
            subtotal = unit_price * item['quantity']
            
            await db.execute(
                """
                INSERT INTO order_items 
                (order_id, product_id, product_name, quantity, unit_price, subtotal, delivery_type, delivery_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (order_id, item['product_id'], item['product_name'], item['quantity'], unit_price, subtotal, item.get('delivery_type'), item.get('delivery_data'))
            )
            
            # Update stock if limited
            if product and product['stock'] != -1:
                await ProductService.update_stock(item['product_id'], -item['quantity'])
        
        return await OrderService.get_order(order_id)
    
    @staticmethod
    async def get_order(order_id: int) -> Optional[Dict]:
        """Get order by ID"""
        row = await db.fetchone(
            "SELECT * FROM orders WHERE id = ?",
            (order_id,)
        )
        if row:
            order = dict(row)
            order['items'] = await OrderService.get_order_items(order_id)
            return order
        return None
    
    @staticmethod
    async def get_order_by_number(order_number: str) -> Optional[Dict]:
        """Get order by order number"""
        row = await db.fetchone(
            "SELECT * FROM orders WHERE order_number = ?",
            (order_number,)
        )
        if row:
            order = dict(row)
            order['items'] = await OrderService.get_order_items(order['id'])
            return order
        return None
    
    @staticmethod
    async def get_order_items(order_id: int) -> List[Dict]:
        """Get order items"""
        rows = await db.fetchall(
            "SELECT * FROM order_items WHERE order_id = ?",
            (order_id,)
        )
        return [dict(row) for row in rows]
    
    @staticmethod
    async def get_player_orders(discord_id: str, limit: int = 20) -> List[Dict]:
        """Get player's order history"""
        rows = await db.fetchall(
            """
            SELECT * FROM orders 
            WHERE discord_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
            """,
            (discord_id, limit)
        )
        
        orders = []
        for row in rows:
            order = dict(row)
            order['items'] = await OrderService.get_order_items(order['id'])
            orders.append(order)
        
        return orders
    
    @staticmethod
    async def get_all_orders(status: str = None, limit: int = 50) -> List[Dict]:
        """Get all orders with optional status filter"""
        if status:
            rows = await db.fetchall(
                "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            )
        else:
            rows = await db.fetchall(
                "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        
        orders = []
        for row in rows:
            order = dict(row)
            order['items'] = await OrderService.get_order_items(order['id'])
            orders.append(order)
        
        return orders
    
    @staticmethod
    async def update_order_status(order_id: int, status: str) -> bool:
        """Update order status"""
        valid_statuses = ['pending', 'processing', 'paid', 'delivering', 'delivered', 'cancelled', 'failed', 'refunded']
        
        if status not in valid_statuses:
            return False
        
        updates = []
        updates.append("status = ?")
        values = [status]
        
        if status in ['delivered', 'cancelled', 'failed', 'refunded']:
            updates.append("completed_at = ?")
            values.append(datetime.now())
        
        updates.append("updated_at = ?")
        values.append(datetime.now())
        values.append(order_id)
        
        await db.execute(
            f"UPDATE orders SET {', '.join(updates)} WHERE id = ?",
            tuple(values)
        )
        
        return True
    
    @staticmethod
    async def cancel_order(order_id: int, reason: str = "") -> bool:
        """Cancel an order and refund coins"""
        order = await OrderService.get_order(order_id)
        
        if not order or order['status'] in ['cancelled', 'delivered', 'refunded']:
            return False
        
        # Refund coins
        if order['coins_used'] > 0:
            await PlayerService.refund_coins(
                discord_id=order['discord_id'],
                amount=order['coins_used'],
                reason=f"Reembolso - Pedido {order['order_number']} cancelado: {reason}"
            )
        
        # Restore stock
        items = await OrderService.get_order_items(order_id)
        for item in items:
            await ProductService.update_stock(item['product_id'], item['quantity'])
        
        # Update order status
        await OrderService.update_order_status(order_id, 'cancelled')
        
        return True
    
    @staticmethod
    async def complete_order(order_id: int) -> bool:
        """Mark order as delivered"""
        return await OrderService.update_order_status(order_id, 'delivered')


class CouponService:
    """Manages coupons and discounts"""
    
    @staticmethod
    async def get_coupon(code: str) -> Optional[Dict]:
        """Get coupon by code"""
        row = await db.fetchone(
            "SELECT * FROM coupons WHERE code = ?",
            (code.upper(),)
        )
        if row:
            return dict(row)
        return None
    
    @staticmethod
    async def validate_coupon(code: str, discord_id: str, total_value: int) -> tuple:
        """Validate coupon and return (is_valid, error_message, discount_amount)"""
        coupon = await CouponService.get_coupon(code)
        
        if not coupon:
            return False, "Cupom inválido", 0
        
        if coupon['status'] != 'active':
            return False, "Cupom expirado ou inválido", 0
        
        # Check date range
        now = datetime.now()
        if coupon['start_date'] and now < coupon['start_date']:
            return False, "Cupom ainda não está válido", 0
        
        if coupon['end_date'] and now > coupon['end_date']:
            return False, "Cupom expirado", 0
        
        # Check usage limits
        if coupon['max_uses'] and coupon['used_count'] >= coupon['max_uses']:
            return False, "Cupom esgotado", 0
        
        # Check minimum purchase
        if coupon['min_purchase'] and total_value < coupon['min_purchase']:
            return False, f"Valor mínimo de compra: {coupon['min_purchase']} Coins", 0
        
        # Calculate discount
        discount_amount = 0
        if coupon['discount_type'] == 'percent':
            discount_amount = int(total_value * coupon['discount_value'] / 100)
        elif coupon['discount_type'] == 'fixed':
            discount_amount = min(coupon['discount_value'], total_value)
        
        if discount_amount <= 0:
            return False, "Cupom não aplicável", 0
        
        return True, "", discount_amount
    
    @staticmethod
    async def use_coupon(code: str) -> bool:
        """Increment coupon usage count"""
        await db.execute(
            "UPDATE coupons SET used_count = used_count + 1, updated_at = ? WHERE code = ?",
            (datetime.now(), code.upper())
        )
        return True
    
    @staticmethod
    async def create_coupon(
        code: str,
        discount_type: str,
        discount_value: int,
        description: str = "",
        min_purchase: int = 0,
        max_uses: int = None,
        max_uses_per_user: int = 1,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict:
        """Create a new coupon"""
        cursor = await db.execute(
            """
            INSERT INTO coupons 
            (code, description, discount_type, discount_value, min_purchase, max_uses, max_uses_per_user, start_date, end_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (code.upper(), description, discount_type, discount_value, min_purchase, max_uses, max_uses_per_user, start_date, end_date)
        )
        
        return await CouponService.get_coupon(code.upper())
