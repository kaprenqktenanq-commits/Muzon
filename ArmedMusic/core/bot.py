from pyrogram import Client, errors
from pyrogram.enums import ChatMemberStatus, ParseMode
from pyrogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeAllGroupChats
import config
from ..logging import LOGGER

class Anony(Client):

    def __init__(self):
        LOGGER(__name__).info(f'Starting Bot...')
        super().__init__(name='ArmedMusicBot', api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN, in_memory=True, parse_mode=ParseMode.HTML, max_concurrent_transmissions=7)

    async def start(self):
        await super().start()
        self.id = self.me.id
        self.name = self.me.first_name + ' ' + (self.me.last_name or '')
        self.username = self.me.username
        self.mention = self.me.mention
        
        # Set bot commands for private chats
        private_commands = [
            BotCommand('start', 'Start the bot'),
            BotCommand('song', 'Download a song'),
            BotCommand('help', 'Show help message'),
        ]
        
        # Set bot commands for group chats
        group_commands = [
            BotCommand('play', 'Play music'),
            BotCommand('song', 'Download a song'),
            BotCommand('queue', 'Show queue'),
            BotCommand('pause', 'Pause music'),
            BotCommand('resume', 'Resume music'),
            BotCommand('skip', 'Skip current song'),
            BotCommand('stop', 'Stop music'),
            BotCommand('shuffle', 'Shuffle queue'),
            BotCommand('settings', 'Bot settings'),
        ]
        
        try:
            await self.set_bot_commands(
                commands=private_commands,
                scope=BotCommandScopeDefault()
            )
            await self.set_bot_commands(
                commands=group_commands,
                scope=BotCommandScopeAllGroupChats()
            )
            LOGGER(__name__).info('Bot commands configured successfully')
        except Exception as e:
            LOGGER(__name__).warning(f'Failed to set bot commands: {e}')
            
        try:
            LOGGER(__name__).info(f'Attempting to access log group/channel: {config.LOGGER_ID}')
            await self.send_message(chat_id=config.LOGGER_ID, text=f'<u><b>» {self.mention} ʙᴏᴛ sᴛᴀʀᴛᴇᴅ :</b></u>\n\nɪᴅ : <code>{self.id}</code>\nɴᴀᴍᴇ : {self.name}\nᴜsᴇʀɴᴀᴍᴇ : @{self.username}')
        except (errors.ChannelInvalid, errors.PeerIdInvalid):
            LOGGER(__name__).error('Bot has failed to access the log group/channel. Make sure that you have added your bot to your log group/channel.')
            exit()
        except (errors.BadRequest, errors.Forbidden):
            LOGGER(__name__).error('Bot does not have permission to access the log group/channel. Make sure:\n  1. Bot is added to the group/channel\n  2. Bot has admin permissions\n  3. LOGGER_ID is correct')
            exit()
        except ValueError as ve:
            LOGGER(__name__).error(f'Invalid LOGGER_ID value: {config.LOGGER_ID}. Expected a valid Telegram chat ID (negative for groups).\n  Error: {ve}')
            exit()
        except Exception as ex:
            LOGGER(__name__).error(f'Bot has failed to access the log group/channel.\n  Reason : {type(ex).__name__}: {str(ex)}')
            exit()
        try:
            a = await self.get_chat_member(config.LOGGER_ID, self.id)
            if a.status != ChatMemberStatus.ADMINISTRATOR:
                LOGGER(__name__).error('Please promote your bot as an admin in your log group/channel.')
                exit()
        except Exception as ex:
            LOGGER(__name__).error(f'Failed to verify admin status: {type(ex).__name__}: {str(ex)}')
            exit()
        LOGGER(__name__).info(f'Music Bot Started as {self.name}')

    async def stop(self):
        await super().stop()
