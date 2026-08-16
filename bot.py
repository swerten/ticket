import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import os
from datetime import datetime

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
                label="💰 Финансовые вопросы",
                description="Оплата, донаты, премиум",
                emoji="💳",
                value="finance"
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
        guild = interaction.guild

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

        # Создаём канал
        channel_name = f"ticket-{interaction.user.name}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(SUPPORT_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
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
            "finance": "💰 Финансовые вопросы",
            "partner": "🤝 Сотрудничество",
            "other": "❓ Другое"
        }
        ticket_type = ticket_types.get(self.values[0], "❓ Другое")

        # Цвета для разных типов
        colors = {
            "tech": 0xFF4444,
            "finance": 0x44FF44,
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
        embed.set_footer(text="ArbuZ Support System", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

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
            f"{interaction.user.mention} {guild.get_role(SUPPORT_ROLE_ID).mention}",
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
        select = TicketSelect()
        view = View()
        view.add_item(select)
        await interaction.response.send_message(
            "Выберите тип тикета:",
            view=view,
            ephemeral=True
        )


# ==================== ОБРАБОТЧИКИ КНОПОК ====================
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id")

        # Закрытие тикета
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

            import asyncio
            await asyncio.sleep(5)
            await interaction.channel.delete()

        # Взятие тикета
        elif custom_id == "claim_ticket":
            support_role = interaction.guild.get_role(SUPPORT_ROLE_ID)
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
                        if item.custom_id == "claim_ticket":
                            item.disabled = True
                            await interaction.message.edit(view=view)

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


# ==================== КОМАНДА ДЛЯ СОЗДАНИЯ ПАНЕЛИ ====================
@bot.command()
@commands.has_permissions(administrator=True)
async def ticket_panel(ctx):
    """Создаёт панель для создания тикетов"""
    embed = discord.Embed(
        title="🎫 **ArbuZ Support System**",
        description=(
            "❗ Нажмите на кнопку ниже, чтобы создать тикет.\n\n"
            "• Администрация обрабатывает тикеты в порядке очереди.\n"
            "• Если вы не получили ответ мгновенно — не стоит паниковать.\n"
            "• Мы тоже люди, а не роботы. Просто немного подождите."
        ),
        color=0x5865F2,
        timestamp=datetime.now()
    )
    embed.set_footer(
        text="ArbuZ Support System",
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )

    view = TicketPanelView()
    await ctx.send(embed=embed, view=view)


# ==================== СТАТУС БОТА ====================
@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            text="ArbuZ | !ticket_panel"
        )
    )
    print(f"✅ Бот {bot.user} запущен и готов к работе!")
    print(f"ArbuZ Support System активен!")


# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    bot.run(TOKEN)
