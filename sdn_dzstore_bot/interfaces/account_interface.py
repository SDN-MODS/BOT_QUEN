"""
Account Interface for SDN_DZSTORE_BOT
Handles player account display and management UI
"""

import discord
from discord import ui
from typing import Optional
from datetime import datetime

from interfaces.discord_ui import create_embed, MainMenuView, SteamIdModal
from services import PlayerService
from config import config


class AccountInterface:
    """Manages account-related interface interactions"""
    
    @staticmethod
    async def show_account(interaction: discord.Interaction):
        """Show player account information"""
        discord_id = str(interaction.user.id)
        
        # Update last access
        await PlayerService.update_last_access(discord_id)
        
        # Get or create player
        player = await PlayerService.get_player_by_discord(discord_id)
        
        if not player:
            # Show registration prompt
            await AccountInterface.show_registration(interaction)
            return
        
        # Format dates
        created_at = player['created_at'][:10] if player.get('created_at') else 'N/A'
        last_access = player['last_access'][:16] if player.get('last_access') else 'N/A'
        
        # Get transaction count
        transactions = await PlayerService.get_transaction_history(discord_id, limit=1)
        tx_count = len(await PlayerService.get_transaction_history(discord_id, limit=100))
        
        embed = create_embed(
            title="👤 Minha Conta",
            description=f"Bem-vindo de volta, **{player['player_name']}**!",
            color='primary',
            thumbnail=interaction.user.display_avatar.url,
            fields=[
                {
                    'name': "💰 Saldo Atual",
                    'value': f"**{player['coin_balance']:,} {config.currency_symbol}**",
                    'inline': True
                },
                {
                    'name': "🎮 Steam ID",
                    'value': f"`{player['steam_id'] or 'Não vinculado'}`",
                    'inline': True
                },
                {
                    'name': "📊 Status",
                    'value': "✅ Ativo" if player['status'] == 'active' else "⛔ Bloqueado",
                    'inline': True
                },
                {
                    'name': "📅 Cadastro",
                    'value': created_at,
                    'inline': True
                },
                {
                    'name': "🕐 Último Acesso",
                    'value': last_access,
                    'inline': True
                },
                {
                    'name': "💳 Transações",
                    'value': f"{tx_count} registradas",
                    'inline': True
                }
            ],
            footer=f"ID: {player['discord_id']} • {config.store_name}"
        )
        
        view = AccountView(interaction.user.id, player)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @staticmethod
    async def show_registration(interaction: discord.Interaction):
        """Show registration form for new players"""
        embed = create_embed(
            title="👤 Bem-vindo à Loja!",
            description=f"Olá **{interaction.user.name}**! Parece que esta é sua primeira vez na **{config.store_name}**.\n\nPara começar, precisamos vincular sua conta do Discord ao seu Steam.",
            color='info',
            fields=[
                {
                    'name': "📝 Por que registrar?",
                    'value': "• Receber seus produtos automaticamente\n• Acompanhar seus pedidos\n• Gerenciar seu saldo de Coins\n• Participar de promoções exclusivas",
                    'inline': False
                },
                {
                    'name': "⚠️ Importante",
                    'value': "Seu Steam ID deve ser válido e único. Não será possível vincular um Steam ID já registrado em outra conta.",
                    'inline': False
                }
            ],
            footer="Passo 1 de 2 - Informações da Conta"
        )
        
        view = RegisterView(interaction.user.id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @staticmethod
    async def confirm_steam_link(interaction: discord.Interaction, steam_id: str):
        """Confirm and process Steam ID linking"""
        discord_id = str(interaction.user.id)
        
        # Validate Steam ID format (basic validation)
        if not steam_id.isdigit() or len(steam_id) < 15:
            await interaction.response.send_message(
                "❌ **Steam ID Inválido**\n\nPor favor, insira um Steam ID válido (ex: 76561198000000000).\n\nVocê pode encontrar seu Steam ID em: https://steamid.io/",
                ephemeral=True
            )
            return
        
        # Check if Steam ID is already registered
        if await PlayerService.steam_exists(steam_id):
            await interaction.response.send_message(
                "❌ **Steam ID Já Registrado**\n\nEste Steam ID já está vinculado a outra conta. Se você acredita que isso é um erro, contate a administração.",
                ephemeral=True
            )
            return
        
        # Show confirmation modal for player name
        modal = PlayerNameModal(steam_id=steam_id)
        await interaction.response.send_modal(modal)
    
    @staticmethod
    async def complete_registration(interaction: discord.Interaction, steam_id: str, player_name: str):
        """Complete player registration"""
        discord_id = str(interaction.user.id)
        discord_username = interaction.user.name
        
        try:
            # Create player
            player = await PlayerService.create_player(
                discord_id=discord_id,
                discord_username=discord_username,
                steam_id=steam_id,
                player_name=player_name
            )
            
            embed = create_embed(
                title="✅ Cadastro Concluído!",
                description=f"Bem-vindo à **{config.store_name}**, **{player_name}**!\n\nSua conta foi criada com sucesso e você já pode começar a usar nossa loja.",
                color='success',
                fields=[
                    {
                        'name': "💰 Saldo Inicial",
                        'value': f"**0 {config.currency_symbol}**",
                        'inline': True
                    },
                    {
                        'name': "🎮 Steam ID",
                        'value': f"`{steam_id}`",
                        'inline': True
                    }
                ],
                footer="Agora você pode explorar a loja!"
            )
            
            view = MainMenuView(interaction.user.id)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao criar conta: {str(e)}\n\nPor favor, tente novamente ou contate a administração.",
                ephemeral=True
            )
    
    @staticmethod
    async def show_transaction_history(interaction: discord.Interaction, player: dict):
        """Show player's transaction history"""
        discord_id = player['discord_id']
        transactions = await PlayerService.get_transaction_history(discord_id, limit=10)
        
        if not transactions:
            embed = create_embed(
                title="📜 Histórico de Transações",
                description="Você ainda não possui transações registradas.",
                color='info'
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Format transactions
        tx_list = []
        for tx in transactions:
            tx_type = tx['transaction_type']
            amount = tx['amount']
            sign = "+" if amount > 0 else ""
            date = tx['created_at'][:16] if tx.get('created_at') else 'N/A'
            
            type_emoji = {
                'purchase': '🛒',
                'bonus': '🎁',
                'admin_add': '➕',
                'admin_remove': '➖',
                'refund': '↩️',
                'removal': '➖'
            }.get(tx_type, '💰')
            
            tx_list.append(f"{type_emoji} `{date}` | {sign}{amount:,} Coins | {tx.get('reason', 'Sem descrição')[:30]}")
        
        embed = create_embed(
            title="📜 Histórico de Transações",
            description="\n".join(tx_list),
            color='info',
            footer=f"Mostrando últimas {len(transactions)} transações"
        )
        
        view = TransactionHistoryView(interaction.user.id, player)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RegisterView(ui.View):
    """View for registration flow"""
    
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="Vincular Steam ID", style=discord.ButtonStyle.primary, emoji="🎮")
    async def link_steam_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(SteamIdModal())
    
    @ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def back_button(self, interaction: discord.Interaction, button: ui.Button):
        await AccountInterface.show_account(interaction)


class PlayerNameModal(ui.Modal, title="Informações do Jogador"):
    """Modal for entering player name"""
    
    def __init__(self, steam_id: str):
        super().__init__()
        self.steam_id = steam_id
        
        self.player_name = ui.TextInput(
            label="Nome do Jogador",
            style=discord.TextStyle.short,
            placeholder="Como você quer ser chamado na loja?",
            max_length=50
        )
        self.add_item(self.player_name)
    
    async def on_submit(self, interaction: discord.Interaction):
        player_name = self.player_name.value.strip()
        if not player_name:
            await interaction.response.send_message(
                "❌ Por favor, insira um nome válido.",
                ephemeral=True
            )
            return
        
        await AccountInterface.complete_registration(interaction, self.steam_id, player_name)


class AccountView(ui.View):
    """View for account menu"""
    
    def __init__(self, user_id: int, player: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.player = player
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @ui.button(label="📜 Histórico", style=discord.ButtonStyle.secondary)
    async def history_button(self, interaction: discord.Interaction, button: ui.Button):
        await AccountInterface.show_transaction_history(interaction, self.player)
    
    @ui.button(label="🔄 Atualizar", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await AccountInterface.show_account(interaction)
    
    @ui.button(label="🏠 Menu Principal", style=discord.ButtonStyle.primary, emoji="🏠")
    async def home_button(self, interaction: discord.Interaction, button: ui.Button):
        await AccountInterface.show_account(interaction)
