"""
SDN_DZSTORE_BOT - Main Bot Application
DayZ Virtual Store System for Discord
"""

import discord
from discord import app_commands, ui
from discord.ext import commands
import asyncio
import logging

from config import config, Config
from database import db
from services import PlayerService
from interfaces.discord_ui import MainMenuView, create_embed, HelpInterface
from interfaces.account_interface import AccountInterface


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sdn_dzstore_bot')


class SDNZStoreBot(commands.Bot):
    """Main bot class"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.config = config
        self.loaded = False
    
    async def setup_hook(self):
        """Setup hook called before bot starts"""
        logger.info("Connecting to database...")
        await db.connect()
        logger.info("Database connected successfully")
        
        # Load default categories if none exist
        await self._load_default_data()
        
        self.loaded = True
        logger.info("Bot setup completed")
    
    async def _load_default_data(self):
        """Load default categories and sample data"""
        from services import CategoryService, ProductService, CoinPackageService
        
        # Check if categories exist
        categories = await CategoryService.get_all_categories(status=None)
        
        if not categories:
            logger.info("Loading default categories...")
            default_categories = [
                {"name": "Armas", "icon": "🔫", "description": "Armas e equipamentos militares"},
                {"name": "Kits", "icon": "🎒", "description": "Kits de sobrevivência e equipamentos"},
                {"name": "VIP", "icon": "👑", "description": "Benefícios VIP exclusivos"},
                {"name": "Veículos", "icon": "🚗", "description": "Carros, motos e helicópteros"},
                {"name": "Cosméticos", "icon": "🎨", "description": "Skins e personalizações"},
                {"name": "Caixas", "icon": "📦", "description": "Caixas surpresa e loot boxes"},
                {"name": "Serviços", "icon": "⚙️", "description": "Serviços e customizações"},
            ]
            
            for i, cat in enumerate(default_categories):
                await CategoryService.create_category(
                    name=cat['name'],
                    description=cat['description'],
                    icon=cat['icon'],
                    display_order=i
                )
            
            logger.info("Default categories loaded")
        
        # Check if coin packages exist
        packages = await CoinPackageService.get_all_packages(status=None)
        
        if not packages:
            logger.info("Loading default coin packages...")
            default_packages = [
                {"name": "Pacote Bronze", "coins": 500, "bonus": 0, "price": 4.99},
                {"name": "Pacote Prata", "coins": 1200, "bonus": 100, "price": 9.99},
                {"name": "Pacote Ouro", "coins": 2500, "bonus": 500, "price": 19.99},
                {"name": "Pacote Diamante", "coins": 5500, "bonus": 1500, "price": 39.99},
            ]
            
            for i, pkg in enumerate(default_packages):
                await CoinPackageService.create_package(
                    name=pkg['name'],
                    coin_amount=pkg['coins'],
                    bonus_amount=pkg['bonus'],
                    price=pkg['price'],
                    description=f"{pkg['coins']} Coins + {pkg['bonus']} Bônus",
                    display_order=i
                )
            
            logger.info("Default coin packages loaded")
        
        # Check if products exist
        products = await ProductService.get_all_products(status=None)
        
        if not products:
            logger.info("Loading sample products...")
            cats = await CategoryService.get_all_categories()
            
            if cats:
                # Get first category for sample products
                kit_cat = next((c for c in cats if c['name'] == 'Kits'), cats[0])
                
                await ProductService.create_product(
                    name="Kit Iniciante",
                    description="Kit básico para sobreviventes iniciantes. Inclui comida, água e equipamento básico.",
                    category_id=kit_cat['id'],
                    price=500,
                    stock=-1,
                    delivery_type="manual",
                    delivery_data='{"items": ["food_can", "water_bottle", "hatchet"]}'
                )
                
                await ProductService.create_product(
                    name="Kit Militar",
                    description="Equipamento militar completo para jogadores experientes.",
                    category_id=kit_cat['id'],
                    price=2500,
                    stock=-1,
                    delivery_type="manual",
                    delivery_data='{"items": ["assault_rifle", "ammo_box", "tactical_vest"]}'
                )
                
                logger.info("Sample products loaded")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"Bot logged in as {self.user.name}")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        
        # Sync commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
        
        # Change presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name=f"{config.store_name}"
            )
        )
    
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle interactions"""
        if interaction.type == discord.InteractionType.ping:
            return
        
        # Update player last access if registered
        if interaction.user and not interaction.user.bot:
            await PlayerService.update_last_access(str(interaction.user.id))


# Create bot instance
bot = SDNZStoreBot()


# Register slash commands
@bot.tree.command(name="loja", description="Abrir a loja virtual")
async def store_command(interaction: discord.Interaction):
    """Open the main store menu"""
    from interfaces.store_interface import StoreInterface
    await StoreInterface.show_categories(interaction)


@bot.tree.command(name="conta", description="Gerenciar sua conta")
async def account_command(interaction: discord.Interaction):
    """Manage your account"""
    await AccountInterface.show_account(interaction)


@bot.tree.command(name="coins", description="Comprar Coins")
async def coins_command(interaction: discord.Interaction):
    """Buy coins"""
    from interfaces.coins_interface import CoinsInterface
    await CoinsInterface.show_coins_menu(interaction)


@bot.tree.command(name="pedidos", description="Ver seus pedidos")
async def orders_command(interaction: discord.Interaction):
    """View your orders"""
    from interfaces.orders_interface import OrdersInterface
    await OrdersInterface.show_orders(interaction)


@bot.tree.command(name="carrinho", description="Ver seu carrinho")
async def cart_command(interaction: discord.Interaction):
    """View your cart"""
    from interfaces.cart_interface import CartInterface
    await CartInterface.show_cart(interaction)


@bot.tree.command(name="ajuda", description="Central de ajuda")
async def help_command(interaction: discord.Interaction):
    """Show help center"""
    await HelpInterface.show_help(interaction)


@bot.tree.command(name="admin", description="Painel administrativo (Apenas admins)")
async def admin_command(interaction: discord.Interaction):
    """Admin panel (Admins only)"""
    from interfaces.admin_interface import AdminInterface
    
    # Check if user is admin
    if not await AdminInterface.check_admin_permission(interaction):
        await interaction.response.send_message(
            "❌ Você não tem permissão para acessar o painel administrativo.",
            ephemeral=True
        )
        return
    
    await AdminInterface.show_admin_panel(interaction)


# Error handler
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError) -> None:
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        await interaction.response.send_message("❌ Comando não encontrado.", ephemeral=True)
    elif isinstance(error, commands.MissingPermissions):
        await interaction.response.send_message("❌ Você não tem permissão para usar este comando.", ephemeral=True)
    else:
        logger.error(f"Command error: {error}")
        await interaction.response.send_message(
            f"❌ Ocorreu um erro: {str(error)}\n\nTente novamente ou contate a administração.",
            ephemeral=True
        )


async def main():
    """Main entry point"""
    logger.info("Starting SDN_DZSTORE_BOT...")
    logger.info(f"Store Name: {config.store_name}")
    logger.info(f"Currency: {config.currency_name} ({config.currency_symbol})")
    
    token = config.token
    
    if not token:
        logger.error("No Discord token found! Please set DISCORD_TOKEN in .env or config.json")
        return
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("Invalid Discord token!")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")


if __name__ == "__main__":
    asyncio.run(main())
