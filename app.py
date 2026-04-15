#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║      🕌  بوت تيليجرام — صانع الريلز القرآني (Koyeb)      ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import re, gc, uuid, json, shutil, random, requests, unicodedata, asyncio, logging
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import PIL.Image
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import (
    ImageClip, VideoFileClip, AudioFileClip,
    CompositeVideoClip, ColorClip, concatenate_videoclips,
)
from moviepy.config import change_settings
from pydub import AudioSegment
import arabic_reshaper
from bidi.algorithm import get_display

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters,
)
from telegram.constants import ParseMode, ChatAction
from telegram.error import BadRequest

# ══════════════════════════════════════════════════════════
# ⚙️  الإعدادات والمسارات (مجهزة لبيئة Docker/Koyeb)
# ══════════════════════════════════════════════════════════
BOT_TOKEN     = os.environ.get("BOT_TOKEN")   # يُقرأ من إعدادات Koyeb

BASE_DIR      = "/app"
FONT_DIR      = os.path.join(BASE_DIR, "fonts")
FONT_ARABIC   = os.path.join(FONT_DIR, "Arabic.ttf")
FONT_ENGLISH  = os.path.join(FONT_DIR, "English.otf")
LOCAL_BGS_DIR = os.path.join(BASE_DIR, "local_bgs")

# استخدام مسار /tmp للملفات المؤقتة لتجنب امتلاء مساحة السيرفر
VISION_DIR    = "/tmp/vision"
TEMP_DIR      = "/tmp/workspaces"
VIDEOS_DIR    = "/tmp/videos"

for _d in [FONT_DIR, LOCAL_BGS_DIR, VISION_DIR, TEMP_DIR, VIDEOS_DIR]:
    os.makedirs(_d, exist_ok=True)

os.environ["FFMPEG_BINARY"] = "ffmpeg"
AudioSegment.converter = "ffmpeg"
try:
    change_settings({"IMAGEMAGICK_BINARY": os.getenv("IMAGEMAGICK_BINARY", "convert")})
except Exception:
    pass

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("moviepy").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════
# 🎵  فلتر الصوت
# ══════════════════════════════════════════════════════════
STUDIO_FILTER = (
    "highpass=f=60,"
    "equalizer=f=200:width_type=h:width=200:g=3,"
    "equalizer=f=8000:width_type=h:width=1000:g=2,"
    "acompressor=threshold=-21dB:ratio=4:attack=200:release=1000,"
    "extrastereo=m=1.3,"
    "loudnorm=I=-16:TP=-1.5:LRA=11"
)

# ══════════════════════════════════════════════════════════
# 🎨  ثيمات الألوان
# ══════════════════════════════════════════════════════════
COLOR_THEMES = {
    "مخصص":       None,
    "ذهبي":       {"ar_color":"#FFD700","ar_out_c":"#3d2000","en_color":"#ffffff","en_out_c":"#3d2000","bg1":"#1a0800","bg2":"#3d1500"},
    "ليلي أزرق":  {"ar_color":"#ffffff","ar_out_c":"#000428","en_color":"#7EB8F7","en_out_c":"#000428","bg1":"#000428","bg2":"#004e92"},
    "أخضر":       {"ar_color":"#ffffff","ar_out_c":"#003300","en_color":"#90EE90","en_out_c":"#003300","bg1":"#003300","bg2":"#006600"},
    "بنفسجي":     {"ar_color":"#FFD700","ar_out_c":"#1a0030","en_color":"#DDA0DD","en_out_c":"#1a0030","bg1":"#1a0030","bg2":"#3d0070"},
    "أبيض":       {"ar_color":"#1a1a1a","ar_out_c":"#cccccc","en_color":"#333333","en_out_c":"#cccccc","bg1":"#f5f5f0","bg2":"#e8e8e0"},
    "غروب":       {"ar_color":"#ffffff","ar_out_c":"#4a0000","en_color":"#FFD700","en_out_c":"#4a0000","bg1":"#0d0221","bg2":"#ff6b35"},
}

# ══════════════════════════════════════════════════════════
# 🌄  مواضيع الخلفيات
# ══════════════════════════════════════════════════════════
BG_TOPICS = {
    "عشوائي":        None,
    "سماء وغيوم":   "sky clouds timelapse",
    "كواكب ونجوم":  "galaxy stars milky way",
    "أمواج البحر":  "ocean waves slow motion",
    "غابات":         "forest trees aerial",
    "صحراء":         "desert sand dunes sunset",
    "شلالات":        "waterfall nature peaceful",
    "جبال":          "mountains fog mist",
    "مساجد":         "mosque architecture islamic",
    "مطر وليل":     "rain night bokeh",
    "شروق الشمس":   "sunrise golden hour",
    "مدينة وأضواء": "city lights night aerial",
    "نار ولهب":     "fire flames dark",
    "ماء وانعكاس":  "water reflection calm",
}

# ══════════════════════════════════════════════════════════
# 📊  البيانات
# ══════════════════════════════════════════════════════════
VERSE_COUNTS = {
    1:7,2:286,3:200,4:176,5:120,6:165,7:206,8:75,9:129,10:109,11:123,
    12:111,13:43,14:52,15:99,16:128,17:111,18:110,19:98,20:135,21:112,
    22:78,23:118,24:64,25:77,26:227,27:93,28:88,29:69,30:60,31:34,32:30,
    33:73,34:54,35:45,36:83,37:182,38:88,39:75,40:85,41:54,42:53,43:89,
    44:59,45:37,46:35,47:38,48:29,49:18,50:45,51:60,52:49,53:62,54:55,
    55:78,56:96,57:29,58:22,59:24,60:13,61:14,62:11,63:11,64:18,65:12,
    66:12,67:30,68:52,69:52,70:44,71:28,72:28,73:20,74:56,75:40,76:31,
    77:50,78:40,79:46,80:42,81:29,82:19,83:36,84:25,85:22,86:17,87:19,
    88:26,89:30,90:20,91:15,92:21,93:11,94:8,95:8,96:19,97:5,98:8,99:8,
    100:11,101:11,102:8,103:3,104:9,105:5,106:4,107:7,108:3,109:6,110:3,
    111:5,112:4,113:5,114:6,
}
SURAH_NAMES = [
    "الفاتحة","البقرة","آل عمران","النساء","المائدة","الأنعام","الأعراف",
    "الأنفال","التوبة","يونس","هود","يوسف","الرعد","إبراهيم","الحجر",
    "النحل","الإسراء","الكهف","مريم","طه","الأنبياء","الحج","المؤمنون",
    "النور","الفرقان","الشعراء","النمل","القصص","العنكبوت","الروم","لقمان",
    "السجدة","الأحزاب","سبأ","فاطر","يس","الصافات","ص","الزمر","غافر",
    "فصلت","الشورى","الزخرف","الدخان","الجاثية","الأحقاف","محمد","الفتح",
    "الحجرات","ق","الذاريات","الطور","النجم","القمر","الرحمن","الواقعة",
    "الحديد","المجادلة","الحشر","الممتحنة","الصف","الجمعة","المنافقون",
    "التغابن","الطلاق","التحريم","الملك","القلم","الحاقة","المعارج","نوح",
    "الجن","المزمل","المدثر","القيامة","الإنسان","المرسلات","النبأ",
    "النازعات","عبس","التكوير","الانفطار","المطففين","الانشقاق","البروج",
    "الطارق","الأعلى","الغاشية","الفجر","البلد","الشمس","الليل","الضحى",
    "الشرح","التين","العلق","القدر","البينة","الزلزلة","العاديات","القارعة",
    "التكاثر","العصر","الهمزة","الفيل","قريش","الماعون","الكوثر","الكافرون",
    "النصر","المسد","الإخلاص","الفلق","الناس",
]
NEW_RECITERS = {
    "احمد النفيس"   : (259, "https://server16.mp3quran.net/nufais/Rewayat-Hafs-A-n-Assem/"),
    "وديع اليماني"  : (219, "https://server6.mp3quran.net/wdee3/"),
    "بندر بليلة"    : (217, "https://server6.mp3quran.net/balilah/"),
    "ادريس أبكر"    : (12,  "https://server6.mp3quran.net/abkr/"),
    "منصور السالمي" : (245, "https://server14.mp3quran.net/mansor/"),
    "رعد الكردي"    : (221, "https://server6.mp3quran.net/kurdi/"),
}
OLD_RECITERS = {
    "أبو بكر الشاطري"  : "Abu_Bakr_Ash-Shaatree_128kbps",
    "ياسر الدوسري"     : "Yasser_Ad-Dussary_128kbps",
    "عبدالرحمن السديس" : "Abdurrahmaan_As-Sudais_64kbps",
    "ماهر المعيقلي"    : "Maher_AlMuaiqly_64kbps",
    "سعود الشريم"      : "Saood_ash-Shuraym_64kbps",
    "مشاري العفاسي"    : "Alafasy_64kbps",
    "ناصر القطامي"     : "Nasser_Alqatami_128kbps",
}
ALL_RECITERS = list(NEW_RECITERS) + list(OLD_RECITERS)
RECITERS_MAP = {**{k: k for k in NEW_RECITERS}, **OLD_RECITERS}
PEXELS_KEYS  = [
    os.environ.get("PEXELS_API_KEY", "AmAgE0J5AuBbsvR6dmG7qQLIc5uYZvDim2Vx250F5QoHNKnGdCofFerx")
]

# ══════════════════════════════════════════════════════════
# 🔢  حالات المحادثة
# ══════════════════════════════════════════════════════════
(
    ST_MAIN, ST_SURAH, ST_AYAH_MODE, ST_AYAH_FROM, ST_AYAH_TO,
    ST_RECITER, ST_QUALITY, ST_BG_TYPE, ST_BG_TOPIC,
    ST_THEME, ST_EXTRAS, ST_WATERMARK, ST_CONFIRM,
) = range(13)

SURAH_PER_PAGE   = 10
RECITER_PER_PAGE = 7

# ══════════════════════════════════════════════════════════
# 🛠️  دوال مساعدة
# ══════════════════════════════════════════════════════════
def safe_filename(t):
    t = unicodedata.normalize("NFKC", t)
    t = re.sub(r'[\\/*?:"<>|]', "", t)
    return t.strip().replace(" ", "_")

def make_video_name(surah_num, start, last, reciter, quality):
    s = safe_filename(SURAH_NAMES[surah_num - 1])
    r = safe_filename(reciter)
    return f"سورة_{s}_{surah_num:03d}_آية_{start}-{last}_{r}_{quality}.mp4"

def reshape_ar(text):
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text

def wrap_ar(text, per_line):
    words = text.split()
    lines = [" ".join(words[i:i+per_line]) for i in range(0, len(words), per_line)]
    return "\n".join(reshape_ar(l) for l in reversed(lines))

def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

@lru_cache(maxsize=30)
def get_font(path, size):
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        try:
            return ImageFont.truetype(path, size)
        except Exception as e:
            logger.warning("Font failed %s: %s", path, e)
    return ImageFont.load_default()

def trim_silence(seg, offset=-16, fade=40):
    thresh = seg.dBFS + offset
    chunk  = 10
    s = 0
    while s < len(seg) and seg[s:s+chunk].dBFS < thresh:
        s += chunk
    e = 0
    rev = seg.reverse()
    while e < len(rev) and rev[e:e+chunk].dBFS < thresh:
        e += chunk
    r = seg[max(0, s-30): len(seg)-max(0, e-30)]
    return r.fade_in(fade).fade_out(fade) if len(r) > 200 else seg

def smart_dl(url, dest):
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)

# ══════════════════════════════════════════════════════════
# 🎵  الصوت والنص
# ══════════════════════════════════════════════════════════
def download_audio(reciter_key, surah, ayah, idx, workspace):
    if reciter_key in NEW_RECITERS:
        rid, base_url = NEW_RECITERS[reciter_key]
        cache = os.path.join(BASE_DIR, "cache", str(rid))
        os.makedirs(cache, exist_ok=True)
        mp3   = os.path.join(cache, f"{surah:03d}.mp3")
        tjson = os.path.join(cache, f"{surah:03d}.json")
        if not os.path.exists(mp3) or not os.path.exists(tjson):
            smart_dl(f"{base_url}{surah:03d}.mp3", mp3)
            resp = requests.get(
                f"https://mp3quran.net/api/v3/ayat_timing?surah={surah}&read={rid}"
            ).json()
            with open(tjson, "w") as f:
                json.dump(
                    {str(item["ayah"]): {"start": item["start_time"],
                     "end": item["end_time"]} for item in resp}, f
                )
        with open(tjson) as f:
            t = json.load(f)[str(ayah)]
        seg = AudioSegment.from_file(mp3)[t["start"]:t["end"]]
        seg = trim_silence(seg, -16, 50)
    else:
        url = (f"https://everyayah.com/data/"
               f"{RECITERS_MAP[reciter_key]}/{surah:03d}{ayah:03d}.mp3")
        raw = os.path.join(workspace, f"raw_{idx}.mp3")
        smart_dl(url, raw)
        seg = trim_silence(AudioSegment.from_file(raw), -20, 20)
        if os.path.exists(raw):
            os.remove(raw)
    out = os.path.join(workspace, f"part_{idx}.mp3")
    seg.export(out, format="mp3")
    return out

def get_ar_text(surah, ayah):
    try:
        t = requests.get(
            f"https://api.alquran.cloud/v1/ayah/{surah}:{ayah}/quran-simple"
        ).json()["data"]["text"]
        if surah not in (1, 9) and ayah == 1:
            t = re.sub(r"^بِسْمِ [^ ]+ [^ ]+ [^ ]+", "", t).strip()
        return t
    except Exception:
        return "خطأ في النص"

def get_en_text(surah, ayah):
    try:
        return requests.get(
            f"http://api.alquran.cloud/v1/ayah/{surah}:{ayah}/en.sahih"
        ).json()["data"]["text"]
    except Exception:
        return ""

# ══════════════════════════════════════════════════════════
# 🎨  رسم النصوص والطبقات
# ══════════════════════════════════════════════════════════
def make_ar_clip(text, dur, W, scale, glow,
                 ar_color, ar_size, ar_out_c, ar_out_w, ar_shadow, ar_shadow_c):
    wc = len(text.split())
    if   wc > 60: fs, pl = 30, 12
    elif wc > 40: fs, pl = 35, 10
    elif wc > 25: fs, pl = 41, 9
    elif wc > 15: fs, pl = 46, 8
    else:         fs, pl = 52, 7
    fs       = max(20, int(fs * scale * float(ar_size)))
    stroke_w = int(ar_out_w)
    font     = get_font(FONT_ARABIC, fs)
    wrapped  = wrap_ar(text, pl)
    lines    = wrapped.split("\n")
    GAP      = max(8, int(14 * scale))
    probe    = ImageDraw.Draw(Image.new("RGBA", (W, 10)))
    heights, total_h = [], 0
    for line in lines:
        bb = probe.textbbox((0, 0), line, font=font, stroke_width=stroke_w)
        h  = max(10, bb[3]-bb[1])
        heights.append(h)
        total_h += h + GAP
    total_h = max(80, total_h + 60)
    img  = Image.new("RGBA", (W, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cy   = 30
    for i, line in enumerate(lines):
        bb = draw.textbbox((0, 0), line, font=font, stroke_width=stroke_w)
        w  = max(1, bb[2]-bb[0])
        x  = max(0, (W-w)//2)
        if ar_shadow:
            draw.text((x+3, cy+3), line, font=font, fill=ar_shadow_c)
        if glow:
            draw.text((x, cy), line, font=font, fill=(255, 255, 255, 40),
                      stroke_width=stroke_w+6, stroke_fill=(255, 255, 255, 15))
        draw.text((x, cy), line, font=font, fill=ar_color,
                  stroke_width=stroke_w, stroke_fill=ar_out_c)
        cy += heights[i] + GAP
    return ImageClip(np.array(img)).set_duration(dur).crossfadein(0.3).crossfadeout(0.3)

def make_en_clip(text, dur, W, scale,
                 en_color, en_size, en_out_c, en_out_w, en_shadow, en_shadow_c):
    fs       = max(16, int(28 * scale * float(en_size)))
    stroke_w = int(en_out_w)
    font     = get_font(FONT_ENGLISH, fs)
    words    = text.split()
    lines    = [" ".join(words[i:i+9]) for i in range(0, len(words), 9)]
    probe    = ImageDraw.Draw(Image.new("RGBA", (W, 10)))
    heights, total_h = [], 30
    for line in lines:
        bb = probe.textbbox((0, 0), line, font=font, stroke_width=stroke_w)
        h  = max(10, bb[3]-bb[1])
        heights.append(h)
        total_h += h + 8
    total_h = max(60, total_h + 20)
    img  = Image.new("RGBA", (W, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cy   = 15
    for i, line in enumerate(lines):
        bb = draw.textbbox((0, 0), line, font=font, stroke_width=stroke_w)
        w  = max(1, bb[2]-bb[0])
        x  = (W-w)//2
        if en_shadow:
            draw.text((x+2, cy+2), line, font=font, fill=en_shadow_c)
        draw.text((x, cy), line, font=font, fill=en_color,
                  stroke_width=stroke_w, stroke_fill=en_out_c)
        cy += heights[i] + 8
    return ImageClip(np.array(img)).set_duration(dur).crossfadein(0.3).crossfadeout(0.3)

def make_gradient(W, H, c1, c2, dur):
    a = np.array(hex_rgb(c1), dtype=np.float32)
    b = np.array(hex_rgb(c2), dtype=np.float32)
    img = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        t = y / H
        img[y] = (a*(1-t) + b*t).astype(np.uint8)
    return ImageClip(img).set_duration(dur)

def make_vignette(W, H):
    Y, X = np.ogrid[:H, :W]
    mask = np.clip(
        (np.sqrt((X-W/2)**2 + (Y-H/2)**2) / np.sqrt((W/2)**2 + (H/2)**2)) * 1.16,
        0, 1) ** 3
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    arr[:, :, 3] = (mask * 255).astype(np.uint8)
    return ImageClip(arr, ismask=False)

def make_surah_banner(surah_name, W, scale, dur):
    fs   = max(22, int(38*scale))
    font = get_font(FONT_ARABIC, fs)
    text = reshape_ar(f"سورة {surah_name}")
    h    = int(90 * scale)
    img  = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    bg   = Image.new("RGBA", (W, h), (0, 0, 0, 160))
    img.paste(bg, (0, 0), bg)
    draw = ImageDraw.Draw(img)
    lw   = max(2, int(3*scale))
    draw.rectangle([0, 0, W, lw], fill="#FFD700")
    draw.rectangle([0, h-lw, W, h], fill="#FFD700")
    bb   = draw.textbbox((0, 0), text, font=font, stroke_width=2)
    x    = (W - (bb[2]-bb[0])) // 2
    y    = (h - (bb[3]-bb[1])) // 2
    draw.text((x, y), text, font=font, fill="#FFD700",
              stroke_width=2, stroke_fill="#3d2000")
    return ImageClip(np.array(img)).set_duration(dur)

def make_verse_counter(current, total, W, scale, dur):
    fs   = max(14, int(22*scale))
    font = get_font(FONT_ENGLISH, fs)
    text = f"{current} / {total}"
    h    = int(50 * scale)
    img  = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    bg   = Image.new("RGBA", (W, h), (0, 0, 0, 130))
    img.paste(bg, (0, 0), bg)
    draw = ImageDraw.Draw(img)
    bar_h = max(3, int(4*scale))
    prog  = int((current/total) * W)
    draw.rectangle([0, 0, W, bar_h], fill=(255, 255, 255, 60))
    draw.rectangle([0, 0, prog, bar_h], fill="#FFD700")
    bb = draw.textbbox((0, 0), text, font=font)
    x  = (W - (bb[2]-bb[0])) // 2
    draw.text((x, bar_h+8), text, font=font,
              fill="#ffffff", stroke_width=1, stroke_fill="#000000")
    return ImageClip(np.array(img)).set_duration(dur)

def make_watermark(text, W, H, scale, dur, wm_color="#ffffff", opacity=0.4):
    if not text.strip():
        return None
    fs   = max(14, int(24*scale))
    font = get_font(FONT_ARABIC, fs)
    text = reshape_ar(text)
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bb   = draw.textbbox((0, 0), text, font=font, stroke_width=1)
    x    = W - (bb[2]-bb[0]) - int(20*scale)
    y    = H - int(80*scale)
    rgba = hex_rgb(wm_color) + (int(255*opacity),)
    draw.text((x, y), text, font=font, fill=rgba,
              stroke_width=1, stroke_fill=(0, 0, 0, int(255*opacity*0.5)))
    return ImageClip(np.array(img)).set_duration(dur)

def make_bismillah(W, H, bg1, bg2, scale, dur=3.0):
    a = np.array(hex_rgb(bg1), dtype=np.float32)
    b = np.array(hex_rgb(bg2), dtype=np.float32)
    img = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        t = y / H
        img[y] = (a*(1-t) + b*t).astype(np.uint8)
    pil  = Image.fromarray(img).convert("RGBA")
    draw = ImageDraw.Draw(pil)
    text = reshape_ar("بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ")
    fs   = max(40, int(70*scale))
    font = get_font(FONT_ARABIC, fs)
    bb   = draw.textbbox((0, 0), text, font=font, stroke_width=3)
    x    = (W - (bb[2]-bb[0])) // 2
    y    = (H - (bb[3]-bb[1])) // 2 - int(40*scale)
    draw.text((x, y), text, font=font, fill=(255, 215, 0, 40),
              stroke_width=10, stroke_fill=(255, 215, 0, 15))
    draw.text((x, y), text, font=font, fill="#FFD700",
              stroke_width=3, stroke_fill="#3d2000")
    lw = int(3*scale)
    ly = y + (bb[3]-bb[1]) + int(30*scale)
    m  = W // 5
    draw.rectangle([m, ly, W-m, ly+lw], fill="#FFD700")
    return ImageClip(np.array(pil)[:, :, :3]).set_duration(dur).fadein(0.5).fadeout(0.5)

def make_outro(surah_name, reciter, W, H, bg1, bg2, scale, dur=3.0):
    a = np.array(hex_rgb(bg1), dtype=np.float32)
    b = np.array(hex_rgb(bg2), dtype=np.float32)
    img = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        t = y / H
        img[y] = (a*(1-t) + b*t).astype(np.uint8)
    pil  = Image.fromarray(img).convert("RGBA")
    draw = ImageDraw.Draw(pil)
    data = [
        (reshape_ar(f"سورة {surah_name}"),          max(36, int(60*scale)), "#FFD700"),
        (reshape_ar(f"بصوت: {reciter}"),             max(22, int(36*scale)), "#ffffff"),
        (reshape_ar("صَدَقَ اللَّهُ الْعَظِيمُ"),  max(28, int(46*scale)), "#d4af37"),
    ]
    cy = H // 4
    for text, fs, color in data:
        font = get_font(FONT_ARABIC, fs)
        bb   = draw.textbbox((0, 0), text, font=font, stroke_width=2)
        x    = (W - (bb[2]-bb[0])) // 2
        draw.text((x, cy), text, font=font, fill=color,
                  stroke_width=2, stroke_fill="#000000")
        cy += (bb[3]-bb[1]) + int(20*scale)
    return ImageClip(np.array(pil)[:, :, :3]).set_duration(dur).fadein(0.5).fadeout(0.5)

# ══════════════════════════════════════════════════════════
# 🌄  الخلفيات
# ══════════════════════════════════════════════════════════
def fetch_pexels(topic_key, count):
    pool = []
    key  = random.choice(PEXELS_KEYS)
    q    = BG_TOPICS.get(topic_key) or random.choice(
        [v for v in BG_TOPICS.values() if v])
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            params={"query": q, "per_page": min(count+5, 20),
                    "page": random.randint(1, 5), "orientation": "portrait"},
            headers={"Authorization": key}, timeout=10,
        )
        if r.status_code == 200:
            vids = r.json().get("videos", [])
            random.shuffle(vids)
            for vid in vids:
                if len(pool) >= count:
                    break
                f = next((vf for vf in vid["video_files"]
                          if vf["width"] <= 1080 and vf["height"] > vf["width"]), None)
                if not f and vid["video_files"]:
                    f = vid["video_files"][0]
                if f:
                    path = os.path.join(VISION_DIR, f"bg_{vid['id']}.mp4")
                    if not os.path.exists(path):
                        smart_dl(f["link"], path)
                    pool.append(path)
    except Exception:
        pass
    if not pool:
        local = [os.path.join(LOCAL_BGS_DIR, fn) for fn in os.listdir(LOCAL_BGS_DIR)
                 if fn.lower().endswith((".mp4", ".mov", ".mkv"))]
        if local:
            pool = random.choices(local, k=count)
    return pool

# ══════════════════════════════════════════════════════════
# 🎬  منشئ الفيديو
# ══════════════════════════════════════════════════════════
def generate_video(params: dict, on_progress=None) -> str:
    surah_num    = params["surah_num"]
    start        = params["start"]
    last         = params["last"]
    reciter      = params["reciter"]
    quality      = params["quality"]
    fps          = int(params["fps"].replace("fps", ""))
    bg_type      = params.get("bg_type", "تدرج")
    bg_topic     = params.get("bg_topic", "عشوائي")
    theme_key    = params.get("theme", "ذهبي")
    show_banner  = params.get("show_banner", True)
    show_counter = params.get("show_counter", True)
    show_trans   = params.get("show_trans", True)
    add_bism     = params.get("add_bismillah", False)
    add_outro_f  = params.get("add_outro", False)
    wm_text      = params.get("watermark", "")

    theme = COLOR_THEMES.get(theme_key, COLOR_THEMES["ذهبي"])
    if theme:
        ar_color = theme["ar_color"]; ar_out_c = theme["ar_out_c"]
        en_color = theme["en_color"]; en_out_c = theme["en_out_c"]
        bg1 = theme["bg1"];           bg2 = theme["bg2"]
    else:
        ar_color = "#ffffff"; ar_out_c = "#000000"
        en_color = "#FFD700"; en_out_c = "#000000"
        bg1 = "#0a0a1e";      bg2 = "#1a1a3e"

    surah_name = SURAH_NAMES[surah_num - 1]
    total      = last - start + 1
    W, H       = (1080, 1920) if quality == "1080p" else (720, 1280)
    scale      = 1.0 if quality == "1080p" else 0.67

    workspace  = os.path.join(TEMP_DIR, str(uuid.uuid4()))
    os.makedirs(workspace, exist_ok=True)
    final_clip = None

    try:
        vpool    = fetch_pexels(bg_topic, total) if bg_type == "فيديو" else []
        dim      = ColorClip((W, H), color=(0, 0, 0)).set_opacity(0.38)
        vignette = make_vignette(W, H)
        segments = []
        bg_time  = 0.0

        if add_bism:
            segments.append(make_bismillah(W, H, bg1, bg2, scale))

        for i, ayah in enumerate(range(start, last + 1)):
            if on_progress:
                on_progress(i, total)

            rkey    = RECITERS_MAP.get(reciter, reciter)
            ap      = download_audio(rkey, surah_num, ayah, i, workspace)
            ac      = AudioFileClip(ap)
            dur     = ac.duration

            ar_raw  = reshape_ar(f"{get_ar_text(surah_num, ayah)} ({ayah})")
            en_raw  = get_en_text(surah_num, ayah)

            ar_clip = make_ar_clip(ar_raw, dur, W, scale, True,
                                   ar_color, 1.0, ar_out_c, 4, False, "#000000")
            ar_y    = H * 0.30
            ar_clip = ar_clip.set_position(("center", ar_y))

            # ── خلفية ──
            if bg_type == "تدرج":
                bg_clip = make_gradient(W, H, bg1, bg2, dur)
            elif i < len(vpool):
                bg_clip = (VideoFileClip(vpool[i]).resize(height=H)
                           .crop(width=W, height=H, x_center=W/2, y_center=H/2))
                if bg_clip.duration < dur:
                    bg_clip = bg_clip.loop(duration=dur)
                else:
                    ms = max(0.0, bg_clip.duration - dur)
                    st = random.uniform(0, ms)
                    bg_clip = bg_clip.subclip(st, st + dur)
                bg_clip = bg_clip.set_duration(dur).fadein(0.4).fadeout(0.4)
            else:
                bg_clip = make_gradient(W, H, bg1, bg2, dur)

            layers = [
                bg_clip,
                dim.set_duration(dur),
                vignette.set_duration(dur),
                ar_clip,
            ]

            if show_trans and en_raw:
                en_clip = make_en_clip(en_raw, dur, W, scale,
                                       en_color, 1.0, en_out_c, 3, False, "#000000")
                en_clip = en_clip.set_position(("center", ar_y + ar_clip.h + int(10*scale)))
                layers.append(en_clip)

            if show_banner:
                banner = make_surah_banner(surah_name, W, scale, dur)
                layers.append(banner.set_position(("center", 0)))

            if show_counter:
                counter = make_verse_counter(i+1, total, W, scale, dur)
                layers.append(counter.set_position(("center", H - int(50*scale))))

            if wm_text:
                wm = make_watermark(wm_text, W, H, scale, dur)
                if wm:
                    layers.append(wm)

            seg = CompositeVideoClip(layers).set_audio(ac)
            segments.append(seg)

        if add_outro_f:
            segments.append(make_outro(surah_name, reciter, W, H, bg1, bg2, scale))

        final_clip = concatenate_videoclips(segments, method="compose")
        mix_path   = os.path.join(workspace, "mix.mp4")
        vid_name   = make_video_name(surah_num, start, last, reciter, quality)
        out_path   = os.path.join(VIDEOS_DIR, vid_name)

        final_clip.write_videofile(
            mix_path, fps=fps, codec="libx264",
            audio_codec="aac", audio_bitrate="192k",
            preset="ultrafast", threads=os.cpu_count() or 4,
            logger=None,
        )

        cmd = (f'ffmpeg -y -i "{mix_path}" -af "{STUDIO_FILTER}" '
               f'-c:v copy -c:a aac -b:a 192k "{out_path}"')
        if os.system(cmd) != 0:
            shutil.copy2(mix_path, out_path)
        if os.path.exists(mix_path):
            os.remove(mix_path)

        return out_path

    finally:
        try:
            if final_clip:
                final_clip.close()
        except Exception:
            pass
        gc.collect()
        shutil.rmtree(workspace, ignore_errors=True)

# ══════════════════════════════════════════════════════════
# 🎹  لوحات المفاتيح
# ══════════════════════════════════════════════════════════
def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 إنشاء فيديو", callback_data="new")],
        [InlineKeyboardButton("📁 فيديوهاتي",   callback_data="my_videos"),
         InlineKeyboardButton("ℹ️ مساعدة",       callback_data="help")],
    ])

def kb_surah(page=0):
    s  = page * SURAH_PER_PAGE
    e  = min(s + SURAH_PER_PAGE, 114)
    tp = (113 // SURAH_PER_PAGE) + 1
    rows = [[InlineKeyboardButton(
        f"{n}. {SURAH_NAMES[n-1]}  ({VERSE_COUNTS[n]} آية)",
        callback_data=f"surah_{n}")] for n in range(s+1, e+1)]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"sp_{page-1}"))
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{tp}", callback_data="noop"))
    if e < 114:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"sp_{page+1}"))
    rows += [nav, [InlineKeyboardButton("🏠 رئيسية", callback_data="main")]]
    return InlineKeyboardMarkup(rows)

def kb_ayah_mode(max_ayah):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📖 السورة كاملة ({max_ayah} آية)", callback_data="ayah_full")],
        [InlineKeyboardButton("✂️ آيات محددة",  callback_data="ayah_custom")],
        [InlineKeyboardButton("🏠 رئيسية",      callback_data="main")],
    ])

def kb_reciter(page=0):
    s  = page * RECITER_PER_PAGE
    e  = min(s + RECITER_PER_PAGE, len(ALL_RECITERS))
    tp = (len(ALL_RECITERS)-1) // RECITER_PER_PAGE + 1
    rows = [[InlineKeyboardButton(f"🎤 {n}", callback_data=f"rec_{n}")]
            for n in ALL_RECITERS[s:e]]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"rp_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{tp}", callback_data="noop"))
    if e < len(ALL_RECITERS):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"rp_{page+1}"))
    rows += [nav, [InlineKeyboardButton("🏠 رئيسية", callback_data="main")]]
    return InlineKeyboardMarkup(rows)

def kb_quality():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 720p  20fps",  callback_data="q_720p_20fps"),
         InlineKeyboardButton("🖥️ 1080p 24fps", callback_data="q_1080p_24fps")],
        [InlineKeyboardButton("⚡ 720p  30fps",  callback_data="q_720p_30fps"),
         InlineKeyboardButton("🎞️ 1080p 30fps", callback_data="q_1080p_30fps")],
        [InlineKeyboardButton("🏠 رئيسية", callback_data="main")],
    ])

def kb_bg_type():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 فيديو طبيعة (Pexels)", callback_data="bg_فيديو")],
        [InlineKeyboardButton("🌈 تدرج لوني",             callback_data="bg_تدرج")],
        [InlineKeyboardButton("🏠 رئيسية",                callback_data="main")],
    ])

def kb_bg_topic():
    topics = list(BG_TOPICS.keys())
    rows   = []
    for i in range(0, len(topics), 2):
        row = [InlineKeyboardButton(topics[i], callback_data=f"bgt_{topics[i]}")]
        if i+1 < len(topics):
            row.append(InlineKeyboardButton(topics[i+1], callback_data=f"bgt_{topics[i+1]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("🏠 رئيسية", callback_data="main")])
    return InlineKeyboardMarkup(rows)

def kb_theme():
    themes = list(COLOR_THEMES.keys())
    labels = {"مخصص":"✏️","ذهبي":"✨","ليلي أزرق":"🌙","أخضر":"🌿",
              "بنفسجي":"👑","أبيض":"⬜","غروب":"🌅"}
    rows   = []
    for i in range(0, len(themes), 2):
        row = [InlineKeyboardButton(
            f"{labels.get(themes[i],'')} {themes[i]}",
            callback_data=f"theme_{themes[i]}")]
        if i+1 < len(themes):
            row.append(InlineKeyboardButton(
                f"{labels.get(themes[i+1],'')} {themes[i+1]}",
                callback_data=f"theme_{themes[i+1]}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("🏠 رئيسية", callback_data="main")])
    return InlineKeyboardMarkup(rows)

def kb_extras(d):
    def tog(key):
        return "✅" if d.get(key) else "⬜"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{tog('show_banner')} بانر اسم السورة",
                              callback_data="ext_show_banner"),
         InlineKeyboardButton(f"{tog('show_counter')} عداد الآيات",
                              callback_data="ext_show_counter")],
        [InlineKeyboardButton(f"{tog('show_trans')} الترجمة الإنجليزية",
                              callback_data="ext_show_trans"),
         InlineKeyboardButton(f"{tog('add_bismillah')} شريحة البسملة",
                              callback_data="ext_add_bismillah")],
        [InlineKeyboardButton(f"{tog('add_outro')} شريحة الختام",
                              callback_data="ext_add_outro"),
         InlineKeyboardButton("💧 علامة مائية", callback_data="ext_watermark")],
        [InlineKeyboardButton("✅ تأكيد الإعدادات", callback_data="extras_done")],
        [InlineKeyboardButton("🏠 رئيسية", callback_data="main")],
    ])

def kb_confirm(d):
    sn    = d["surah_num"]
    name  = SURAH_NAMES[sn - 1]
    total = d["last"] - d["start"] + 1
    eta   = max(1, total * 9 // 60)
    text  = (
        f"📋 *ملخص الطلب*\n\n"
        f"📖 *{name}* ({sn})\n"
        f"📿 الآيات: *{d['start']}* ← *{d['last']}* ({total} آية)\n"
        f"🎤 *{d['reciter']}*\n"
        f"📺 *{d['quality']}* | ⚡ *{d['fps']}*\n"
        f"🖼️ *{d.get('bg_type','تدرج')}*"
        + (f" — {d.get('bg_topic','')}" if d.get('bg_type') == 'فيديو' else "") + "\n"
        f"🎨 ثيم: *{d.get('theme','ذهبي')}*\n"
        f"⏱️ الوقت المتوقع: ~{eta} دقيقة"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ إنشاء الفيديو الآن!", callback_data="go")],
        [InlineKeyboardButton("🔄 غيّر القارئ",   callback_data="chg_rec"),
         InlineKeyboardButton("🔄 غيّر الثيم",    callback_data="chg_theme")],
        [InlineKeyboardButton("🔄 غيّر الإضافات", callback_data="chg_extras"),
         InlineKeyboardButton("🆕 طلب جديد",      callback_data="new")],
        [InlineKeyboardButton("🏠 رئيسية", callback_data="main")],
    ])
    return text, kb

# ══════════════════════════════════════════════════════════
# 📨  معالجات الأوامر
# ══════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text(
        "🕌 *أهلاً في صانع الريلز القرآني*\n\n"
        "إنشاء فيديوهات قرآنية احترافية بضغطة زر!\n\n"
        "• 13 قارئ مختلف\n"
        "• 14 نوع خلفية\n"
        "• 7 ثيمات ألوان\n"
        "• بانر + عداد + علامة مائية\n"
        "• شريحة بسملة وختام",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_main(),
    )
    return ST_MAIN

async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("❌ تم الإلغاء.", reply_markup=kb_main())
    return ConversationHandler.END

async def cmd_videos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    vids = sorted(
        [f for f in os.listdir(VIDEOS_DIR) if f.endswith(".mp4")],
        key=lambda x: os.path.getmtime(os.path.join(VIDEOS_DIR, x)),
        reverse=True,
    )
    if not vids:
        await update.message.reply_text("📭 لا توجد فيديوهات بعد.", reply_markup=kb_main())
        return
    lines = [f"📂 *الفيديوهات* ({len(vids)})\n"]
    for i, v in enumerate(vids[:10], 1):
        sz = os.path.getsize(os.path.join(VIDEOS_DIR, v)) / 1024 / 1024
        lines.append(f"{i}. `{v[:50]}` _{sz:.1f} MB_")
    await update.message.reply_text(
        "\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb_main()
    )

# ══════════════════════════════════════════════════════════
# 🔁  Callbacks
# ══════════════════════════════════════════════════════════
async def cb_main(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data.clear()
    await q.edit_message_text(
        "🕌 *صانع الريلز القرآني*\nاختر:",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb_main(),
    )
    return ST_MAIN

async def cb_new(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ctx.user_data.clear()
    await q.edit_message_text(
        "📖 *اختر السورة:*",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb_surah(0),
    )
    return ST_SURAH

async def cb_surah_page(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    page = int(q.data.split("_")[1])
    await q.answer()
    await q.edit_message_reply_markup(reply_markup=kb_surah(page))
    return ST_SURAH

async def cb_surah_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q  = update.callback_query
    sn = int(q.data.split("_")[1])
    await q.answer(SURAH_NAMES[sn-1])
    ctx.user_data["surah_num"] = sn
    await q.edit_message_text(
        f"📖 *سورة {SURAH_NAMES[sn-1]}* ({VERSE_COUNTS[sn]} آية)\n\nكيف تريد الآيات؟",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb_ayah_mode(VERSE_COUNTS[sn]),
    )
    return ST_AYAH_MODE

async def cb_ayah_full(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q  = update.callback_query
    sn = ctx.user_data["surah_num"]
    await q.answer("✅ السورة كاملة")
    ctx.user_data["start"] = 1
    ctx.user_data["last"]  = VERSE_COUNTS[sn]
    await q.edit_message_text(
        "🎤 *اختر القارئ:*",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb_reciter(0),
    )
    return ST_RECITER

async def cb_ayah_custom(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q  = update.callback_query
    sn = ctx.user_data["surah_num"]
    await q.answer()
    await q.edit_message_text(
        f"✂️ أرسل رقم *آية البداية*:\n_(1 إلى {VERSE_COUNTS[sn]})_",
        parse_mode=ParseMode.MARKDOWN,
    )
    return ST_AYAH_FROM

async def msg_ayah_from(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sn = ctx.user_data["surah_num"]
    mx = VERSE_COUNTS[sn]
    try:
        n = int(update.message.text.strip())
        if not 1 <= n <= mx:
            raise ValueError
        ctx.user_data["start"] = n
        await update.message.reply_text(
            f"✅ من آية *{n}*\nأرسل رقم *آية النهاية*:  ({n}–{mx})",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ST_AYAH_TO
    except ValueError:
        await update.message.reply_text(f"❌ أرسل رقماً من 1 إلى {mx}")
        return ST_AYAH_FROM

async def msg_ayah_to(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sn = ctx.user_data["surah_num"]
    mx = VERSE_COUNTS[sn]
    s  = ctx.user_data["start"]
    try:
        n = int(update.message.text.strip())
        if not s <= n <= mx:
            raise ValueError
        ctx.user_data["last"] = n
        await update.message.reply_text(
            f"✅ آية {s} ← {n}  ({n-s+1} آيات)\n\n🎤 *اختر القارئ:*",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb_reciter(0),
        )
        return ST_RECITER
    except ValueError:
        await update.message.reply_text(f"❌ أرسل رقماً من {s} إلى {mx}")
        return ST_AYAH_TO

async def cb_reciter_page(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    page = int(q.data.split("_")[1])
    await q.answer()
    await q.edit_message_reply_markup(reply_markup=kb_reciter(page))
    return ST_RECITER

async def cb_reciter_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q   = update.callback_query
    rec = q.data[4:]
    await q.answer(rec)
    ctx.user_data["reciter"] = rec
    await q.edit_message_text(
        "📺 *اختر الجودة:*",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb_quality(),
    )
    return ST_QUALITY

async def cb_quality_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q       = update.callback_query
    parts   = q.data.split("_")
    quality, fps = parts[1], parts[2]
    await q.answer(f"{quality} {fps}")
    ctx.user_data["quality"] = quality
    ctx.user_data["fps"]     = fps
    await q.edit_message_text(
        "🖼️ *نوع الخلفية:*",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb_bg_type(),
    )
    return ST_BG_TYPE

async def cb_bg_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q  = update.callback_query
    bg = q.data.split("_")[1]
    await q.answer()
    ctx.user_data["bg_type"] = bg
    if bg == "فيديو":
        await q.edit_message_text(
            "🎬 *اختر موضوع الخلفية:*",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb_bg_topic(),
        )
        return ST_BG_TOPIC
    else:
        await q.edit_message_text(
            "🎨 *اختر الثيم:*",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb_theme(),
        )
        return ST_THEME

async def cb_bg_topic(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q     = update.callback_query
    topic = q.data[4:]
    await q.answer(topic)
    ctx.user_data["bg_topic"] = topic
    await q.edit_message_text(
        "🎨 *اختر الثيم:*",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb_theme(),
    )
    return ST_THEME

async def cb_theme_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q     = update.callback_query
    theme = q.data[6:]
    await q.answer(theme)
    ctx.user_data["theme"] = theme
    ctx.user_data.setdefault("show_banner",   True)
    ctx.user_data.setdefault("show_counter",  True)
    ctx.user_data.setdefault("show_trans",    True)
    ctx.user_data.setdefault("add_bismillah", False)
    ctx.user_data.setdefault("add_outro",     False)
    ctx.user_data.setdefault("watermark",     "")
    await q.edit_message_text(
        "⚡ *الإضافات:*\nاضغط لتفعيل/إلغاء كل خاصية",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb_extras(ctx.user_data),
    )
    return ST_EXTRAS

async def cb_extra_toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q   = update.callback_query
    key = q.data[4:]
    if key == "watermark":
        await q.answer()
        await q.edit_message_text(
            "💧 أرسل نص العلامة المائية:\n_(مثال: @قناتك)_\nأو أرسل . للتخطي",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ST_WATERMARK
    ctx.user_data[key] = not ctx.user_data.get(key, True)
    await q.answer("✅" if ctx.user_data[key] else "⬜")
    await q.edit_message_reply_markup(reply_markup=kb_extras(ctx.user_data))
    return ST_EXTRAS

async def cb_extras_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text, kb = kb_confirm(ctx.user_data)
    await q.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    return ST_CONFIRM

async def msg_watermark(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    ctx.user_data["watermark"] = "" if txt == "." else txt
    await update.message.reply_text(
        "⚡ *الإضافات:*",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb_extras(ctx.user_data),
    )
    return ST_EXTRAS

async def cb_chg_rec(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🎤 *اختر القارئ:*",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb_reciter(0),
    )
    return ST_RECITER

async def cb_chg_theme(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🎨 *اختر الثيم:*",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb_theme(),
    )
    return ST_THEME

async def cb_chg_extras(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "⚡ *الإضافات:*",
        parse_mode=ParseMode.MARKDOWN, reply_markup=kb_extras(ctx.user_data),
    )
    return ST_EXTRAS

async def cb_my_videos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    vids = sorted(
        [f for f in os.listdir(VIDEOS_DIR) if f.endswith(".mp4")],
        key=lambda x: os.path.getmtime(os.path.join(VIDEOS_DIR, x)),
        reverse=True,
    )
    if not vids:
        await q.edit_message_text(
            "📭 لا توجد فيديوهات بعد.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🎬 إنشاء فيديو", callback_data="new"),
            ]]),
        )
        return ST_MAIN
    lines = [f"📂 *الفيديوهات* ({len(vids)})\n"]
    for i, v in enumerate(vids[:8], 1):
        sz = os.path.getsize(os.path.join(VIDEOS_DIR, v)) / 1024 / 1024
        lines.append(f"{i}. `{v[:52]}` _{sz:.1f} MB_")
    await q.edit_message_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 إنشاء فيديو", callback_data="new")],
            [InlineKeyboardButton("🏠 رئيسية",       callback_data="main")],
        ]),
    )
    return ST_MAIN

async def cb_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "ℹ️ *كيفية الاستخدام*\n\n"
        "1️⃣ اختر *السورة*\n2️⃣ اختر *الآيات*\n3️⃣ اختر *القارئ*\n"
        "4️⃣ اختر *الجودة والخلفية*\n5️⃣ اختر *الثيم والإضافات*\n"
        "6️⃣ اضغط *إنشاء* ✅\n\n"
        "📌 الأوامر:\n/start — الرئيسية\n/videos — الفيديوهات\n/cancel — إلغاء",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🎬 إنشاء", callback_data="new"),
            InlineKeyboardButton("🏠 رئيسية", callback_data="main"),
        ]]),
    )
    return ST_MAIN

async def cb_noop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

# ══════════════════════════════════════════════════════════
# ✅  إنشاء الفيديو
# ══════════════════════════════════════════════════════════
async def cb_go(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q       = update.callback_query
    await q.answer("✅ بدأ!")
    params  = dict(ctx.user_data)
    sname   = SURAH_NAMES[params["surah_num"] - 1]
    total   = params["last"] - params["start"] + 1
    chat_id = q.message.chat_id

    last_pct = [-1]
    prog_msg = await q.edit_message_text(
        f"⏳ *جاري الإنشاء...*\n\n📖 {sname}  |  {total} آية\n"
        f"🎤 {params['reciter']}\n\n▱▱▱▱▱▱▱▱▱▱  0%\n\n_يرجى الانتظار..._",
        parse_mode=ParseMode.MARKDOWN,
    )
    msg_id = prog_msg.message_id

    async def upd(i, t):
        pct = (i+1) * 100 // t
        if pct == last_pct[0]:
            return
        last_pct[0] = pct
        bar = "▰" * (pct//10) + "▱" * (10 - pct//10)
        try:
            await ctx.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=(f"⏳ *جاري الإنشاء...*\n\n📖 {sname}  |  {total} آية\n"
                      f"🎤 {params['reciter']}\n\n{bar}  {pct}%\n"
                      f"الآية {i+1}/{t}\n\n_يرجى الانتظار..._"),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest:
            pass

    try:
        loop = asyncio.get_event_loop()

        def sync_run():
            def prog(i, t):
                asyncio.run_coroutine_threadsafe(upd(i, t), loop)
            return generate_video(params, on_progress=prog)

        out_path = await loop.run_in_executor(None, sync_run)
        size_mb  = os.path.getsize(out_path) / 1024 / 1024

        await ctx.bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id,
            text=f"✅ *اكتمل!* ({size_mb:.1f} MB)\nجاري الإرسال...",
            parse_mode=ParseMode.MARKDOWN,
        )
        await ctx.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VIDEO)

        caption = (f"🕌 *سورة {sname}*\n"
                   f"📿 آية {params['start']} ← {params['last']}\n"
                   f"🎤 {params['reciter']}\n"
                   f"📺 {params['quality']} | {params['fps']}\n"
                   f"📦 {size_mb:.1f} MB")

        with open(out_path, "rb") as vf:
            await ctx.bot.send_video(
                chat_id=chat_id, video=vf, caption=caption,
                parse_mode=ParseMode.MARKDOWN, supports_streaming=True,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎬 فيديو جديد", callback_data="new"),
                    InlineKeyboardButton("🏠 رئيسية",     callback_data="main"),
                ]]),
            )
        await ctx.bot.delete_message(chat_id=chat_id, message_id=msg_id)

        # 🧹 التنظيف بعد الإرسال لتوفير مساحة السيرفر في Koyeb
        try:
            os.remove(out_path)
        except Exception as e:
            logger.warning(f"Could not delete video file: {e}")

    except Exception as e:
        logger.exception("Video generation failed")
        await ctx.bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id,
            text=f"❌ *خطأ:*\n`{str(e)[:300]}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 حاول مجدداً", callback_data="new"),
                InlineKeyboardButton("🏠 رئيسية",      callback_data="main"),
            ]]),
        )
    finally:
        ctx.user_data.clear()
    return ConversationHandler.END

# ══════════════════════════════════════════════════════════
# 🚀  التشغيل
# ══════════════════════════════════════════════════════════
def main():
    for path, label in [(FONT_ARABIC, "العربي"), (FONT_ENGLISH, "الإنجليزي")]:
        ok = os.path.exists(path) and os.path.getsize(path) > 1000
        logger.info("%s خط %s: %s", "✅" if ok else "❌", label, path)

    if not BOT_TOKEN:
        print("❌ الرجاء إضافة BOT_TOKEN في متغيرات البيئة (Environment Variables)")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(cb_new, pattern="^new$"),
        ],
        states={
            ST_MAIN:      [CallbackQueryHandler(cb_new,       pattern="^new$"),
                           CallbackQueryHandler(cb_my_videos, pattern="^my_videos$"),
                           CallbackQueryHandler(cb_help,      pattern="^help$"),
                           CallbackQueryHandler(cb_main,      pattern="^main$")],
            ST_SURAH:     [CallbackQueryHandler(cb_surah_select, pattern="^surah_[0-9]+$"),
                           CallbackQueryHandler(cb_surah_page,   pattern="^sp_[0-9]+$"),
                           CallbackQueryHandler(cb_main,         pattern="^main$")],
            ST_AYAH_MODE: [CallbackQueryHandler(cb_ayah_full,   pattern="^ayah_full$"),
                           CallbackQueryHandler(cb_ayah_custom, pattern="^ayah_custom$"),
                           CallbackQueryHandler(cb_main,        pattern="^main$")],
            ST_AYAH_FROM: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_ayah_from)],
            ST_AYAH_TO:   [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_ayah_to)],
            ST_RECITER:   [CallbackQueryHandler(cb_reciter_select, pattern="^rec_.+"),
                           CallbackQueryHandler(cb_reciter_page,   pattern="^rp_[0-9]+$"),
                           CallbackQueryHandler(cb_main,           pattern="^main$")],
            ST_QUALITY:   [CallbackQueryHandler(cb_quality_select, pattern="^q_.+"),
                           CallbackQueryHandler(cb_main,           pattern="^main$")],
            ST_BG_TYPE:   [CallbackQueryHandler(cb_bg_type, pattern="^bg_.+"),
                           CallbackQueryHandler(cb_main,    pattern="^main$")],
            ST_BG_TOPIC:  [CallbackQueryHandler(cb_bg_topic, pattern="^bgt_.+"),
                           CallbackQueryHandler(cb_main,     pattern="^main$")],
            ST_THEME:     [CallbackQueryHandler(cb_theme_select, pattern="^theme_.+"),
                           CallbackQueryHandler(cb_main,         pattern="^main$")],
            ST_EXTRAS:    [CallbackQueryHandler(cb_extra_toggle, pattern="^ext_.+"),
                           CallbackQueryHandler(cb_extras_done,  pattern="^extras_done$"),
                           CallbackQueryHandler(cb_main,         pattern="^main$")],
            ST_WATERMARK: [MessageHandler(filters.TEXT & ~filters.COMMAND, msg_watermark)],
            ST_CONFIRM:   [CallbackQueryHandler(cb_go,         pattern="^go$"),
                           CallbackQueryHandler(cb_chg_rec,    pattern="^chg_rec$"),
                           CallbackQueryHandler(cb_chg_theme,  pattern="^chg_theme$"),
                           CallbackQueryHandler(cb_chg_extras, pattern="^chg_extras$"),
                           CallbackQueryHandler(cb_new,        pattern="^new$"),
                           CallbackQueryHandler(cb_main,       pattern="^main$")],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            CommandHandler("start",  cmd_start),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("videos", cmd_videos))
    app.add_handler(CallbackQueryHandler(cb_noop,      pattern="^noop$"))
    app.add_handler(CallbackQueryHandler(cb_my_videos, pattern="^my_videos$"))
    app.add_handler(CallbackQueryHandler(cb_help,      pattern="^help$"))
    app.add_handler(CallbackQueryHandler(cb_main,      pattern="^main$"))

    print("\n" + "="*54)
    print("  🕌  بوت صانع الريلز القرآني (Koyeb) — يعمل الآن!")
    print(f"  📁  Temp Storage: {VIDEOS_DIR}")
    print("  📲  أرسل /start للبوت في تيليجرام")
    print("="*54 + "\n")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
