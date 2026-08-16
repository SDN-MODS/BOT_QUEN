"""
Cart Interface for SDN_DZSTORE_BOT
Handles shopping cart display and checkout UI
"""

import discord
from discord import ui
from typing import Optional, List, Dict

from interfaces.discord_ui import create_embed, CouponModal
from services import CartService, OrderService, PlayerService, ProductService, CouponService
from config import config


class CartInterface:
    """Manages cart-related interface interactions"""
    
    @staticmethod
    async def show_cart(interaction: discord.Interaction):
        """Show player's cart"""
        discord_id = str(interaction.user.id)
        cart_data = await CartService.get_cart_total(discord_id)
        
        if not cart_data['items']:
            embed = create_embed(
                title="🛒 Seu Carrinho",
                description="Seu carrinho está vazio.\n\nExplore nossa loja para adicionar produtos!",
                color='info'
            )
            
            view = EmptyCartView(interaction.user.id)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return
        
        # Format cart items
        items_list = []
        for item in cart_data['items']:
            price = await ProductService.get_final_price(item)
            subtotal = price * item['quantity']
            
            items_list.append(
                f"📦 **{item['product_name']}**\n"
                f"Quantidade: `{item['quantity']}` x `{price:,}` = `{subtotal:,}` Coins\n"
            )
        
        # Get player balance
        player = await PlayerService.get_player_by_discord(discord_id)
        balance = player['coin_balance'] if player else 0
        
        embed = create_embed(
            title="🛒 Seu Carrinho",
            description="\n".join(items_list),
            color='primary',
            fields=[
                {
                    'name': "💰 Subtotal",
                    'value': f"`{cart_data['total']:,}` Coins",
                    'inline': True
                },
                {
                    'name': "💳 Seu Saldo",
                    'value': f"`{balance:,}` Coins",
                    'inline': True
                },
                {
                    'name': "✅ Saldo Após Compra",
                    'value': f"`{max(0, balance - cart_data['total']):,}` Coins",
                    'inline': True
                }
            ],
            footer=f"{len(cart_data['items'])} itens no carrinho"
        )
        
        can_afford = balance >= cart_data['total']
        
        view = CartView(interaction.user.id, cart_data, can_afford)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @staticmethod
    async def remove_item(interaction: discord.Interaction, product_id: int):
        """Remove item from cart"""
        discord_id = str(interaction.user.id)
        
        await CartService.remove_from_cart(discord_id, product_id)
        
        await interaction.response.send_message(
            "✅ Item removido do carrinho.",
            ephemeral=True
        )
        
        # Refresh cart display
        await CartInterface.show_cart(interaction)
    
    @staticmethod
    async def clear_cart(interaction: discord.Interaction):
        """Clear entire cart"""
        discord_id = str(interaction.user.id)
        
        await CartService.clear_cart(discord_id)
        
        embed = create_embed(
            title="🗑️ Carrinho Limpo",
            description="Todos os itens foram removidos do seu carrinho.",
            color='warning'
        )
        
        view = EmptyCartView(interaction.user.id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @staticmethod
    async def apply_coupon(interaction: discord.Interaction, coupon_code: str):
        """Apply coupon to cart"""
        discord_id = str(interaction.user.id)
        cart_data = await CartService.get_cart_total(discord_id)
        
        if not cart_data['items']:
            await interaction.response.send_message(
                "❌ Seu carrinho está vazio.",
                ephemeral=True
            )
            return
        
        # Validate coupon
        is_valid, error_msg, discount_amount = await CouponService.validate_coupon(
            coupon_code,
            discord_id,
            cart_data['total']
        )
        
        if not is_valid:
            await interaction.response.send_message(
                f"❌ Cupom inválido: {error_msg}",
                ephemeral=True
            )
            return
        
        # Show success with discount info
        new_total = cart_data['total'] - discount_amount
        
        embed = create_embed(
            title="✅ Cupom Aplicado!",
            description=f"Cupom **{coupon_code.upper()}** aplicado com sucesso!",
            color='success',
            fields=[
                {
                    'name': "💰 Valor Original",
                    'value': f"`{cart_data['total']:,}` Coins",
                    'inline': True
                },
                {
                    'name': "🎉 Desconto",
                    'value': f"`-{discount_amount:,}` Coins",
                    'inline': True
                },
                {
                    'name': "💵 Novo Total",
                    'value': f"`{new_total:,}` Coins",
                    'inline': True
                }
            ]
        )
        
        view = CheckoutView(interaction.user.id, cart_data, coupon_code.upper(), discount_amount)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @staticmethod
    async def checkout(interaction: discord.Interaction, cart_data: dict, coupon_code: str = None, discount_amount: int = 0):
        """Process checkout"""
        discord_id = str(interaction.user.id)
        
        # Get player
        player = await PlayerService.get_player_by_discord(discord_id)
        
        if not player:
            await interaction.response.send_message(
                "❌ Você precisa ter uma conta cadastrada para finalizar a compra.\n\nUse `/conta` para se cadastrar.",
                ephemeral=True
            )
            return
        
        # Check if player is blocked
        if player['status'] != 'active':
            await interaction.response.send_message(
                "❌ Sua conta está bloqueada. Contate a administração.",
                ephemeral=True
            )
            return
        
        # Calculate totals
        total = cart_data['total'] - discount_amount
        
        # Check balance
        if player['coin_balance'] < total:
            await interaction.response.send_message(
                f"❌ Saldo insuficiente.\n\nVocê precisa de `{total:,}` Coins mas tem apenas `{player['coin_balance']:,}` Coins.\n\nAdicione mais Coins ao seu saldo e tente novamente.",
                ephemeral=True
            )
            return
        
        # Prepare order items
        order_items = []
        for item in cart_data['items']:
            order_items.append({
                'product_id': item['product_id'],
                'product_name': item['product_name'],
                'quantity': item['quantity'],
                'price': item['price'],
                'delivery_type': item.get('delivery_type', 'manual'),
                'delivery_data': item.get('delivery_data', '')
            })
        
        # Spend coins
        success = await PlayerService.spend_coins(
            discord_id=discord_id,
            amount=total,
            reason=f"Compra de {len(order_items)} produto(s)",
        )
        
        if not success:
            await interaction.response.send_message(
                "❌ Erro ao processar pagamento. Tente novamente.",
                ephemeral=True
            )
            return
        
        # Create order
        order = await OrderService.create_order(
            discord_id=discord_id,
            player_id=player['id'],
            steam_id=player.get('steam_id', ''),
            items=order_items,
            total_value=cart_data['total'],
            coins_used=total,
            coupon_code=coupon_code,
            discount_amount=discount_amount
        )
        
        if not order:
            # Refund coins if order creation failed
            await PlayerService.add_coins(
                discord_id=discord_id,
                amount=total,
                reason="Reembolso - Erro ao criar pedido"
            )
            
            await interaction.response.send_message(
                "❌ Erro ao criar pedido. Seus Coins foram reembolsados.",
                ephemeral=True
            )
            return
        
        # Use coupon if applicable
        if coupon_code:
            await CouponService.use_coupon(coupon_code)
        
        # Clear cart
        await CartService.clear_cart(discord_id)
        
        # Format order items for display
        items_summary = "\n".join([
            f"• `{item['quantity']}`x {item['product_name']}"
            for item in order['items']
        ])
        
        embed = create_embed(
            title="✅ Compra Realizada com Sucesso!",
            description=f"Seu pedido **{order['order_number']}** foi criado!\n\n{items_summary}",
            color='success',
            fields=[
                {
                    'name': "📦 Número do Pedido",
                    'value': f"`{order['order_number']}`",
                    'inline': True
                },
                {
                    'name': "💰 Valor Total",
                    'value': f"`{total:,}` Coins",
                    'inline': True
                },
                {
                    'name': "📊 Status",
                    'value': "`Pendente`",
                    'inline': True
                }
            ],
            footer="Seu pedido será processado em breve!"
        )
        
        view = OrderSuccessView(interaction.user.id, order['id'])
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class EmptyCartView(ui.View):
    """View for empty cart"""
    
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


class CartView(ui.View):
    """View for cart management"""
    
    def __init__(self, user_id: int, cart_data: dict, can_afford: bool):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.cart_data = cart_data
        self.can_afford = can_afford
        
        # Disable checkout if can't afford
        if not can_afford:
            self.checkout_button.disabled = True
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="🎟️ Cupom", style=discord.ButtonStyle.secondary)
    async def coupon_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(CouponModal())
    
    @ui.button(label="🧹 Limpar", style=discord.ButtonStyle.danger)
    async def clear_button(self, interaction: discord.Interaction, button: ui.Button):
        await CartInterface.clear_cart(interaction)
    
    @ui.button(label="💳 Finalizar Compra", style=discord.ButtonStyle.success, emoji="💳")
    async def checkout_button(self, interaction: discord.Interaction, button: ui.Button):
        await CartInterface.checkout(interaction, self.cart_data)
    
    @ui.button(label="🛒 Continuar Comprando", style=discord.ButtonStyle.primary)
    async def continue_shopping_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.store_interface import StoreInterface
        await StoreInterface.show_categories(interaction)


class CheckoutView(ui.View):
    """View for checkout with coupon applied"""
    
    def __init__(self, user_id: int, cart_data: dict, coupon_code: str, discount_amount: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.cart_data = cart_data
        self.coupon_code = coupon_code
        self.discount_amount = discount_amount
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="💳 Finalizar Compra", style=discord.ButtonStyle.success, emoji="💳")
    async def checkout_button(self, interaction: discord.Interaction, button: ui.Button):
        await CartInterface.checkout(interaction, self.cart_data, self.coupon_code, self.discount_amount)
    
    @ui.button(label="🗑️ Remover Cupom", style=discord.ButtonStyle.secondary)
    async def remove_coupon_button(self, interaction: discord.Interaction, button: ui.Button):
        await CartInterface.show_cart(interaction)
    
    @ui.button(label="⬅️ Voltar", style=discord.ButtonStyle.grey)
    async def back_button(self, interaction: discord.Interaction, button: ui.Button):
        await CartInterface.show_cart(interaction)


class OrderSuccessView(ui.View):
    """View shown after successful order"""
    
    def __init__(self, user_id: int, order_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.order_id = order_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="📦 Ver Pedido", style=discord.ButtonStyle.primary)
    async def view_order_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.orders_interface import OrdersInterface
        await OrdersInterface.show_order_detail(interaction, self.order_id)
    
    @ui.button(label="🛒 Continuar Comprando", style=discord.ButtonStyle.success, emoji="🛒")
    async def continue_shopping_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.store_interface import StoreInterface
        await StoreInterface.show_categories(interaction)
    
    @ui.button(label="🏠 Menu Principal", style=discord.ButtonStyle.grey, emoji="🏠")
    async def home_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.account_interface import AccountInterface
        await AccountInterface.show_account(interaction)
