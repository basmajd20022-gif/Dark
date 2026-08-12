import asyncio
from telethon.tl.types import Channel, Message
from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import PhoneCodeInvalidError, PhoneNumberInvalidError, SessionPasswordNeededError, ChatAdminRequiredError, ChannelPrivateError, UserBannedInChannelError, FloodWaitError
from telethon.sessions import StringSession
from datetime import datetime, timedelta
import os
import json
import logging
import tempfile
import secrets
import re

# ================== إعدادات التسجيل ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================== بيانات API ==================
api_id = 28557217
api_hash = "22fb694b8c569117cc056073fc444597"
bot_token = "8894081737:AAFoIpmtw7nZUgi7U1hfb2tw8nxYggL41cQ"
owner_id = 1487040062

# ================== بدء البوت ==================
bot = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)

# ================== أسماء الملفات ==================
users_db = "users.json"
added_channels_file = "added_channels.json"
vip_users_file = "vip_users.json"
bot_state_file = "bot_state.json"
captions_log_file = "captions_log.json"
subscription_plans_file = "subscription_plans.json"
referral_config_file = "referral_config.json"

# ================== تهيئة الملفات ==================
def init_files_and_folders():
    required_files = {
        'users.json': {},
        'user_group_links.json': {},
        'user_clips.json': {},
        'user_ads.json': {},
        'bot_state.json': {'locked': False},
        'captions_log.json': {},
        'subscription_plans.json': {
            'plans': [
                {'days': 7, 'points': 15},
                {'days': 15, 'points': 30},
                {'days': 30, 'points': 50}
            ]
        },
        'referral_config.json': {
            'points_per_referral': 1,
            'trial_hours': 24
        }
    }
    required_folders = ['restricted', 'clips_media', 'Image_of', 'media_captions']
    for filename, default_content in required_files.items():
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(default_content, f, ensure_ascii=False, indent=4)
    for folder in required_folders:
        if not os.path.exists(folder):
            os.makedirs(folder)

init_files_and_folders()

# ================== دوال التحميل والحفظ ==================
def load_bot_state():
    if os.path.exists(bot_state_file):
        with open(bot_state_file, "r", encoding='utf-8') as f:
            return json.load(f).get("locked", False)
    return False

def save_bot_state(state):
    with open(bot_state_file, "w", encoding='utf-8') as f:
        json.dump({"locked": state}, f, ensure_ascii=False, indent=4)

def load_users():
    if os.path.exists(users_db):
        with open(users_db, "r", encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users():
    with open(users_db, "w", encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def load_vip_users():
    if os.path.exists(vip_users_file):
        with open(vip_users_file, "r", encoding='utf-8') as f:
            return json.load(f)
    return []

def save_vip_users(vip_users):
    with open(vip_users_file, "w", encoding='utf-8') as f:
        json.dump(vip_users, f, ensure_ascii=False, indent=4)

def load_added_channels():
    if os.path.exists(added_channels_file):
        with open(added_channels_file, "r", encoding='utf-8') as f:
            return json.load(f)
    return []

def write_added_channels(file, data):
    with open(file, "w", encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_captions_log():
    if os.path.exists(captions_log_file):
        with open(captions_log_file, "r", encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_captions_log():
    with open(captions_log_file, "w", encoding='utf-8') as f:
        json.dump(captions_log, f, ensure_ascii=False, indent=4)

def load_subscription_plans():
    if os.path.exists(subscription_plans_file):
        with open(subscription_plans_file, "r", encoding='utf-8') as f:
            return json.load(f).get('plans', [])
    return [{'days': 7, 'points': 15}, {'days': 15, 'points': 30}, {'days': 30, 'points': 50}]

def save_subscription_plans(plans):
    with open(subscription_plans_file, "w", encoding='utf-8') as f:
        json.dump({'plans': plans}, f, ensure_ascii=False, indent=4)

def load_referral_config():
    if os.path.exists(referral_config_file):
        with open(referral_config_file, "r", encoding='utf-8') as f:
            return json.load(f)
    return {'points_per_referral': 1, 'trial_hours': 24}

def save_referral_config(config):
    with open(referral_config_file, "w", encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

# ================== تحميل البيانات ==================
users = load_users()
vip_users = load_vip_users()
added_channels = load_added_channels()
bot_locked = load_bot_state()
captions_log = load_captions_log()
subscription_plans = load_subscription_plans()
referral_config = load_referral_config()

# ================== المتغيرات العامة ==================
user_clients = {}
forward_handlers = {}
repeat_tasks = {}
user_states = {}

# ================== دوال النظام الجديد ==================

def get_user_subscription(user_id):
    """الحصول على معلومات اشتراك المستخدم"""
    user_id_str = str(user_id)
    user_data = users.get(user_id_str, {})
    return {
        'has_subscription': user_data.get('has_subscription', False),
        'subscription_end': user_data.get('subscription_end'),
        'trial_end': user_data.get('trial_end'),
        'is_trial_active': user_data.get('is_trial_active', False)
    }

def get_user_points(user_id):
    """الحصول على نقاط المستخدم"""
    user_id_str = str(user_id)
    return users.get(user_id_str, {}).get('points', 0)

def is_user_subscribed(user_id):
    """التحقق من اشتراك المستخدم (مدفوع أو تجريبي)"""
    user_id_str = str(user_id)
    user_data = users.get(user_id_str, {})
    
    # التحقق من الاشتراك المدفوع
    if user_data.get('has_subscription', False):
        subscription_end = user_data.get('subscription_end')
        if subscription_end:
            try:
                end_date = datetime.fromisoformat(subscription_end)
                if end_date > datetime.now():
                    return True
            except:
                pass
        # إذا انتهى الاشتراك
        user_data['has_subscription'] = False
        user_data['subscription_end'] = None
        users[user_id_str] = user_data
        save_users()
    
    # التحقق من التجربة المجانية
    if user_data.get('is_trial_active', False):
        trial_end = user_data.get('trial_end')
        if trial_end:
            try:
                end_date = datetime.fromisoformat(trial_end)
                if end_date > datetime.now():
                    return True
            except:
                pass
        # إذا انتهت التجربة
        user_data['is_trial_active'] = False
        user_data['trial_end'] = None
        users[user_id_str] = user_data
        save_users()
    
    return False

def get_user_subscription_status(user_id):
    """الحصول على حالة الاشتراك للمستخدم"""
    user_id_str = str(user_id)
    user_data = users.get(user_id_str, {})
    
    if user_data.get('has_subscription', False):
        subscription_end = user_data.get('subscription_end')
        if subscription_end:
            try:
                end_date = datetime.fromisoformat(subscription_end)
                if end_date > datetime.now():
                    return 'مدفوع', end_date
            except:
                pass
        user_data['has_subscription'] = False
        user_data['subscription_end'] = None
        users[user_id_str] = user_data
        save_users()
    
    if user_data.get('is_trial_active', False):
        trial_end = user_data.get('trial_end')
        if trial_end:
            try:
                end_date = datetime.fromisoformat(trial_end)
                if end_date > datetime.now():
                    return 'تجريبي', end_date
            except:
                pass
        user_data['is_trial_active'] = False
        user_data['trial_end'] = None
        users[user_id_str] = user_data
        save_users()
    
    return 'منتهي', None

def grant_trial_to_user(user_id):
    """منح تجربة مجانية لمستخدم جديد"""
    user_id_str = str(user_id)
    user_data = users.get(user_id_str, {})
    
    # التحقق من وجود اشتراك أو تجربة سابقة
    if user_data.get('has_subscription', False) or user_data.get('is_trial_active', False):
        return False
    
    trial_hours = referral_config.get('trial_hours', 24)
    trial_end = datetime.now() + timedelta(hours=trial_hours)
    
    user_data['is_trial_active'] = True
    user_data['trial_end'] = trial_end.isoformat()
    user_data['trial_started'] = datetime.now().isoformat()
    
    users[user_id_str] = user_data
    save_users()
    return True

def add_points_to_user(user_id, points):
    """إضافة نقاط للمستخدم"""
    user_id_str = str(user_id)
    if user_id_str not in users:
        return False
    users[user_id_str]['points'] = users[user_id_str].get('points', 0) + points
    save_users()
    return True

def deduct_points_from_user(user_id, points):
    """خصم نقاط من المستخدم"""
    user_id_str = str(user_id)
    if user_id_str not in users:
        return False
    current_points = users[user_id_str].get('points', 0)
    if current_points < points:
        return False
    users[user_id_str]['points'] = current_points - points
    save_users()
    return True

def activate_subscription(user_id, days):
    """تفعيل اشتراك مدفوع للمستخدم"""
    user_id_str = str(user_id)
    user_data = users.get(user_id_str, {})
    
    # حساب تاريخ الانتهاء
    now = datetime.now()
    if user_data.get('has_subscription', False) and user_data.get('subscription_end'):
        try:
            current_end = datetime.fromisoformat(user_data['subscription_end'])
            if current_end > now:
                # تمديد الاشتراك الحالي
                end_date = current_end + timedelta(days=days)
            else:
                end_date = now + timedelta(days=days)
        except:
            end_date = now + timedelta(days=days)
    else:
        end_date = now + timedelta(days=days)
    
    user_data['has_subscription'] = True
    user_data['subscription_end'] = end_date.isoformat()
    # إلغاء التجربة المجانية إذا كانت مفعلة
    user_data['is_trial_active'] = False
    user_data['trial_end'] = None
    
    users[user_id_str] = user_data
    save_users()
    return True

def generate_referral_link(user_id):
    """توليد رابط دعوة للمستخدم"""
    return f"https://t.me/Dark3_3bot?start=ref_{user_id}"

def process_referral(new_user_id, referrer_id):
    """معالجة الإحالة عند انضمام مستخدم جديد"""
    if str(new_user_id) == str(referrer_id):
        return False  # لا يمكن للمستخدم دعوة نفسه
    
    points = referral_config.get('points_per_referral', 1)
    
    # إضافة نقاط للمحيل
    if add_points_to_user(referrer_id, points):
        # تسجيل الإحالة للمستخدم الجديد
        user_id_str = str(new_user_id)
        user_data = users.get(user_id_str, {})
        user_data['referred_by'] = str(referrer_id)
        user_data['referral_date'] = datetime.now().isoformat()
        users[user_id_str] = user_data
        save_users()
        return True
    return False

def get_bot_username():
    """الحصول على اسم المستخدم للبوت"""
    try:
        return bot.me.username
    except:
        return "YourBotUsername"

# ================== الأزرار الرئيسية مع الأزرار الجديدة ==================
home_markup = [
    [Button.inline("📊 لوحة التحكم", b"dashboard"), Button.inline("🔗 رابط الدعوة", b"referral_link")],
    [Button.inline("📤 النشر التلقائي", b"posting_settings"), Button.inline("👥 إدارة السوبرات", b"manage_super")],
    [Button.inline("🤖 الرد التلقائي", b"auto_reply_settings"), Button.inline("📱 الحسابات", b"acc_mun")],
    [Button.inline("🛒 شراء اشتراك", b"buy_subscription"), Button.inline("⚙️ الإعدادات المتقدمة", b"advanced_settings")],
    [Button.inline("ℹ️ معلومات البوت", b"bot_info")],
]

cancel_markup = [[Button.inline("🔙 إلغاء والعودة", b"cancel_action")]]

# ================== الدوال المساعدة ==================
def is_vip(user_id):
    return user_id in vip_users or user_id == owner_id

def get_user_session(user_id):
    try:
        sessions = users.get(str(user_id), {}).get("sessions", [])
        if sessions:
            return sessions[0].get("session")
        return None
    except Exception as e:
        logger.error(f"Error reading session: {e}")
        return None

async def get_entity_safe(client, identifier):
    try:
        return await client.get_entity(identifier)
    except ValueError:
        return None
    except Exception:
        return None

async def get_user_client(user_id):
    if user_id in user_clients and user_clients[user_id].is_connected():
        return user_clients[user_id]
    session_string = get_user_session(user_id)
    if not session_string:
        return None
    try:
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            return None
        user_clients[user_id] = client
        return client
    except Exception as e:
        logger.error(f"Error connecting client: {e}")
        return None

# ================== التأكد من قفل البوت مع نظام الاشتراك ==================
@bot.on(events.CallbackQuery)
async def check_subscription_and_lock(event):
    user_id = event.sender_id
    data = event.data
    
    # الأزرار المستثناة من التحقق
    exempt_buttons = [b"referral_link", b"buy_subscription", b"home", b"cancel_action", b"bot_info", b"advanced_settings"]
    
    # التحقق من الأزرار المستثناة
    for exempt in exempt_buttons:
        if data.startswith(exempt) or data == exempt:
            return
    
    # التحقق من البوت المغلق
    if bot_locked and not is_vip(user_id):
        await event.answer("🚫 البوت مدفوع، تواصل مع @D_8_5", alert=True)
        raise events.StopPropagation
    
    # التحقق من الاشتراك
    if not is_user_subscribed(user_id) and not is_vip(user_id):
        await event.answer("⚠️ عذرا تم انتهاء الاشتراك المجاني عليك بالاشتراك المدفوع @D_8_5", alert=True)
        raise events.StopPropagation

@bot.on(events.NewMessage)
async def check_subscription_and_lock_message(event):
    user_id = event.sender_id
    if event.raw_text == "/start":
        return  # السماح لأمر /start دائماً
    
    if bot_locked and not is_vip(user_id):
        await event.reply("🚫 البوت مدفوع، تواصل مع @D_8_5")
        raise events.StopPropagation
    
    if not is_user_subscribed(user_id) and not is_vip(user_id):
        await event.reply("⚠️ عذرا تم انتهاء الاشتراك المجاني عليك بالاشتراك المدفوع @D_8_5")
        raise events.StopPropagation

# ================== زر إلغاء العملية ==================
@bot.on(events.CallbackQuery(data=b"cancel_action"))
async def cancel_action(event):
    user_id = event.sender_id
    if user_id in user_states:
        del user_states[user_id]
    await event.edit("✅ تم إلغاء العملية.", buttons=[[Button.inline("🔙 العودة للقائمة", b"home")]])

# ================== دالة النسخ من القناة ==================
async def forward_handler(event, user_id, client):
    user_id_str = str(user_id)
    try:
        if not users.get(user_id_str, {}).get("auto_forward_enabled", False):
            return
        
        groups = users[user_id_str].get("groups", [])
        if not groups:
            return
        
        if not client.is_connected():
            try:
                await client.connect()
            except:
                return
        
        message = event.message
        text = message.text or message.caption or ""
        media = message.media
        msg_id = message.id
        
        today = datetime.now().date().isoformat()
        tracker_key = f"{msg_id}_{today}"
        
        repeat_enabled = users[user_id_str].get("repeat_enabled", False)
        max_repeats = users[user_id_str].get("repeat_count", 5)
        interval_minutes = users[user_id_str].get("repeat_interval", 60)
        
        if "repeat_tracker" not in users[user_id_str]:
            users[user_id_str]["repeat_tracker"] = {}
        tracker = users[user_id_str]["repeat_tracker"]
        
        if tracker_key not in tracker:
            tracker[tracker_key] = {"count": 0, "text": text[:100] if text else "📷 صورة"}
        
        # ========== دالة النشر بدون إضافات ==========
        async def publish_to_groups():
            published = 0
            for group in groups:
                try:
                    entity = await get_entity_safe(client, group)
                    if not entity:
                        continue
                    
                    try:
                        await client(JoinChannelRequest(entity))
                    except:
                        pass
                    
                    if media:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                            tmp_path = tmp.name
                        try:
                            await client.download_media(media, tmp_path)
                            await client.send_file(entity, tmp_path, caption=text)
                            os.unlink(tmp_path)
                            published += 1
                        except Exception as e:
                            logger.error(f"❌ فشل إرسال الملف: {e}")
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                    else:
                        await client.send_message(entity, text)
                        published += 1
                    
                    await asyncio.sleep(3)
                    
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds)
                except UserBannedInChannelError:
                    if group in users[user_id_str]["groups"]:
                        users[user_id_str]["groups"].remove(group)
                        save_users()
                except Exception as e:
                    logger.error(f"❌ فشل النشر: {e}")
            
            return published
        # ==========================================
        
        if tracker[tracker_key]["count"] < max_repeats or not repeat_enabled:
            await publish_to_groups()
            tracker[tracker_key]["count"] += 1
            users[user_id_str]["repeat_tracker"] = tracker
            save_users()
            logger.info(f"📤 نشر فوري للمستخدم {user_id}")
        
        if repeat_enabled and tracker[tracker_key]["count"] < max_repeats:
            task_key = f"{user_id}_{tracker_key}"
            if task_key in repeat_tasks:
                repeat_tasks[task_key].cancel()
                del repeat_tasks[task_key]
            
            async def repeat_publish():
                try:
                    remaining = max_repeats - tracker[tracker_key]["count"]
                    for i in range(remaining):
                        await asyncio.sleep(interval_minutes * 60)
                        if not users.get(user_id_str, {}).get("repeat_enabled", False):
                            break
                        current_tracker = users[user_id_str].get("repeat_tracker", {})
                        if tracker_key not in current_tracker:
                            break
                        if current_tracker[tracker_key]["count"] >= max_repeats:
                            break
                        await publish_to_groups()
                        current_tracker[tracker_key]["count"] += 1
                        users[user_id_str]["repeat_tracker"] = current_tracker
                        save_users()
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"❌ خطأ في التكرار: {e}")
            
            task = asyncio.create_task(repeat_publish())
            repeat_tasks[task_key] = task
                
    except Exception as e:
        logger.error(f"❌ خطأ في معالج التوجيه: {e}")

async def setup_forward_handler(user_id):
    user_id_str = str(user_id)
    await remove_forward_handler(user_id)
    
    source = users[user_id_str].get("source_channel")
    if not source:
        return False
    
    client = await get_user_client(user_id)
    if not client:
        return False
    
    if not client.is_connected():
        await client.connect()
    
    try:
        entity = await get_entity_safe(client, source)
        if not entity:
            return False
        handler = client.add_event_handler(
            lambda event, uid=user_id, cl=client: forward_handler(event, uid, cl),
            events.NewMessage(chats=entity)
        )
        forward_handlers[user_id] = handler
        return True
    except Exception as e:
        logger.error(f"❌ فشل إعداد معالج النسخ: {e}")
        return False

async def remove_forward_handler(user_id):
    if user_id in forward_handlers:
        try:
            client = await get_user_client(user_id)
            if client and client.is_connected():
                client.remove_event_handler(forward_handlers[user_id])
            del forward_handlers[user_id]
        except Exception as e:
            logger.error(f"❌ خطأ في إزالة المعالج: {e}")
            if user_id in forward_handlers:
                del forward_handlers[user_id]
    for task_key in list(repeat_tasks.keys()):
        if task_key.startswith(f"{user_id}_"):
            repeat_tasks[task_key].cancel()
            del repeat_tasks[task_key]

# ================== عرض الرسائل المكررة ==================
@bot.on(events.CallbackQuery(data=b"view_repeated_messages"))
async def view_repeated_messages(event):
    user_id = event.sender_id
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        await event.edit("❌ المستخدم غير موجود.", buttons=[[Button.inline("🔙 العودة", b"monitoring_settings")]])
        return
    
    tracker = users[user_id_str].get("repeat_tracker", {})
    
    if not tracker:
        await event.edit("📭 لا توجد رسائل مكررة حالياً.", buttons=[[Button.inline("🔙 العودة", b"monitoring_settings")]])
        return
    
    sorted_items = sorted(tracker.items(), key=lambda x: x[0], reverse=True)
    
    buttons = []
    for key, data in sorted_items[:20]:
        try:
            if isinstance(data, dict):
                text_preview = data.get("text", "نص غير معروف")[:35]
            else:
                text_preview = "نص غير معروف"
            buttons.append([Button.inline(f"🗑️ {text_preview}", f"delete_repeat:{key}")])
        except:
            continue
    
    buttons.append([Button.inline("🔙 العودة", b"monitoring_settings")])
    
    await event.edit(
        "📊 **الرسائل المكررة**\n\n"
        "اختر الرسالة التي تريد حذف تكرارها:",
        buttons=buttons
    )

@bot.on(events.CallbackQuery(pattern=b"delete_repeat:(.+)"))
async def delete_repeated_message(event):
    user_id = event.sender_id
    user_id_str = str(user_id)
    tracker_key = event.data.decode().split(":", 1)[1]
    
    if user_id_str not in users:
        await event.answer("❌ المستخدم غير موجود!", alert=True)
        return
    
    tracker = users[user_id_str].get("repeat_tracker", {})
    if tracker_key in tracker:
        task_key = f"{user_id}_{tracker_key}"
        if task_key in repeat_tasks:
            repeat_tasks[task_key].cancel()
            del repeat_tasks[task_key]
        
        del tracker[tracker_key]
        users[user_id_str]["repeat_tracker"] = tracker
        save_users()
        
        await event.edit("✅ تم حذف تكرار هذه الرسالة!", buttons=[[Button.inline("🔙 العودة", b"view_repeated_messages")]])
    else:
        await event.answer("❌ الرسالة غير موجودة!", alert=True)

# ================== تهيئة البوت ==================
async def initialize_user_clients():
    for user_id in users.keys():
        try:
            user_id_int = int(user_id)
            if users[user_id].get("auto_forward_enabled", False) and users[user_id].get("source_channel"):
                await setup_forward_handler(user_id_int)
        except:
            continue

# ================== أمر البدء مع نظام الإحالة والتجربة ==================
@bot.on(events.NewMessage(pattern="/start(?:\\s+(.+))?"))
async def start(event):
    user_id = event.sender_id
    user_id_str = str(user_id)
    
    # معالجة رابط الإحالة
    if event.pattern_match and event.pattern_match.group(1):
        args = event.pattern_match.group(1)
        if args.startswith("ref_"):
            try:
                referrer_id = int(args.replace("ref_", ""))
                if user_id != referrer_id:
                    # التحقق من عدم وجود إحالة سابقة
                    if not users.get(user_id_str, {}).get('referred_by'):
                        process_referral(user_id, referrer_id)
                        await event.reply(f"🎉 تم تفعيل دعوتك! حصل المحيل على نقاط.")
            except ValueError:
                pass
    
    # إنشاء المستخدم إذا لم يكن موجوداً
    if user_id_str not in users:
        users[user_id_str] = {
            "sessions": [],
            "groups": [],
            "posting": False,
            "captions": [],
            "waitTime": 60,
            "auto_reply_enabled": False,
            "auto_reply_caption": "",
            "auto_reply_media": None,
            "auto_reply_count": -1,
            "source_channel": None,
            "auto_forward_enabled": False,
            "repeat_enabled": False,
            "repeat_count": 5,
            "repeat_interval": 60,
            "repeat_tracker": {},
            "points": 0,
            "has_subscription": False,
            "subscription_end": None,
            "is_trial_active": False,
            "trial_end": None,
            "referred_by": None,
            "referral_date": None
        }
        save_users()
        
        # منح تجربة مجانية للمستخدم الجديد
        if grant_trial_to_user(user_id):
            await event.reply("🎉 مرحباً بك! لقد حصلت على تجربة مجانية لمدة 24 ساعة.")
    
    # عرض حالة الاشتراك
    status, end_date = get_user_subscription_status(user_id)
    status_text = {
        'مدفوع': f'✅ اشتراك مدفوع حتى {end_date.strftime("%Y-%m-%d %H:%M") if end_date else "غير محدد"}',
        'تجريبي': f'⏳ تجربة مجانية حتى {end_date.strftime("%Y-%m-%d %H:%M") if end_date else "غير محدد"}',
        'منتهي': '❌ الاشتراك منتهي'
    }.get(status, '❌ غير معروف')
    
    points = get_user_points(user_id)
    
    await event.reply(
        f"👋 **مرحباً بك في البوت الذكي!**\n\n"
        f"📊 **حالة الاشتراك:** {status_text}\n"
        f"⭐ **النقاط:** {points}\n\n"
        "اختر أحد الخيارات من القائمة:",
        buttons=home_markup
    )

# ================== العودة للقائمة ==================
@bot.on(events.CallbackQuery(data=b"home"))
async def back_to_home(event):
    user_id = event.sender_id
    status, end_date = get_user_subscription_status(user_id)
    status_text = {
        'مدفوع': f'✅ اشتراك مدفوع',
        'تجريبي': f'⏳ تجربة مجانية',
        'منتهي': '❌ الاشتراك منتهي'
    }.get(status, '❌ غير معروف')
    points = get_user_points(user_id)
    
    await event.edit(
        f"👋 **مرحباً بك في البوت الذكي!**\n\n"
        f"📊 **حالة الاشتراك:** {status_text}\n"
        f"⭐ **النقاط:** {points}\n\n"
        "اختر أحد الخيارات من القائمة:",
        buttons=home_markup
    )

# ================== لوحة التحكم ==================
@bot.on(events.CallbackQuery(data=b"dashboard"))
async def dashboard(event):
    user_id = event.sender_id
    user_data = users.get(str(user_id), {})
    
    status, end_date = get_user_subscription_status(user_id)
    status_text = {
        'مدفوع': f'✅ اشتراك مدفوع',
        'تجريبي': f'⏳ تجربة مجانية',
        'منتهي': '❌ الاشتراك منتهي'
    }.get(status, '❌ غير معروف')
    points = get_user_points(user_id)
    
    await event.edit(
        "📊 **لوحة التحكم**\n\n"
        f"👤 المستخدم: {user_id}\n"
        f"⭐ النقاط: {points}\n"
        f"📊 حالة الاشتراك: {status_text}\n"
        f"📱 عدد الحسابات: {len(user_data.get('sessions', []))}\n"
        f"👥 عدد السوبرات: {len(user_data.get('groups', []))}\n"
        f"📝 عدد الكلايش: {len(user_data.get('captions', []))}\n"
        f"⏱️ وقت الانتظار: {user_data.get('waitTime', 60)} ثانية\n"
        f"🚀 حالة المراقبة: {'🟢 مفعل' if user_data.get('auto_forward_enabled', False) else '🔴 غير مفعل'}\n"
        f"🔁 حالة التكرار: {'🟢 مفعل' if user_data.get('repeat_enabled', False) else '🔴 غير مفعل'}",
        buttons=[
            [Button.inline("📱 إدارة الحسابات", b"acc_mun"), Button.inline("👥 إدارة السوبرات", b"manage_super")],
            [Button.inline("📤 النشر التلقائي", b"posting_settings"), Button.inline("📡 المراقبة", b"monitoring_settings")],
            [Button.inline("🔗 رابط الدعوة", b"referral_link"), Button.inline("🛒 شراء اشتراك", b"buy_subscription")],
            [Button.inline("🔙 العودة", b"home")]
        ]
    )

# ================== رابط الدعوة ==================
@bot.on(events.CallbackQuery(data=b"referral_link"))
async def referral_link(event):
    user_id = event.sender_id
    link = generate_referral_link(user_id)
    points = get_user_points(user_id)
    points_per_ref = referral_config.get('points_per_referral', 1)
    
    await event.edit(
        f"🔗 **رابط الدعوة الخاص بك**\n\n"
        f"`{link}`\n\n"
        f"⭐ **نقاطك الحالية:** {points}\n"
        f"🎁 **النقاط لكل دعوة:** {points_per_ref}\n\n"
        f"قم بمشاركة الرابط مع أصدقائك، وعندما ينضمون عبر الرابط ستحصل على نقاط!",
        buttons=[
            [Button.inline("📋 نسخ الرابط", f"copy_link:{link}")],
            [Button.inline("🔙 العودة", b"home")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"copy_link:(.+)"))
async def copy_link(event):
    # هذه دالة وهمية لأن التليجرام لا يدعم نسخ النص مباشرة
    await event.answer("📋 تم نسخ الرابط! (انسخه يدوياً)", alert=True)

# ================== شراء اشتراك ==================
@bot.on(events.CallbackQuery(data=b"buy_subscription"))
async def buy_subscription(event):
    user_id = event.sender_id
    points = get_user_points(user_id)
    status, end_date = get_user_subscription_status(user_id)
    
    plans_text = "🛒 **شراء اشتراك**\n\n"
    plans_text += f"⭐ **نقاطك الحالية:** {points}\n"
    plans_text += f"📊 **حالة الاشتراك:** {status}\n\n"
    plans_text += "**الخطط المتاحة:**\n"
    
    buttons = []
    for i, plan in enumerate(subscription_plans):
        days = plan.get('days', 0)
        price = plan.get('points', 0)
        plans_text += f"• {days} يوم = {price} نقطة\n"
        buttons.append([Button.inline(f"شراء {days} يوم ({price} نقطة)", f"buy_plan:{i}")])
    
    buttons.append([Button.inline("🔙 العودة", b"home")])
    
    await event.edit(plans_text, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b"buy_plan:(\\d+)"))
async def confirm_buy_plan(event):
    user_id = event.sender_id
    plan_index = int(event.data.decode().split(":")[1])
    
    if plan_index >= len(subscription_plans):
        await event.answer("❌ الخطة غير موجودة!", alert=True)
        return
    
    plan = subscription_plans[plan_index]
    days = plan.get('days', 0)
    price = plan.get('points', 0)
    
    points = get_user_points(user_id)
    
    if points < price:
        await event.answer(f"❌ نقاطك غير كافية! تحتاج {price} نقطة، لديك {points}", alert=True)
        return
    
    # خصم النقاط
    if not deduct_points_from_user(user_id, price):
        await event.answer("❌ حدث خطأ في خصم النقاط!", alert=True)
        return
    
    # تفعيل الاشتراك
    if activate_subscription(user_id, days):
        status, end_date = get_user_subscription_status(user_id)
        end_date_str = end_date.strftime("%Y-%m-%d %H:%M") if end_date else "غير محدد"
        
        await event.edit(
            f"✅ **تم شراء الاشتراك بنجاح!**\n\n"
            f"📅 المدة: {days} يوم\n"
            f"⭐ النقاط المتبقية: {get_user_points(user_id)}\n"
            f"📊 حالة الاشتراك: {status}\n"
            f"📆 ينتهي في: {end_date_str}\n\n"
            "🎉 تم تفعيل جميع خدمات البوت!",
            buttons=[[Button.inline("🔙 العودة للقائمة", b"home")]]
        )
    else:
        # إعادة النقاط في حالة الفشل
        add_points_to_user(user_id, price)
        await event.answer("❌ حدث خطأ في تفعيل الاشتراك!", alert=True)

# ================== إعدادات النشر ==================
@bot.on(events.CallbackQuery(data=b"posting_settings"))
async def posting_settings(event):
    user_id = event.sender_id
    user_data = users.get(str(user_id), {})
    
    await event.edit(
        "📤 **إعدادات النشر التلقائي**\n\n"
        f"📝 عدد الكلايش: {len(user_data.get('captions', []))}\n"
        f"⏱️ وقت الانتظار: {user_data.get('waitTime', 60)} ثانية\n"
        f"📤 حالة النشر: {'🟢 يعمل' if user_data.get('posting', False) else '🔴 متوقف'}",
        buttons=[
            [Button.inline("📝 إدارة الكلايش", b"manage_captions")],
            [Button.inline("▶️ بدء النشر", b"startPosting"), Button.inline("⏹️ إيقاف النشر", b"stopPosting")],
            [Button.inline("⚡ النشر السريع", b"post_to_all_supergroups")],
            [Button.inline("⏱️ تعديل وقت الانتظار", b"waitTime")],
            [Button.inline("📡 المراقبة والنسخ", b"monitoring_settings")],
            [Button.inline("🔙 العودة", b"home")]
        ]
    )

# ================== إدارة الكلايش ==================
@bot.on(events.CallbackQuery(data=b"manage_captions"))
async def manage_captions(event):
    user_id = event.sender_id
    captions = users.get(str(user_id), {}).get("captions", [])
    
    if not captions:
        await event.edit(
            "📝 **إدارة الكلايش**\n\nلا توجد كلايش حالياً.",
            buttons=[
                [Button.inline("➕ إضافة كليشة", b"add_caption")],
                [Button.inline("📋 عرض سجل الكلايش", b"view_captions_log")],
                [Button.inline("🔙 العودة", b"posting_settings")]
            ]
        )
        return
    
    captions_list = ""
    for i, caption in enumerate(captions):
        text = caption.get("text", "")[:30]
        has_media = "📷" if caption.get("media") else "📝"
        captions_list += f"{i+1}. {has_media} {text}...\n"
    
    await event.edit(
        f"📝 **إدارة الكلايش**\n\nعدد الكلايش: {len(captions)}\n\n{captions_list}",
        buttons=[
            [Button.inline("➕ إضافة كليشة", b"add_caption")],
            [Button.inline("🗑️ حذف كليشة", b"delete_caption")],
            [Button.inline("📋 عرض سجل الكلايش", b"view_captions_log")],
            [Button.inline("🔙 العودة", b"posting_settings")]
        ]
    )

# ================== إضافة كليشة ==================
@bot.on(events.CallbackQuery(data=b"add_caption"))
async def add_caption(event):
    user_id = event.sender_id
    await event.delete()
    user_states[user_id] = "awaiting_caption"
    async with bot.conversation(user_id) as conv:
        await conv.send_message(
            "📝 **أرسل الكليشة الجديدة** (نص أو مع صورة):\n\n🔄 للإلغاء أرسل /cancel",
            buttons=cancel_markup
        )
        try:
            response = await conv.get_response(timeout=120)
            if response.raw_text == "/cancel":
                await bot.send_message(user_id, "✅ تم إلغاء العملية.")
                if user_id in user_states:
                    del user_states[user_id]
                return
            
            text = response.raw_text
            media_path = None
            if response.media:
                media_path = f"Image_of/{user_id}_caption_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                await response.download_media(media_path)
            
            if "captions" not in users[str(user_id)]:
                users[str(user_id)]["captions"] = []
            
            users[str(user_id)]["captions"].append({"text": text, "media": media_path, "date": datetime.now().isoformat()})
            save_users()
            
            if str(user_id) not in captions_log:
                captions_log[str(user_id)] = []
            captions_log[str(user_id)].append({"text": text, "date": datetime.now().isoformat(), "action": "إضافة"})
            save_captions_log()
            
            await bot.send_message(user_id, f"✅ تم إضافة الكليشة بنجاح!")
            if user_id in user_states:
                del user_states[user_id]
        except:
            await bot.send_message(user_id, "⏰ انتهى الوقت.")

# ================== حذف كليشة ==================
@bot.on(events.CallbackQuery(data=b"delete_caption"))
async def delete_caption(event):
    user_id = event.sender_id
    captions = users.get(str(user_id), {}).get("captions", [])
    
    if not captions:
        await event.answer("📭 لا توجد كلايش!", alert=True)
        return
    
    buttons = []
    for i, caption in enumerate(captions):
        text = caption.get("text", "")[:25]
        buttons.append([Button.inline(f"{i+1}. {text}...", f"delete_caption_{i}")])
    
    buttons.append([Button.inline("🔙 إلغاء", b"manage_captions")])
    await event.edit("🗑️ **اختر الكليشة للحذف:**", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b"delete_caption_(\\d+)"))
async def confirm_delete_caption(event):
    user_id = event.sender_id
    index = int(event.data.decode().split("_")[2])
    captions = users[str(user_id)].get("captions", [])
    
    if index >= len(captions):
        await event.answer("❌ غير موجودة!", alert=True)
        return
    
    deleted = captions.pop(index)
    save_users()
    
    if str(user_id) not in captions_log:
        captions_log[str(user_id)] = []
    captions_log[str(user_id)].append({"text": deleted.get("text", ""), "date": datetime.now().isoformat(), "action": "حذف"})
    save_captions_log()
    
    await event.edit("✅ تم حذف الكليشة!", buttons=[[Button.inline("🔙 العودة", b"manage_captions")]])

# ================== عرض سجل الكلايش ==================
@bot.on(events.CallbackQuery(data=b"view_captions_log"))
async def view_captions_log(event):
    user_id = event.sender_id
    log = captions_log.get(str(user_id), [])
    
    if not log:
        await event.edit("📭 لا يوجد سجل.", buttons=[[Button.inline("🔙 العودة", b"manage_captions")]])
        return
    
    log_text = "📋 **سجل الكلايش**\n\n"
    for entry in log[-20:]:
        action = "➕ إضافة" if entry.get("action") == "إضافة" else "🗑️ حذف"
        date = entry.get("date", "")[:16]
        text = entry.get("text", "")[:30]
        log_text += f"{action} | {date}\n📝 {text}...\n\n"
    
    await event.edit(log_text, buttons=[[Button.inline("🔙 العودة", b"manage_captions")]])

# ================== النشر ==================
@bot.on(events.CallbackQuery(data=b"startPosting"))
async def start_posting(event):
    user_id = event.sender_id
    user_id_str = str(user_id)
    
    if user_id_str not in users:
        await event.answer("❌ المستخدم غير موجود!", alert=True)
        return
    
    captions = users[user_id_str].get("captions", [])
    if not captions:
        await event.answer("❌ لا توجد كلايش!", alert=True)
        return
    
    if not users[user_id_str].get("sessions"):
        await event.answer("❌ لا توجد حسابات!", alert=True)
        return
    
    groups = users[user_id_str].get("groups", [])
    if not groups:
        await event.answer("❌ لا توجد سوبرات!", alert=True)
        return
    
    await event.answer("✅ تم بدء النشر!")
    users[user_id_str]["posting"] = True
    save_users()
    
    wait_time = users[user_id_str].get("waitTime", 60)

    async def post_in_group(session_string, group):
        try:
            client = TelegramClient(StringSession(session_string), api_id, api_hash)
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    return
                while users[user_id_str]["posting"]:
                    for caption in captions:
                        try:
                            entity = await get_entity_safe(client, group)
                            if not entity:
                                continue
                            try:
                                await client(JoinChannelRequest(entity))
                            except:
                                pass
                            if caption.get("media") and os.path.exists(caption["media"]):
                                await client.send_file(entity, caption["media"], caption=caption["text"])
                            else:
                                await client.send_message(entity, caption["text"])
                        except FloodWaitError as e:
                            await asyncio.sleep(e.seconds)
                        except Exception as e:
                            logger.error(f"❌ فشل الإرسال: {e}")
                    await asyncio.sleep(wait_time)
            except:
                pass
        finally:
            await client.disconnect()

    tasks = []
    for session_data in users[user_id_str]["sessions"]:
        session_string = session_data["session"]
        for group in groups:
            tasks.append(post_in_group(session_string, group))
    try:
        await asyncio.gather(*tasks)
    except:
        pass

@bot.on(events.CallbackQuery(data=b"stopPosting"))
async def stop_posting(event):
    user_id = event.sender_id
    users[str(user_id)] = users.get(str(user_id), {})
    users[str(user_id)]["posting"] = False
    save_users()
    await event.answer("⏹️ تم إيقاف النشر!")

# ================== النشر السريع ==================
@bot.on(events.CallbackQuery(data=b"post_to_all_supergroups"))
async def post_to_all_supergroups(event):
    user_id = event.sender_id
    user_id_str = str(user_id)
    client = await get_user_client(user_id)
    if not client:
        await event.answer("❌ يجب تسجيل الدخول!", alert=True)
        return
    
    captions = users[user_id_str].get("captions", [])
    if not captions:
        await event.answer("❌ لا توجد كلايش!", alert=True)
        return
    
    groups = users[user_id_str].get("groups", [])
    if not groups:
        await event.answer("❌ لا توجد سوبرات!", alert=True)
        return
    
    wait_time = users[user_id_str].get("waitTime", 60)
    await event.edit("⏳ جاري النشر السريع...")
    
    success = 0
    failed = 0
    for group in groups:
        try:
            entity = await get_entity_safe(client, group)
            if not entity:
                failed += 1
                continue
            for caption in captions:
                if caption.get("media") and os.path.exists(caption["media"]):
                    await client.send_file(entity, caption["media"], caption=caption["text"])
                else:
                    await client.send_message(entity, caption["text"])
                success += 1
                await asyncio.sleep(wait_time)
        except:
            failed += 1
    
    await event.edit(
        f"✅ اكتمل النشر!\n\n✔️ {success} ناجحة\n✖️ {failed} فاشلة",
        buttons=[[Button.inline("🔙 العودة", b"posting_settings")]]
    )

# ================== وقت الانتظار ==================
@bot.on(events.CallbackQuery(data=b"waitTime"))
async def wait_time(event):
    user_id = event.sender_id
    await event.delete()
    async with bot.conversation(user_id) as conv:
        await conv.send_message(
            "⏱️ أرسل مدة الانتظار (بالثواني):\n\n🔄 للإلغاء أرسل /cancel",
            buttons=cancel_markup
        )
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(user_id, "✅ تم إلغاء العملية.")
                return
            
            wait_time = int(response.text.strip())
            if wait_time < 5:
                raise ValueError("يجب أن تكون 5 ثواني أو أكثر.")
            users[str(user_id)]["waitTime"] = wait_time
            save_users()
            await bot.send_message(user_id, f"✅ تم تعيين وقت الانتظار: {wait_time} ثانية")
        except:
            await bot.send_message(user_id, "❌ خطأ: يجب إدخال رقم صحيح")

# ================== إعدادات المراقبة ==================
@bot.on(events.CallbackQuery(data=b"monitoring_settings"))
async def monitoring_settings(event):
    user_id = event.sender_id
    user_data = users.get(str(user_id), {})
    
    await event.edit(
        "📡 **المراقبة والنسخ من القناة**\n\n"
        f"📡 القناة المصدر: `{user_data.get('source_channel', 'غير محدد')}`\n"
        f"🚀 حالة المراقبة: {'🟢 مفعل' if user_data.get('auto_forward_enabled', False) else '🔴 غير مفعل'}\n"
        f"🔁 حالة التكرار: {'🟢 مفعل' if user_data.get('repeat_enabled', False) else '🔴 غير مفعل'}\n"
        f"🔢 عدد التكرارات: {user_data.get('repeat_count', 5)}\n"
        f"⏱️ الفاصل الزمني: {user_data.get('repeat_interval', 60)} دقيقة",
        buttons=[
            [Button.inline("📡 تعيين القناة المصدر", b"set_source_channel")],
            [Button.inline("▶️ تشغيل المراقبة", b"start_auto_forward"), Button.inline("⏹️ إيقاف المراقبة", b"stop_auto_forward")],
            [Button.inline("🔁 عدد التكرارات", b"set_repeat_count"), Button.inline("⏱️ الفاصل الزمني", b"set_repeat_interval")],
            [Button.inline("✅ تفعيل التكرار", b"enable_repeat"), Button.inline("❌ إيقاف التكرار", b"disable_repeat")],
            [Button.inline("📊 عرض الرسائل المكررة", b"view_repeated_messages")],
            [Button.inline("🔙 العودة", b"posting_settings")]
        ]
    )

# ================== دوال التكرار ==================
@bot.on(events.CallbackQuery(data=b"set_repeat_count"))
async def set_repeat_count(event):
    user_id = event.sender_id
    await event.delete()
    async with bot.conversation(user_id) as conv:
        await conv.send_message("🔁 **أدخل عدد التكرارات اليومية:**\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(user_id, "✅ تم إلغاء العملية.")
                return
            count = int(response.text.strip())
            if count < 1:
                await bot.send_message(user_id, "⚠️ يجب أن يكون العدد 1 على الأقل.")
                return
            users[str(user_id)]["repeat_count"] = count
            save_users()
            await bot.send_message(user_id, f"✅ تم تعيين عدد التكرارات إلى {count}.")
        except:
            await bot.send_message(user_id, "❌ خطأ: يجب إدخال رقم صحيح")

@bot.on(events.CallbackQuery(data=b"set_repeat_interval"))
async def set_repeat_interval(event):
    user_id = event.sender_id
    await event.delete()
    async with bot.conversation(user_id) as conv:
        await conv.send_message("⏱️ **أدخل الفاصل الزمني (بالدقائق):**\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(user_id, "✅ تم إلغاء العملية.")
                return
            interval = int(response.text.strip())
            if interval < 1:
                await bot.send_message(user_id, "⚠️ يجب أن يكون الفاصل دقيقة على الأقل.")
                return
            users[str(user_id)]["repeat_interval"] = interval
            save_users()
            await bot.send_message(user_id, f"✅ تم تعيين الفاصل الزمني إلى {interval} دقيقة.")
        except:
            await bot.send_message(user_id, "❌ خطأ: يجب إدخال رقم صحيح")

@bot.on(events.CallbackQuery(data=b"enable_repeat"))
async def enable_repeat(event):
    user_id = event.sender_id
    users[str(user_id)]["repeat_enabled"] = True
    save_users()
    await event.edit("✅ تم تفعيل التكرار.", buttons=[[Button.inline("🔙 العودة", b"monitoring_settings")]])

@bot.on(events.CallbackQuery(data=b"disable_repeat"))
async def disable_repeat(event):
    user_id = event.sender_id
    users[str(user_id)]["repeat_enabled"] = False
    save_users()
    await event.edit("❌ تم إيقاف التكرار.", buttons=[[Button.inline("🔙 العودة", b"monitoring_settings")]])

# ================== القناة المصدر ==================
@bot.on(events.CallbackQuery(data=b"set_source_channel"))
async def set_source_channel(event):
    user_id = event.sender_id
    await event.delete()
    async with bot.conversation(user_id) as conv:
        await conv.send_message("📡 **أرسل رابط قناتك:**\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(user_id, "✅ تم إلغاء العملية.")
                return
            source = response.text.strip()
            client = await get_user_client(user_id)
            if not client:
                await bot.send_message(user_id, "❌ يجب تسجيل حساب أولاً!")
                return
            entity = await get_entity_safe(client, source)
            if not entity:
                await bot.send_message(user_id, "❌ لا يمكن الوصول إلى القناة.")
                return
            users[str(user_id)]["source_channel"] = source
            save_users()
            await bot.send_message(user_id, f"✅ تم تعيين القناة: `{source}`")
        except:
            await bot.send_message(user_id, "⏰ انتهى الوقت.")

@bot.on(events.CallbackQuery(data=b"start_auto_forward"))
async def start_auto_forward(event):
    user_id = event.sender_id
    user_id_str = str(user_id)
    
    if not users[user_id_str].get("source_channel"):
        await event.answer("❌ يرجى تعيين قناة مصدر أولاً!", alert=True)
        return
    
    if not users[user_id_str].get("groups"):
        await event.answer("❌ لا توجد سوبرات!", alert=True)
        return
    
    if not users[user_id_str].get("sessions"):
        await event.answer("❌ يجب تسجيل حساب أولاً!", alert=True)
        return
    
    users[user_id_str]["auto_forward_enabled"] = True
    save_users()
    
    success = await setup_forward_handler(user_id)
    if success:
        await event.edit("✅ **تم تشغيل المراقبة!**", buttons=[[Button.inline("🔙 العودة", b"monitoring_settings")]])
    else:
        users[user_id_str]["auto_forward_enabled"] = False
        save_users()
        await event.answer("❌ فشل التشغيل!", alert=True)

@bot.on(events.CallbackQuery(data=b"stop_auto_forward"))
async def stop_auto_forward(event):
    user_id = event.sender_id
    user_id_str = str(user_id)
    
    users[user_id_str]["auto_forward_enabled"] = False
    save_users()
    await remove_forward_handler(user_id)
    await event.edit("⏹️ **تم إيقاف المراقبة.**", buttons=[[Button.inline("🔙 العودة", b"monitoring_settings")]])

# ================== إدارة الحسابات ==================
@bot.on(events.CallbackQuery(data=b"acc_mun"))
async def acc_mun(event):
    await event.edit(
        "📱 **إدارة الحسابات**",
        buttons=[
            [Button.inline("➕ إضافة حساب", b"register"), Button.inline("🗑️ حذف حساب", b"delete_account")],
            [Button.inline("📋 عرض الحسابات", b"view_account")],
            [Button.inline("🔙 العودة", b"home")]
        ]
    )

@bot.on(events.CallbackQuery(data=b"register"))
async def register_account(event):
    user_id = event.sender_id
    await event.delete()
    
    if str(user_id) not in users:
        users[str(user_id)] = {
            "sessions": [], "groups": [], "posting": False, "captions": [],
            "waitTime": 60, "auto_reply_enabled": False, "auto_reply_caption": "",
            "auto_reply_media": None, "auto_reply_count": -1,
            "source_channel": None, "auto_forward_enabled": False,
            "repeat_enabled": False, "repeat_count": 5, "repeat_interval": 60,
            "repeat_tracker": {},
            "points": 0, "has_subscription": False, "subscription_end": None,
            "is_trial_active": False, "trial_end": None, "referred_by": None,
            "referral_date": None
        }
        save_users()
    
    if 'sessions' not in users[str(user_id)]:
        users[str(user_id)]['sessions'] = []
        save_users()
    
    max_accounts = 10 if user_id == owner_id or user_id in vip_users else 1
    if len(users[str(user_id)]["sessions"]) >= max_accounts:
        await bot.send_message(user_id, f"⚠️ لقد وصلت للحد الأقصى ({max_accounts}).")
        return

    async with bot.conversation(user_id) as conv:
        await conv.send_message("📱 **أدخل رقم هاتفك** (مثال: +9647712345678):\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(user_id, "✅ تم إلغاء العملية.")
                return
            phone = response.text.strip()
            if not phone.startswith('+'):
                await conv.send_message("⚠️ يجب أن يبدأ بـ +")
                return
        except:
            await conv.send_message("⏰ انتهى الوقت.")
            return

        client = TelegramClient(StringSession(), api_id, api_hash)
        try:
            await client.connect()
            await client.send_code_request(phone)
            await conv.send_message("✅ تم إرسال الرمز. **أدخل الرمز:**\n\n🔄 للإلغاء أرسل /cancel")
            
            try:
                response = await conv.get_response(timeout=120)
                if response.raw_text == "/cancel":
                    await bot.send_message(user_id, "✅ تم إلغاء العملية.")
                    return
                code = response.text.strip()
                if not code.isdigit():
                    await conv.send_message("⚠️ الرمز أرقام فقط.")
                    return
            except:
                await conv.send_message("⏰ انتهى الوقت.")
                return

            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 أدخل كلمة المرور:\n\n🔄 للإلغاء أرسل /cancel")
                try:
                    response = await conv.get_response(timeout=60)
                    if response.raw_text == "/cancel":
                        await bot.send_message(user_id, "✅ تم إلغاء العملية.")
                        return
                    password = response.text.strip()
                    await client.sign_in(password=password)
                except:
                    await conv.send_message("⏰ انتهى الوقت.")
                    return

            me = await client.get_me()
            full_name = f"{me.first_name} {me.last_name}" if me.last_name else me.first_name
            session_string = client.session.save()

            users[str(user_id)]["sessions"].append({
                "session": session_string,
                "username": me.username,
                "id": me.id,
                "phone": phone
            })
            save_users()

            await conv.send_message(f"✅ **تم تسجيل الدخول!**\nمرحباً {full_name}")

        except PhoneNumberInvalidError:
            await conv.send_message("❌ رقم الهاتف غير صحيح.")
        except PhoneCodeInvalidError:
            await conv.send_message("❌ رمز التحقق غير صحيح.")
        except Exception as e:
            await conv.send_message(f"❌ خطأ: {e}")
        finally:
            await client.disconnect()

@bot.on(events.CallbackQuery(data=b"view_account"))
async def view_account(event):
    user_id = event.sender_id
    sessions = users[str(user_id)].get("sessions", [])
    if not sessions:
        await event.edit("📭 لا توجد حسابات.", buttons=[[Button.inline("🔙 العودة", b"acc_mun")]])
        return
    accounts_info = []
    valid_sessions = []
    for i, session_data in enumerate(sessions):
        session_string = session_data["session"]
        try:
            client = TelegramClient(StringSession(session_string), api_id, api_hash)
            await client.connect()
            if not await client.is_user_authorized():
                raise Exception("غير صالحة")
            me = await client.get_me()
            full_name = f"{me.first_name} {me.last_name}" if me.last_name else me.first_name
            accounts_info.append(f"**الحساب {i+1}:**\n👤 {full_name}\n🆔 {me.id}\n📱 {me.phone}")
            valid_sessions.append(session_data)
        except:
            accounts_info.append(f"**الحساب {i+1}:**\n❌ غير صالح (تم حذفه)")
        finally:
            await client.disconnect()
    users[str(user_id)]["sessions"] = valid_sessions
    save_users()
    await event.edit("📋 **الحسابات المسجلة:**\n\n" + "\n\n".join(accounts_info), buttons=[[Button.inline("🔙 العودة", b"acc_mun")]])

@bot.on(events.CallbackQuery(data=b"delete_account"))
async def delete_account(event):
    user_id = event.sender_id
    sessions = users[str(user_id)].get("sessions", [])
    if not sessions:
        await event.edit("📭 لا توجد حسابات.", buttons=[[Button.inline("🔙 العودة", b"acc_mun")]])
        return
    buttons = [
        [Button.inline(f"🗑️ حساب {i+1}: {s.get('username', s.get('id'))}", f"del_account:{i}")]
        for i, s in enumerate(sessions)
    ]
    buttons.append([Button.inline("🔙 العودة", b"acc_mun")])
    await event.edit("🗑️ **اختر الحساب للحذف:**", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b"del_account:(\\d+)"))
async def confirm_delete_account(event):
    user_id = event.sender_id
    index = int(event.data.decode().split(":")[1])
    sessions = users[str(user_id)].get("sessions", [])
    if index >= len(sessions):
        await event.answer("❌ غير موجود!", alert=True)
        return
    session_data = sessions[index]
    users[str(user_id)]["sessions"].pop(index)
    save_users()
    await event.edit(f"✅ تم حذف الحساب {session_data.get('username', session_data.get('id'))}!", buttons=[[Button.inline("🔙 العودة", b"acc_mun")]])

# ================== إدارة السوبرات ==================
@bot.on(events.CallbackQuery(data=b"manage_super"))
async def manage_super(event):
    await event.edit(
        "👥 **إدارة السوبرات**",
        buttons=[
            [Button.inline("➕ إضافة سوبر", b"newSuper"), Button.inline("📋 عرض السوبرات", b"currentSupers")],
            [Button.inline("🗑️ حذف سوبر", b"deleteSpecificSuper"), Button.inline("🗑️ حذف الكل", b"deleteAllSupers")],
            [Button.inline("🔄 جلب السوبرات", b"fetch_supergroups")],
            [Button.inline("🔙 العودة", b"home")]
        ]
    )

@bot.on(events.CallbackQuery(data=b"newSuper"))
async def new_super(event):
    user_id = event.sender_id
    await event.delete()
    async with bot.conversation(user_id) as conv:
        await conv.send_message("📎 أرسل رابط السوبر:\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(user_id, "✅ تم إلغاء العملية.")
                return
            link = response.text.strip()
            if not link:
                await conv.send_message("⚠️ رابط غير صالح.")
                return
            if link.startswith("https://t.me/+") and not is_vip(user_id):
                await bot.send_message(user_id, "⚠️ رابط خاص، تحتاج VIP.")
                return
            if "groups" in users[str(user_id)] and link in users[str(user_id)]["groups"]:
                await conv.send_message("✅ الرابط موجود مسبقاً.")
                return
            
            sessions = users[str(user_id)].get("sessions", [])
            if not sessions:
                await bot.send_message(user_id, "❌ لا توجد جلسات.")
                return
            
            for session_data in sessions:
                session_string = session_data.get("session")
                if not session_string:
                    continue
                client = TelegramClient(StringSession(session_string), api_id, api_hash)
                try:
                    await client.connect()
                    if not await client.is_user_authorized():
                        continue
                    entity = await get_entity_safe(client, link)
                    if not entity:
                        continue
                    await client(JoinChannelRequest(entity))
                    if isinstance(entity, Channel) and entity.megagroup:
                        if "groups" not in users[str(user_id)]:
                            users[str(user_id)]["groups"] = []
                        users[str(user_id)]["groups"].append(link)
                        save_users()
                        await bot.send_message(user_id, f"✅ تم إضافة السوبر: {link}")
                        return
                except:
                    pass
                finally:
                    await client.disconnect()
            await bot.send_message(user_id, "❌ فشل الإضافة.")
        except:
            await bot.send_message(user_id, "⏰ انتهى الوقت.")

@bot.on(events.CallbackQuery(data=b"deleteSpecificSuper"))
async def delete_specific_super(event):
    user_id = event.sender_id
    await event.delete()
    async with bot.conversation(user_id) as conv:
        await conv.send_message("📎 أرسل رابط السوبر للحذف:\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(user_id, "✅ تم إلغاء العملية.")
                return
            link = response.text
            if "groups" in users[str(user_id)] and link in users[str(user_id)]["groups"]:
                users[str(user_id)]["groups"].remove(link)
                save_users()
                await bot.send_message(user_id, f"✅ تم حذف {link}")
            else:
                await bot.send_message(user_id, "❌ غير موجود.")
        except:
            await bot.send_message(user_id, "⏰ انتهى الوقت.")

@bot.on(events.CallbackQuery(data=b"currentSupers"))
async def current_supers(event):
    user_id = event.sender_id
    groups = users[str(user_id)].get("groups", [])
    if not groups:
        await event.answer("📭 لا توجد سوبرات.", alert=True)
    else:
        buttons = [[Button.inline(f"📌 {g[:30]}", f"delSuper:{g}")] for g in groups]
        buttons.append([Button.inline("🔙 العودة", b"manage_super")])
        await event.edit("👥 **السوبرات المضافة:**", buttons=buttons)

@bot.on(events.CallbackQuery(data=b"deleteAllSupers"))
async def delete_all_supers(event):
    user_id = event.sender_id
    if "groups" in users[str(user_id)] and users[str(user_id)]["groups"]:
        users[str(user_id)]["groups"] = []
        save_users()
        await bot.send_message(user_id, "✅ تم حذف جميع السوبرات.")
    else:
        await bot.send_message(user_id, "📭 لا توجد سوبرات.")

@bot.on(events.CallbackQuery(data=b"fetch_supergroups"))
async def fetch_supergroups(event):
    user_id = event.sender_id
    client = await get_user_client(user_id)
    if not client:
        await event.answer("❌ يجب تسجيل الدخول!", alert=True)
        return
    await event.edit("⏳ جاري الجلب...")
    try:
        async for dialog in client.iter_dialogs():
            if dialog.is_group and isinstance(dialog.entity, Channel) and dialog.entity.megagroup:
                link = f"https://t.me/{dialog.entity.username}" if dialog.entity.username else f"https://t.me/c/{dialog.entity.id}"
                users[str(user_id)]["groups"] = users[str(user_id)].get("groups", []) + [link]
        save_users()
        await event.edit(f"✅ تم جلب السوبرات.", buttons=[[Button.inline("🔙 العودة", b"manage_super")]])
    except Exception as e:
        await event.edit(f"❌ خطأ: {e}", buttons=[[Button.inline("🔙 العودة", b"manage_super")]])

# ================== الرد التلقائي ==================
@bot.on(events.CallbackQuery(data=b"auto_reply_settings"))
async def auto_reply_settings(event):
    buttons = [
        [Button.inline("📝 تعيين كليشة", b"set_auto_reply_caption"), Button.inline("👁️ عرض الكليشة", b"show_auto_reply_caption")],
        [Button.inline("🔢 عدد الردود", b"set_auto_reply_count")],
        [Button.inline("✅ تفعيل", b"enable_auto_reply"), Button.inline("❌ إيقاف", b"disable_auto_reply")],
        [Button.inline("🔙 العودة", b"home")]
    ]
    await event.edit("🤖 **إعدادات الرد التلقائي**", buttons=buttons)

@bot.on(events.CallbackQuery(data=b"set_auto_reply_caption"))
async def set_auto_reply_caption(event):
    user_id = event.sender_id
    users[str(user_id)] = users.get(str(user_id), {})
    users[str(user_id)]["awaiting_caption"] = True
    save_users()
    await event.respond("📝 أرسل الكليشة الجديدة (نص أو مع صورة):\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
    await event.answer()

@bot.on(events.CallbackQuery(data=b"show_auto_reply_caption"))
async def show_auto_reply_caption(event):
    user_id = event.sender_id
    user_data = users.get(str(user_id), {})
    caption = user_data.get("auto_reply_caption")
    media = user_data.get("auto_reply_media")
    reply_count = user_data.get("auto_reply_count", -1)
    if not caption:
        await event.answer("📭 لا توجد كليشة!", alert=True)
    else:
        await event.answer()
        message = f"📝 الكليشة:\n\n{caption}\n\n🔢 عدد الردود: {'رد دائم' if reply_count == -1 else f'{reply_count} مرة'}"
        if media and os.path.exists(media):
            await bot.send_file(user_id, media, caption=message)
        else:
            await bot.send_message(user_id, message)

@bot.on(events.CallbackQuery(data=b"set_auto_reply_count"))
async def set_auto_reply_count(event):
    user_id = event.sender_id
    buttons = [
        [Button.inline("مرة واحدة", b"set_reply_count:1"), Button.inline("مرتين", b"set_reply_count:2")],
        [Button.inline("ثلاث مرات", b"set_reply_count:3"), Button.inline("رد دائم", b"set_reply_count:-1")],
        [Button.inline("🔙 العودة", b"auto_reply_settings")]
    ]
    await event.edit("🔢 اختر عدد الردود:", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b"set_reply_count:(-?\\d+)"))
async def confirm_set_reply_count(event):
    user_id = event.sender_id
    count = int(event.data.decode().split(":")[1])
    users[str(user_id)]["auto_reply_count"] = count
    save_users()
    count_text = "رد دائم" if count == -1 else f"{count} مرة"
    await event.edit(f"✅ تم تعيين عدد الردود: {count_text}", buttons=[[Button.inline("🔙 العودة", b"auto_reply_settings")]])

@bot.on(events.CallbackQuery(data=b"enable_auto_reply"))
async def enable_auto_reply(event):
    user_id = event.sender_id
    users[str(user_id)]["auto_reply_enabled"] = True
    save_users()
    await event.edit("✅ تم تفعيل الرد التلقائي.")
    await event.answer()

@bot.on(events.CallbackQuery(data=b"disable_auto_reply"))
async def disable_auto_reply(event):
    user_id = event.sender_id
    users[str(user_id)]["auto_reply_enabled"] = False
    save_users()
    await event.edit("❌ تم إيقاف الرد التلقائي.")
    await event.answer()

# ================== معالج الرسائل (المُصحَّح) ==================
@bot.on(events.NewMessage(incoming=True))
async def handle_new_caption(event):
    user_id = event.sender_id
    user_data = users.get(str(user_id), {})
    
    # تجاهل الأوامر
    if event.raw_text and event.raw_text.startswith('/'):
        return
    
    # معالج الإلغاء
    if event.raw_text == "/cancel" and user_id in user_states:
        del user_states[user_id]
        await event.reply("✅ تم إلغاء العملية.")
        return
    
    # معالج الكليشة
    if user_data.get("awaiting_caption"):
        users[str(user_id)]["auto_reply_caption"] = event.raw_text
        if event.media:
            file_path = f"Image_of/{user_id}_{event.id}.jpg"
            await event.download_media(file_path)
            users[str(user_id)]["auto_reply_media"] = file_path
        users[str(user_id)]["awaiting_caption"] = False
        save_users()
        await event.reply("✅ تم تعيين الكليشة بنجاح!")

# ================== تحكم المطور مع النظام الجديد ==================
@bot.on(events.CallbackQuery(data=b"advanced_settings"))
async def advanced_settings(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    buttons = [
        [Button.inline("👑 إدارة VIP", b"manage_vip")],
        [Button.inline("📢 قناة اشتراك", b"add_subscription_channel"), Button.inline("📊 إحصائيات", b"stats")],
        [Button.inline("🔒 قفل البوت", b"lock_bot"), Button.inline("🔓 فتح البوت", b"unlock_bot")],
        [Button.inline("⭐ إدارة النقاط", b"manage_points")],
        [Button.inline("📋 إدارة خطط الاشتراك", b"manage_subscription_plans")],
        [Button.inline("🎁 إعدادات الإحالة", b"manage_referral_settings")],
        [Button.inline("🗑️ مسح البيانات", b"reset_bot")],
        [Button.inline("🔙 العودة", b"home")]
    ]
    await event.edit("⚙️ **الإعدادات المتقدمة**", buttons=buttons)

# ================== إدارة النقاط ==================
@bot.on(events.CallbackQuery(data=b"manage_points"))
async def manage_points(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    buttons = [
        [Button.inline("➕ إضافة نقاط", b"add_points"), Button.inline("➖ خصم نقاط", b"remove_points")],
        [Button.inline("📊 عرض نقاط مستخدم", b"view_user_points")],
        [Button.inline("🔙 العودة", b"advanced_settings")]
    ]
    await event.edit("⭐ **إدارة النقاط**", buttons=buttons)

@bot.on(events.CallbackQuery(data=b"add_points"))
async def add_points(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    async with bot.conversation(owner_id) as conv:
        await conv.send_message("🆔 أرسل معرف المستخدم:\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(owner_id, "✅ تم إلغاء العملية.")
                return
            target_id = int(response.text.strip())
            
            await conv.send_message("⭐ أرسل عدد النقاط للإضافة:\n\n🔄 للإلغاء أرسل /cancel")
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(owner_id, "✅ تم إلغاء العملية.")
                return
            points = int(response.text.strip())
            
            if add_points_to_user(target_id, points):
                current_points = get_user_points(target_id)
                await conv.send_message(f"✅ تم إضافة {points} نقطة للمستخدم {target_id}\n⭐ النقاط الحالية: {current_points}")
            else:
                await conv.send_message("❌ المستخدم غير موجود!")
        except:
            await conv.send_message("❌ خطأ في الإدخال.")

@bot.on(events.CallbackQuery(data=b"remove_points"))
async def remove_points(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    async with bot.conversation(owner_id) as conv:
        await conv.send_message("🆔 أرسل معرف المستخدم:\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(owner_id, "✅ تم إلغاء العملية.")
                return
            target_id = int(response.text.strip())
            
            await conv.send_message("⭐ أرسل عدد النقاط للخصم:\n\n🔄 للإلغاء أرسل /cancel")
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(owner_id, "✅ تم إلغاء العملية.")
                return
            points = int(response.text.strip())
            
            if deduct_points_from_user(target_id, points):
                current_points = get_user_points(target_id)
                await conv.send_message(f"✅ تم خصم {points} نقطة من المستخدم {target_id}\n⭐ النقاط الحالية: {current_points}")
            else:
                await conv.send_message("❌ المستخدم غير موجود أو نقاط غير كافية!")
        except:
            await conv.send_message("❌ خطأ في الإدخال.")

@bot.on(events.CallbackQuery(data=b"view_user_points"))
async def view_user_points(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    async with bot.conversation(owner_id) as conv:
        await conv.send_message("🆔 أرسل معرف المستخدم:\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(owner_id, "✅ تم إلغاء العملية.")
                return
            target_id = int(response.text.strip())
            points = get_user_points(target_id)
            status, end_date = get_user_subscription_status(target_id)
            await conv.send_message(
                f"📊 **معلومات المستخدم {target_id}**\n\n"
                f"⭐ النقاط: {points}\n"
                f"📊 حالة الاشتراك: {status}\n"
                f"📆 ينتهي في: {end_date.strftime('%Y-%m-%d %H:%M') if end_date else 'غير محدد'}"
            )
        except:
            await conv.send_message("❌ خطأ في الإدخال.")

# ================== إدارة خطط الاشتراك ==================
@bot.on(events.CallbackQuery(data=b"manage_subscription_plans"))
async def manage_subscription_plans(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    
    plans_text = "📋 **خطط الاشتراك الحالية**\n\n"
    for i, plan in enumerate(subscription_plans):
        plans_text += f"{i+1}. {plan['days']} يوم = {plan['points']} نقطة\n"
    
    buttons = [
        [Button.inline("➕ إضافة خطة", b"add_plan"), Button.inline("🗑️ حذف خطة", b"remove_plan")],
        [Button.inline("🔙 العودة", b"advanced_settings")]
    ]
    await event.edit(plans_text, buttons=buttons)

@bot.on(events.CallbackQuery(data=b"add_plan"))
async def add_plan(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    async with bot.conversation(owner_id) as conv:
        try:
            await conv.send_message("📅 أدخل عدد الأيام:\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(owner_id, "✅ تم إلغاء العملية.")
                return
            days = int(response.text.strip())
            
            await conv.send_message("⭐ أدخل السعر بالنقاط:\n\n🔄 للإلغاء أرسل /cancel")
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(owner_id, "✅ تم إلغاء العملية.")
                return
            points = int(response.text.strip())
            
            subscription_plans.append({'days': days, 'points': points})
            save_subscription_plans(subscription_plans)
            await conv.send_message(f"✅ تم إضافة الخطة: {days} يوم = {points} نقطة")
        except:
            await conv.send_message("❌ خطأ في الإدخال.")

@bot.on(events.CallbackQuery(data=b"remove_plan"))
async def remove_plan(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    
    if not subscription_plans:
        await event.answer("📭 لا توجد خطط للحذف!", alert=True)
        return
    
    buttons = []
    for i, plan in enumerate(subscription_plans):
        buttons.append([Button.inline(f"{plan['days']} يوم ({plan['points']} نقطة)", f"remove_plan:{i}")])
    buttons.append([Button.inline("🔙 إلغاء", b"manage_subscription_plans")])
    await event.edit("🗑️ **اختر الخطة للحذف:**", buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b"remove_plan:(\\d+)"))
async def confirm_remove_plan(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    
    index = int(event.data.decode().split(":")[1])
    if index >= len(subscription_plans):
        await event.answer("❌ الخطة غير موجودة!", alert=True)
        return
    
    removed = subscription_plans.pop(index)
    save_subscription_plans(subscription_plans)
    await event.edit(f"✅ تم حذف الخطة: {removed['days']} يوم = {removed['points']} نقطة", buttons=[[Button.inline("🔙 العودة", b"manage_subscription_plans")]])

# ================== إعدادات الإحالة ==================
@bot.on(events.CallbackQuery(data=b"manage_referral_settings"))
async def manage_referral_settings(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    
    current_points = referral_config.get('points_per_referral', 1)
    trial_hours = referral_config.get('trial_hours', 24)
    
    await event.edit(
        f"🎁 **إعدادات الإحالة**\n\n"
        f"⭐ النقاط لكل إحالة: {current_points}\n"
        f"⏰ مدة التجربة المجانية: {trial_hours} ساعة\n\n"
        f"اختر الإعداد لتعديله:",
        buttons=[
            [Button.inline("⭐ تعديل نقاط الإحالة", b"set_referral_points")],
            [Button.inline("⏰ تعديل مدة التجربة", b"set_trial_hours")],
            [Button.inline("🔙 العودة", b"advanced_settings")]
        ]
    )

@bot.on(events.CallbackQuery(data=b"set_referral_points"))
async def set_referral_points(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    async with bot.conversation(owner_id) as conv:
        await conv.send_message("⭐ **أدخل عدد النقاط لكل إحالة:**\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(owner_id, "✅ تم إلغاء العملية.")
                return
            points = int(response.text.strip())
            if points < 0:
                await conv.send_message("⚠️ لا يمكن أن يكون سالباً.")
                return
            referral_config['points_per_referral'] = points
            save_referral_config(referral_config)
            await conv.send_message(f"✅ تم تعيين نقاط الإحالة إلى {points} نقطة")
        except:
            await conv.send_message("❌ خطأ في الإدخال.")

@bot.on(events.CallbackQuery(data=b"set_trial_hours"))
async def set_trial_hours(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    async with bot.conversation(owner_id) as conv:
        await conv.send_message("⏰ **أدخل مدة التجربة المجانية (بالساعات):**\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(owner_id, "✅ تم إلغاء العملية.")
                return
            hours = int(response.text.strip())
            if hours < 0:
                await conv.send_message("⚠️ لا يمكن أن تكون سالبة.")
                return
            referral_config['trial_hours'] = hours
            save_referral_config(referral_config)
            await conv.send_message(f"✅ تم تعيين مدة التجربة إلى {hours} ساعة")
        except:
            await conv.send_message("❌ خطأ في الإدخال.")

# ================== تحكم المطور القديم ==================
@bot.on(events.CallbackQuery(data=b"manage_vip"))
async def manage_vip(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    buttons = [
        [Button.inline("➕ إضافة VIP", b"add_vip"), Button.inline("➖ حذف VIP", b"remove_vip")],
        [Button.inline("📋 عرض VIP", b"list_vip")],
        [Button.inline("🔙 العودة", b"advanced_settings")]
    ]
    await event.edit("👑 **إدارة المستخدمين VIP**", buttons=buttons)

@bot.on(events.CallbackQuery(data=b"add_vip"))
async def add_vip(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    async with bot.conversation(owner_id) as conv:
        await conv.send_message("🆔 أرسل معرف المستخدم:\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(owner_id, "✅ تم إلغاء العملية.")
                return
            vip_id = int(response.text.strip())
            if vip_id in vip_users:
                await conv.send_message("⚠️ موجود بالفعل.")
            else:
                vip_users.append(vip_id)
                save_vip_users(vip_users)
                await conv.send_message(f"✅ تم إضافة {vip_id}.")
        except:
            await conv.send_message("❌ معرف غير صالح.")

@bot.on(events.CallbackQuery(data=b"remove_vip"))
async def remove_vip(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    async with bot.conversation(owner_id) as conv:
        await conv.send_message("🆔 أرسل معرف المستخدم للحذف:\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(owner_id, "✅ تم إلغاء العملية.")
                return
            vip_id = int(response.text.strip())
            if vip_id in vip_users:
                vip_users.remove(vip_id)
                save_vip_users(vip_users)
                await conv.send_message(f"✅ تم حذف {vip_id}.")
            else:
                await conv.send_message("❌ غير موجود.")
        except:
            await conv.send_message("❌ معرف غير صالح.")

@bot.on(events.CallbackQuery(data=b"list_vip"))
async def list_vip(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    if not vip_users:
        await event.edit("📭 لا يوجد مستخدمين VIP.", buttons=[[Button.inline("🔙 العودة", b"manage_vip")]])
    else:
        vip_list = "\n".join([f"👤 {vip_id}" for vip_id in vip_users])
        await event.edit(f"👑 **قائمة VIP:**\n\n{vip_list}", buttons=[[Button.inline("🔙 العودة", b"manage_vip")]])

@bot.on(events.CallbackQuery(data=b"add_subscription_channel"))
async def add_subscription_channel(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    async with bot.conversation(owner_id) as conv:
        await conv.send_message("📢 أرسل معرف القناة (مثل: @channel):\n\n🔄 للإلغاء أرسل /cancel", buttons=cancel_markup)
        try:
            response = await conv.get_response(timeout=60)
            if response.raw_text == "/cancel":
                await bot.send_message(owner_id, "✅ تم إلغاء العملية.")
                return
            channel = response.text.strip()
            added_channels.append(channel)
            write_added_channels(added_channels_file, added_channels)
            await conv.send_message(f"✅ تم تعيين {channel}.")
        except:
            await conv.send_message("⏰ انتهى الوقت.")

@bot.on(events.CallbackQuery(data=b"stats"))
async def stats(event):
    if event.sender_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    total_users = len(users)
    total_groups = sum(len(user.get("groups", [])) for user in users.values())
    total_accounts = sum(len(user.get("sessions", [])) for user in users.values())
    total_captions = sum(len(user.get("captions", [])) for user in users.values())
    subscribed_users = sum(1 for user in users.values() if user.get('has_subscription', False))
    trial_users = sum(1 for user in users.values() if user.get('is_trial_active', False))
    total_points = sum(user.get('points', 0) for user in users.values())
    
    await event.edit(
        f"📊 **الإحصائيات**\n\n"
        f"👥 المستخدمين: {total_users}\n"
        f"✅ مشتركين مدفوع: {subscribed_users}\n"
        f"⏳ تجربة مجانية: {trial_users}\n"
        f"⭐ إجمالي النقاط: {total_points}\n"
        f"📁 السوبرات: {total_groups}\n"
        f"📱 الحسابات: {total_accounts}\n"
        f"📝 الكلايش: {total_captions}",
        buttons=[[Button.inline("🔙 العودة", b"advanced_settings")]]
    )

@bot.on(events.CallbackQuery(data=b"lock_bot"))
async def lock_bot(event):
    global bot_locked
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    bot_locked = True
    save_bot_state(bot_locked)
    await event.edit("🔒 البوت مقفل!", buttons=[[Button.inline("🔙 العودة", b"advanced_settings")]])

@bot.on(events.CallbackQuery(data=b"unlock_bot"))
async def unlock_bot(event):
    global bot_locked
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    bot_locked = False
    save_bot_state(bot_locked)
    await event.edit("🔓 البوت مفتوح!", buttons=[[Button.inline("🔙 العودة", b"advanced_settings")]])

@bot.on(events.CallbackQuery(data=b"reset_bot"))
async def reset_bot(event):
    user_id = event.sender_id
    if user_id != owner_id:
        await event.answer("🚫 للمالك فقط!", alert=True)
        return
    users.clear()
    vip_users.clear()
    added_channels.clear()
    captions_log.clear()
    user_clients.clear()
    forward_handlers.clear()
    repeat_tasks.clear()
    save_users()
    save_vip_users(vip_users)
    write_added_channels(added_channels_file, added_channels)
    save_captions_log()
    await event.edit("🗑️ تم مسح جميع البيانات!", buttons=[[Button.inline("🔙 العودة", b"home")]])

# ================== معلومات البوت ==================
@bot.on(events.CallbackQuery(data=b"bot_info"))
async def bot_info(event):
    info_text = (
        "🤖 **بوت النشر التلقائي المتكامل**\n\n"
        "📌 الإصدار: 5.0\n"
        "👨‍💻 المطور: @D_8_5\n\n"
        "✨ **المميزات الجديدة**\n"
        "• تجربة مجانية 24 ساعة للمستخدمين الجدد\n"
        "• نظام إحالة مع نقاط\n"
        "• شراء اشتراكات بالنقاط\n"
        "• لوحة تحكم متقدمة\n\n"
        "✨ **المميزات الأساسية**\n"
        "• نشر تلقائي بكلايش غير محدودة\n"
        "• نسخ تلقائي من قناتك مع تكرار يومي\n"
        "• حذف الرسائل المكررة بسهولة\n"
        "• إدارة حسابات وسوبرات متعددة\n"
        "• سجل كامل للكلايش\n"
        "• زر إلغاء لكل العمليات\n"
        "• يعمل 24 ساعة\n\n"
        "💡 للاستفسار: @D_8_5"
    )
    await event.edit(info_text, buttons=[[Button.inline("🔙 العودة", b"home")]])

# ================== تشغيل البوت ==================
async def main():
    await bot.start()
    await initialize_user_clients()
    logger.info("🚀 البوت يعمل بنجاح!")
    await bot.run_until_disconnected()
# ================== خادم Flask للإبقاء على النشاط ==================
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!", 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# تشغيل Flask في خيط منفصل
threading.Thread(target=run_flask, daemon=True).start()
if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("⏹️ تم إيقاف البوت.")