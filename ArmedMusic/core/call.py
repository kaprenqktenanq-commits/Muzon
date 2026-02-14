import asyncio
import os
from datetime import datetime ,timedelta
from typing import Union

from pyrogram import Client
from pyrogram .types import InlineKeyboardMarkup

import pyrogram
from pyrogram import errors as py_errors
if not hasattr (py_errors ,'GroupcallForbidden'):
    class GroupcallForbidden (Exception ):

        pass
    py_errors .GroupcallForbidden =GroupcallForbidden

from pytgcalls import PyTgCalls
try:
    from pytgcalls.exceptions import (
        NoActiveGroupCall,
        AlreadyJoinedError,
    )
except Exception:
    from pytgcalls.exceptions import NoActiveGroupCall
    class AlreadyJoinedError(Exception):
        pass
from ntgcalls import TelegramServerError
from pytgcalls .types import Update ,StreamEnded
from pytgcalls import filters as fl
from pytgcalls .types import AudioQuality ,VideoQuality
from pytgcalls .types import MediaStream ,ChatUpdate

import config
from config import autoclean
from ArmedMusic import LOGGER ,YouTube ,app
from ArmedMusic .misc import db
from ArmedMusic .utils .database import (
add_active_chat ,
add_active_video_chat ,
get_lang ,
get_loop ,
group_assistant ,
is_autoend ,
music_on ,
remove_active_chat ,
remove_active_video_chat ,
set_loop ,
)
from ArmedMusic .utils .exceptions import AssistantErr
from ArmedMusic .utils .formatters import check_duration ,seconds_to_min ,speed_converter ,remove_emoji
from ArmedMusic .utils .inline .play import stream_markup
from ArmedMusic .utils .thumbnails import get_thumb
from strings import get_string

autoend ={}
counter ={}
stream_start_time ={}

async def _clear_ (chat_id ):
    db [chat_id ]=[]
    await remove_active_video_chat (chat_id )
    await remove_active_chat (chat_id )
    # Clear stream start time tracking
    if chat_id in stream_start_time :
        del stream_start_time [chat_id ]

class Call (PyTgCalls ):
    def __init__ (self ):
        self .userbot1 =Client (
        name ="DevAss1",
        api_id =config .API_ID ,
        api_hash =config .API_HASH ,
        session_string =str (config .STRING1 ),
        )
        self .one =PyTgCalls (
        self .userbot1 ,
        cache_duration =100 ,
        )
        self .userbot2 =Client (
        name ="DevAss2",
        api_id =config .API_ID ,
        api_hash =config .API_HASH ,
        session_string =str (config .STRING2 ),
        )
        self .two =PyTgCalls (
        self .userbot2 ,
        cache_duration =100 ,
        )
        self .userbot3 =Client (
        name ="DevAss3",
        api_id =config .API_ID ,
        api_hash =config .API_HASH ,
        session_string =str (config .STRING3 ),
        )
        self .three =PyTgCalls (
        self .userbot3 ,
        cache_duration =100 ,
        )
        self .userbot4 =Client (
        name ="DevAss4",
        api_id =config .API_ID ,
        api_hash =config .API_HASH ,
        session_string =str (config .STRING4 ),
        )
        self .four =PyTgCalls (
        self .userbot4 ,
        cache_duration =100 ,
        )
        self .userbot5 =Client (
        name ="DevAss5",
        api_id =config .API_ID ,
        api_hash =config .API_HASH ,
        session_string =str (config .STRING5 ),
        )
        self .five =PyTgCalls (
        self .userbot5 ,
        cache_duration =100 ,
        )

    async def pause_stream (self ,chat_id :int ):
        assistant =await group_assistant (self ,chat_id )
        await assistant .pause (chat_id )

    async def resume_stream (self ,chat_id :int ):
        assistant =await group_assistant (self ,chat_id )
        await assistant .resume (chat_id )

    async def stop_stream (self ,chat_id :int ):
        try :
            assistant =await group_assistant (self ,chat_id )
            try :
                await _clear_ (chat_id )
            except Exception as e :
                LOGGER (__name__ ).warning (f"Error clearing chat {chat_id}: {e }")
            try :
                await assistant .leave_call (chat_id )
            except Exception as e :
                LOGGER (__name__ ).warning (f"Error leaving call for {chat_id}: {e }")
        except Exception as e :
            LOGGER (__name__ ).error (f"Error in stop_stream for {chat_id}: {e }")
            try :
                await _clear_ (chat_id )
            except :
                pass

    async def stop_stream_force (self ,chat_id :int ):
        try :
            if config .STRING1 :
                await self .one .leave_call (chat_id )
        except :
            pass
        try :
            if config .STRING2 :
                await self .two .leave_call (chat_id )
        except :
            pass
        try :
            if config .STRING3 :
                await self .three .leave_call (chat_id )
        except :
            pass
        try :
            if config .STRING4 :
                await self .four .leave_call (chat_id )
        except :
            pass
        try :
            if config .STRING5 :
                await self .five .leave_call (chat_id )
        except :
            pass
        try :
            await _clear_ (chat_id )
        except :
            pass

    async def speedup_stream (self ,chat_id :int ,file_path ,speed ,playing ):
        assistant =await group_assistant (self ,chat_id )
        if str (speed )!=str ("1.0"):
            base =os .path .basename (file_path )
            chatdir =os .path .join (os .getcwd (),"playback",str (speed ))
            if not os .path .isdir (chatdir ):
                os .makedirs (chatdir )
            out =os .path .join (chatdir ,base )
            if not os .path .isfile (out ):
                if str (speed )==str ("0.5"):
                    vs =2.0
                if str (speed )==str ("0.75"):
                    vs =1.35
                if str (speed )==str ("1.5"):
                    vs =0.68
                if str (speed )==str ("2.0"):
                    vs =0.5
                proc =await asyncio .create_subprocess_shell (
                cmd =(
                "ffmpeg "
                "-i "
                f"{file_path } "
                "-filter:v "
                f"setpts={vs }*PTS "
                "-filter:a "
                f"atempo={speed } "
                f"{out }"
                ),
                stdin =asyncio .subprocess .PIPE ,
                stderr =asyncio .subprocess .PIPE ,
                )
                await proc .communicate ()
            else :
                pass
        else :
            out =file_path
        dur =await asyncio .get_event_loop ().run_in_executor (None ,check_duration ,out )
        dur =int (dur )
        played ,con_seconds =speed_converter (playing [0 ]["played"],speed )
        duration =seconds_to_min (dur )
        stream =(
        MediaStream (
        out ,
        audio_parameters =AudioQuality .HIGH ,
        video_parameters =VideoQuality .SD_480p ,
        ffmpeg_parameters =f"-ss {played } -to {duration }",

        )
        if playing [0 ]["streamtype"]=="video"
        else MediaStream (
        out ,
        audio_parameters =AudioQuality .HIGH ,
        ffmpeg_parameters =f"-ss {played } -to {duration }",
        video_flags =MediaStream .Flags .IGNORE
        )
        )
        if str (db [chat_id ][0 ]["file"])==str (file_path ):
            await assistant .play (chat_id ,stream )
        else :
            raise AssistantErr ("Umm")
        if str (db [chat_id ][0 ]["file"])==str (file_path ):
            exis =(playing [0 ]).get ("old_dur")
            if not exis :
                db [chat_id ][0 ]["old_dur"]=db [chat_id ][0 ]["dur"]
                db [chat_id ][0 ]["old_second"]=db [chat_id ][0 ]["seconds"]
            db [chat_id ][0 ]["played"]=con_seconds
            db [chat_id ][0 ]["dur"]=duration
            db [chat_id ][0 ]["seconds"]=dur
            db [chat_id ][0 ]["speed_path"]=out
            db [chat_id ][0 ]["speed"]=speed

    async def force_stop_stream (self ,chat_id :int ):
        assistant =await group_assistant (self ,chat_id )
        try :
            check =db .get (chat_id )
            check .pop (0 )
        except :
            pass
        await remove_active_video_chat (chat_id )
        await remove_active_chat (chat_id )
        try :
            await assistant .leave_call (chat_id )
        except :
            pass

    async def skip_stream (
    self ,
    chat_id :int ,
    link :str ,
    video :Union [bool ,str ]=None ,
    image :Union [bool ,str ]=None ,
    ):
        assistant =await group_assistant (self ,chat_id )
        if video :
            stream =MediaStream (
            link ,
            audio_parameters =AudioQuality .HIGH ,
            video_parameters =VideoQuality .SD_480p ,
            ffmpeg_parameters ="-ar 48000 -ac 2 -b:a 256k -bufsize 128k",
            )
        else :
            stream =MediaStream (link ,audio_parameters =AudioQuality .HIGH ,video_flags =MediaStream .Flags .IGNORE ,ffmpeg_parameters ="-ar 48000 -ac 2 -b:a 256k -bufsize 128k")
        await assistant .play (
        chat_id ,
        stream ,
        )

    async def seek_stream (self ,chat_id ,file_path ,to_seek ,duration ,mode ):
        assistant =await group_assistant (self ,chat_id )
        stream =(
        MediaStream (
        file_path ,
        audio_parameters =AudioQuality .HIGH ,
        video_parameters =VideoQuality .SD_480p ,
        ffmpeg_parameters =f"-ss {to_seek } -to {duration }",
        )
        if mode =="video"
        else MediaStream (
        file_path ,
        audio_parameters =AudioQuality .HIGH ,
        video_flags =MediaStream .Flags .IGNORE ,
        ffmpeg_parameters =f"-ss {to_seek } -to {duration }",
        )
        )
        await assistant .play (chat_id ,stream )

    async def stream_call (self ,link ):

        try :
            assistant =await group_assistant (self ,config .LOGGER_ID )
            await assistant .play (
            config .LOGGER_ID ,
            MediaStream (link ,ffmpeg_parameters ="-ar 48000 -ac 2 -b:a 256k -bufsize 128k")
            )
            await asyncio .sleep (0.2 )
            await assistant .leave_call (config .LOGGER_ID )
            LOGGER (__name__ ).info ("✓ Stream test successful")
        except NoActiveGroupCall :
            LOGGER (__name__ ).error ("No active group call in log channel. Enable voice chat.")
            raise
        except TelegramServerError as e :
            LOGGER (__name__ ).warning (f"Server error during stream test (will retry): {e }")
            await asyncio .sleep (3 )
        except ValueError as ve :
            if 'Peer id invalid'in str (ve ):
                LOGGER (__name__ ).warning (f"Cannot access log group for stream test - group may not be accessible. This is non-critical.")
            else :
                LOGGER (__name__ ).error (f"Stream test error: ValueError: {ve }")
        except Exception as e :
            LOGGER (__name__ ).error (f"Stream test error: {type (e ).__name__ }: {e }")

    async def join_call (
    self ,
    chat_id :int ,
    original_chat_id :int ,
    link ,
    video :Union [bool ,str ]=None ,
    image :Union [bool ,str ]=None ,
    ):
        assistant =await group_assistant (self ,chat_id )
        language =await get_lang (chat_id )
        _ =get_string (language )
        if video :
            stream =MediaStream (
            link ,
            audio_parameters =AudioQuality .HIGH ,video_parameters =VideoQuality .SD_480p ,
            ffmpeg_parameters ="-ar 48000 -ac 2 -b:a 256k -bufsize 128k",
            )
        else :
            stream =MediaStream (
            link ,
            audio_parameters =AudioQuality .HIGH ,
            video_flags =MediaStream .Flags .IGNORE ,
            ffmpeg_parameters ="-ar 48000 -ac 2 -b:a 256k -bufsize 128k",
            )
        try :
            # Ensure assistant is ready before first play
            await asyncio .sleep (0.5 )
            await assistant .play (
            chat_id ,
            stream
            )

        except NoActiveGroupCall :
            raise AssistantErr (_ ["call_8"])
        except AlreadyJoinedError :
            raise AssistantErr (_ ["call_9"])
        except TelegramServerError :
            raise AssistantErr (_ ["call_10"])
        except Exception as e :
            LOGGER (__name__ ).error (f"Unexpected error joining call {chat_id}: {e }")
            raise AssistantErr (_ ["call_10"])
        # Give pytgcalls and FFmpeg time to initialize the audio pipeline
        await asyncio .sleep (0.5 )
        await add_active_chat (chat_id )
        await music_on (chat_id )
        if video :
            await add_active_video_chat (chat_id )
        # Track when this stream started to prevent premature stream-end detection
        stream_start_time [chat_id ]=datetime .now ()
        if await is_autoend ():
            counter [chat_id ]={}
            try:
                users =len (await assistant .get_participants (chat_id ))
                # Բոտի համար միայն 30 վայրկյան, ուստի բոտ ինքնուրույն չի մնա
                if users >1 :
                    autoend [chat_id ]=datetime .now ()+timedelta (minutes =60 )
            except:
                pass

    async def change_stream (self ,client ,chat_id ):
        try:
            # Կարճ delay՝ որպեսզի queue-ն ժամանակ ունենա լցվելու
            await asyncio.sleep(0.5)
        except:
            pass
        
        # Check if stream has been playing for a minimum duration
        # This prevents false stream-end events triggered while stream is initializing
        current_time = datetime.now()
        if chat_id in stream_start_time:
            elapsed = (current_time - stream_start_time[chat_id]).total_seconds()
            # If less than 2 seconds have elapsed, it's likely a false positive
            if elapsed < 2:
                LOGGER(__name__).warning(f"Ignoring premature stream-end event for {chat_id} (elapsed: {elapsed:.1f}s)")
                return
            
        check =db .get (chat_id )
        popped =None
        loop =await get_loop (chat_id )
        try :
            if loop ==0 :
                popped =check .pop (0 )
            else :
                loop =loop -1
                await set_loop (chat_id ,loop )
            if popped :
                rem =popped ["file"]
                autoclean .remove (rem )
            if not check :
                await _clear_ (chat_id )
                return await client .leave_call (chat_id )
        except :
            try :
                await _clear_ (chat_id )
                return await client .leave_call (chat_id )
            except :
                return
        else :
            queued =check [0 ]["file"]
            language =await get_lang (chat_id )
            _ =get_string (language )
            title =(check [0 ]["title"]).title ()
            user =check [0 ]["by"]
            user_id =check [0 ]["user_id"]
            original_chat_id =check [0 ]["chat_id"]
            streamtype =check [0 ]["streamtype"]
            videoid =check [0 ]["vidid"]
            db [chat_id ][0 ]["played"]=0
            exis =(check [0 ]).get ("old_dur")
            if exis :
                db [chat_id ][0 ]["dur"]=exis
                db [chat_id ][0 ]["seconds"]=check [0 ]["old_second"]
                db [chat_id ][0 ]["speed_path"]=None
                db [chat_id ][0 ]["speed"]=1.0
            video =True if str (streamtype )=="video"else False
            if "live_"in queued :
                n ,link =await YouTube .video (videoid ,True )
                if n ==0 :
                    return await app .send_message (
                    original_chat_id ,
                    text =_ ["call_6"],
                    )
                if video :
                    stream =MediaStream (
                    link ,
                    audio_parameters =AudioQuality .HIGH ,
                    video_parameters =VideoQuality .SD_480p ,
                    ffmpeg_parameters ="-ar 48000 -ac 2 -b:a 256k -bufsize 128k",
                    )
                else :
                    stream =MediaStream (
                    link ,
                    audio_parameters =AudioQuality .HIGH ,
                    video_flags =MediaStream .Flags .IGNORE ,
                    ffmpeg_parameters ="-ar 48000 -ac 2 -b:a 256k -bufsize 128k",
                    )
                try :
                    await client .play (chat_id ,stream )
                    await asyncio .sleep (0.1 )
                    # Update stream start time when playing new song
                    stream_start_time [chat_id ]=datetime .now ()
                except Exception :
                    return await app .send_message (
                    original_chat_id ,
                    text =_ ["call_6"],
                    )
                img =await get_thumb (videoid ,user_id )
                button =stream_markup (_ ,chat_id )

                display_title =remove_emoji (title )
                msg_link =check [0 ].get ('link',f"https://t.me/{app .username }?start=info_{videoid }")
                run =await app .send_photo (
                chat_id =original_chat_id ,
                photo =img ,
                caption =_ ["stream_1"].format (
                msg_link ,
                display_title ,
                check [0 ]["dur"],
                user ,
                ),
                reply_markup =InlineKeyboardMarkup (button ),
                )
                db [chat_id ][0 ]["mystic"]=run
                db [chat_id ][0 ]["markup"]="yt"

                try :
                    from ArmedMusic .utils .stream .stream import _add_requester_message_link
                    await _add_requester_message_link (run ,original_chat_id ,_ ["stream_1"],msg_link ,title ,check [0 ]["dur"],user ,InlineKeyboardMarkup (button ))
                except Exception :
                    pass
            elif "vid_"in queued :
                mystic =await app .send_message (original_chat_id ,_ ["call_7"])
                try :
                    file_path ,direct =await YouTube .download (
                    videoid ,
                    mystic ,
                    videoid =True ,
                    video =True if str (streamtype )=="video"else False ,
                    )
                except :
                    return await mystic .edit_text (
                    _ ["call_6"],disable_web_page_preview =True
                    )
                if video :
                    stream =MediaStream (
                    file_path ,
                    audio_parameters =AudioQuality .HIGH ,
                    video_parameters =VideoQuality .SD_480p ,
                    ffmpeg_parameters =\"-ar 48000 -ac 2 -b:a 256k -bufsize 128k\",
                    )
                else :
                    stream =MediaStream (
                    file_path ,
                    audio_parameters =AudioQuality .HIGH ,
                    video_flags =MediaStream .Flags .IGNORE ,
                    ffmpeg_parameters ="-ar 48000 -ac 2 -b:a 256k -bufsize 128k",
                    )
                try :
                    await client .play (chat_id ,stream )
                    await asyncio .sleep (0.1 )
                    # Update stream start time when playing new song
                    stream_start_time [chat_id ]=datetime .now ()
                except :
                    return await app .send_message (
                    original_chat_id ,
                    text =_ ["call_6"],
                    )
                img =await get_thumb (videoid ,user_id )
                button =stream_markup (_ ,chat_id )
                await mystic .delete ()

                display_title =remove_emoji (title )
                msg_link =check [0 ].get ('link',f"https://t.me/{app .username }?start=info_{videoid }")
                run =await app .send_photo (
                chat_id =original_chat_id ,
                photo =img ,
                caption =_ ["stream_1"].format (
                msg_link ,
                display_title ,
                check [0 ]["dur"],
                user ,
                ),
                reply_markup =InlineKeyboardMarkup (button ),
                )
                db [chat_id ][0 ]["mystic"]=run
                db [chat_id ][0 ]["markup"]="yt"
                try :
                    from ArmedMusic .utils .stream .stream import _add_requester_message_link
                    await _add_requester_message_link (run ,original_chat_id ,_ ["stream_1"],msg_link ,title ,check [0 ]["dur"],user ,InlineKeyboardMarkup (button ))
                except Exception :
                    pass
            elif "index_"in queued :
                stream =(
                MediaStream (
                videoid ,
                audio_parameters =AudioQuality .HIGH ,
                video_parameters =VideoQuality .SD_480p ,
                ffmpeg_parameters ="-ar 48000 -ac 2 -b:a 256k -bufsize 128k",
                )
                if str (streamtype )=="video"
                else MediaStream (videoid ,audio_parameters =AudioQuality .HIGH ,video_flags =MediaStream .Flags .IGNORE ,ffmpeg_parameters ="-ar 48000 -ac 2 -b:a 256k -bufsize 128k")
                )
                try :
                    await client .play (chat_id ,stream )
                    await asyncio .sleep (0.1 )
                    # Update stream start time when playing new song
                    stream_start_time [chat_id ]=datetime .now ()
                except :
                    return await app .send_message (
                    original_chat_id ,
                    text =_ ["call_6"],
                    )
                button =stream_markup (_ ,chat_id )
                run =await app .send_photo (
                chat_id =original_chat_id ,
                photo =config .STREAM_IMG_URL ,
                caption =_ ["stream_2"].format (user ),
                reply_markup =InlineKeyboardMarkup (button ),
                )
                db [chat_id ][0 ]["mystic"]=run
                db [chat_id ][0 ]["markup"]="tg"
            else :
                if video :
                    stream =MediaStream (
                    queued ,
                    audio_parameters =AudioQuality .HIGH ,
                    video_parameters =VideoQuality .SD_480p ,
                    ffmpeg_parameters ="-ar 48000 -ac 2 -b:a 256k -bufsize 128k",
                    )
                else :
                    stream =MediaStream (
                    queued ,
                    audio_parameters =AudioQuality .HIGH ,
                    video_flags =MediaStream .Flags .IGNORE ,
                    ffmpeg_parameters ="-ar 48000 -ac 2 -b:a 256k -bufsize 128k",
                    )
                try :
                    await client .play (chat_id ,stream )
                    await asyncio .sleep (0.1 )
                    # Update stream start time when playing new song
                    stream_start_time [chat_id ]=datetime .now ()
                except :
                    return await app .send_message (
                    original_chat_id ,
                    text =_ ["call_6"],
                    )
                if videoid =="file_id":
                    button =stream_markup (_ ,chat_id )

                    display_title =remove_emoji (title )
                    msg_link =check [0 ].get ('link')or f"https://t.me/{app .username }"
                    run =await app .send_photo (
                    chat_id =original_chat_id ,
                    photo =config .TELEGRAM_AUDIO_URL if str (streamtype )=="audio"else config .TELEGRAM_VIDEO_URL ,
                    caption =_ ["stream_1"].format (
                    msg_link ,
                    display_title ,
                    check [0 ]["dur"],
                    user ,
                    ),
                    reply_markup =InlineKeyboardMarkup (button ),
                    )
                    try :
                        from ArmedMusic .utils .stream .stream import _add_requester_message_link
                        await _add_requester_message_link (run ,original_chat_id ,_ ["stream_1"],msg_link ,title ,check [0 ]["dur"],user ,InlineKeyboardMarkup (button ))
                    except Exception :
                        pass
                    db [chat_id ][0 ]["mystic"]=run
                    db [chat_id ][0 ]["markup"]="tg"
                elif videoid =="soundcloud":
                    button =stream_markup (_ ,chat_id )

                    display_title =remove_emoji (title )
                    msg_link =check [0 ].get ('link',f"https://t.me/{app .username }?start=info_{videoid }")
                    run =await app .send_photo (
                    chat_id =original_chat_id ,
                    photo =config .SOUNCLOUD_IMG_URL ,
                    caption =_ ["stream_1"].format (
                    msg_link ,
                    display_title ,
                    check [0 ]["dur"],
                    user ,
                    ),
                    reply_markup =InlineKeyboardMarkup (button ),
                    )
                    db [chat_id ][0 ]["mystic"]=run
                    db [chat_id ][0 ]["markup"]="sc"
                else :
                    img =await get_thumb (videoid ,user_id )
                    button =stream_markup (_ ,chat_id )

                    display_title =remove_emoji (title )
                    msg_link =check [0 ].get ('link',f"https://t.me/{app .username }?start=info_{videoid }")
                    run =await app .send_photo (
                    chat_id =original_chat_id ,
                    photo =img ,
                    caption =_ ["stream_1"].format (
                    msg_link ,
                    display_title ,
                    check [0 ]["dur"],
                    user ,
                    ),
                    reply_markup =InlineKeyboardMarkup (button ),
                    )
                    db [chat_id ][0 ]["mystic"]=run
                    db [chat_id ][0 ]["markup"]="yt"

    async def ping (self ):
        pings =[]
        if config .STRING1 :
            pings .append (self .one .ping )
        if config .STRING2 :
            pings .append (self .two .ping )
        if config .STRING3 :
            pings .append (self .three .ping )
        if config .STRING4 :
            pings .append (self .four .ping )
        if config .STRING5 :
            pings .append (self .five .ping )
        return str (round (sum (pings )/len (pings ),3 ))

    async def start (self ):

        LOGGER (__name__ ).info ("Starting PyTgCalls Client...\n")

        instances =[
        (config .STRING1 ,self .one ,"PyTgCalls-1"),
        (config .STRING2 ,self .two ,"PyTgCalls-2"),
        (config .STRING3 ,self .three ,"PyTgCalls-3"),
        (config .STRING4 ,self .four ,"PyTgCalls-4"),
        (config .STRING5 ,self .five ,"PyTgCalls-5"),
        ]

        for session ,instance ,name in instances :
            if session :
                try :
                    await instance .start ()
                    LOGGER (__name__ ).info (f"✓ {name } started successfully")
                except Exception as e :
                    LOGGER (__name__ ).error (f"✗ {name } failed to start: {type (e ).__name__ }: {e }")

                    await asyncio .sleep (1 )

    async def decorators (self ):
        @self .one .on_update (
        fl .chat_update (
        ChatUpdate .Status .KICKED |
        ChatUpdate .Status .LEFT_GROUP |
        ChatUpdate .Status .CLOSED_VOICE_CHAT
        ))
        @self .two .on_update (
        fl .chat_update (
        ChatUpdate .Status .KICKED |
        ChatUpdate .Status .LEFT_GROUP |
        ChatUpdate .Status .CLOSED_VOICE_CHAT
        ))
        @self .three .on_update (
        fl .chat_update (
        ChatUpdate .Status .KICKED |
        ChatUpdate .Status .LEFT_GROUP |
        ChatUpdate .Status .CLOSED_VOICE_CHAT
        ))
        @self .four .on_update (
        fl .chat_update (
        ChatUpdate .Status .KICKED |
        ChatUpdate .Status .LEFT_GROUP |
        ChatUpdate .Status .CLOSED_VOICE_CHAT
        ))
        @self .five .on_update (
        fl .chat_update (
        ChatUpdate .Status .KICKED |
        ChatUpdate .Status .LEFT_GROUP |
        ChatUpdate .Status .CLOSED_VOICE_CHAT
        ))
        async def stream_services_handler (client ,update :Update ):
            try :
                chat_id =update .chat_id
                LOGGER (__name__ ).info (f"Assistant left/kicked from call {chat_id}")
                await self .stop_stream (chat_id )
            except Exception as e :
                LOGGER (__name__ ).error (f"Error in stream_services_handler: {e }")

        @self .one .on_update (fl .stream_end ())
        @self .two .on_update (fl .stream_end ())
        @self .three .on_update (fl .stream_end ())
        @self .four .on_update (fl .stream_end ())
        @self .five .on_update (fl .stream_end ())
        async def stream_end_handler1 (client :PyTgCalls ,update :StreamEnded ):
            await self .change_stream (client ,update .chat_id )

Anony =Call ()
