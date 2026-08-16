"""
Orders Interface for SDN_DZSTORE_BOT
Handles order history and order details UI
"""

import discord
from discord import ui
from typing import Optional, List, Dict

from interfaces.discord_ui import create_embed
from services import OrderService
from config import config


class OrdersInterface:
    """Manages orders-related interface interactions"""
    
    @staticmethod
    async def show_orders(interaction: discord.Interaction):
        """Show player's order history"""
        discord_id = str(interaction.user.id)
        orders = await OrderService.get_player_orders(discord_id, limit=10)
        
        if not orders:
            embed = create_embed(
                title="📦 Meus Pedidos",
                description="Você ainda não realizou nenhum pedido.\n\nExplore nossa loja para fazer sua primeira compra!",
                color='info'
            )
            
            view = EmptyOrdersView(interaction.user.id)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return
        
        # Format orders list
        status_emoji = {
            'pending': '⏳',
            'processing': '⚙️',
            'paid': '💰',
            'delivering': '🚚',
            'delivered': '✅',
            'cancelled': '❌',
            'failed': '⚠️',
            'refunded': '↩️'
        }
        
        orders_list = []
        for order in orders:
            emoji = status_emoji.get(order['status'], '📦')
            date = order['created_at'][:10] if order.get('created_at') else 'N/A'
            
            orders_list.append(
                f"{emoji} **{order['order_number']}**\n"
                f"`{date}` | `{order['coins_used']:,}` Coins | Status: `{order['status'].title()}`\n"
            )
        
        embed = create_embed(
            title="📦 Histórico de Pedidos",
            description="\n".join(orders_list),
            color='primary',
            footer=f"Mostrando últimos {len(orders)} pedidos"
        )
        
        view = OrdersListView(interaction.user.id, orders)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @staticmethod
    async def show_order_detail(interaction: discord.Interaction, order_id: int):
        """Show detailed order information"""
        order = await OrderService.get_order(order_id)
        
        if not order:
            await interaction.response.send_message("❌ Pedido não encontrado.", ephemeral=True)
            return
        
        # Verify ownership
        discord_id = str(interaction.user.id)
        if order['discord_id'] != discord_id:
            # Check if user is admin (simplified check)
            from interfaces.admin_interface import AdminInterface
            if not await AdminInterface.check_admin_permission(interaction):
                await interaction.response.send_message(
                    "❌ Você não tem permissão para ver este pedido.",
                    ephemeral=True
                )
                return
        
        # Format items
        items_list = []
        for item in order['items']:
            items_list.append(
                f"📦 `{item['quantity']}`x **{item['product_name']}**\n"
                f"`{item['unit_price']:,}` x `{item['quantity']}` = `{item['subtotal']:,}` Coins\n"
            )
        
        # Status info
        status_display = {
            'pending': '⏳ Pendente',
            'processing': '⚙️ Processando',
            'paid': '💰 Pago',
            'delivering': '🚚 Em Entrega',
            'delivered': '✅ Entregue',
            'cancelled': '❌ Cancelado',
            'failed': '⚠️ Falhou',
            'refunded': '↩️ Reembolsado'
        }
        
        status_str = status_display.get(order['status'], order['status'].title())
        
        embed = create_embed(
            title=f"📦 Pedido {order['order_number']}",
            description="\n".join(items_list),
            color='success' if order['status'] == 'delivered' else 'primary' if order['status'] in ['pending', 'processing'] else 'warning',
            fields=[
                {
                    'name': "📊 Status",
                    'value': f"`{status_str}`",
                    'inline': True
                },
                {
                    'name': "💰 Valor Total",
                    'value': f"`{order['total_value']:,}` Coins",
                    'inline': True
                },
                {
                    'name': "🎉 Desconto",
                    'value': f"`{order.get('discount_amount', 0):,}` Coins" if order.get('discount_amount') else "`0` Coins",
                    'inline': True
                },
                {
                    'name': "💳 Coins Usados",
                    'value': f"`{order['coins_used']:,}`",
                    'inline': True
                },
                {
                    'name': "📅 Data do Pedido",
                    'value': order['created_at'][:16] if order.get('created_at') else 'N/A',
                    'inline': True
                },
                {
                    'name': "🎟️ Cupom",
                    'value': f"`{order.get('coupon_code', 'Nenhum')}`",
                    'inline': True
                }
            ],
            footer=f"ID: {order['id']} • {config.store_name}"
        )
        
        # Add delivery info if available
        if order.get('delivery_type'):
            embed.add_field(
                name="📬 Entrega",
                value=f"Tipo: `{order['delivery_type'].title()}`",
                inline=False
            )
        
        view = OrderDetailView(interaction.user.id, order)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class EmptyOrdersView(ui.View):
    """View for empty orders list"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="🛒 Ir para Loja", style=discord.ButtonStyle.success, emoji="🛒")
    async def go_to_store_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.store_interface import StoreInterface
        await StoreInterface.show_categories(interaction)
    
    @ui.button(label="🏠 Menu Principal", style=discord.ButtonStyle.primary, emoji="🏠")
    async def home_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.account_interface import AccountInterface
        await AccountInterface.show_account(interaction)


class OrdersListView(ui.View):
    """View for orders list"""
    
    def __init__(self, user_id: int, orders: List[Dict]):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.orders = orders
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="🔄 Atualizar", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await OrdersInterface.show_orders(interaction)
    
    @ui.button(label="🏠 Menu Principal", style=discord.ButtonStyle.primary, emoji="🏠")
    async def home_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.account_interface import AccountInterface
        await AccountInterface.show_account(interaction)


class OrderDetailView(ui.View):
    """View for order detail page"""
    
    def __init__(self, user_id: int, order: Dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.order = order
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="🔙 Voltar", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: ui.Button):
        await OrdersInterface.show_orders(interaction)
    
    @ui.button(label="🏠 Menu Principal", style=discord.ButtonStyle.grey, emoji="🏠")
    async def home_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.account_interface import AccountInterface
        await AccountInterface.show_account(interaction)
