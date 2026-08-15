import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
import json
import os
from datetime import datetime

# Настройки бота
TOKEN = os.getenv('DISCORD_TOKEN')  # Обязательно добавьте в переменные окружения Kerit

# ID каналов и ролей (замените на свои)
GUILD_ID =1531643603741442129   # ID вашего сервера
CATEGORY_ID = 1531709462635741297  # ID категории, где будут создаваться тикеты
SUPPORT_ROLE_ID = 1538332828645855287  # ID роли поддержки
LOG_CHANNEL_ID = 1538333206678343691  # ID канала для логов

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ---------- КНОПКИ ДЛЯ СОЗДАНИЯ ТИКЕТА ----------
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
            options=options,
            custom_id="ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        # Проверяем, есть ли уже открытый тикет у пользователя
        guild = interaction.guild
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
            category = await guild.create_category("🎫 Тикеты")

        # Создаём текстовый канал
        channel_name = f"ticket-{interaction.user.name}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.get_role(SUPPORT_ROLE_ID): discord.PermissionOverwrite(
                read_messages=True, send_messages=True
            )
        }

        channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Тикет от {interaction.user.name}"
        )

        # Определяем цвет эмбеда в зависимости от выбора
        colors = {
            "tech": 0xFF4444,   # Красный
            "finance": 0x44FF44, # Зелёный
            "partner": 0x4444FF, # Синий
            "other": 0xFFFF44   # Жёлтый
        }
        color = colors.get(self.values[0], 0xFFFFFF)

        # Отправляем приветственное сообщение в тикет
        embed = discord.Embed(
            title="🎫 Новый тикет",
            description=f"**Тип:** {self.options[0].label if self.values[0] == 'tech' else self.options[1].label if self.values[0] == 'finance' else self.options[2].label if self.values[0] == 'partner' else self.options[3].label}",
            color=color,
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Создал", value=interaction.user.mention, inline=True)
        embed.add_field(name="📅 Дата", value=datetime.now().strftime("%d.%m.%Y %H:%M"), inline=True)
        embed.set_footer(text="Soul Support System", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

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
                description=f"**Канал:** {channel.mention}\n**Создал:** {interaction.user.mention}\n**Тип:** {self.options[0].label if self.values[0] == 'tech' else self.options[1].label if self.values[0] == 'finance' else self.options[2].label if self.values[0] == 'partner' else self.options[3].label}",
                color=0x00FF00,
                timestamp=datetime.now()
            )
            await log_channel.send(embed=log_embed)

        await interaction.response.send_message(
            f"✅ Тикет создан! Перейдите в {channel.mention}",
            ephemeral=True
        )

# ---------- ПАНЕЛЬ СОЗДАНИЯ ТИКЕТОВ ----------
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

# ---------- ОБРАБОТЧИКИ КНОПОК В ТИКЕТЕ ----------
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get("custom_id")

        # Закрытие тикета
        if custom_id == "close_ticket":
            await interaction.response.send_message(
                "🔄 Тикет будет закрыт через 5 секунд...",
                ephemeral=False
            )
            await interaction.channel.send("🔒 Тикет закрывается...")

            # Логируем закрытие
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="🔒 Тикет закрыт",
                    description=f"**Канал:** {interaction.channel.mention}\n**Закрыл:** {interaction.user.mention}",
                    color=0xFF0000,
                    timestamp=datetime.now()
                )
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

                # Обновляем название канала
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

                # Логируем
                log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    log_embed = discord.Embed(
                        title="👋 Тикет взят",
                        description=f"**Канал:** {interaction.channel.mention}\n**Сотрудник:** {interaction.user.mention}",
                        color=0x00FF00,
                        timestamp=datetime.now()
                    )
                    await log_channel.send(embed=log_embed)
            else:
                await interaction.response.send_message(
                    "❌ У вас нет прав для взятия тикета!",
                    ephemeral=True
                )

# ---------- КОМАНДА ДЛЯ СОЗДАНИЯ ПАНЕЛИ ----------
@bot.command()
@commands.has_permissions(administrator=True)
async def ticket_panel(ctx):
    """Создаёт панель для создания тикетов"""
    embed = discord.Embed(
        title="🎫 **Soul Support System**",
        description=(
            "❗ Нажмите на кнопку ниже, чтобы создать тикет.\n\n"
            "• Администрация обрабатывает тикеты в порядке очереди.\n"
            "• Если вы не получили ответ мгновенно — не стоит паниковать.\n"
            "• Мы тоже люди, а не роботы. Просто немного подождите."
        ),
        color=0x5865F2,
        timestamp=datetime.now()
    )
    embed.set_footer(text="Soul Support System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

    view = TicketPanelView()
    await ctx.send(embed=embed, view=view)

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user} запущен и готов к работе!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="тикеты"))

# Запуск
if __name__ == "__main__":
    bot.run(TOKEN)
