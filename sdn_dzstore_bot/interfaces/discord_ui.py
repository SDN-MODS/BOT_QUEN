"""
Discord Interface Utilities for SDN_DZSTORE_BOT
Creates embeds, buttons, menus, and modals for user interaction
"""

import discord
from discord import ui
from typing import Optional, List, Dict, Any
from datetime import datetime
from config import config


# Color constants
COLORS = {
    'primary': int(config.colors.get('primary', '#5865F2').replace('#', ''), 16),
    'success': int(config.colors.get('success', '#57F287').replace('#', ''), 16),
    'warning': int(config.colors.get('warning', '#FEE75C').replace('#', ''), 16),
    'error': int(config.colors.get('error', '#ED4245').replace('#', ''), 16),
    'info': int(config.colors.get('info', '#5865F2').replace('#', ''), 16)
}


def create_embed(
    title: str,
    description: str = None,
    color: str = 'primary',
    thumbnail: str = None,
    image: str = None,
    fields: List[Dict] = None,
    footer: str = None,
    timestamp: bool = False
) -> discord.Embed:
    """Create a standardized embed"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=COLORS.get(color, COLORS['primary'])
    )
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    if image:
        embed.set_image(url=image)
    
    if fields:
        for field in fields:
            embed.add_field(
                name=field.get('name', '\u200b'),
                value=field.get('value', '\u200b'),
                inline=field.get('inline', False)
            )
    
    if footer:
        embed.set_footer(text=footer)
    
    if timestamp:
        embed.timestamp = datetime.now()
    
    return embed


class MainMenuView(ui.View):
    """Main menu view with navigation buttons"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="👤 Minha Conta", style=discord.ButtonStyle.primary, emoji="👤")
    async def account_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.account_interface import AccountInterface
        await AccountInterface.show_account(interaction)
    
    @ui.button(label="🛒 Loja", style=discord.ButtonStyle.success, emoji="🛒")
    async def store_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.store_interface import StoreInterface
        await StoreInterface.show_categories(interaction)
    
    @ui.button(label="💰 Coins", style=discord.ButtonStyle.blurple, emoji="💰")
    async def coins_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.coins_interface import CoinsInterface
        await CoinsInterface.show_coins_menu(interaction)
    
    @ui.button(label="📦 Pedidos", style=discord.ButtonStyle.secondary, emoji="📦")
    async def orders_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.orders_interface import OrdersInterface
        await OrdersInterface.show_orders(interaction)
    
    @ui.button(label="❓ Ajuda", style=discord.ButtonStyle.grey, emoji="❓")
    async def help_button(self, interaction: discord.Interaction, button: ui.Button):
        await HelpInterface.show_help(interaction)


class PaginationView(ui.View):
    """Pagination controls for lists"""
    
    def __init__(self, items: List, callback, user_id: int, items_per_page: int = 10):
        super().__init__(timeout=120)
        self.items = items
        self.callback = callback
        self.user_id = user_id
        self.items_per_page = items_per_page
        self.current_page = 0
        self.total_pages = (len(items) - 1) // items_per_page + 1 if items else 1
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="◀ Anterior", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def previous_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.callback(interaction, self.current_page)
    
    @ui.button(label="Próximo ▶", style=discord.ButtonStyle.secondary, emoji="➡️")
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self.callback(interaction, self.current_page)
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1


class CategorySelect(ui.Select):
    """Category selection dropdown"""
    
    def __init__(self, categories: List[Dict], callback):
        options = []
        for cat in categories:
            emoji = cat.get('icon', '📁') or '📁'
            options.append(
                discord.SelectOption(
                    label=cat['name'],
                    value=str(cat['id']),
                    description=cat.get('description', '')[:100],
                    emoji=emoji
                )
            )
        
        super().__init__(
            placeholder="Selecione uma categoria...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.callback_func = callback
    
    async def callback(self, interaction: discord.Interaction):
        category_id = int(self.values[0])
        await self.callback_func(interaction, category_id)


class ProductSelect(ui.Select):
    """Product selection dropdown"""
    
    def __init__(self, products: List[Dict], callback):
        options = []
        for product in products[:25]:  # Discord limit
            price = product.get('discount_percent', 0)
            final_price = int(product['price'] * (100 - price) / 100) if price else product['price']
            
            option_label = f"{product['name']} - {final_price} 🪙"
            if len(option_label) > 100:
                option_label = option_label[:97] + "..."
            
            options.append(
                discord.SelectOption(
                    label=option_label,
                    value=str(product['id']),
                    description=f"Preço: {final_price} Coins"[:100]
                )
            )
        
        super().__init__(
            placeholder="Selecione um produto...",
            min_values=1,
            max_values=1,
            options=options
        )
        self.callback_func = callback
    
    async def callback(self, interaction: discord.Interaction):
        product_id = int(self.values[0])
        await self.callback_func(interaction, product_id)


class QuantityModal(ui.Modal, title="Quantidade"):
    """Modal for entering quantity"""
    
    def __init__(self, product_name: str, max_stock: int = 99):
        super().__init__()
        self.product_name = product_name
        self.max_stock = max_stock
        
        self.quantity = ui.TextInput(
            label=f"Quantidade de {product_name}",
            style=discord.TextStyle.short,
            placeholder="1",
            default="1",
            min_length=1,
            max_length=4
        )
        self.add_item(self.quantity)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            quantity = int(self.quantity.value)
            if quantity < 1:
                await interaction.response.send_message(
                    "❌ A quantidade mínima é 1.",
                    ephemeral=True
                )
                return
            if quantity > self.max_stock and self.max_stock != -1:
                await interaction.response.send_message(
                    f"❌ Quantidade máxima disponível: {self.max_stock}",
                    ephemeral=True
                )
                return
            
            # Return quantity to callback
            if hasattr(self, 'callback_func'):
                await self.callback_func(interaction, quantity)
        except ValueError:
            await interaction.response.send_message(
                "❌ Por favor, insira um número válido.",
                ephemeral=True
            )


class CouponModal(ui.Modal, title="Aplicar Cupom"):
    """Modal for entering coupon code"""
    
    def __init__(self):
        super().__init__()
        
        self.coupon_code = ui.TextInput(
            label="Código do Cupom",
            style=discord.TextStyle.short,
            placeholder="DIGITE SEU CUPOM",
            max_length=50
        )
        self.add_item(self.coupon_code)
    
    async def on_submit(self, interaction: discord.Interaction):
        from interfaces.cart_interface import CartInterface
        await CartInterface.apply_coupon(interaction, self.coupon_code.value.strip())


class SteamIdModal(ui.Modal, title="Vincular Steam ID"):
    """Modal for entering Steam ID"""
    
    def __init__(self):
        super().__init__()
        
        self.steam_id = ui.TextInput(
            label="Steam ID",
            style=discord.TextStyle.short,
            placeholder="Seu Steam ID (ex: 76561198000000000)",
            max_length=50
        )
        self.add_item(self.steam_id)
    
    async def on_submit(self, interaction: discord.Interaction):
        from interfaces.account_interface import AccountInterface
        await AccountInterface.confirm_steam_link(interaction, self.steam_id.value.strip())


class HelpInterface:
    """Help interface utilities"""
    
    @staticmethod
    async def show_help(interaction: discord.Interaction):
        embed = create_embed(
            title="❓ Central de Ajuda",
            description=f"Bem-vindo à **{config.store_name}**!",
            color='info',
            fields=[
                {
                    'name': "👤 Minha Conta",
                    'value': "Gerencie seu perfil, visualize seu saldo e histórico de transações.",
                    'inline': False
                },
                {
                    'name': "🛒 Loja",
                    'value': "Explore nossos produtos organizados por categorias. Adicione itens ao carrinho e finalize sua compra.",
                    'inline': False
                },
                {
                    'name': "💰 Coins",
                    'value': "Adquira pacotes de Coins para usar na loja. Cada pacote oferece diferentes quantidades e bônus.",
                    'inline': False
                },
                {
                    'name': "📦 Meus Pedidos",
                    'value': "Acompanhe o status dos seus pedidos e visualize seu histórico de compras.",
                    'inline': False
                },
                {
                    'name': "🎟️ Cupons",
                    'value': "Possui um cupom de desconto? Aplique durante o checkout para economizar Coins.",
                    'inline': False
                },
                {
                    'name': "⚠️ Importante",
                    'value': "• Mantenha seu Steam ID sempre atualizado\n• Verifique seu saldo antes de comprar\n• Pedidos são processados automaticamente\n• Em caso de problemas, contate a administração",
                    'inline': False
                }
            ],
            footer=f"{config.server_name} • {config.currency_name} System"
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
