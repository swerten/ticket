import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import os
import asyncio
from datetime import datetime
import logging

# ==================== НАСТРОЙКА ЛОГОВ ====================
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('DISCORD_TOKEN')

# ==================== НАСТРОЙКИ (ЗАМЕНИ НА СВОИ) ====================
GUILD_ID = 1531643603741442129          # ID твоего сервера
CATEGORY_ID = 1531709462635741297       # ID категории для тикетов
SUPPORT_ROLE_ID = 1538332828645855287   # ID роли поддержки
LOG_CHANNEL_ID = 1538333206678343691    # ID канала для логов
# ===================================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ==================== ГЛОБАЛЬНАЯ ОБРАБОТКА ОШИБОК ====================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ У вас нет прав для использования этой команды!")
        return
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Не хватает аргументов: {error.param}")
        return
    
    if isinstance(error, discord.errors.HTTPException):
        if error.status == 429:  # Rate Limit
            await asyncio.sleep(5)
            await ctx.send("⏳ Слишком много запросов, подождите немного...")
            return
        if error.status == 403:
            await ctx.send("❌ У бота недостаточно прав для этого действия!")
            return
    
    # Логируем ошибку
    print(f"Ошибка: {error}")
    await ctx.send(f"❌ Произошла ошибка: {str(error)[:100]}")

# ==================== ВЫБОР ТИПА ТИКЕТА ====================
class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="💻 Техническая поддержка",
                description="Проблемы с ботом, ошибки, баги",
                emoji="🛠️",
                value="tech"
            ),
            discord.SelectOption(
                label="🤝 Сотрудничество",
                description="Партнёрство, реклама, отзывы",
                emoji="📢",
                value="partner"
            ),
            discord.SelectOption(
                label="❓ Другое",
                description="Если не подходит ни один вариант",
                emoji="📝",
                value="other"
            )
        ]
        super().__init__(
            placeholder="Выберите тип тикета...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message("❌ Ошибка: сервер не найден!", ephemeral=True)
                return

            # Проверяем, есть ли уже открытый тикет
            for channel in guild.channels:
                if channel.name == f"ticket-{interaction.user.name}":
                    await interaction.response.send_message(
                        "❌ У вас уже есть открытый тикет! Закройте его, чтобы создать новый.",
                        ephemeral=True
                    )
                    return

            # Создаём категорию, если её нет
            category = discord.utils.get(guild.categories, id=CATEGORY_ID)
            if not category:
                category = await guild.create_category("🎫 Тикеты ArbuZ")
                print(f"Создана категория: {category.name}")

            # Создаём канал
            channel_name = f"ticket-{interaction.user.name}"
            support_role = guild.get_role(SUPPORT_ROLE_ID)
            
            if not support_role:
                await interaction.response.send_message(
                    "❌ Ошибка: роль поддержки не найдена! Обратитесь к администратору.",
                    ephemeral=True
                )
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            channel = await guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites,
                reason=f"Тикет от {interaction.user.name}"
            )

            # Определяем тип тикета
            ticket_types = {
                "tech": "💻 Техническая поддержка",
                "partner": "🤝 Сотрудничество",
                "other": "❓ Другое"
            }
            ticket_type = ticket_types.get(self.values[0], "❓ Другое")

            # Цвета для разных типов
            colors = {
                "tech": 0xFF4444,
                "partner": 0x4444FF,
                "other": 0xFFFF44
            }
            color = colors.get(self.values[0], 0x5865F2)

            # Приветственное сообщение в тикете
            embed = discord.Embed(
                title="🎫 Новый тикет",
                description=f"**Тип:** {ticket_type}",
                color=color,
                timestamp=datetime.now()
            )
            embed.add_field(name="👤 Создал", value=interaction.user.mention, inline=True)
            embed.add_field(name="📅 Дата", value=datetime.now().strftime("%d.%m.%Y %H:%M"), inline=True)
            embed.add_field(name="📌 Статус", value="🟡 Ожидает ответа", inline=True)
            embed.set_footer(
                text="ArbuZ Support System",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )

            # Кнопки
            close_button = Button(
                label="❌ Закрыть тикет",
                style=discord.ButtonStyle.danger,
                custom_id="close_ticket"
            )
            claim_button = Button(
                label="👋 Взять тикет",
                style=discord.ButtonStyle.success,
                custom_id="claim_ticket"
            )

            view = View()
            view.add_item(claim_button)
            view.add_item(close_button)

            await channel.send(
                f"{interaction.user.mention} {support_role.mention}",
                embed=embed,
                view=view
            )

            # Логируем создание тикета
            log_channel = guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="📩 Новый тикет",
                    description=f"**Канал:** {channel.mention}\n**Создал:** {interaction.user.mention}\n**Тип:** {ticket_type}",
                    color=0x00FF00,
                    timestamp=datetime.now()
                )
                log_embed.set_footer(text="ArbuZ Support System")
                await log_channel.send(embed=log_embed)

            await interaction.response.send_message(
                f"✅ Тикет создан! Перейдите в {channel.mention}",
                ephemeral=True
            )
            
        except discord.errors.HTTPException as e:
            await interaction.response.send_message(
                f"❌ Ошибка при создании тикета: {str(e)[:100]}",
                ephemeral=True
            )
            print(f"HTTP ошибка: {e}")
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Произошла непредвиденная ошибка! Попробуйте позже.",
                ephemeral=True
            )
            print(f"Ошибка в TicketSelect: {e}")

# ==================== ПАНЕЛЬ СОЗДАНИЯ ТИКЕТОВ ====================
class TicketPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 Создать тикет",
        style=discord.ButtonStyle.primary,
        custom_id="create_ticket",
        emoji="🎫"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        try:
            select = TicketSelect()
            view = View()
            view.add_item(select)
            await interaction.response.send_message(
                "Выберите тип тикета:",
                view=view,
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "❌ Ошибка при создании тикета!",
                ephemeral=True
            )
            print(f"Ошибка в create_ticket: {e}")

# ==================== ОБРАБОТЧИКИ КНОПОК ====================
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        try:
            custom_id = interaction.data.get("custom_id")
            
            if custom_id == "close_ticket":
                await interaction.response.send_message(
                    "🔒 Тикет будет закрыт через 5 секунд...",
                    ephemeral=False
                )
                await interaction.channel.send("🔒 Тикет закрывается. Спасибо за обращение!")

                # Логируем закрытие
                log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(
                        title="🔒 Тикет закрыт",
                        description=f"**Канал:** {interaction.channel.mention}\n**Закрыл:** {interaction.user.mention}",
                        color=0xFF0000,
                        timestamp=datetime.now()
                    )
                    log_embed.set_footer(text="ArbuZ Support System")
                    await log_channel.send(embed=log_embed)

                await asyncio.sleep(5)
                await interaction.channel.delete()

            elif custom_id == "claim_ticket":
                support_role = interaction.guild.get_role(SUPPORT_ROLE_ID)
                if not support_role:
                    await interaction.response.send_message(
                        "❌ Роль поддержки не найдена!",
                        ephemeral=True
                    )
                    return

                if support_role in interaction.user.roles:
                    await interaction.response.send_message(
                        f"✅ {interaction.user.mention} взял тикет в работу!",
                        ephemeral=False
                    )

                    # Меняем название канала
                    try:
                        await interaction.channel.edit(
                            name=f"📌 {interaction.channel.name}"
                        )
                    except:
                        pass

                    # Отключаем кнопку взятия
                    view = interaction.message.view
                    if view:
                        for item in view.children:
                            if hasattr(item, 'custom_id') and item.custom_id == "claim_ticket":
                                item.disabled = True
                                await interaction.message.edit(view=view)
                                break

                    # Обновляем статус в эмбеде
                    if interaction.message.embeds:
                        embed = interaction.message.embeds[0]
                        embed_dict = embed.to_dict()
                        for i, field in enumerate(embed_dict.get('fields', [])):
                            if field.get('name') == "📌 Статус":
                                embed_dict['fields'][i]['value'] = "🟢 В работе (взял " + interaction.user.mention + ")"
                                break
                        new_embed = discord.Embed.from_dict(embed_dict)
                        await interaction.message.edit(embed=new_embed)

                    # Логируем взятие
                    log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
                    if log_channel:
                        log_embed = discord.Embed(
                            title="👋 Тикет взят",
                            description=f"**Канал:** {interaction.channel.mention}\n**Сотрудник:** {interaction.user.mention}",
                            color=0x00FF00,
                            timestamp=datetime.now()
                        )
                        log_embed.set_footer(text="ArbuZ Support System")
                        await log_channel.send(embed=log_embed)
                else:
                    await interaction.response.send_message(
                        "❌ У вас нет прав для взятия тикета!",
                        ephemeral=True
                    )
                    
        except Exception as e:
            try:
                await interaction.response.send_message(
                    f"❌ Ошибка: {str(e)[:100]}",
                    ephemeral=True
                )
            except:
                pass
            print(f"Ошибка в on_interaction: {e}")

# ==================== КОМАНДА ДЛЯ СОЗДАНИЯ ПАНЕЛИ ====================
@bot.command()
@commands.has_permissions(administrator=True)
async def ticket_panel(ctx):
    """Создаёт панель для создания тикетов"""
    try:
        # Арбузная картинка
        arbuZ_image = "https://i.imgur.com/dwKcG3h.jpeg"
        
        embed = discord.Embed(
            title="🎫 **ArbuZ Support System**",
            description=(
                "❗ Нажмите на кнопку ниже, чтобы создать тикет.\n\n"
                "🕒 Администрация обрабатывает тикеты в порядке очереди.\n"
                "Если вы не получили ответ мгновенно — не стоит паниковать.\n"
                "Мы тоже люди, а не роботы. Просто немного подождите.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=0x5865F2,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=arbuZ_image)
        embed.set_footer(
            text="ArbuZ Support System",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )

        view = TicketPanelView()
        await ctx.send(embed=embed, view=view)
        
    except Exception as e:
        await ctx.send(f"❌ Ошибка при создании панели: {str(e)[:100]}")
        print(f"Ошибка в ticket_panel: {e}")

# ==================== КОМАНДА ДЛЯ ПРОВЕРКИ ID ====================
@bot.command()
@commands.has_permissions(administrator=True)
async def get_ids(ctx):
    """Показывает ID сервера и каналов"""
    embed = discord.Embed(
        title="📋 ID на сервере",
        color=0x5865F2
    )
    embed.add_field(name="🆔 Сервер", value=f"`{ctx.guild.id}`", inline=False)
    
    # Категории
    categories = [c for c in ctx.guild.categories][:5]
    cat_text = "\n".join([f"{c.name}: `{c.id}`" for c in categories]) or "Нет категорий"
    embed.add_field(name="📁 Категории", value=cat_text, inline=False)
    
    # Каналы
    channels = [c for c in ctx.guild.text_channels][:5]
    chan_text = "\n".join([f"#{c.name}: `{c.id}`" for c in channels])
    embed.add_field(name="📢 Текстовые каналы", value=chan_text, inline=False)
    
    # Роли
    roles = [r for r in ctx.guild.roles if not r.is_default()][:5]
    role_text = "\n".join([f"@{r.name}: `{r.id}`" for r in roles])
    embed.add_field(name="👤 Роли", value=role_text, inline=False)
    
    await ctx.send(embed=embed)

# ==================== СТАТУС БОТА ====================
@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="ArbuZ | !ticket_panel"
        )
    )
    print(f"✅ Бот {bot.user} запущен и готов к работе!")
    print(f"🍉 ArbuZ Support System активен!")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"🆔 ID сервера: {GUILD_ID}")
    print(f"📁 ID категории: {CATEGORY_ID}")
    print(f"👤 ID роли поддержки: {SUPPORT_ROLE_ID}")
    print(f"📊 ID канала логов: {LOG_CHANNEL_ID}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ОШИБКА: Токен не найден! Добавь переменную DISCORD_TOKEN в Render")
        exit(1)
    
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("❌ ОШИБКА: Неверный токен! Проверь DISCORD_TOKEN")
    except Exception as e:
        print(f"❌ ОШИБКА при запуске: {e}")
