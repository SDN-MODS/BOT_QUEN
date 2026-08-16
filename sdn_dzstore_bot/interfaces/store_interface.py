"""
Store Interface for SDN_DZSTORE_BOT
Handles store browsing, categories, and product display UI
"""

import discord
from discord import ui
from typing import Optional, List, Dict

from interfaces.discord_ui import create_embed, CategorySelect, ProductSelect, QuantityModal, MainMenuView
from services import CategoryService, ProductService, CartService
from config import config


class StoreInterface:
    """Manages store-related interface interactions"""
    
    @staticmethod
    async def show_categories(interaction: discord.Interaction):
        """Show available categories"""
        categories = await CategoryService.get_all_categories()
        
        if not categories:
            embed = create_embed(
                title="🛒 Loja",
                description="Desculpe, não há categorias disponíveis no momento.",
                color='info'
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create category cards
        category_list = []
        for cat in categories:
            icon = cat.get('icon', '📁') or '📁'
            products = await ProductService.get_products_by_category(cat['id'])
            product_count = len(products)
            
            category_list.append(
                f"{icon} **{cat['name']}**\n"
                f"{cat.get('description', 'Sem descrição')[:80]}\n"
                f"`{product_count}` produtos disponíveis\n"
            )
        
        embed = create_embed(
            title="🛒 Bem-vindo à Loja",
            description=f"Escolha uma categoria para explorar os produtos disponíveis na **{config.store_name}**.\n\n" + "\n".join(category_list),
            color='primary',
            footer=f"{config.server_name} • Use o menu abaixo para navegar"
        )
        
        view = CategoryView(interaction.user.id, categories)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @staticmethod
    async def show_category_products(interaction: discord.Interaction, category_id: int):
        """Show products in a specific category"""
        category = await CategoryService.get_category(category_id)
        
        if not category:
            await interaction.response.send_message("❌ Categoria não encontrada.", ephemeral=True)
            return
        
        products = await ProductService.get_products_by_category(category_id)
        
        if not products:
            embed = create_embed(
                title=f"{category.get('icon', '📁')} {category['name']}",
                description="Não há produtos nesta categoria no momento.",
                color='info'
            )
            
            view = CategoryProductsView(interaction.user.id, category_id, products=[])
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return
        
        # Show first 10 products
        display_products = products[:10]
        
        product_list = []
        for i, prod in enumerate(display_products, 1):
            price = prod.get('discount_percent', 0)
            final_price = int(prod['price'] * (100 - price) / 100) if price else prod['price']
            
            stock_info = "∞" if prod['stock'] == -1 else str(prod['stock'])
            
            product_list.append(
                f"`{i}.` **{prod['name']}**\n"
                f"{prod.get('description', 'Sem descrição')[:60]}...\n"
                f"💰 `{final_price:,}` Coins | 📦 Estoque: `{stock_info}`\n"
            )
        
        embed = create_embed(
            title=f"{category.get('icon', '📁')} {category['name']}",
            description="\n".join(product_list),
            color='primary',
            footer=f"Mostrando {len(display_products)} de {len(products)} produtos"
        )
        
        view = CategoryProductsView(interaction.user.id, category_id, products)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @staticmethod
    async def show_product_detail(interaction: discord.Interaction, product_id: int):
        """Show detailed product information"""
        product = await ProductService.get_product(product_id)
        
        if not product:
            await interaction.response.send_message("❌ Produto não encontrado.", ephemeral=True)
            return
        
        category = await CategoryService.get_category(product['category_id']) if product.get('category_id') else None
        
        # Calculate final price
        discount = product.get('discount_percent', 0)
        base_price = product['price']
        final_price = int(base_price * (100 - discount) / 100) if discount else base_price
        
        # Stock info
        if product['stock'] == -1:
            stock_display = "✅ Estoque Ilimitado"
        elif product['stock'] > 10:
            stock_display = f"✅ Em estoque ({product['stock']} unidades)"
        elif product['stock'] > 0:
            stock_display = f"⚠️ Últimas unidades ({product['stock']} restantes)"
        else:
            stock_display = "❌ Esgotado"
        
        embed = create_embed(
            title=f"📦 {product['name']}",
            description=product.get('description', 'Sem descrição'),
            color='success' if product['status'] == 'active' else 'warning',
            thumbnail=product.get('image_url'),
            fields=[
                {
                    'name': "💰 Preço",
                    'value': f"**{final_price:,} {config.currency_symbol}**" + (f"\n~~{base_price:,}~~" if discount else ""),
                    'inline': True
                },
                {
                    'name': "📦 Estoque",
                    'value': stock_display,
                    'inline': True
                },
                {
                    'name': "📁 Categoria",
                    'value': category['name'] if category else "Geral",
                    'inline': True
                }
            ],
            footer=f"ID: {product['id']} • {config.store_name}"
        )
        
        # Add discount info if applicable
        if discount:
            embed.add_field(
                name="🎉 Promoção",
                value=f"**{discount}% de desconto** por tempo limitado!",
                inline=False
            )
        
        has_stock = product['stock'] == -1 or product['stock'] > 0
        
        view = ProductDetailView(interaction.user.id, product, has_stock)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @staticmethod
    async def add_to_cart_callback(interaction: discord.Interaction, product: dict, quantity: int):
        """Callback for adding product to cart"""
        discord_id = str(interaction.user.id)
        product_id = product['id']
        
        success = await CartService.add_to_cart(discord_id, product_id, quantity)
        
        if success:
            # Calculate price
            discount = product.get('discount_percent', 0)
            unit_price = int(product['price'] * (100 - discount) / 100) if discount else product['price']
            total = unit_price * quantity
            
            embed = create_embed(
                title="✅ Adicionado ao Carrinho!",
                description=f"**{product['name']}** foi adicionado ao seu carrinho.",
                color='success',
                fields=[
                    {
                        'name': "📦 Quantidade",
                        'value': f"`{quantity}`",
                        'inline': True
                    },
                    {
                        'name': "💰 Valor Unitário",
                        'value': f"`{unit_price:,}` Coins",
                        'inline': True
                    },
                    {
                        'name': "💵 Total",
                        'value': f"`{total:,}` Coins",
                        'inline': True
                    }
                ]
            )
            
            view = AddToCartView(interaction.user.id, product)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Não foi possível adicionar este produto ao carrinho.\n\nVerifique se o produto está disponível e tente novamente.",
                ephemeral=True
            )


class CategoryView(ui.View):
    """View for category selection"""
    
    def __init__(self, user_id: int, categories: List[Dict]):
        super().__init__(timeout=300)
        self.user_id = user_id
        
        # Add category selector
        selector = CategorySelect(categories, StoreInterface.show_category_products)
        self.add_item(selector)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="🏠 Menu Principal", style=discord.ButtonStyle.primary, emoji="🏠")
    async def home_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.account_interface import AccountInterface
        await AccountInterface.show_account(interaction)


class CategoryProductsView(ui.View):
    """View for category products"""
    
    def __init__(self, user_id: int, category_id: int, products: List[Dict]):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.category_id = category_id
        self.products = products
        
        # Add product selector if products exist
        if products:
            selector = ProductSelect(products, StoreInterface.show_product_detail)
            self.add_item(selector)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="⬅️ Voltar", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: ui.Button):
        await StoreInterface.show_categories(interaction)
    
    @ui.button(label="🏠 Menu Principal", style=discord.ButtonStyle.primary, emoji="🏠")
    async def home_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.account_interface import AccountInterface
        await AccountInterface.show_account(interaction)


class ProductDetailView(ui.View):
    """View for product detail page"""
    
    def __init__(self, user_id: int, product: dict, has_stock: bool):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.product = product
        self.has_stock = has_stock
        
        # Disable buttons if no stock
        if not has_stock:
            self.buy_now_button.disabled = True
            self.add_to_cart_button.disabled = True
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="🛒 Comprar Agora", style=discord.ButtonStyle.success)
    async def buy_now_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = QuantityModal(
            product_name=self.product['name'],
            max_stock=self.product['stock']
        )
        modal.callback_func = lambda i, q: StoreInterface.add_to_cart_callback(i, self.product, q)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="➕ Adicionar ao Carrinho", style=discord.ButtonStyle.primary)
    async def add_to_cart_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = QuantityModal(
            product_name=self.product['name'],
            max_stock=self.product['stock']
        )
        modal.callback_func = lambda i, q: StoreInterface.add_to_cart_callback(i, self.product, q)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="⬅️ Voltar", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.product.get('category_id'):
            await StoreInterface.show_category_products(interaction, self.product['category_id'])
        else:
            await StoreInterface.show_categories(interaction)
    
    @ui.button(label="🏠 Menu Principal", style=discord.ButtonStyle.grey, emoji="🏠")
    async def home_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.account_interface import AccountInterface
        await AccountInterface.show_account(interaction)


class AddToCartView(ui.View):
    """View shown after adding to cart"""
    
    def __init__(self, user_id: int, product: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.product = product
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="🛍️ Ver Carrinho", style=discord.ButtonStyle.success, emoji="🛍️")
    async def view_cart_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.cart_interface import CartInterface
        await CartInterface.show_cart(interaction)
    
    @ui.button(label="➕ Adicionar Mais", style=discord.ButtonStyle.primary)
    async def add_more_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = QuantityModal(
            product_name=self.product['name'],
            max_stock=self.product['stock']
        )
        modal.callback_func = lambda i, q: StoreInterface.add_to_cart_callback(i, self.product, q)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="🏠 Continuar Comprando", style=discord.ButtonStyle.secondary, emoji="🏠")
    async def continue_shopping_button(self, interaction: discord.Interaction, button: ui.Button):
        await StoreInterface.show_categories(interaction)
