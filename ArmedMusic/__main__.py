import asyncio
import importlib
from pyrogram import idle
from pyrogram.errors import FloodWait
from pytgcalls.exceptions import NoActiveGroupCall
import config
from ArmedMusic import LOGGER, app, userbot
from ArmedMusic.core.call import Anony
from ArmedMusic.misc import sudo
import asyncio
import importlib
from pyrogram import idle
from pyrogram.errors import FloodWait
from pytgcalls.exceptions import NoActiveGroupCall
import config
from ArmedMusic import LOGGER, app, userbot
from ArmedMusic.core.call import Anony
from ArmedMusic.misc import sudo
from ArmedMusic.plugins import ALL_MODULES
from ArmedMusic.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS

async def init():
    if not config.STRING1 and (not config.STRING2) and (not config.STRING3) and (not config.STRING4) and (not config.STRING5):
        LOGGER(__name__).error('Assistant client variables not defined, exiting...')
        exit()
    await sudo()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass
    try:
        await app.start()
    except FloodWait as e:
        LOGGER(__name__).info(f"FloodWait detected: waiting {e.value} seconds before retrying...")
        await asyncio.sleep(e.value)
        await app.start()
    for all_module in ALL_MODULES:
        importlib.import_module('ArmedMusic.plugins' + all_module)
    LOGGER('ArmedMusic.plugins').info('Successfully Imported Modules...')
    try:
        await userbot.start()
    except FloodWait as e:
        LOGGER(__name__).info(f"FloodWait detected for userbot: waiting {e.value} seconds before retrying...")
        await asyncio.sleep(e.value)
        await userbot.start()
    await Anony.start()
    try:
        await Anony.stream_call('https://image2url.com/r2/default/videos/1769268795930-72965ce5-60f7-4bf2-bdcd-e5a49cce8ad4.mp4')
    except NoActiveGroupCall:
        LOGGER('ArmedMusic').error('Please turn on the videochat of your log group\\channel.\n\nStopping Bot...')
        exit()
    except:
        pass
    await Anony.decorators()
    await idle()
    await app.stop()
    LOGGER('ArmedMusic').info('Stopping Armed Music Bot...')

def _handle_loop_exception(loop, context):
    try:
        msg = context.get('exception', context.get('message'))
    except Exception:
        msg = str(context)
    LOGGER(__name__).error(f'Unhandled exception in event loop: {msg}', exc_info=True)


def _install_signal_handlers(loop):
    import signal

    def _shutdown(signame):
        LOGGER(__name__).info(f'Received signal {signame}; attempting graceful shutdown...')
        try:
            asyncio.ensure_future(app.stop())
        except Exception:
            pass

    for s in ('SIGINT', 'SIGTERM'):
        try:
            loop.add_signal_handler(getattr(signal, s), lambda s=s: _shutdown(s))
        except Exception:
            # Not all platforms support add_signal_handler (Windows)
            pass


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(_handle_loop_exception)
    _install_signal_handlers(loop)

    # Run init inside a safe wrapper to avoid process exit on recoverable errors
    async def _safe_init():
        while True:
            try:
                await init()
                break
            except Exception as e:
                LOGGER(__name__).error(f'Unhandled exception in init(): {e}', exc_info=True)
                # wait and retry initialization; prevents crash-loop by long sleep
                await asyncio.sleep(10)

    try:
        loop.run_until_complete(_safe_init())
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
from ArmedMusic.plugins import ALL_MODULES
from ArmedMusic.utils.database import get_banned_users, get_gbanned
from config import BANNED_USERS

async def init():
    if not config.STRING1 and (not config.STRING2) and (not config.STRING3) and (not config.STRING4) and (not config.STRING5):
        LOGGER(__name__).error('Assistant client variables not defined, exiting...')
        exit()
    await sudo()
    try:
        users = await get_gbanned()
        for user_id in users:
            BANNED_USERS.add(user_id)
        users = await get_banned_users()
        for user_id in users:
            BANNED_USERS.add(user_id)
    except:
        pass
    try:
        await app.start()
    except FloodWait as e:
        LOGGER(__name__).info(f"FloodWait detected: waiting {e.value} seconds before retrying...")
        await asyncio.sleep(e.value)
        await app.start()
    for all_module in ALL_MODULES:
        importlib.import_module('ArmedMusic.plugins' + all_module)
    LOGGER('ArmedMusic.plugins').info('Successfully Imported Modules...')
    try:
        await userbot.start()
    except FloodWait as e:
        LOGGER(__name__).info(f"FloodWait detected for userbot: waiting {e.value} seconds before retrying...")
        await asyncio.sleep(e.value)
        await userbot.start()
    await Anony.start()
    try:
        await Anony.stream_call('https://image2url.com/r2/default/videos/1769268795930-72965ce5-60f7-4bf2-bdcd-e5a49cce8ad4.mp4')
    except NoActiveGroupCall:
        LOGGER('ArmedMusic').error('Please turn on the videochat of your log group\\channel.\n\nStopping Bot...')
        exit()
    except:
        pass
    await Anony.decorators()
    await idle()
    await app.stop()
    LOGGER('ArmedMusic').info('Stopping Armed Music Bot...')
def _handle_loop_exception(loop, context):
    try:
        msg = context.get('exception', context.get('message'))
    except Exception:
        msg = str(context)
    LOGGER(__name__).error(f'Unhandled exception in event loop: {msg}', exc_info=True)


def _install_signal_handlers(loop):
    import signal

    def _shutdown(signame):
        LOGGER(__name__).info(f'Received signal {signame}; attempting graceful shutdown...')
        try:
            asyncio.ensure_future(app.stop())
        except Exception:
            pass

    for s in ('SIGINT', 'SIGTERM'):
        try:
            loop.add_signal_handler(getattr(signal, s), lambda s=s: _shutdown(s))
        except Exception:
            # Not all platforms support add_signal_handler (Windows)
            pass


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(_handle_loop_exception)
    _install_signal_handlers(loop)

    # Run init inside a safe wrapper to avoid process exit on recoverable errors
    async def _safe_init():
        while True:
            try:
                await init()
                break
            except Exception as e:
                LOGGER(__name__).error(f'Unhandled exception in init(): {e}', exc_info=True)
                # wait and retry initialization; prevents crash-loop by long sleep
                await asyncio.sleep(10)

    try:
        loop.run_until_complete(_safe_init())
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
