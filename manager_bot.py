import os
import json
import subprocess
import discord
from discord.ext import commands
from keep_alive import keep_alive

# Configuration file for tracking deployed bots and file-based code entries
CONFIG_FILE = 'bots_config.json'
BASE_DIR = 'bots'

# Ensure necessary directories and config
os.makedirs(BASE_DIR, exist_ok=True)
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({}, f)

# Load/save helpers

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# Track subprocesses for each bot
processes = {}

# Initialize Discord bot
token = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.default()
intents.message_content = True  # Needed to read attachments
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user.name} is online and managing bots and code files!")
    # Restart any configured bots on startup
    config = load_config()
    for name, path in config.items():
        if name not in processes and os.path.exists(path):
            start_bot_process(name, path)

# Helper: start a child bot process

def start_bot_process(name, path):
    if name in processes:
        return False
    script = os.path.join(path, 'bot.py')
    if not os.path.isfile(script):
        return False
    proc = subprocess.Popen(
        ['python', script], cwd=path
    )
    processes[name] = proc
    return True

# Helper: stop a child bot process

def stop_bot_process(name):
    proc = processes.pop(name, None)
    if proc:
        proc.terminate()
        return True
    return False

# Command: Add & deploy a bot via Git repo or uploaded file
@bot.command()
async def addbot(ctx, name: str, repo_url: str = None):
    """Add a bot from a Git repo or by file upload (attach a .py file)."""
    config = load_config()
    if name in config:
        return await ctx.send(f"Bot `{name}` already exists.")

    path = os.path.join(BASE_DIR, name)
    os.makedirs(path, exist_ok=True)

    # If repo URL provided, clone it
    if repo_url:
        ret = subprocess.call(['git', 'clone', repo_url, path])
        if ret != 0:
            return await ctx.send("Failed to clone repository.")
    else:
        # Expecting one attachment named bot.py
        if not ctx.message.attachments:
            return await ctx.send("Please attach your bot.py file when no repo URL is given.")
        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith('.py'):
            return await ctx.send("Attachment must be a .py file.")
        file_path = os.path.join(path, 'bot.py')
        await attachment.save(file_path)

    # Update config and start
    config[name] = path
    save_config(config)
    if start_bot_process(name, path):
        await ctx.send(f"Bot `{name}` added and started.")
    else:
        await ctx.send(f"Bot `{name}` added, but failed to start. Check your bot.py.")

# Command: list deployed bots and statuses
@bot.command()
async def listbots(ctx):
    """List all deployed bots with status."""
    config = load_config()
    if not config:
        return await ctx.send("No bots deployed.")
    lines = []
    for name in config:
        status = '🟢 Online' if name in processes else '🔴 Offline'
        lines.append(f"{status} — `{name}`")
    await ctx.send("\n".join(lines))

# Command: remove and stop a bot
@bot.command()
async def removebot(ctx, name: str):
    """Stop and remove a deployed bot."""
    config = load_config()
    if name not in config:
        return await ctx.send(f"Bot `{name}` not found.")
    stop_bot_process(name)
    # Clean up files
    path = config.pop(name)
    subprocess.call(['rm', '-rf', path])
    save_config(config)
    await ctx.send(f"Bot `{name}` stopped and removed.")

# Command: host arbitrary code files (store and list)
@bot.command()
async def uploadcode(ctx, filename: str = None):
    """Upload a code file to host (no auto-run). Attach the file in your message."""
    if not ctx.message.attachments:
        return await ctx.send("Attach a file to upload.")
    attachment = ctx.message.attachments[0]
    name = filename or attachment.filename
    save_path = os.path.join(BASE_DIR, 'files')
    os.makedirs(save_path, exist_ok=True)
    dest = os.path.join(save_path, name)
    await attachment.save(dest)
    await ctx.send(f"File `{name}` uploaded and hosted.")

@bot.command()
async def listfiles(ctx):
    """List hosted code files."""
    file_dir = os.path.join(BASE_DIR, 'files')
    if not os.path.isdir(file_dir):
        return await ctx.send("No files hosted yet.")
    files = os.listdir(file_dir)
    if not files:
        return await ctx.send("No files hosted yet.")
    await ctx.send("Hosted files:\n" + "\n".join(f"`{f}`" for f in files))

# Start the keep-alive server and manager bot
if __name__ == '__main__':
    keep_alive()
    bot.run(token)
