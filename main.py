import discord
from discord.ext import commands
import random
import string
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import asyncio
import time
import logging

# Constants
custom_settings = {
    "captcha_timeout": 60,
    "captcha_attempts_limit": 3,
    "rate_limit_window": 60,
    "rate_limit_max_attempts": 3,
    "captcha_retry_limit": 3,
    "captcha_retry_ban_duration": 300
}

# Logging configuration
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Bot initialization
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Global dictionaries
verified_users = {}
verifying_users = {}
last_attempt_timestamp = {}
failed_attempts = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    logging.info(f'Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="all CAPTCHA verifications 🧙‍♂️"))

@bot.event
async def on_member_join(member):
    logging.info(f'{member.display_name} joined the server.')
    await send_captcha(member)

async def send_captcha(member):
    try:
        if member.id in last_attempt_timestamp:
            current_time = time.time()
            time_since_last_attempt = current_time - last_attempt_timestamp[member.id]
            if time_since_last_attempt < custom_settings["rate_limit_window"]:
                await member.send(f"You've exceeded the rate limit. Please wait for {int(custom_settings['rate_limit_window'] - time_since_last_attempt)} seconds before trying again.")
                return
        
        if member.id not in verified_users and member.id not in verifying_users:
            captcha_text = generate_captcha_text(6)
            captcha_image = generate_captcha_image(captcha_text)
            file = discord.File(captcha_image, filename="captcha.png")
            
            embed = discord.Embed(
                title="CAPTCHA Verification",
                description=f"Hello {member.display_name}!\nPlease complete the CAPTCHA below to gain access.",
                color=random.randint(0, 0xFFFFFF)
            )
            embed.add_field(name="Instructions:", value="Type the text displayed in the image in the chat. The CAPTCHA is case-sensitive.")
            embed.set_image(url="attachment://captcha.png")
            embed.set_footer(text="You have 60 seconds to solve the CAPTCHA. Use !retry to refresh the CAPTCHA.")
            
            message = await member.send(embed=embed, file=file)
            verifying_users[member.id] = {"captcha_text": captcha_text, "message_id": message.id}
            await verify_captcha(member, captcha_text)
            last_attempt_timestamp[member.id] = time.time()
    except Exception as e:
        logging.error(f'Error sending CAPTCHA to {member.display_name}: {e}')

async def verify_captcha(member, captcha_text):
    data = verifying_users.get(member.id)
    if not data:
        return
    
    message_id = data["message_id"]
    
    def check(message):
        return message.author == member and message.content == captcha_text
    
    try:
        response = await bot.wait_for('message', check=check, timeout=custom_settings["captcha_timeout"])
        await handle_verification_success(member)
    except asyncio.TimeoutError:
        await handle_verification_failure(member, "timeout")
    except Exception as e:
        logging.error(f'Error verifying CAPTCHA for {member.display_name}: {e}')
        await handle_verification_failure(member, "an unexpected error")
    finally:
        await delete_captcha_message(member, message_id)

async def delete_captcha_message(member, message_id):
    try:
        message = await member.dm_channel.fetch_message(message_id)
        await message.delete()
    except discord.NotFound:
        logging.error(f"Message with ID {message_id} not found.")
    except discord.Forbidden:
        logging.error(f"Bot does not have permission to delete message with ID {message_id}.")

def generate_captcha_text(length):
    captcha_characters = string.ascii_letters + string.digits
    captcha_text = ''.join(random.choices(captcha_characters, k=length))
    return captcha_text

def generate_captcha_image(text):
    width, height = 200, 80
    
    background_color = (random.randint(200, 255), random.randint(200, 255), random.randint(200, 255))
    image = Image.new("RGB", (width, height), color=background_color)
    draw = ImageDraw.Draw(image)
    
    text_color = (random.randint(0, 50), random.randint(0, 50), random.randint(0, 50))
    font_path = random.choice(["arial.ttf", "times.ttf", "cour.ttf"])
    font_size = random.randint(36, 42)
    font = ImageFont.truetype(font_path, font_size)
    
    # Add gradient background
    draw.rectangle([0, 0, width, height], fill=(255,255,255), width=0)
    for i in range(0, width, 10):
        draw.line([(i, 0), (0, i)], fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    
    for char_index, char in enumerate(text):
        char_offset_x = random.randint(-5, 5)
        char_offset_y = random.randint(-5, 5)
        char_position = (10 + char_index * (font_size // 2) + char_offset_x, random.randint(5, 20) + char_offset_y)
        # Rotate each character randomly
        rotation_angle = random.randint(-30, 30)
        draw.text(char_position, char, fill=text_color, font=font, align="center", anchor=None, direction=None, features=None, language=None, stroke_width=0, stroke_fill=None, rotation=rotation_angle)
    
    # Add noise and distortion
    for _ in range(200):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        draw.point((x, y), fill=(random.randint(150, 255), random.randint(150, 255), random.randint(150, 255), random.randint(150, 255)))
    
    # Apply Gaussian blur for additional distortion
    image = image.filter(ImageFilter.GaussianBlur(radius=1.5))
    
    image_buffer = io.BytesIO()
    image.save(image_buffer, format="PNG")
    image_buffer.seek(0)
    
    return image_buffer

async def handle_verification_success(member):
    await member.send("CAPTCHA verification successful! Welcome to the server.")
    verified_users[member.id] = True
    
    role_id = ROLE ID HERE
    role = member.guild.get_role(role_id)
    if role:
        await member.add_roles(role)
    else:        
        logging.error(f"Role with ID {role_id} not found.")
    
    verifying_users.pop(member.id)
    logging.info(f'{member.display_name} successfully verified.')

async def handle_verification_failure(member, reason):
    await member.send(f"CAPTCHA verification failed: {reason}. You have been removed from the server.")
    await member.kick(reason=f"Failed CAPTCHA verification: {reason}")
    verifying_users.pop(member.id)
    logging.info(f'{member.display_name} failed CAPTCHA verification: {reason}')
    
    # Add user to failed attempts dictionary
    if member.id not in failed_attempts:
        failed_attempts[member.id] = 1
    else:
        failed_attempts[member.id] += 1
        # If retry limit exceeded, ban user temporarily
        if failed_attempts[member.id] >= custom_settings["captcha_retry_limit"]:
            await ban_user(member)
            logging.info(f'{member.display_name} banned for exceeding CAPTCHA retry limit.')
            # Reset failed attempts after ban duration
            await asyncio.sleep(custom_settings["captcha_retry_ban_duration"])
            await unban_user(member)
            logging.info(f'{member.display_name} unbanned after {custom_settings["captcha_retry_ban_duration"]} seconds.')
            failed_attempts.pop(member.id)

async def ban_user(member):
    await member.ban(reason=f"Exceeded CAPTCHA retry limit: {custom_settings['captcha_retry_limit']} attempts")

async def unban_user(member):
    await member.guild.unban(member)

@bot.command()
async def retry(ctx):
    if ctx.author.id in verifying_users:
        try:
            message_id = verifying_users[ctx.author.id]["message_id"]
            await delete_captcha_message(ctx.author, message_id)
        except Exception as e:
            logging.error(f"Error deleting CAPTCHA message for {ctx.author.display_name}: {e}")
        
        await send_captcha(ctx.author)

@bot.command()
async def newcaptcha(ctx):
    if ctx.author.id not in verified_users and ctx.author.id not in verifying_users:
        await send_captcha(ctx.author)
    else:
        await ctx.send("You are already verified or currently undergoing verification.")

@bot.event
async def on_message(message):
    if isinstance(message.author, discord.Member) and message.author.id not in verified_users:
        await message.delete()
        if message.author.id not in verifying_users:
            await message.author.send("You must verify the CAPTCHA before you can send messages in the server.")
            await send_captcha(message.author)
    else:
        await bot.process_commands(message)

bot.run('TOKEN HERE')
