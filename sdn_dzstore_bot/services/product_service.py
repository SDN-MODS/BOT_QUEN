"""
Product Service for SDN_DZSTORE_BOT
Handles products, categories, and inventory management
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from database import db


class CategoryService:
    """Manages product categories"""
    
    @staticmethod
    async def get_category(category_id: int) -> Optional[Dict]:
        """Get category by ID"""
        row = await db.fetchone(
            "SELECT * FROM categories WHERE id = ?",
            (category_id,)
        )
        if row:
            return dict(row)
        return None
    
    @staticmethod
    async def get_all_categories(status: str = 'active') -> List[Dict]:
        """Get all categories"""
        if status:
            rows = await db.fetchall(
                "SELECT * FROM categories WHERE status = ? ORDER BY display_order, name",
                (status,)
            )
        else:
            rows = await db.fetchall(
                "SELECT * FROM categories ORDER BY display_order, name"
            )
        return [dict(row) for row in rows]
    
    @staticmethod
    async def create_category(
        name: str,
        description: str = "",
        icon: str = "",
        image_url: str = "",
        display_order: int = 0
    ) -> Dict:
        """Create a new category"""
        cursor = await db.execute(
            """
            INSERT INTO categories (name, description, icon, image_url, display_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, description, icon, image_url, display_order)
        )
        
        return await CategoryService.get_category(cursor.lastrowid)
    
    @staticmethod
    async def update_category(category_id: int, **kwargs) -> Optional[Dict]:
        """Update category information"""
        allowed_fields = ['name', 'description', 'icon', 'image_url', 'display_order', 'status']
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return await CategoryService.get_category(category_id)
        
        updates.append("updated_at = ?")
        values.append(datetime.now())
        values.append(category_id)
        
        await db.execute(
            f"UPDATE categories SET {', '.join(updates)} WHERE id = ?",
            tuple(values)
        )
        
        return await CategoryService.get_category(category_id)
    
    @staticmethod
    async def delete_category(category_id: int) -> bool:
        """Delete a category (soft delete by setting status)"""
        await db.execute(
            "UPDATE categories SET status = 'deleted', updated_at = ? WHERE id = ?",
            (datetime.now(), category_id)
        )
        return True


class ProductService:
    """Manages products"""
    
    @staticmethod
    async def get_product(product_id: int) -> Optional[Dict]:
        """Get product by ID"""
        row = await db.fetchone(
            "SELECT * FROM products WHERE id = ?",
            (product_id,)
        )
        if row:
            return dict(row)
        return None
    
    @staticmethod
    async def get_products_by_category(category_id: int, status: str = 'active') -> List[Dict]:
        """Get all products in a category"""
        if status:
            rows = await db.fetchall(
                "SELECT * FROM products WHERE category_id = ? AND status = ? ORDER BY display_order, name",
                (category_id, status)
            )
        else:
            rows = await db.fetchall(
                "SELECT * FROM products WHERE category_id = ? ORDER BY display_order, name",
                (category_id,)
            )
        return [dict(row) for row in rows]
    
    @staticmethod
    async def get_featured_products(limit: int = 10) -> List[Dict]:
        """Get featured products"""
        rows = await db.fetchall(
            """
            SELECT * FROM products 
            WHERE is_featured = TRUE AND status = 'active' 
            ORDER BY display_order, created_at DESC 
            LIMIT ?
            """,
            (limit,)
        )
        return [dict(row) for row in rows]
    
    @staticmethod
    async def get_all_products(status: str = 'active') -> List[Dict]:
        """Get all products"""
        if status:
            rows = await db.fetchall(
                "SELECT * FROM products WHERE status = ? ORDER BY display_order, name",
                (status,)
            )
        else:
            rows = await db.fetchall(
                "SELECT * FROM products ORDER BY display_order, name"
            )
        return [dict(row) for row in rows]
    
    @staticmethod
    async def search_products(query: str, limit: int = 50) -> List[Dict]:
        """Search products by name"""
        rows = await db.fetchall(
            """
            SELECT * FROM products 
            WHERE name LIKE ? AND status = 'active'
            ORDER BY display_order, name
            LIMIT ?
            """,
            (f"%{query}%", limit)
        )
        return [dict(row) for row in rows]
    
    @staticmethod
    async def create_product(
        name: str,
        price: int,
        category_id: int = None,
        description: str = "",
        stock: int = -1,
        image_url: str = "",
        delivery_type: str = "manual",
        delivery_data: str = "",
        discount_percent: int = 0,
        is_featured: bool = False,
        display_order: int = 0
    ) -> Dict:
        """Create a new product"""
        cursor = await db.execute(
            """
            INSERT INTO products 
            (name, description, category_id, price, stock, image_url, delivery_type, delivery_data, discount_percent, is_featured, display_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, description, category_id, price, stock, image_url, delivery_type, delivery_data, discount_percent, is_featured, display_order)
        )
        
        return await ProductService.get_product(cursor.lastrowid)
    
    @staticmethod
    async def update_product(product_id: int, **kwargs) -> Optional[Dict]:
        """Update product information"""
        allowed_fields = [
            'name', 'description', 'category_id', 'price', 'stock',
            'image_url', 'status', 'is_featured', 'display_order',
            'delivery_type', 'delivery_data', 'discount_percent'
        ]
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return await ProductService.get_product(product_id)
        
        updates.append("updated_at = ?")
        values.append(datetime.now())
        values.append(product_id)
        
        await db.execute(
            f"UPDATE products SET {', '.join(updates)} WHERE id = ?",
            tuple(values)
        )
        
        return await ProductService.get_product(product_id)
    
    @staticmethod
    async def delete_product(product_id: int) -> bool:
        """Delete a product (soft delete by setting status)"""
        await db.execute(
            "UPDATE products SET status = 'deleted', updated_at = ? WHERE id = ?",
            (datetime.now(), product_id)
        )
        return True
    
    @staticmethod
    async def update_stock(product_id: int, quantity: int) -> bool:
        """Update product stock"""
        product = await ProductService.get_product(product_id)
        if not product:
            return False
        
        current_stock = product['stock']
        
        # -1 means unlimited stock
        if current_stock == -1:
            return True
        
        new_stock = current_stock + quantity
        
        if new_stock < 0:
            return False
        
        await db.execute(
            "UPDATE products SET stock = ?, updated_at = ? WHERE id = ?",
            (new_stock, datetime.now(), product_id)
        )
        
        return True
    
    @staticmethod
    async def has_stock(product_id: int, quantity: int = 1) -> bool:
        """Check if product has enough stock"""
        product = await ProductService.get_product(product_id)
        if not product:
            return False
        
        # -1 means unlimited stock
        if product['stock'] == -1:
            return True
        
        return product['stock'] >= quantity
    
    @staticmethod
    async def get_final_price(product: Dict) -> int:
        """Get final price after discounts"""
        base_price = product['price']
        discount = product.get('discount_percent', 0)
        
        if discount > 0:
            return int(base_price * (100 - discount) / 100)
        
        return base_price


class CoinPackageService:
    """Manages coin packages"""
    
    @staticmethod
    async def get_package(package_id: int) -> Optional[Dict]:
        """Get package by ID"""
        row = await db.fetchone(
            "SELECT * FROM coin_packages WHERE id = ?",
            (package_id,)
        )
        if row:
            return dict(row)
        return None
    
    @staticmethod
    async def get_all_packages(status: str = 'active') -> List[Dict]:
        """Get all available packages"""
        if status:
            rows = await db.fetchall(
                "SELECT * FROM coin_packages WHERE status = ? ORDER BY display_order, price",
                (status,)
            )
        else:
            rows = await db.fetchall(
                "SELECT * FROM coin_packages ORDER BY display_order, price"
            )
        return [dict(row) for row in rows]
    
    @staticmethod
    async def get_featured_packages() -> List[Dict]:
        """Get featured packages"""
        rows = await db.fetchall(
            """
            SELECT * FROM coin_packages 
            WHERE is_featured = TRUE AND status = 'active' 
            ORDER BY display_order
            """
        )
        return [dict(row) for row in rows]
    
    @staticmethod
    async def create_package(
        name: str,
        coin_amount: int,
        price: float,
        description: str = "",
        bonus_amount: int = 0,
        image_url: str = "",
        is_featured: bool = False,
        is_promotion: bool = False,
        display_order: int = 0
    ) -> Dict:
        """Create a new coin package"""
        total_coins = coin_amount + bonus_amount
        
        cursor = await db.execute(
            """
            INSERT INTO coin_packages 
            (name, description, coin_amount, bonus_amount, price, image_url, is_featured, is_promotion, display_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, description, coin_amount, bonus_amount, price, image_url, is_featured, is_promotion, display_order)
        )
        
        return await CoinPackageService.get_package(cursor.lastrowid)
    
    @staticmethod
    async def update_package(package_id: int, **kwargs) -> Optional[Dict]:
        """Update package information"""
        allowed_fields = [
            'name', 'description', 'coin_amount', 'bonus_amount', 'price',
            'status', 'display_order', 'image_url', 'is_featured', 'is_promotion'
        ]
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if not updates:
            return await CoinPackageService.get_package(package_id)
        
        updates.append("updated_at = ?")
        values.append(datetime.now())
        values.append(package_id)
        
        await db.execute(
            f"UPDATE coin_packages SET {', '.join(updates)} WHERE id = ?",
            tuple(values)
        )
        
        return await CoinPackageService.get_package(package_id)
    
    @staticmethod
    async def delete_package(package_id: int) -> bool:
        """Delete a package (soft delete by setting status)"""
        await db.execute(
            "UPDATE coin_packages SET status = 'deleted', updated_at = ? WHERE id = ?",
            (datetime.now(), package_id)
        )
        return True
