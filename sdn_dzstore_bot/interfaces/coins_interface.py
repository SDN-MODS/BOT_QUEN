"""
Coins Interface for SDN_DZSTORE_BOT
Handles coin packages display and purchase UI
"""

import discord
from discord import ui
from typing import Optional, List, Dict

from interfaces.discord_ui import create_embed
from services import CoinPackageService, PlayerService
from config import config


class CoinsInterface:
    """Manages coins-related interface interactions"""
    
    @staticmethod
    async def show_coins_menu(interaction: discord.Interaction):
        """Show available coin packages"""
        discord_id = str(interaction.user.id)
        
        # Get player balance
        player = await PlayerService.get_player_by_discord(discord_id)
        balance = player['coin_balance'] if player else 0
        
        # Get packages
        packages = await CoinPackageService.get_all_packages()
        
        if not packages:
            embed = create_embed(
                title="💰 Coins",
                description="Não há pacotes de Coins disponíveis no momento.",
                color='info'
            )
            
            view = EmptyPackagesView(interaction.user.id)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return
        
        # Format packages
        package_list = []
        for pkg in packages[:5]:  # Show top 5
            total_coins = pkg['coin_amount'] + pkg.get('bonus_amount', 0)
            featured = "⭐ " if pkg.get('is_featured') else ""
            promotion = "🎉 " if pkg.get('is_promotion') else ""
            
            package_list.append(
                f"{featured}{promotion}**{pkg['name']}**\n"
                f"`{pkg['coin_amount']}` Coins" + (f" + `{pkg.get('bonus_amount', 0)}` Bônus" if pkg.get('bonus_amount') else "") + "\n"
                f"Total: `{total_coins}` Coins\n"
                f"Preço: `${pkg['price']:.2f}`\n"
            )
        
        embed = create_embed(
            title=f"💰 Comprar {config.currency_name}",
            description=f"**Seu Saldo Atual:** `{balance:,}` {config.currency_symbol}\n\nEscolha um pacote para mais informações:\n\n" + "\n".join(package_list),
            color='primary',
            footer=f"{config.store_name} • Pacotes seguros e instantâneos"
        )
        
        view = PackagesView(interaction.user.id, packages)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @staticmethod
    async def show_package_detail(interaction: discord.Interaction, package_id: int):
        """Show detailed package information"""
        package = await CoinPackageService.get_package(package_id)
        
        if not package:
            await interaction.response.send_message("❌ Pacote não encontrado.", ephemeral=True)
            return
        
        total_coins = package['coin_amount'] + package.get('bonus_amount', 0)
        
        # Check if package is available
        is_available = package['status'] == 'active'
        
        embed = create_embed(
            title=f"{'⭐ ' if package.get('is_featured') else ''}{'🎉 ' if package.get('is_promotion') else ''}{package['name']}",
            description=package.get('description', 'Sem descrição'),
            color='success' if is_available else 'warning',
            fields=[
                {
                    'name': "💰 Valor do Pacote",
                    'value': f"`{package['coin_amount']:,}` Coins",
                    'inline': True
                },
                {
                    'name': "🎁 Bônus",
                    'value': f"`+{package.get('bonus_amount', 0):,}` Coins",
                    'inline': True
                },
                {
                    'name': "💵 Total",
                    'value': f"`{total_coins:,}` Coins",
                    'inline': True
                },
                {
                    'name': "💳 Preço",
                    'value': f"**${package['price']:.2f}**",
                    'inline': True
                },
                {
                    'name': "📊 Status",
                    'value': "✅ Disponível" if is_available else "⛔ Indisponível",
                    'inline': True
                }
            ],
            thumbnail=package.get('image_url')
        )
        
        # Add promo info
        if package.get('is_promotion'):
            embed.add_field(
                name="🎉 Promoção",
                value="Este pacote está em promoção por tempo limitado!",
                inline=False
            )
        
        view = PackageDetailView(interaction.user.id, package, is_available)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @staticmethod
    async def initiate_purchase(interaction: discord.Interaction, package: dict):
        """Initiate coin package purchase"""
        total_coins = package['coin_amount'] + package.get('bonus_amount', 0)
        
        embed = create_embed(
            title="💳 Confirmar Compra",
            description=f"Você está prestes a comprar o pacote **{package['name']}**.\n\n⚠️ **Nota:** Esta é uma simulação. Em produção, isso redirecionaria para um gateway de pagamento.",
            color='warning',
            fields=[
                {
                    'name': "📦 Pacote",
                    'value': package['name'],
                    'inline': True
                },
                {
                    'name': "💰 Coins",
                    'value': f"`{total_coins:,}` Coins",
                    'inline': True
                },
                {
                    'name': "💵 Preço",
                    'value': f"${package['price']:.2f}",
                    'inline': True
                }
            ],
            footer="Após a confirmação do pagamento, as Coins serão adicionadas automaticamente."
        )
        
        view = PurchaseConfirmView(interaction.user.id, package)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class EmptyPackagesView(ui.View):
    """View for empty packages list"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="🏠 Menu Principal", style=discord.ButtonStyle.primary, emoji="🏠")
    async def home_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.account_interface import AccountInterface
        await AccountInterface.show_account(interaction)


class PackagesView(ui.View):
    """View for coin packages"""
    
    def __init__(self, user_id: int, packages: List[Dict]):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.packages = packages
        
        # Add package selector
        options = []
        for pkg in packages[:25]:
            total = pkg['coin_amount'] + pkg.get('bonus_amount', 0)
            label = f"{pkg['name']} - ${pkg['price']:.2f}"
            options.append(
                discord.SelectOption(
                    label=label[:100],
                    value=str(pkg['id']),
                    description=f"{total} Coins Total"[:100]
                )
            )
        
        if options:
            selector = ui.Select(
                placeholder="Selecione um pacote...",
                min_values=1,
                max_values=1,
                options=options
            )
            
            async def callback(interaction: discord.Interaction):
                package_id = int(selector.values[0])
                await CoinsInterface.show_package_detail(interaction, package_id)
            
            selector.callback = callback
            self.add_item(selector)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="🔄 Atualizar", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await CoinsInterface.show_coins_menu(interaction)
    
    @ui.button(label="🏠 Menu Principal", style=discord.ButtonStyle.primary, emoji="🏠")
    async def home_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.account_interface import AccountInterface
        await AccountInterface.show_account(interaction)


class PackageDetailView(ui.View):
    """View for package detail page"""
    
    def __init__(self, user_id: int, package: dict, is_available: bool):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.package = package
        self.is_available = is_available
        
        if not is_available:
            self.buy_button.disabled = True
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="💳 Comprar", style=discord.ButtonStyle.success, emoji="💳")
    async def buy_button(self, interaction: discord.Interaction, button: ui.Button):
        await CoinsInterface.initiate_purchase(interaction, self.package)
    
    @ui.button(label="⬅️ Voltar", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: ui.Button):
        await CoinsInterface.show_coins_menu(interaction)
    
    @ui.button(label="🏠 Menu Principal", style=discord.ButtonStyle.grey, emoji="🏠")
    async def home_button(self, interaction: discord.Interaction, button: ui.Button):
        from interfaces.account_interface import AccountInterface
        await AccountInterface.show_account(interaction)


class PurchaseConfirmView(ui.View):
    """View for purchase confirmation"""
    
    def __init__(self, user_id: int, package: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.package = package
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="✅ Confirmar Compra", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        # In production, this would redirect to payment gateway
        # For now, show informational message
        embed = create_embed(
            title="⏳ Aguardando Pagamento",
            description="Em um ambiente de produção, você seria redirecionado para o gateway de pagamento.\n\nApós a confirmação do pagamento, as Coins seriam automaticamente adicionadas à sua conta.",
            color='warning',
            fields=[
                {
                    'name': "📦 Pacote",
                    'value': self.package['name'],
                    'inline': True
                },
                {
                    'name': "💵 Valor",
                    'value': f"${self.package['price']:.2f}",
                    'inline': True
                }
            ]
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            "Compra cancelada.",
            ephemeral=True
        )
    
    @ui.button(label="⬅️ Voltar", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: ui.Button):
        await CoinsInterface.show_package_detail(interaction, self.package['id'])
