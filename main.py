
import pygame, random, sys, math, json, os, array

pygame.init()

# ---------------- SOUND (safe) ----------------
SOUND_ON = True
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
except Exception:
    SOUND_ON = False

def make_beep(freq, ms, vol=0.10):
    if not SOUND_ON:
        return None
    sr = 44100
    n = int(sr * ms / 1000)
    buf = array.array("h")
    amp = int(32767 * vol)
    for i in range(n):
        t = i / sr
        env = 1.0 - (i / n)
        val = math.sin(2 * math.pi * freq * t) * env
        buf.append(int(amp * val))
    try:
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception:
        return None

snd_shot  = make_beep(650, 25, 0.08)
snd_coin  = make_beep(1100, 55, 0.10)
snd_gold  = make_beep(900, 80, 0.11)
snd_click = make_beep(420, 35, 0.08)

def play(snd):
    if SOUND_ON and snd:
        try:
            snd.play()
        except Exception:
            pass

# ---------------- DISPLAY (Android safe) ----------------
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
W, H = screen.get_size()
clock = pygame.time.Clock()
pygame.display.set_caption("Space Runner")
BASE = min(W, H)

# ---------------- COLORS ----------------
WHITE=(255,255,255); BLACK=(0,0,0)
BG1=(10,12,30); BG2=(18,24,55)
PANEL=(22,26,54)
BLUE=(70,120,230); BLUE_D=(35,55,120)
DARK=(25,25,45)
GRAY=(170,175,200)
GREEN=(70,220,120)
RED=(255,70,70)

SILVER_MAIN=(210,210,235); SILVER_INNER=(245,245,255); SILVER_EDGE=(120,120,140)
GOLD_MAIN=(255,195,60);   GOLD_INNER=(255,242,175);   GOLD_EDGE=(170,120,0)

METEOR_MAIN=(160,90,55);  METEOR_EDGE=(120,65,40)
METEOR_GRAY=(110,110,120)

# ---------------- FONTS ----------------
FONT = pygame.font.SysFont(None, max(26, int(BASE*0.050)))
MID  = pygame.font.SysFont(None, max(34, int(BASE*0.065)))
BIG  = pygame.font.SysFont(None, max(56, int(BASE*0.105)))
SMALL = pygame.font.SysFont(None, max(20, int(BASE*0.038)))

def txt(s, f, c): return f.render(str(s), True, c)

def blit_center(surf, x, y):
    screen.blit(surf, surf.get_rect(center=(x,y)))

def clamp(v,a,b): return a if v<a else (b if v>b else v)

# ---------------- SAVE / LOAD ----------------
SAVE_PATH = os.path.join(os.path.dirname(__file__) if "__file__" in globals() else ".", "space_runner_save.json")

def load_save():
    data = {
        "bank_coins": 0,
        "level": 1,
        "xp": 0,
        "xp_need": 50,
        "unlocked_max_level": 1,
        "best_scores": {},  # level(str) -> int
        "weapon_owned": {"starter": True},
        "equipped_weapon": "starter",
        "weapon_level": 1
    }
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for k in data:
            if k in raw:
                data[k] = raw[k]
    except Exception:
        pass
    return data

def save_game():
    try:
        out = {
            "bank_coins": bank_coins,
            "level": level,
            "xp": xp,
            "xp_need": xp_need,
            "unlocked_max_level": unlocked_max_level,
            "best_scores": best_scores,
            "weapon_owned": weapon_owned,
            "equipped_weapon": equipped_weapon,
            "weapon_level": weapon_level
        }
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(out, f)
    except Exception:
        pass

# ---------------- STATES ----------------
STATE_MENU="menu"
STATE_CAMPAIGN="campaign"
STATE_SHOP="shop"
STATE_WEAPON="weapon"
STATE_GAME="game"
STATE_PAUSE="pause"
STATE_PASSED="passed"

# ---------------- PROGRESSION ----------------
save = load_save()
bank_coins = int(save["bank_coins"])
level = int(save["level"])
xp = int(save["xp"])
xp_need = int(save["xp_need"])
unlocked_max_level = int(save["unlocked_max_level"])
best_scores = dict(save.get("best_scores", {}))

weapon_owned = dict(save.get("weapon_owned", {"starter": True}))
equipped_weapon = str(save.get("equipped_weapon", "starter"))
weapon_level = int(save.get("weapon_level", 1))

def add_xp(amount):
    global xp, level, xp_need
    xp += int(amount)
    while xp >= xp_need:
        xp -= xp_need
        level += 1
        xp_need += 25

def difficulty_name(lvl):
    if lvl <= 5: return "EASY"
    if lvl <= 10: return "MEDIUM"
    if lvl <= 15: return "HARD"
    return "EXPERT"

def time_limit_for_level(lvl):
    base = 30 + (lvl-1)*5
    return int(base * 1000)

def coin_target_for_level(lvl):
    t = 15
    for _ in range(1, lvl):
        t += max(1, t//3)  # + 1/3
    return t

# ---------------- WEAPONS ----------------
WEAPONS = [
    {"id":"starter", "name":"Starter", "cost":0,   "dmg":21, "spd":7},
    {"id":"pistol",  "name":"Pistol",  "cost":200, "dmg":34, "spd":10},
    {"id":"rifle",   "name":"Rifle",   "cost":350, "dmg":70, "spd":18},
]

def weapon_by_id(wid):
    for w in WEAPONS:
        if w["id"] == wid:
            return w
    return WEAPONS[0]

def fire_delay_ms():
    # higher speed => smaller delay
    w = weapon_by_id(equipped_weapon)
    spd = w["spd"]
    base = 420
    delay = base - int(spd * 16)
    return clamp(delay, 80, 380)

def bullet_speed():
    w = weapon_by_id(equipped_weapon)
    return 12 + int(w["spd"] * 0.6)

def weapon_damage():
    w = weapon_by_id(equipped_weapon)
    return int(w["dmg"])

# ---------------- UI LAYOUT ----------------
SAFE_TOP = int(H*0.03)
SAFE_BOT = int(H*0.05)

nav_h = int(H*0.12)
nav_y = H - nav_h

BTN_W = W // 4
BTN_CAM = pygame.Rect(0*BTN_W, nav_y, BTN_W, nav_h)
BTN_SHO = pygame.Rect(1*BTN_W, nav_y, BTN_W, nav_h)
BTN_WEP = pygame.Rect(2*BTN_W, nav_y, BTN_W, nav_h)
BTN_SET = pygame.Rect(3*BTN_W, nav_y, BTN_W, nav_h)

BTN_PLAY = pygame.Rect(W//2-int(W*0.22), int(H*0.54), int(W*0.44), int(H*0.10))

# ---------------- STARFIELDS ----------------
menu_stars = [{"x":random.randrange(W), "y":random.randrange(H), "s":random.randint(1,3)} for _ in range(70)]
game_stars = [{"x":random.randrange(W), "y":random.randrange(H), "s":random.randint(1,3)} for _ in range(140)]

def draw_gradient(bg_top, bg_bottom):
    # cheap vertical gradient
    for y in range(0, H, 6):
        t = y / max(1, H-1)
        r = int(bg_top[0]*(1-t) + bg_bottom[0]*t)
        g = int(bg_top[1]*(1-t) + bg_bottom[1]*t)
        b = int(bg_top[2]*(1-t) + bg_bottom[2]*t)
        pygame.draw.rect(screen, (r,g,b), (0,y,W,6))

def draw_stars(stars, speed):
    for st in stars:
        st["y"] += speed * (0.7 + st["s"]*0.35)
        if st["y"] > H:
            st["y"] = -2
            st["x"] = random.randrange(W)
            st["s"] = random.randint(1,3)
        c = (160,170,220) if st["s"] == 3 else (120,130,190)
        pygame.draw.circle(screen, c, (int(st["x"]), int(st["y"])), st["s"])

# ---------------- ICONS ----------------
def draw_coin_icon(x, y, r, gold=True):
    main = GOLD_MAIN if gold else SILVER_MAIN
    inner = GOLD_INNER if gold else SILVER_INNER
    edge = GOLD_EDGE if gold else SILVER_EDGE
    pygame.draw.circle(screen, main, (x,y), r)
    pygame.draw.circle(screen, inner, (x,y), int(r*0.72))
    pygame.draw.circle(screen, edge, (x,y), r, 3)
    pygame.draw.circle(screen, (255,255,255), (x-int(r*0.25), y-int(r*0.25)), max(2, r//6))

def draw_padlock(cx, cy, scale=1.0):
    w = int(32*scale); h = int(24*scale)
    body = pygame.Rect(cx-w//2, cy-h//2+8, w, h)
    pygame.draw.rect(screen, (30,30,45), body, border_radius=6)
    pygame.draw.rect(screen, WHITE, body, 2, border_radius=6)
    pygame.draw.arc(screen, WHITE, (cx-w//3, cy-h//2-6, w*2//3, h), math.pi, 2*math.pi, 3)
    pygame.draw.circle(screen, WHITE, (cx, cy+10), 3)

def draw_nav_icon(rect, kind, active=False):
    cx, cy = rect.centerx, rect.y + int(rect.h*0.38)
    col = (210,220,255) if active else (170,175,200)
    if kind == "Campaign":
        # flag
        pygame.draw.line(screen, col, (cx-10, cy+14), (cx-10, cy-14), 3)
        pygame.draw.polygon(screen, col, [(cx-10,cy-14),(cx+18,cy-8),(cx-10,cy+2)])
    elif kind == "Shop":
        # bag
        pygame.draw.rect(screen, col, (cx-16, cy-6, 32, 26), 3, border_radius=6)
        pygame.draw.arc(screen, col, (cx-12, cy-18, 24, 20), math.pi, 2*math.pi, 3)
    elif kind == "Weapon":
        # gun
        pygame.draw.rect(screen, col, (cx-18, cy-2, 34, 10), border_radius=4)
        pygame.draw.rect(screen, col, (cx-2, cy+6, 8, 14), border_radius=3)
    else:
        # settings gear
        pygame.draw.circle(screen, col, (cx, cy+4), 12, 3)
        for a in range(0, 360, 45):
            dx = int(math.cos(math.radians(a))*16)
            dy = int(math.sin(math.radians(a))*16)
            pygame.draw.line(screen, col, (cx, cy+4), (cx+dx, cy+4+dy), 2)
        pygame.draw.circle(screen, col, (cx, cy+4), 4)

def draw_logo_under_title(x, y):
    # simple rocket-ish emblem
    pygame.draw.circle(screen, (40,50,110), (x, y), 34)
    pygame.draw.circle(screen, (90,120,240), (x, y), 28)
    pygame.draw.polygon(screen, (220,230,255), [(x, y-18), (x-18, y+10), (x, y+18), (x+18, y+10)])
    pygame.draw.circle(screen, (20,25,55), (x, y+2), 8)
    pygame.draw.circle(screen, (255,255,255), (x-3, y), 3)
    # ---------------- COMMON UI ----------------
def draw_button(rect, label, enabled=True):
    col = BLUE if enabled else BLUE_D
    pygame.draw.rect(screen, col, rect, border_radius=18)
    pygame.draw.rect(screen, WHITE, rect, 3, border_radius=18)
    blit_center(txt(label, MID, WHITE), rect.centerx, rect.centery)

def draw_top_bar_menu():
    # Left: XP bar with text inside
    bar_w = int(W*0.44)
    bar_h = int(H*0.045)
    bx = 16
    by = 16

    pygame.draw.rect(screen, (0,0,0), (bx,by,bar_w,bar_h), border_radius=14)
    pygame.draw.rect(screen, WHITE, (bx,by,bar_w,bar_h), 2, border_radius=14)

    fill = int(bar_w * (xp / max(1, xp_need)))
    pygame.draw.rect(screen, GREEN, (bx,by,fill,bar_h), border_radius=14)

    label = f"LVL {level}   XP {xp}/{xp_need}"
    blit_center(txt(label, SMALL, WHITE), bx + bar_w//2, by + bar_h//2)

    # Right: larger coin icon + number
    r = int(bar_h*0.70)
    cx = W - 16 - r - int(W*0.12)
    cy = by + bar_h//2
    draw_coin_icon(cx, cy, r, gold=True)

    c_text = txt(str(bank_coins), MID, WHITE)
    screen.blit(c_text, (cx + r + 10, cy - c_text.get_height()//2))

def draw_bottom_bar(active_name):
    pygame.draw.rect(screen, BLACK, (0, nav_y, W, nav_h))
    items = [(BTN_CAM,"Campaign"), (BTN_SHO,"Shop"), (BTN_WEP,"Weapon"), (BTN_SET,"Settings")]
    for r,name in items:
        on = (name == active_name)
        bg = BLUE_D if on else DARK
        pygame.draw.rect(screen, bg, r)
        pygame.draw.rect(screen, WHITE, r, 2)
        # icon above, label below
        draw_nav_icon(r, name, active=on)
        blit_center(txt(name, SMALL, WHITE), r.centerx, r.y + int(r.h*0.78))

def draw_menu():
    draw_gradient(BG1, BG2)
    draw_stars(menu_stars, speed=0.25)

    draw_top_bar_menu()

    blit_center(txt("SPACE RUNNER", BIG, WHITE), W//2, int(H*0.18))
    draw_logo_under_title(W//2, int(H*0.25))

    # subtle panel behind play
    panel = pygame.Rect(W//2-int(W*0.40), int(H*0.42), int(W*0.80), int(H*0.28))
    pygame.draw.rect(screen, (0,0,0), panel, border_radius=22)
    pygame.draw.rect(screen, WHITE, panel, 2, border_radius=22)

    draw_button(BTN_PLAY, "PLAY", enabled=True)
    blit_center(txt("Tap PLAY to start", FONT, GRAY), W//2, int(H*0.66))

    draw_bottom_bar(active_name="")

def blur_tile_overlay(rect, alpha=130):
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    s.fill((10,10,20, alpha))
    screen.blit(s, (rect.x, rect.y))
    # fake blur lines
    for _ in range(10):
        y = rect.y + random.randint(2, rect.h-3)
        x1 = rect.x + random.randint(2, rect.w//2)
        x2 = rect.x + random.randint(rect.w//2, rect.w-2)
        pygame.draw.line(screen, (20,20,35), (x1,y), (x2,y), 2)

def draw_weapon_info_panel(x, y, w, h):
    card = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, PANEL, card, border_radius=18)
    pygame.draw.rect(screen, WHITE, card, 2, border_radius=18)

    wpn = weapon_by_id(equipped_weapon)

    # small pistol icon
    ix = card.x + 16
    iy = card.y + 18
    pygame.draw.rect(screen, (30,30,55), (ix, iy, 96, 56), border_radius=12)
    pygame.draw.rect(screen, WHITE, (ix, iy, 96, 56), 2, border_radius=12)
    px = ix + 18; py = iy + 26
    pygame.draw.rect(screen, (220,220,235), (px, py, 52, 12), border_radius=6)
    pygame.draw.rect(screen, (220,220,235), (px+18, py+8, 14, 18), border_radius=6)
    pygame.draw.circle(screen, (255,230,120), (px+48, py+6), 3)

    screen.blit(txt("EQUIPPED", SMALL, GRAY), (ix+110, iy+2))
    screen.blit(txt(wpn["name"], MID, WHITE), (ix+110, iy+18))
    screen.blit(txt(f"Damage: {wpn['dmg']}", FONT, GRAY), (ix+110, iy+54))
    screen.blit(txt(f"Speed:  {wpn['spd']}", FONT, GRAY), (ix+110, iy+86))
    # ---------------- CAMPAIGN ----------------
TOTAL_LEVELS = 20

lvl_btns = []
grid_top = int(H*0.22)
cell_w = int(W*0.15)
cell_h = int(H*0.075)
gap_x = int(W*0.03)
gap_y = int(H*0.04)

cols = 5
rows = 4

total_w = cols*cell_w + (cols-1)*gap_x
sx = (W - total_w) // 2

for i in range(TOTAL_LEVELS):
    row = i // cols
    col = i % cols
    x = sx + col*(cell_w+gap_x)
    y = grid_top + row*(cell_h+gap_y)
    lvl_btns.append((i+1, pygame.Rect(x,y,cell_w,cell_h)))

def section_label_for_row(row_idx):
    # each row is 5 levels
    return ["EASY", "MEDIUM", "HARD", "EXPERT"][row_idx]

def draw_campaign():
    # different background
    draw_gradient((12,16,36), (26,20,60))
    draw_stars(menu_stars, speed=0.20)

    draw_top_bar_menu()
    blit_center(txt("CAMPAIGN", BIG, WHITE), W//2, int(H*0.14))

    # section headers centered above each row
    for r in range(rows):
        # center x same as grid
        y = grid_top + r*(cell_h+gap_y) - int(H*0.035)
        blit_center(txt(section_label_for_row(r), MID, (200,210,255)), W//2, y)

    for lvl, rect in lvl_btns:
        unlocked = (lvl <= unlocked_max_level)
        selected = (lvl == level)

        base_col = (65,95,190) if unlocked else (40,40,60)
        pygame.draw.rect(screen, base_col, rect, border_radius=14)
        pygame.draw.rect(screen, WHITE, rect, 3 if selected else 2, border_radius=14)

        # level number inside square
        sq = pygame.Rect(rect.x+10, rect.y+10, rect.h-20, rect.h-20)
        pygame.draw.rect(screen, (0,0,0), sq, border_radius=10)
        pygame.draw.rect(screen, WHITE, sq, 2, border_radius=10)
        ncol = WHITE if unlocked else (170,170,190)
        blit_center(txt(str(lvl), MID, ncol), sq.centerx, sq.centery)

        # "LVL" small text
        screen.blit(txt("LVL", SMALL, GRAY), (sq.right+8, rect.y+12))

        # best score
        bs = int(best_scores.get(str(lvl), 0))
        screen.blit(txt(f"Best: {bs}", SMALL, GRAY), (sq.right+8, rect.y+rect.h-28))

        if not unlocked:
            blur_tile_overlay(rect, alpha=140)
            draw_padlock(rect.centerx+int(rect.w*0.30), rect.centery, scale=0.9)

    # weapon info panel
    draw_weapon_info_panel(int(W*0.08), int(H*0.70), int(W*0.84), int(H*0.14))

    draw_bottom_bar(active_name="Campaign")

# ---------------- SHOP / WEAPON / SETTINGS ----------------
def draw_shop():
    draw_gradient((10,14,34),(20,28,62))
    draw_stars(menu_stars, speed=0.18)
    draw_top_bar_menu()
    blit_center(txt("SHOP", BIG, WHITE), W//2, int(H*0.14))

    cards = []
    top = int(H*0.24)
    card_w = int(W*0.84)
    card_h = int(H*0.12)
    cx = W//2 - card_w//2

    for i, wpn in enumerate(WEAPONS):
        rect = pygame.Rect(cx, top + i*(card_h+int(H*0.03)), card_w, card_h)
        cards.append((wpn, rect))

        pygame.draw.rect(screen, PANEL, rect, border_radius=18)
        pygame.draw.rect(screen, WHITE, rect, 2, border_radius=18)

        # icon
        ix = rect.x + 18; iy = rect.y + 18
        pygame.draw.rect(screen, (30,30,55), (ix,iy,96,56), border_radius=12)
        pygame.draw.rect(screen, WHITE, (ix,iy,96,56), 2, border_radius=12)
        px=ix+18; py=iy+26
        pygame.draw.rect(screen, (220,220,235), (px,py,52,12), border_radius=6)
        pygame.draw.rect(screen, (220,220,235), (px+18,py+8,14,18), border_radius=6)
        pygame.draw.circle(screen, (255,230,120), (px+48,py+6), 3)

        screen.blit(txt(wpn["name"], MID, WHITE), (ix+116, rect.y+14))
        screen.blit(txt(f"Damage {wpn['dmg']}   Speed {wpn['spd']}", FONT, GRAY), (ix+116, rect.y+54))

        owned = weapon_owned.get(wpn["id"], False) or (wpn["cost"] == 0)
        if wpn["cost"] == 0:
            owned = True

        # buy/equip button
        btn = pygame.Rect(rect.right-160, rect.y+28, 140, 56)
        if equipped_weapon == wpn["id"]:
            pygame.draw.rect(screen, (40,120,70), btn, border_radius=14)
            pygame.draw.rect(screen, WHITE, btn, 2, border_radius=14)
            blit_center(txt("EQUIPPED", SMALL, WHITE), btn.centerx, btn.centery)
        elif owned:
            pygame.draw.rect(screen, BLUE, btn, border_radius=14)
            pygame.draw.rect(screen, WHITE, btn, 2, border_radius=14)
            blit_center(txt("EQUIP", MID, WHITE), btn.centerx, btn.centery)
        else:
            can = bank_coins >= wpn["cost"]
            pygame.draw.rect(screen, BLUE if can else BLUE_D, btn, border_radius=14)
            pygame.draw.rect(screen, WHITE, btn, 2, border_radius=14)
            blit_center(txt(f"BUY {wpn['cost']}", SMALL, WHITE), btn.centerx, btn.centery)

    draw_bottom_bar(active_name="Shop")
    return cards

def draw_weapon_screen():
    draw_gradient((10,14,34),(20,28,62))
    draw_stars(menu_stars, speed=0.18)
    draw_top_bar_menu()
    blit_center(txt("WEAPON", BIG, WHITE), W//2, int(H*0.14))

    wpn = weapon_by_id(equipped_weapon)
    blit_center(txt(f"Equipped: {wpn['name']}", MID, WHITE), W//2, int(H*0.30))
    blit_center(txt(f"Damage: {wpn['dmg']}", FONT, GRAY), W//2, int(H*0.40))
    blit_center(txt(f"Speed:  {wpn['spd']}", FONT, GRAY), W//2, int(H*0.46))
    blit_center(txt(f"Fire delay: {fire_delay_ms()} ms", FONT, GRAY), W//2, int(H*0.52))
    blit_center(txt(f"Bullet speed: {bullet_speed()}", FONT, GRAY), W//2, int(H*0.58))

    draw_bottom_bar(active_name="Weapon")

def draw_settings_menu():
    draw_gradient((10,14,34),(20,28,62))
    draw_stars(menu_stars, speed=0.18)
    draw_top_bar_menu()
    blit_center(txt("SETTINGS", BIG, WHITE), W//2, int(H*0.14))

    btn1 = pygame.Rect(W//2-int(W*0.32), int(H*0.30), int(W*0.64), int(H*0.11))
    btn2 = pygame.Rect(W//2-int(W*0.32), int(H*0.45), int(W*0.64), int(H*0.11))
    btn3 = pygame.Rect(W//2-int(W*0.32), int(H*0.60), int(W*0.64), int(H*0.11))

    draw_button(btn1, "Back to MENU", True)
    draw_button(btn2, "Save", True)
    draw_button(btn3, "Exit", True)

    draw_bottom_bar(active_name="Settings")
    return btn1, btn2, btn3
    # ---------------- GAME OBJECTS ----------------
state = STATE_MENU

player = pygame.Rect(W//2-44, int(H*0.82), 88, 88)
bullets = []
coins = []   # {"rect":Rect,"val":1/3,"gold":bool,"angle":float,"vy":float}
meteors = [] # Meteor objects
popups = []  # {"t":str,"x":float,"y":float,"life":int,"col":(r,g,b)}

touching = False
score = 0
run_coins = 0
lives = 3
invincible_until = 0
run_start_ms = 0
last_shot_ms = 0
coin_angle = 0

GEAR_BTN = pygame.Rect(W-58, 70, 44, 44)  # in-game settings
PAUSE_RESUME = pygame.Rect(W//2-int(W*0.30), int(H*0.35), int(W*0.60), int(H*0.10))
PAUSE_RESTART= pygame.Rect(W//2-int(W*0.30), int(H*0.48), int(W*0.60), int(H*0.10))
PAUSE_MENU   = pygame.Rect(W//2-int(W*0.30), int(H*0.61), int(W*0.60), int(H*0.10))

def add_popup(text_s, x, y, col):
    popups.append({"t":text_s, "x":float(x), "y":float(y), "life":46, "col":col})

def draw_hearts(n):
    base_x = 18
    y = 74  # malo nize
    for i in range(n):
        x = base_x + i*38
        pygame.draw.circle(screen, RED, (x+10, y), 10)
        pygame.draw.circle(screen, RED, (x+24, y), 10)
        pygame.draw.polygon(screen, RED, [(x, y), (x+34, y), (x+17, y+28)])

def draw_player(now_ms):
    cx, cy = player.center
    r = player.w//2

    # blink when invincible
    if now_ms < invincible_until:
        if (now_ms // 120) % 2 == 0:
            return

    wing = (180, 200, 255)
    face = (255, 230, 200)
    eye = BLACK

    pygame.draw.polygon(screen, wing, [(cx-r, cy+8), (cx-r-56, cy-18), (cx-r-20, cy+38)])
    pygame.draw.polygon(screen, wing, [(cx+r, cy+8), (cx+r+56, cy-18), (cx+r+20, cy+38)])

    pygame.draw.circle(screen, face, (cx, cy), r)
    pygame.draw.circle(screen, (230, 200, 170), (cx, cy+12), r-10)

    pygame.draw.circle(screen, eye, (cx-14, cy-10), 6)
    pygame.draw.circle(screen, eye, (cx+14, cy-10), 6)
    pygame.draw.circle(screen, (255,255,255), (cx-16, cy-12), 2)
    pygame.draw.circle(screen, (255,255,255), (cx+12, cy-12), 2)

    # gun
    wpn = weapon_by_id(equipped_weapon)
    edge = (255, 210, 90)
    if wpn["id"] == "rifle":
        pygame.draw.rect(screen, (45,45,70), (cx+10, cy-6, 78, 18), border_radius=6)
        pygame.draw.rect(screen, edge, (cx+10, cy-6, 78, 18), 2, border_radius=6)
        pygame.draw.rect(screen, (110,110,140), (cx+30, cy+6, 22, 18), border_radius=5)
    elif wpn["id"] == "pistol":
        pygame.draw.rect(screen, (60,60,85), (cx+16, cy-3, 62, 16), border_radius=6)
        pygame.draw.rect(screen, edge, (cx+16, cy-3, 62, 16), 2, border_radius=6)
    else:
        pygame.draw.rect(screen, (70,70,95), (cx+16, cy-3, 56, 14), border_radius=6)
        pygame.draw.rect(screen, WHITE, (cx+16, cy-3, 56, 14), 2, border_radius=6)

def draw_rot_coin(rect, gold, angle_deg):
    radius = rect.w//2
    main = GOLD_MAIN if gold else SILVER_MAIN
    inner = GOLD_INNER if gold else SILVER_INNER
    edge = GOLD_EDGE if gold else SILVER_EDGE

    scale = abs(math.cos(math.radians(angle_deg)))
    w = int(radius*scale)
    if w < 4: w = 4
    pygame.draw.ellipse(screen, main, (rect.centerx-w, rect.centery-radius, w*2, radius*2))
    pygame.draw.ellipse(screen, inner, (rect.centerx-int(w*0.60), rect.centery-int(radius*0.60), int(w*1.20), int(radius*1.20)))
    pygame.draw.ellipse(screen, edge, (rect.centerx-w, rect.centery-radius, w*2, radius*2), 3)
    shine_x = rect.centerx - int(w*0.35)
    shine_y = rect.centery - int(radius*0.35)
    pygame.draw.circle(screen, (255,255,255), (shine_x, shine_y), max(2, radius//6))

class Meteor:
    def __init__(self, lvl):
        # 3 types
        typ = random.choices([1,2,3], weights=[55,30,15])[0]
        self.hp = typ
        base_r = int(BASE*0.040)
        self.r = base_r + (typ-1)*int(BASE*0.020)  # bigger per type
        self.x = random.uniform(self.r, W-self.r)
        self.y = -self.r - random.randint(0, 200)
        # speed slightly depends on level
        base_v = 2.6 + (max(0, lvl-1) * 0.12)
        self.vx = random.uniform(-1.6, 1.6)
        self.vy = random.uniform(base_v*0.85, base_v*1.15)
        self.rot = random.uniform(0, 360)
        self.rot_spd = random.uniform(-3.0, 3.0)
        self.typ = typ

    def rect(self):
        return pygame.Rect(int(self.x-self.r), int(self.y-self.r), int(self.r*2), int(self.r*2))

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rot += self.rot_spd

        # walls bounce
        if self.x - self.r < 0:
            self.x = self.r
            self.vx *= -1.05
        if self.x + self.r > W:
            self.x = W - self.r
            self.vx *= -1.05

        # keep some horizontal drift
        self.vx *= 0.995
        self.vx = clamp(self.vx, -6.5, 6.5)
        self.vy = clamp(self.vy, 1.8, 10.5)

    def draw(self):
        cx, cy = int(self.x), int(self.y)

        # more "realistic" layered meteor
        col = METEOR_MAIN if self.typ != 2 else (150,105,70)
        edge = METEOR_EDGE if self.typ != 2 else (110,80,55)

        pygame.draw.circle(screen, col, (cx,cy), self.r)
        pygame.draw.circle(screen, edge, (cx,cy), self.r, 4)

        # craters
        for k in range(self.typ+1):
            rr = max(4, int(self.r*0.18))
            ox = int(math.cos(math.radians(self.rot + k*70))*self.r*0.35)
            oy = int(math.sin(math.radians(self.rot + k*70))*self.r*0.25)
            pygame.draw.circle(screen, (90,60,45), (cx+ox, cy+oy), rr)
            pygame.draw.circle(screen, (60,45,35), (cx+ox, cy+oy), rr, 2)

        # small highlight
        pygame.draw.circle(screen, (230,210,180), (cx-int(self.r*0.25), cy-int(self.r*0.25)), max(3, self.r//7))

def collide_bounce(a: Meteor, b: Meteor):
    dx = b.x - a.x
    dy = b.y - a.y
    dist = math.hypot(dx, dy)
    min_d = a.r + b.r
    if dist <= 0 or dist >= min_d:
        return
    # push apart
    nx = dx / dist
    ny = dy / dist
    overlap = (min_d - dist)
    a.x -= nx * overlap * 0.5
    a.y -= ny * overlap * 0.5
    b.x += nx * overlap * 0.5
    b.y += ny * overlap * 0.5

    # exchange velocity along normal, add "boost" on hit
    rel_vx = b.vx - a.vx
    rel_vy = b.vy - a.vy
    vn = rel_vx*nx + rel_vy*ny
    if vn > 0:
        return

    impulse = -vn * 0.95
    a.vx -= impulse * nx
    a.vy -= impulse * ny * 0.4
    b.vx += impulse * nx
    b.vy += impulse * ny * 0.4

    # boost the "hit" feel
    b.vx *= 1.08
    b.vy *= 1.05
    a.vx *= 1.08
    a.vy *= 1.05

def reset_run():
    global bullets, coins, meteors, popups
    global score, run_coins, lives, invincible_until
    global run_start_ms, last_shot_ms, touching

    bullets=[]
    coins=[]
    meteors=[]
    popups=[]
    score=0
    run_coins=0
    lives=3
    invincible_until=0
    touching=False

    run_start_ms = pygame.time.get_ticks()
    last_shot_ms = run_start_ms

    player.centerx = W//2
    player.centery = int(H*0.82)

def spawn_coin(gold=False):
    size = 72 if gold else 60
    x = random.randint(20, W-size-20)
    y = -size - random.randint(0, 200)
    vy = 6.8 if gold else 6.0  # brze nego pre
    coins.append({"rect": pygame.Rect(x,y,size,size), "val": 3 if gold else 1, "gold": gold, "angle": random.random()*360, "vy": vy})

def spawn_meteor():
    meteors.append(Meteor(level))

def cap_for_elapsed(elapsed_ms):
    # build-up: first 10s low, then higher
    t = elapsed_ms / 1000.0
    base = 2 if level <= 5 else 3
    if t > 10: base += 1
    if t > 20: base += 2
    if level >= 6: base += (level-6) // 2  # medium+ adds
    return clamp(base, 2, 10)

def draw_game_hud(now_ms, left_ms):
    # top-left: level + difficulty
    screen.blit(txt(f"LVL {level} ({difficulty_name(level)})", FONT, WHITE), (15, 15))
    draw_hearts(lives)

    # top-middle timer
    sec = max(0, left_ms // 1000)
    timer_s = txt(f"{int(sec):02d}s", FONT, WHITE)
    screen.blit(timer_s, timer_s.get_rect(center=(W//2, 24)))

    # top-right score + coin icon
    sc = txt(f"SCORE {score}", FONT, WHITE)
    screen.blit(sc, (W - sc.get_width() - 16, 16))

    # gear button
    pygame.draw.rect(screen, (0,0,0), GEAR_BTN, border_radius=10)
    pygame.draw.rect(screen, WHITE, GEAR_BTN, 2, border_radius=10)
    # small gear
    cx, cy = GEAR_BTN.center
    pygame.draw.circle(screen, WHITE, (cx,cy), 10, 2)
    for a in range(0, 360, 60):
        dx = int(math.cos(math.radians(a))*12)
        dy = int(math.sin(math.radians(a))*12)
        pygame.draw.line(screen, WHITE, (cx,cy), (cx+dx, cy+dy), 2)

def draw_pause_overlay():
    overlay = pygame.Surface((W,H), pygame.SRCALPHA)
    overlay.fill((0,0,0, 175))
    screen.blit(overlay, (0,0))
    blit_center(txt("SETTINGS", BIG, WHITE), W//2, int(H*0.22))
    draw_button(PAUSE_RESUME, "RESUME", True)
    draw_button(PAUSE_RESTART, "RESTART", True)
    draw_button(PAUSE_MENU, "MENU", True)
running = True
shop_cards_cache = []

while running:
    dt = clock.tick(60)
    coin_angle = (coin_angle + 8) % 360

    mx, my = pygame.mouse.get_pos()

    # -------- EVENTS --------
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if state == STATE_GAME:
                    state = STATE_PAUSE
                else:
                    running = False

        if e.type == pygame.MOUSEBUTTONDOWN:
            play(snd_click)

            if state == STATE_MENU:
                if BTN_PLAY.collidepoint(e.pos):
                    reset_run()
                    state = STATE_GAME
                elif BTN_CAM.collidepoint(e.pos):
                    state = STATE_CAMPAIGN
                elif BTN_SHO.collidepoint(e.pos):
                    state = STATE_SHOP
                elif BTN_WEP.collidepoint(e.pos):
                    state = STATE_WEAPON
                elif BTN_SET.collidepoint(e.pos):
                    state = STATE_PAUSE  # menu settings screen reused
            elif state == STATE_CAMPAIGN:
                # pick level only if unlocked
                for lvl, r in lvl_btns:
                    if r.collidepoint(e.pos):
                        if lvl <= unlocked_max_level:
                            level = lvl
                            save_game()
                            state = STATE_MENU
                        break
                if BTN_CAM.collidepoint(e.pos): state = STATE_CAMPAIGN
                elif BTN_SHO.collidepoint(e.pos): state = STATE_SHOP
                elif BTN_WEP.collidepoint(e.pos): state = STATE_WEAPON
                elif BTN_SET.collidepoint(e.pos): state = STATE_PAUSE

            elif state == STATE_SHOP:
                # click on weapon cards: buy/equip
                for wpn, rect in shop_cards_cache:
                    btn = pygame.Rect(rect.right-160, rect.y+28, 140, 56)
                    if btn.collidepoint(e.pos):
                        owned = weapon_owned.get(wpn["id"], False) or (wpn["cost"] == 0)
                        if wpn["cost"] == 0:
                            owned = True
                        if equipped_weapon == wpn["id"]:
                            pass
                        elif owned:
                            equipped_weapon = wpn["id"]
                            save_game()
                        else:
                            if bank_coins >= wpn["cost"]:
                                bank_coins -= wpn["cost"]
                                weapon_owned[wpn["id"]] = True
                                equipped_weapon = wpn["id"]
                                save_game()
                        break

                if BTN_CAM.collidepoint(e.pos): state = STATE_CAMPAIGN
                elif BTN_SHO.collidepoint(e.pos): state = STATE_SHOP
                elif BTN_WEP.collidepoint(e.pos): state = STATE_WEAPON
                elif BTN_SET.collidepoint(e.pos): state = STATE_PAUSE

            elif state == STATE_WEAPON:
                if BTN_CAM.collidepoint(e.pos): state = STATE_CAMPAIGN
                elif BTN_SHO.collidepoint(e.pos): state = STATE_SHOP
                elif BTN_WEP.collidepoint(e.pos): state = STATE_WEAPON
                elif BTN_SET.collidepoint(e.pos): state = STATE_PAUSE

            elif state == STATE_PAUSE and state != STATE_GAME:
                # menu settings screen buttons
                b1, b2, b3 = draw_settings_menu()
                if b1.collidepoint(e.pos):
                    state = STATE_MENU
                elif b2.collidepoint(e.pos):
                    save_game()
                    state = STATE_MENU
                elif b3.collidepoint(e.pos):
                    running = False

            elif state == STATE_GAME:
                # in-game touch/drag + gear
                if GEAR_BTN.collidepoint(e.pos):
                    state = STATE_PAUSE
                else:
                    touching = True
                    player.centerx = e.pos[0]

            elif state == STATE_PAUSE:
                # in-game pause overlay buttons
                if PAUSE_RESUME.collidepoint(e.pos):
                    state = STATE_GAME
                elif PAUSE_RESTART.collidepoint(e.pos):
                    reset_run()
                    state = STATE_GAME
                elif PAUSE_MENU.collidepoint(e.pos):
                    save_game()
                    state = STATE_MENU

            elif state == STATE_PASSED:
                # next level if unlocked
                if level >= unlocked_max_level and level < TOTAL_LEVELS:
                    unlocked_max_level = level + 1
                save_game()
                state = STATE_MENU

        if e.type == pygame.MOUSEBUTTONUP:
            touching = False

        if e.type == pygame.MOUSEMOTION and state == STATE_GAME and touching:
            player.centerx = e.pos[0]

    # keep player in bounds
    player.x = clamp(player.x, 0, W-player.w)

    # -------- DRAW / UPDATE --------
    if state == STATE_MENU:
        draw_menu()

    elif state == STATE_CAMPAIGN:
        draw_campaign()

    elif state == STATE_SHOP:
        shop_cards_cache = draw_shop()

    elif state == STATE_WEAPON:
        draw_weapon_screen()

    elif state == STATE_PAUSE and state != STATE_GAME:
        # menu settings screen
        b1, b2, b3 = draw_settings_menu()

    elif state == STATE_GAME:
        # game background
        draw_gradient((6,8,20),(14,18,40))
        draw_stars(game_stars, speed=1.25)

        now = pygame.time.get_ticks()
        elapsed = now - run_start_ms
        left_ms = time_limit_for_level(level) - elapsed

        # auto fire
        if now - last_shot_ms >= fire_delay_ms():
            last_shot_ms = now
            bullets.append(pygame.Rect(player.centerx-4, player.top-18, 8, 18))
            play(snd_shot)

        # spawn coins
        if random.randint(1, 18) == 1:
            spawn_coin(gold=False)
        if random.randint(1, 90) == 1:
            spawn_coin(gold=True)

        # spawn meteors up to cap
        cap = cap_for_elapsed(elapsed)
        while len(meteors) < cap:
            spawn_meteor()

        # update bullets
        bs = bullet_speed()
        for b in bullets[:]:
            b.y -= bs
            if b.bottom < -50:
                bullets.remove(b)

        # update coins
        for c in coins[:]:
            c["rect"].y += int(c["vy"])
            c["angle"] = (c["angle"] + 12) % 360
            if c["rect"].top > H+80:
                coins.remove(c)
                continue
            if player.colliderect(c["rect"]):
                run_coins += c["val"]
                add_popup(f"+{c['val']}", c["rect"].centerx, c["rect"].centery, GOLD_MAIN if c["gold"] else SILVER_MAIN)
                play(snd_gold if c["gold"] else snd_coin)
                coins.remove(c)

        # update meteors
        for m in meteors:
            m.update()

        # meteor-meteor collisions
        for i in range(len(meteors)):
            for j in range(i+1, len(meteors)):
                collide_bounce(meteors[i], meteors[j])

        # bullet-meteor collisions
        for m in meteors[:]:
            mr = m.rect()
            hit_b = None
            for b in bullets:
                if b.colliderect(mr):
                    hit_b = b
                    break
            if hit_b:
                if hit_b in bullets:
                    bullets.remove(hit_b)
                m.hp -= 1
                # knockback a bit
                m.vy += 0.35
                m.vx += random.uniform(-0.45, 0.45)
                if m.hp <= 0:
                    # score by size
                    pts = 1 if m.typ == 1 else (2 if m.typ == 2 else 3)
                    score += pts
                    add_popup(f"+{pts} SCORE", mr.centerx, mr.centery, (200,210,255))
                    meteors.remove(m)

        # player hits meteor (with invincible)
        if now >= invincible_until:
            pr = player
            for m in meteors[:]:
                if pr.colliderect(m.rect()):
                    lives -= 1
                    invincible_until = now + 2000
                    add_popup("-1 HP", pr.centerx, pr.centery-30, RED)
                    # bounce meteor away
                    m.vy += 1.2
                    m.vx += random.uniform(-2.2, 2.2)
                    break

        # popups
        for p in popups[:]:
            p["y"] -= 1.6
            p["life"] -= 1
            blit_center(txt(p["t"], MID, p["col"]), int(p["x"]), int(p["y"]))
            if p["life"] <= 0:
                popups.remove(p)

        # draw objects
        for m in meteors:
            m.draw()

        for c in coins:
            draw_rot_coin(c["rect"], c["gold"], c["angle"])

        for b in bullets:
            pygame.draw.rect(screen, GOLD_MAIN, b, border_radius=6)

        draw_player(now)

        # HUD
        draw_game_hud(now, left_ms)

        # end conditions
        if lives <= 0 or left_ms <= 0:
            # save best score for this level
            cur_best = int(best_scores.get(str(level), 0))
            if score > cur_best:
                best_scores[str(level)] = int(score)
            bank_coins += run_coins
            save_game()
            state = STATE_MENU

        # win condition by coins target
        if run_coins >= coin_target_for_level(level):
            cur_best = int(best_scores.get(str(level), 0))
            if score > cur_best:
                best_scores[str(level)] = int(score)
            bank_coins += run_coins
            add_xp(10 + (level-1)*5)
            save_game()
            state = STATE_PASSED

    elif state == STATE_PAUSE:
        # pause overlay ON TOP of game frame (draw last frame is okay)
        draw_pause_overlay()

    if state == STATE_PASSED:
        overlay = pygame.Surface((W,H), pygame.SRCALPHA)
        overlay.fill((0,0,0, 185))
        screen.blit(overlay, (0,0))
        blit_center(txt("LEVEL PASSED!", BIG, WHITE), W//2, int(H*0.38))
        blit_center(txt("+XP added!", MID, GREEN), W//2, int(H*0.48))
        blit_center(txt("Tap to continue", FONT, GRAY), W//2, int(H*0.60))

    pygame.display.flip()

save_game()
pygame.quit()
sys.exit() 
