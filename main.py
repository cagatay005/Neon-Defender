import pygame
import random
import math
import sys
import json
import os
import time
from achievements import AchievementManager

def resource_path(relative_path):
    """ PyInstaller ile paketlenince geçici klasör yolunu, normalde ise mevcut yolu döner """
    try:
        # PyInstaller geçici klasörü
        base_path = sys._MEIPASS
    except Exception:
        # Normal çalışma yolu
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# --- GÜVENLİK KONTROLÜ ---
DSP_AVAILABLE = False
try:
    import numpy as np
    DSP_AVAILABLE = True
except ImportError:
    print("UYARI: numpy kütüphanesi yok. Sesler kapalı.")

# --- AYARLAR ---
WIDTH = 800
HEIGHT = 600
FPS = 60

# Renkler
BLACK = (5, 5, 10)
WHITE = (255, 255, 255)
RED = (255, 50, 50)
GREEN = (50, 255, 50)
BLUE = (50, 150, 255)
YELLOW = (255, 220, 50)
PURPLE = (180, 50, 255)
ORANGE = (255, 140, 0)
GRAY = (80, 80, 90)
CYAN = (0, 255, 255)
DARK_BLUE = (20, 20, 40)
DARK_RED = (100, 20, 20)
SHIELD_BLUE = (0, 191, 255)
ULTI_COLOR = (255, 165, 0)
ELECTRIC_CYAN = (150, 255, 255)
GRID_COLOR = (40, 0, 60)
GRID_LINE_COLOR = (100, 0, 150)
HOVER_GRAY = (120, 120, 140) 

# Varsayılan Kontroller
DEFAULT_KEYS = {
    "UP": pygame.K_w,
    "DOWN": pygame.K_s,
    "LEFT": pygame.K_a,
    "RIGHT": pygame.K_d,
    "SHOOT": pygame.K_SPACE,
    "ULTI": pygame.K_e,
    "DASH": pygame.K_LSHIFT,
    "SHOP": pygame.K_i,
    "MENU": pygame.K_ESCAPE
}

# --- YARDIMCI FONKSİYONLAR ---
def draw_lightning_bolt(surface, p1, p2):
    deviation = random.randint(-30, 30)
    mid1 = ((p1[0]*2+p2[0])/3 + deviation, (p1[1]*2+p2[1])/3 + deviation)
    deviation = random.randint(-30, 30)
    mid2 = ((p1[0]+p2[0]*2)/3 + deviation, (p1[1]+p2[1]*2)/3 + deviation)
    points = [p1, mid1, mid2, p2]
    pygame.draw.lines(surface, ELECTRIC_CYAN, False, points, 4)
    pygame.draw.lines(surface, WHITE, False, points, 2)

# --- SES MOTORU ---
class SoundEngine:
    def __init__(self):
        self.enabled = DSP_AVAILABLE
        self.volume = 1.0
        self.sounds = {}
        
        if self.enabled:
            try:
                if pygame.mixer.get_init() is None:
                    pygame.mixer.pre_init(44100, -16, 2, 512)
                    pygame.mixer.init()
            except Exception as e:
                print(f"Ses Hatası: {e}")
                self.enabled = False
        
        if self.enabled:
            self.generate_sounds()

    def set_master_volume(self, vol):
        self.volume = max(0.0, min(1.0, vol))
        for s in self.sounds.values():
            s.set_volume(self.volume)

    def _apply_channels(self, audio_array):
        try:
            mixer_settings = pygame.mixer.get_init()
            if not mixer_settings: return audio_array
            channels = mixer_settings[2]
            if channels == 2 and audio_array.ndim == 1:
                return np.column_stack((audio_array, audio_array))
        except: pass
        return audio_array

    def generate_sounds(self):
        self.sounds["laser"] = self._make_sound("square", 400, 0.1, slide=-150)
        self.sounds["sniper"] = self._make_sound("sawtooth", 150, 0.3, slide=-50)
        self.sounds["enemy_shoot"] = self._make_sound("sine", 600, 0.1, slide=-200)
        self.sounds["explosion"] = self._make_noise(0.4)
        self.sounds["coin"] = self._make_coin_sound()
        self.sounds["select"] = self._make_sound("sine", 880, 0.1)
        self.sounds["hover"] = self._make_sound("sine", 440, 0.05)
        self.sounds["powerup"] = self._make_powerup()
        self.sounds["shield_get"] = self._make_sound("sine", 500, 0.2, slide=200)
        self.sounds["boss_hit"] = self._make_sound("sawtooth", 80, 0.05)
        self.sounds["dash"] = self._make_noise(0.2)
        self.sounds["shield_hit"] = self._make_sound("sine", 300, 0.1, slide=50)
        self.sounds["combo"] = self._make_sound("square", 600, 0.15, slide=200)
        self.sounds["ulti"] = self._make_sound("sawtooth", 100, 0.8, slide=400)
        self.sounds["drone"] = self._make_sound("sine", 800, 0.05)
        self.sounds["missile"] = self._make_sound("sawtooth", 200, 0.3, slide=100)
        self.sounds["crit"] = self._make_sound("square", 800, 0.1, slide=100)
        self.sounds["error"] = self._make_sound("sawtooth", 150, 0.2, slide=-20)
        
        self.intro_notes = [
            self._make_sound("square", 261.63, 0.2),
            self._make_sound("square", 329.63, 0.2),
            self._make_sound("square", 392.00, 0.2),
            self._make_sound("square", 523.25, 0.4),
        ]
        self.set_master_volume(self.volume)

    def _make_sound(self, wave_type, freq, duration, slide=0):
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        freqs = np.linspace(freq, freq + slide, n_samples)
        phase = 2 * np.pi * np.cumsum(freqs) / sample_rate
        if wave_type == "sine": waveform = np.sin(phase)
        elif wave_type == "square": waveform = np.sign(np.sin(phase))
        elif wave_type == "sawtooth": waveform = 2 * (phase / (2 * np.pi) - np.floor(0.5 + phase / (2 * np.pi)))
        envelope = np.linspace(1, 0, n_samples)
        audio = (waveform * envelope * 32767 * 0.3).astype(np.int16)
        audio = self._apply_channels(audio)
        return pygame.sndarray.make_sound(audio)

    def _make_noise(self, duration):
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        noise = np.random.uniform(-1, 1, n_samples)
        decay = np.exp(-np.linspace(0, 5, n_samples))
        audio = (noise * decay * 32767 * 0.5).astype(np.int16)
        audio = self._apply_channels(audio)
        return pygame.sndarray.make_sound(audio)

    def _make_powerup(self):
        sample_rate = 44100
        n_samples = int(sample_rate * 0.4)
        t = np.linspace(0, 0.4, n_samples, False)
        waveform = np.sin(2 * np.pi * 600 * t) + np.sin(2 * np.pi * 1200 * t)
        envelope = np.linspace(1, 0, n_samples)
        audio = (waveform * envelope * 32767 * 0.3).astype(np.int16)
        audio = self._apply_channels(audio)
        return pygame.sndarray.make_sound(audio)

    def _make_coin_sound(self):
        sample_rate = 44100
        n_samples = int(sample_rate * 0.2)
        t = np.linspace(0, 0.2, n_samples, False)
        waveform = np.sin(2 * np.pi * 1500 * t)
        envelope = np.linspace(1, 0, n_samples)
        audio = (waveform * envelope * 32767 * 0.2).astype(np.int16)
        audio = self._apply_channels(audio)
        return pygame.sndarray.make_sound(audio)

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()
            
    def play_intro(self, step):
        if self.enabled and 0 <= step < len(self.intro_notes):
            self.intro_notes[step].set_volume(self.volume)
            self.intro_notes[step].play()

# --- GÖRSEL EFEKTLER ---
class CyberGrid:
    def __init__(self):
        self.offset_y = 0
        self.speed = 2
        self.grid_size = 60

    def update(self, speed_mult=1.0):
        self.offset_y = (self.offset_y + self.speed * speed_mult) % self.grid_size

    def draw(self, surface, sx=0, sy=0):
        surface.fill(GRID_COLOR)
        for x in range(0, WIDTH, self.grid_size):
            pygame.draw.line(surface, GRID_LINE_COLOR, (x + sx, 0), (x + sx, HEIGHT), 1)
        for y in range(int(self.offset_y), HEIGHT, self.grid_size):
            pygame.draw.line(surface, GRID_LINE_COLOR, (0, y + sy), (WIDTH, y + sy), 1)

class Star:
    def __init__(self):
        self.reset()
        self.y = random.randint(0, HEIGHT) 

    def reset(self):
        self.x = random.randint(0, WIDTH)
        self.y = 0
        self.speed = random.uniform(3.0, 8.0)
        self.size = random.randint(1, 2)
        self.brightness = random.randint(100, 255)

    def update(self, warp_speed=False):
        current_speed = self.speed * (5 if warp_speed else 1)
        self.y += current_speed
        if self.y > HEIGHT:
            self.reset()
            
    def draw(self, surface, sx=0, sy=0): 
        color = (self.brightness, self.brightness, self.brightness)
        
        pygame.draw.circle(surface, color, (int(self.x + sx), int(self.y + sy)), self.size)

class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, color, speed_mult=1.0):
        super().__init__()
        self.image = pygame.Surface((random.randint(4, 8), random.randint(4, 8)))
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(x, y))
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 6) * speed_mult
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(30, 60)

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.life -= 1
        if self.life <= 0:
            self.kill()
        elif self.life < 15:
            self.image = pygame.transform.scale(self.image, (2, 2))

class FloatingText(pygame.sprite.Sprite):
    def __init__(self, text, x, y, color, size=20, life=40, vy=-2):
        super().__init__()
        font = pygame.font.SysFont("Verdana", size, bold=True)
        self.image = font.render(text, True, color)
        self.rect = self.image.get_rect(center=(x, y))
        self.vy = vy
        self.life = life

    def update(self):
        self.rect.y += self.vy
        self.life -= 1
        if self.life <= 0:
            self.kill()

# --- BULLET VE FÜZE SİSTEMİ ---
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, damage, color, vx=0, vy=-10, size=(6, 15), is_missile=False, target=None):
        super().__init__()
        self.image = pygame.Surface(size)
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.fx = float(x)
        self.fy = float(y)
        self.is_missile = is_missile
        self.target = target
        
        if is_missile:
             self.image = pygame.Surface((10, 10))
             pygame.draw.circle(self.image, RED, (5, 5), 5)
             self.image.set_colorkey(BLACK)

    def update(self):
        if self.is_missile and self.target and self.target.alive():
            dx = self.target.rect.centerx - self.fx
            dy = self.target.rect.centery - self.fy
            dist = math.hypot(dx, dy)
            if dist > 0:
                desired_vx = (dx / dist) * 8
                desired_vy = (dy / dist) * 8
                self.vx += (desired_vx - self.vx) * 0.1
                self.vy += (desired_vy - self.vy) * 0.1

        self.fx += self.vx
        self.fy += self.vy
        self.rect.centerx = int(self.fx)
        self.rect.centery = int(self.fy)
        
        margin = 50
        if self.rect.bottom < -margin or self.rect.top > HEIGHT+margin or self.rect.left < -margin or self.rect.right > WIDTH+margin:
            self.kill()

# --- OYUN NESNELERİ ---
class Player(pygame.sprite.Sprite):
    def __init__(self, type_idx, stats, key_bindings):
        super().__init__()
        self.type = type_idx
        self.keys = key_bindings
        self.image = pygame.Surface((50, 50), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.rect.centerx = WIDTH // 2
        self.rect.bottom = HEIGHT - 20
        self.visible = True
        
        # Temel Statlar
        if self.type == 0: # Interceptor
            self.speed = 6; self.max_hp = 100; self.dmg = 15; self.color = BLUE; self.cooldown_base = 15
        elif self.type == 1: # Destroyer
            self.speed = 3; self.max_hp = 300; self.dmg = 25; self.color = PURPLE; self.cooldown_base = 20
        elif self.type == 2: # Speeder
            self.speed = 10; self.max_hp = 50; self.dmg = 10; self.color = YELLOW; self.cooldown_base = 10
        elif self.type == 3: # Sniper
            self.speed = 5; self.max_hp = 80; self.dmg = 100; self.color = GREEN; self.cooldown_base = 45
            
        # Upgrade Uygula
        self.max_hp += stats['upgrade_hp']
        self.dmg += stats['upgrade_dmg']
        self.speed += stats.get('upgrade_speed', 0)
        self.cooldown_limit = max(5, self.cooldown_base - stats.get('upgrade_firerate', 0))
        
        self.double_shot = stats.get('double_shot', False) and stats.get('active_double', True)
        self.has_drone = stats.get('has_drone', False) and stats.get('active_drone', True)
        self.has_missiles = stats.get('has_missiles', False) and stats.get('active_missile', True)
        
        self.hp = self.max_hp
        self.cooldown = 0
        self.drone_angle = 0
        self.drone_cooldown = 0
        self.missile_cooldown = 0
        
        # Sistemler
        self.ulti_power = 0
        self.max_ulti = 100
        self.shield_active = False
        self.shield_timer = 0
        self.max_shield_time = 7 * FPS 
        
        # Hareket
        self.dash_cooldown = 0
        self.is_dashing = False
        self.dash_timer = 0
        self.base_speed = self.speed 
        self.trail = [] 
        
        self.draw_ship()

    def activate_shield(self):
        self.shield_active = True
        self.shield_timer = self.max_shield_time
        self.draw_ship()
        
    def add_ulti(self, amount):
        self.ulti_power = min(self.max_ulti, self.ulti_power + amount)

    def draw_ship(self):
        self.image.fill((0,0,0,0)) # Temizle
        color = WHITE if self.is_dashing else self.color 
        
        if self.type == 0:
            pygame.draw.polygon(self.image, color, [(25, 0), (50, 40), (25, 30), (0, 40)])
            pygame.draw.rect(self.image, CYAN, (22, 15, 6, 10))
        elif self.type == 1:
            pygame.draw.rect(self.image, color, (5, 10, 40, 30))
            pygame.draw.rect(self.image, GRAY, (0, 15, 5, 20))
            pygame.draw.rect(self.image, GRAY, (45, 15, 5, 20))
        elif self.type == 2:
            pygame.draw.polygon(self.image, color, [(25, 0), (35, 45), (25, 35), (15, 45)])
        elif self.type == 3:
            pygame.draw.polygon(self.image, color, [(25, 5), (40, 40), (10, 40)])
            pygame.draw.rect(self.image, BLACK, (23, 0, 4, 20))
            
        if self.shield_active:
            if self.shield_timer > 90 or (self.shield_timer // 10) % 2 == 0:
                pygame.draw.circle(self.image, SHIELD_BLUE, (25, 25), 28, 2)
                pygame.draw.circle(self.image, (135, 206, 250), (25, 25), 26, 1)
            
    def update(self):
        if not self.visible: return
        pressed = pygame.key.get_pressed()
        
        self.trail.append((self.rect.centerx, self.rect.bottom - 5))
        if len(self.trail) > 10: self.trail.pop(0)

        if self.shield_active:
            self.shield_timer -= 1
            if self.shield_timer <= 0:
                self.shield_active = False
                self.draw_ship()
            elif self.shield_timer < 90: 
                self.draw_ship()

        # DASH CONTROL
        if pressed[self.keys["DASH"]] and self.dash_cooldown == 0:
            self.is_dashing = True
            self.dash_timer = 10 
            self.dash_cooldown = 120 
            self.speed = self.base_speed * 3
        
        if self.is_dashing:
            self.dash_timer -= 1
            self.draw_ship() 
            if self.dash_timer <= 0:
                self.is_dashing = False
                self.speed = self.base_speed
                self.draw_ship()
        if self.dash_cooldown > 0: self.dash_cooldown -= 1
            
        # MOVEMENT CONTROLS
        if pressed[self.keys["LEFT"]] and self.rect.left > 0: self.rect.x -= self.speed
        if pressed[self.keys["RIGHT"]] and self.rect.right < WIDTH: self.rect.x += self.speed
        if pressed[self.keys["UP"]] and self.rect.top > 0: self.rect.y -= self.speed
        if pressed[self.keys["DOWN"]] and self.rect.bottom < HEIGHT: self.rect.y += self.speed
            
        if self.cooldown > 0: self.cooldown -= 1
        
        if self.has_drone:
            self.drone_angle = (self.drone_angle + 5) % 360
            if self.drone_cooldown > 0: self.drone_cooldown -= 1
            
        if self.has_missiles:
            if self.missile_cooldown > 0: self.missile_cooldown -= 1

    def take_damage(self, amount):
        if self.is_dashing: return False, False, False 
        if self.shield_active: return True, False, True 
        self.hp -= amount
        return True, True, False 

    def shoot(self):
        if self.cooldown > 0 or not self.visible: return []
        self.cooldown = self.cooldown_limit
        bullets = []
        
        if self.type == 3: # Sniper
            bullets.append(Bullet(self.rect.centerx, self.rect.top, self.dmg, self.color, vy=-20, size=(4, 30)))
            return bullets

        if self.double_shot:
            bullets.append(Bullet(self.rect.centerx - 15, self.rect.top, self.dmg, self.color))
            bullets.append(Bullet(self.rect.centerx + 15, self.rect.top, self.dmg, self.color))
        else:
            bullets.append(Bullet(self.rect.centerx, self.rect.top, self.dmg, self.color))
        return bullets

class Enemy(pygame.sprite.Sprite):
    def __init__(self, level_mult=1.0):
        super().__init__()
        self.type = random.choices(["normal", "fast", "tank"], weights=[60, 30, 10])[0]
        self.image = pygame.Surface((40, 40), pygame.SRCALPHA)
        self.shoot_timer = random.randint(0, 60)
        
        if self.type == "normal":
            pygame.draw.polygon(self.image, RED, [(0, 0), (40, 0), (20, 40)])
            self.speed = random.randint(2, 5) + (level_mult * 0.5)
            self.hp = 30 * level_mult
            self.score_val = 10
            self.color = RED
            self.can_shoot = False
        elif self.type == "fast": 
            pygame.draw.polygon(self.image, ORANGE, [(10, 0), (30, 0), (20, 40)])
            self.speed = random.randint(3, 7) + (level_mult * 0.5)
            self.hp = 15 * level_mult
            self.score_val = 20
            self.color = ORANGE
            self.can_shoot = True 
        else:
            pygame.draw.rect(self.image, GREEN, (0, 0, 40, 40))
            self.speed = 1 + (level_mult * 0.2)
            self.hp = 100 * level_mult
            self.score_val = 50
            self.color = GREEN
            self.can_shoot = False

        self.rect = self.image.get_rect(x=random.randint(0, WIDTH - 40), y=random.randint(-100, -50))
        
    def update(self):
        self.rect.y += self.speed
        if self.rect.top > HEIGHT: self.kill()
        
        if self.can_shoot:
            self.shoot_timer += 1
            if self.shoot_timer > 120: 
                self.shoot_timer = 0
                return Bullet(self.rect.centerx, self.rect.bottom, 10, ORANGE, vx=0, vy=8) 
        return None

class Boss(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((240, 150), pygame.SRCALPHA)
        self.rect = self.image.get_rect(centerx=WIDTH//2, top=-200)
        
        # --- Statlar ---
        self.max_hp = 3000
        self.hp = self.max_hp
        self.speed = 2
        
        # --- Durum Yönetimi ---
        self.entered = False
        self.phase = 1 # Phase 1: %50 HP üstü, Phase 2: %50 HP altı (Öfke Modu)
        self.state = "IDLE" # IDLE, MOVING, ATTACKING
        self.move_dir = 1
        
        # --- Saldırı Zamanlayıcıları ---
        self.last_shot = 0
        self.pattern_timer = 0
        self.current_pattern = 0
        
        # --- Desen Değişkenleri ---
        self.spiral_angle = 0      # Spiral saldırı için açı
        self.flower_offset = 0     # Çiçek deseni için ofset
        
        self.draw_boss()

    def draw_boss(self):
        # Phase 2'de renkler daha koyu ve agresif olur
        is_enraged = self.phase == 2
        main_color = (180, 0, 0) if is_enraged else (100, 0, 0)
        core_color = (255, 50, 0) if is_enraged else (255, 0, 0)
        
        self.image.fill((0,0,0,0))
        # Gövde (Agresif üçgen yapı)
        pygame.draw.polygon(self.image, main_color, [(0, 0), (240, 0), (180, 140), (60, 140)])
        pygame.draw.polygon(self.image, (255, 255, 255), [(0, 0), (240, 0), (180, 140), (60, 140)], 3)
        
        # Çekirdek (Canı azaldıkça titrek çizilebilir, şimdilik sabit)
        pygame.draw.circle(self.image, core_color, (120, 60), 40)
        pygame.draw.circle(self.image, (255, 200, 0), (120, 60), 30 if is_enraged else 10) # Göz bebeği büyür
        
        # Silah Yuvaları
        pygame.draw.rect(self.image, (50, 50, 50), (10, 80, 30, 60))
        pygame.draw.rect(self.image, (50, 50, 50), (200, 80, 30, 60))

    def update(self, player_rect=None): # Player konumunu bilmesi için parametre ekledik
        now = pygame.time.get_ticks()
        
        # 1. Giriş Animasyonu
        if not self.entered:
            self.rect.y += 2
            if self.rect.top >= 50:
                self.entered = True
                self.last_shot = now
            return []

        # 2. Phase Kontrolü
        if self.hp < self.max_hp * 0.5 and self.phase == 1:
            self.phase = 2
            self.draw_boss() # Görünümü güncelle
            
        # 3. Hareket Mantığı (Sinüs dalgası şeklinde süzülme)
        self.rect.x += self.speed * self.move_dir
        # Hafif aşağı yukarı süzülme (Floating effect)
        self.rect.y = 50 + math.sin(now * 0.002) * 20 
        
        if self.rect.right > WIDTH - 20 or self.rect.left < 20:
            self.move_dir *= -1

        # 4. Saldırı Mantığı (Pattern Seçici)
        bullets = []
        
        # Phase 1: Daha sakin saldırılar (1 saniyede bir)
        # Phase 2: Çılgın saldırılar (0.6 saniyede bir)
        cooldown = 1000 if self.phase == 1 else 600
        
        if now - self.last_shot > cooldown:
            self.last_shot = now
            # Rastgele bir saldırı deseni seç
            pattern = random.choices(["basic", "spiral", "flower", "aimed"], weights=[40, 30, 20, 10] if self.phase == 1 else [20, 30, 30, 20])[0]
            
            if pattern == "basic":
                bullets.extend(self.pattern_shotgun())
            elif pattern == "spiral":
                bullets.extend(self.pattern_spiral(is_double=(self.phase==2)))
            elif pattern == "flower":
                bullets.extend(self.pattern_flower())
            elif pattern == "aimed":
                bullets.extend(self.pattern_aimed(player_rect))
                
        return bullets

    # --- SALDIRI DESENLERİ (MATH POWER) ---
    
    def pattern_shotgun(self):
        """Klasik saçmalı tüfek ateşi"""
        bullets = []
        # 5 mermi, -30 ile +30 derece arasına yayılır
        for angle in range(-30, 31, 15): 
            rad = math.radians(angle + 90) # +90 çünkü 0 derece sağa bakar, aşağı (90) olacak
            vx = math.cos(rad) * 7
            vy = math.sin(rad) * 7
            b = Bullet(self.rect.centerx, self.rect.bottom, 15, ORANGE, vx, vy, (8, 20))
            bullets.append(b)
        return bullets

    def pattern_spiral(self, is_double=False):
        """Dönen mermiler (DNA sarmalı gibi)"""
        bullets = []
        # Tek kol veya Çift kol (Phase 2)
        arms = 2 if is_double else 1
        
        for i in range(arms):
            # Açı sürekli artacak (self.spiral_angle)
            angle_deg = self.spiral_angle + (i * 180) 
            rad = math.radians(angle_deg)
            
            vx = math.cos(rad) * 6
            vy = math.sin(rad) * 6
            
            color = RED if is_double else ORANGE
            b = Bullet(self.rect.centerx, self.rect.centery, 10, color, vx, vy, (10, 10))
            bullets.append(b)
            
        self.spiral_angle = (self.spiral_angle + 15) % 360
        return bullets

    def pattern_flower(self):
        """360 derece çiçek açma efekti"""
        bullets = []
        num_bullets = 12 if self.phase == 1 else 24
        
        for i in range(num_bullets):
            angle_deg = (360 / num_bullets) * i + self.flower_offset
            rad = math.radians(angle_deg)
            
            vx = math.cos(rad) * 5
            vy = math.sin(rad) * 5
            
            b = Bullet(self.rect.centerx, self.rect.centery, 12, (255, 0, 255), vx, vy, (12, 12))
            bullets.append(b)
            
        self.flower_offset = (self.flower_offset + 10) % 360 # Her seferinde biraz döndür
        return bullets

    def pattern_aimed(self, player_rect):
        """Doğrudan oyuncunun kafasına nişan alma"""
        if not player_rect: return self.pattern_shotgun() # Oyuncu yoksa rastgele sık
        
        dx = player_rect.centerx - self.rect.centerx
        dy = player_rect.centery - self.rect.centery
        angle_rad = math.atan2(dy, dx) # Hedef açısını bulur
        
        bullets = []
        # Hızlı, tek bir keskin nişancı mermisi
        vx = math.cos(angle_rad) * 12
        vy = math.sin(angle_rad) * 12
        
        b = Bullet(self.rect.centerx, self.rect.centery, 25, (255, 255, 255), vx, vy, (15, 15))
        bullets.append(b)
        return bullets

    def draw_health(self, surface):
        pygame.draw.rect(surface, BLACK, (WIDTH//2 - 250, 10, 500, 25))
        ratio = max(0, self.hp / self.max_hp)
        col = (255, 50, 0) if self.phase == 2 else (200, 0, 0)
        pygame.draw.rect(surface, col, (WIDTH//2 - 250, 10, 500 * ratio, 25))
        pygame.draw.rect(surface, (255, 255, 255), (WIDTH//2 - 250, 10, 500, 25), 3)

class PowerUp(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.type = random.choices(["health", "shield"], weights=[70, 30])[0]
        self.image = pygame.Surface((24, 24), pygame.SRCALPHA)
        
        if self.type == "health":
            pygame.draw.circle(self.image, GREEN, (12, 12), 12)
            pygame.draw.line(self.image, WHITE, (12, 4), (12, 20), 3)
            pygame.draw.line(self.image, WHITE, (4, 12), (20, 12), 3)
        else: 
            pygame.draw.circle(self.image, SHIELD_BLUE, (12, 12), 12)
            pygame.draw.circle(self.image, WHITE, (12, 12), 8, 2)
            
        self.rect = self.image.get_rect(center=(x, y))
        
    def update(self):
        self.rect.y += 3
        if self.rect.top > HEIGHT: self.kill()

# --- UI ELEMENTS ---
class Button:
    def __init__(self, text, x, y, w, h, color, hover_color, action_code, cost=0):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.base_color = color
        self.hover_color = hover_color
        self.action_code = action_code
        self.cost = cost
        self.selected = False
        self.disabled = False
        self.dynamic_text = False

    def draw(self, screen, font, money_available=99999):
        if self.disabled: current_color = GREEN
        elif self.cost > money_available: current_color = DARK_RED
        elif self.selected: current_color = self.hover_color
        else: current_color = self.base_color

        pygame.draw.rect(screen, current_color, self.rect, border_radius=12)
        border_width = 4 if self.selected else 2
        border_color = WHITE if self.selected else GRAY
        pygame.draw.rect(screen, border_color, self.rect, border_width, border_radius=12)
        
        text_surf = font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

# --- ANA OYUN MOTORU ---
class Game:
    def __init__(self):
        pygame.init()
        # --- EKRAN AYARI ---
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("NEON DEFENDER")
        try:
            icon_path = resource_path("space.ico")
            program_icon = pygame.image.load(icon_path)
            pygame.display.set_icon(program_icon)
        except Exception as e:
            print(f"İkon yüklenemedi: {e}")
        self.clock = pygame.time.Clock()
        self.sound = SoundEngine()
        
        self.achievement_manager = AchievementManager()
        
        self.font_title = pygame.font.SysFont("Verdana", 70, bold=True)
        self.font_large = pygame.font.SysFont("Verdana", 28, bold=True)
        self.font_small = pygame.font.SysFont("Verdana", 18)
        
        self.state = "INTRO"
        self.intro_timer = 0
        self.intro_step = 0
        self.stars = [Star() for _ in range(40)] 
        self.grid = CyberGrid() 
        
        self.player_type = 0
        self.shake_time = 0
        self.paused = False
        
        self.money = 0
        self.stats = {
            'upgrade_hp': 0, 
            'upgrade_dmg': 0, 
            'upgrade_speed': 0,
            'upgrade_firerate': 0,
            'double_shot': False,
            'has_drone': False,
            'has_missiles': False 
        }
        self.keys = DEFAULT_KEYS.copy()
        self.volume_level = 1.0 
        self.current_slot = 1
        self.slot_operation = "LOAD"
        self.pending_slot = None
        
        self.slot_buttons = []
        self.control_buttons = []
        self.binding_key = None 

        # --- BUTONLARI OLUŞTURMA ---
        # Ekran boyutu değişince butonlar kaymasın diye hepsi fonksiyonda toplandı
        self.create_all_buttons()

        self.selected_btn_index = 0 
        self.reset_game()
    
    def create_all_buttons(self):
        """Ekran boyutu değiştiğinde butonları yeniden hizalar."""
        btn_w = 280
        btn_h = 50
        # WIDTH ve HEIGHT global değişkenler olduğu için o anki pencere boyutunu alır
        x_pos = WIDTH // 2 - btn_w // 2  
        center_y = HEIGHT // 2
        
        # --- MENÜ BUTONLARI ---
        self.menu_buttons = [
            Button("START GAME", x_pos, center_y - 50, btn_w, btn_h, GREEN, (100, 255, 100), "GOTO_SLOTS"),
            Button("WEAPON STORE", x_pos, center_y + 20, btn_w, btn_h, PURPLE, YELLOW, "STORE"),
            Button("SETTINGS", x_pos, center_y + 90, btn_w, btn_h, GRAY, HOVER_GRAY, "SETTINGS"), 
            Button("QUIT GAME", x_pos, center_y + 160, btn_w, btn_h, RED, ORANGE, "QUIT")
        ]
        
        # --- SETTINGS BUTONLARI ---
        self.settings_buttons = [
            Button("AUDIO SETTINGS", x_pos, 250, btn_w, btn_h, BLUE, CYAN, "AUDIO"),
            Button("CONTROLS", x_pos, 330, btn_w, btn_h, PURPLE, YELLOW, "CONTROLS"),
            Button("BACK", x_pos, 450, btn_w, btn_h, RED, ORANGE, "BACK_MENU")
        ]

        # --- AUDIO BUTONLARI ---
        self.audio_buttons = [
             Button("BACK", x_pos, 450, btn_w, btn_h, RED, ORANGE, "BACK_SETTINGS")
        ]
        
        # --- MARKET BUTONLARI ---
        sw = 280; sh = 50
        col1_x = WIDTH // 2 - sw - 20 # Dinamik Konum
        col2_x = WIDTH // 2 + 20      # Dinamik Konum
        start_y = 150; gap = 60
        
        self.store_buttons = [
            Button("DMG UP (+10) - $200", col1_x, start_y, sw, sh, BLUE, CYAN, "BUY_DMG", 200),
            Button("FIRE RATE - $300", col2_x, start_y, sw, sh, BLUE, CYAN, "BUY_RATE", 300),
            Button("HP UP (+50) - $150", col1_x, start_y + gap, sw, sh, BLUE, CYAN, "BUY_HP", 150),
            Button("DOUBLE SHOT - $500", col2_x, start_y + gap, sw, sh, PURPLE, GREEN, "BUY_DOUBLE", 500),
            Button("SPEED UP - $150", col1_x, start_y + gap*2, sw, sh, BLUE, CYAN, "BUY_SPD", 150),
            Button("ATTACK DRONE - $1000", col2_x, start_y + gap*2, sw, sh, PURPLE, GREEN, "BUY_DRONE", 1000),
            Button("HOMING MISSILES - $1500", col1_x, start_y + gap*3, sw, sh, PURPLE, RED, "BUY_MISSILE", 1500),
            Button("BACK", WIDTH//2 - sw//2, HEIGHT - 80, sw, sh, RED, ORANGE, "BACK")
        ]
        
        # Diğer dinamik butonlar
        self.create_control_buttons()
        if self.state == "SLOT_MENU": self.create_slot_buttons()
            
        self.btn_select_back = Button("BACK", WIDTH//2 - 100, HEIGHT - 80, 200, 40, RED, ORANGE, "BACK_TO_SLOTS")

    def create_control_buttons(self):
        self.control_buttons = []
        y = 120
        left_col = True
        x_left = 100
        x_right = 450
        
        # Dictionary sırası Python 3.7+ itibariyle eklendiği sıradadır (Default Keys sırası)
        for action, key_code in self.keys.items():
            key_name = pygame.key.name(key_code).upper()
            txt = f"{action}: {key_name}"
            x = x_left if left_col else x_right
            
            btn = Button(txt, x, y, 300, 40, GRAY, CYAN, f"BIND_{action}")
            btn.dynamic_text = True 
            self.control_buttons.append(btn)
            
            if not left_col: y += 60
            left_col = not left_col
            
        self.control_buttons.append(Button("BACK", WIDTH//2 - 140, 520, 280, 50, RED, ORANGE, "BACK_SETTINGS"))

    def get_save_path(self, filename):
        """Kayıt dosyasını AppData içine gizler."""
        app_name = "NeonDefender"
        if os.name == 'nt': # Windows
            base_dir = os.environ.get('APPDATA') or os.path.expanduser("~")
        else: # Mac/Linux
            base_dir = os.path.join(os.path.expanduser("~"), ".local", "share")
            
        save_dir = os.path.join(base_dir, app_name)
        if not os.path.exists(save_dir):
            try: os.makedirs(save_dir)
            except: return filename # Hata olursa oyun klasörüne yaz
        return os.path.join(save_dir, filename)

    def create_slot_buttons(self):
        """Slot menüsü: Metinler çakışmasın diye hepsi info_text içine alındı."""
        self.slot_buttons = []
        
        card_w = 220
        card_h = 240
        gap = 40
        start_x = 30
        y_pos = 110

        self.slot_menu_title = "SAVE YOUR GAME" if self.slot_operation == "SAVE" else "SELECT SAVE SLOT"

        # --- 1. KISIM: MANUEL SLOTLAR ---
        for i in range(1, 4): 
            filename = self.get_save_path(f"save_{i}.json")
            x = start_x + (i-1) * (card_w + gap)
            
            # Değişkenleri hazırla
            text = "" # <-- KRİTİK: Butonun kendi yazısı silinir
            
            if os.path.exists(filename):
                try:
                    with open(filename, "r") as f:
                        data = json.load(f)
                        # Başlığı (SLOT X) buraya eklenir
                        info = f"SLOT {i}\nScore: {data.get('score', 0)}\nCash: ${data.get('money', 0)}"
                        color = (20, 20, 60)
                except: info = f"SLOT {i}\nCorrupted"; color = RED
                
                if self.slot_operation == "LOAD":
                    del_btn = Button("DELETE", x + card_w//2 - 70, y_pos + card_h + 5, 140, 40, RED, ORANGE, f"DEL_{i}")
                    self.slot_buttons.append(del_btn)
            else:
                # Boş slot bilgisini de buraya alınır
                info = "EMPTY\nNew Game"
                color = (20, 20, 20)
            
            slot_btn = Button(text, x, y_pos, card_w, card_h, color, ELECTRIC_CYAN, f"SLOT_{i}")
            slot_btn.info_text = info # Tüm yazı burada
            self.slot_buttons.append(slot_btn)

        # --- 2. KISIM: AUTO-SAVE KARTI ---
        del_button_space = 45 
        auto_y = y_pos + card_h + del_button_space + 15
        auto_w = card_w; auto_h = 110; auto_x = WIDTH // 2 - auto_w // 2
        
        auto_filename = self.get_save_path("autosave.json")
        atext = "" 
        
        if os.path.exists(auto_filename):
            try:
                with open(auto_filename, "r") as f:
                    adata = json.load(f)
                    ainfo = f"AUTO-SAVE\nScore: {adata.get('score', 0)}\nCash: ${adata.get('money', 0)}"
            except: ainfo = "AUTO-SAVE\nCorrupted"
        else:
            ainfo = "AUTO-SAVE\nEmpty"

        if self.slot_operation == "SAVE":
            acolor = (30, 30, 30); ainfo = "AUTO-SAVE\n(System Only)" 
        else:
            acolor = (60, 30, 0)

        auto_btn = Button(atext, auto_x, auto_y, auto_w, auto_h, acolor, ORANGE, "SLOT_AUTO")
        auto_btn.info_text = ainfo
        self.slot_buttons.append(auto_btn)

        # --- 3. KISIM: BACK BUTONU ---
        back_y = auto_y + auto_h + 20
        if back_y > HEIGHT - 55: back_y = HEIGHT - 55
        self.slot_buttons.append(Button("BACK TO MENU", WIDTH//2 - 130, back_y, 260, 40, GRAY, HOVER_GRAY, "BACK_MENU"))

    def wipe_save_data(self, save_to_disk=True):
        """Verileri sıfırlar (New Game)."""
        self.money = 0; self.score = 0
        self.stats = {
            'upgrade_hp': 0, 'upgrade_dmg': 0, 'upgrade_speed': 0, 'upgrade_firerate': 0,
            
            # SAHİPLİK (Satın alındı mı?)
            'double_shot': False, 
            'has_drone': False, 
            'has_missiles': False,
            
            # DURUM (Takılı mı?) -> Varsayılan olarak True yaparım ki alınca hemen çalışsın
            'active_double': True,
            'active_drone': True,
            'active_missile': True
        }
        for ach in self.achievement_manager.achievements:
            ach.unlocked = False
            ach.unlock_time = 0
        if save_to_disk: self.save_data()

    def load_data(self):
        filename = self.get_save_path(f"save_{self.current_slot}.json")
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
                    self.money = data.get("money", 0)
                    self.score = data.get("score", 0)
                    self.next_boss_score = (self.score // 2000 + 1) * 2000
                    self.stats.update(data.get("stats", {}))
                    self.volume_level = data.get("volume", 1.0)
                    self.keys.update(data.get("keys", {}))
                    
                    # --- BAŞARIMLARI YÜKLEME ---
                    # 1. Önce hafızadaki tüm başarımları kilitle (Eski slotun kalıntılarını temizle)
                    for ach in self.achievement_manager.achievements:
                        ach.unlocked = False
                    
                    # 2. Dosyadaki listeyi çek
                    saved_ids = data.get("achievements", [])
                    
                    # 3. Listede olanları aç
                    for ach in self.achievement_manager.achievements:
                        if ach.id in saved_ids:
                            ach.unlocked = True
                    # ---------------------------

                    print(f"Slot {self.current_slot} yüklendi.")
            except: print("Yükleme Hatası")
        else: self.wipe_save_data(save_to_disk=False)

    def save_autosave(self):
        """Sadece otomatik yedekleme dosyasına (autosave.json) kayıt yapar."""
        filename = self.get_save_path("autosave.json")
        unlocked_ids = [ach.id for ach in self.achievement_manager.achievements if ach.unlocked]
        data = {
            "money": self.money, "score": self.score, "stats": self.stats,
            "volume": self.volume_level, "keys": self.keys,
            "achievements": unlocked_ids
        }
        try:
            with open(filename, "w") as f:
                json.dump(data, f)
            # Konsola yazmaya gerek yok, sessizce halletsin
        except: pass

    def save_data(self):
        filename = self.get_save_path(f"save_{self.current_slot}.json")
        unlocked_ids = [ach.id for ach in self.achievement_manager.achievements if ach.unlocked]
        data = {
            "money": self.money, "score": self.score, "stats": self.stats,
            "volume": self.volume_level, "keys": self.keys,
            "achievements": unlocked_ids
        }
        try:
            with open(filename, "w") as f: json.dump(data, f)
        except: print("Kaydetme Hatası")

    def spawn_player(self):
        self.player = Player(self.player_type, self.stats, self.keys)
        self.all_sprites.add(self.player)

    def draw_text(self, text, font, color, x, y, center=True):
        surf = font.render(text, True, color)
        rect = surf.get_rect()
        if center: rect.center = (x, y)
        else: rect.topleft = (x, y)
        self.screen.blit(surf, rect)

    def screen_shake(self):
        if self.shake_time > 0:
            self.shake_time -= 1
            return random.randint(-8, 8), random.randint(-8, 8)
        return 0, 0

    def draw_store_screen(self):
        self.grid.draw(self.screen)
        self.draw_text("WEAPON STORE", self.font_title, BLUE, WIDTH//2, 60)
        self.draw_text(f"Money: ${self.money}", self.font_large, YELLOW, WIDTH//2, 110)
        
        for btn in self.store_buttons:
            
            # --- TİP A: TEK SEFERLİK ÖZEL EŞYALAR (Toggle Mantığı) ---
            if btn.action_code in ["BUY_DOUBLE", "BUY_DRONE", "BUY_MISSILE"]:
                
                # 1. DOUBLE SHOT
                if btn.action_code == "BUY_DOUBLE":
                    if self.stats['double_shot']: # Satın alınmışsa
                        btn.disabled = False
                        if self.stats.get('active_double', True): # Takılıysa
                            btn.text = "UNEQUIP DOUBLE" 
                            btn.base_color = (100, 50, 50) 
                        else:
                            btn.text = "EQUIP DOUBLE"   
                            btn.base_color = (50, 100, 50) 
                    else: 
                        btn.text = "DOUBLE SHOT - $500"
                        btn.base_color = PURPLE
                        btn.disabled = False

                # 2. DRONE
                elif btn.action_code == "BUY_DRONE":
                    if self.stats['has_drone']:
                        btn.disabled = False
                        if self.stats.get('active_drone', True):
                            btn.text = "UNEQUIP DRONE" 
                            btn.base_color = (100, 50, 50)
                        else:
                            btn.text = "EQUIP DRONE"  
                            btn.base_color = (50, 100, 50)
                    else:
                        btn.text = "ATTACK DRONE - $1000"
                        btn.base_color = PURPLE
                        btn.disabled = False

                # 3. MISSILE
                elif btn.action_code == "BUY_MISSILE":
                    if self.stats['has_missiles']:
                        btn.disabled = False
                        if self.stats.get('active_missile', True):
                            btn.text = "UNEQUIP MISSILE" 
                            btn.base_color = (100, 50, 50)
                        else:
                            btn.text = "EQUIP MISSILE"   
                            btn.base_color = (50, 100, 50)
                    else:
                        btn.text = "HOMING MISSILES - $1500"
                        btn.base_color = PURPLE
                        btn.disabled = False
            
            # --- TİP B: STANDART GELİŞTİRMELER ---
            else:
                btn.disabled = False
                btn.base_color = BLUE 

            # Çizim işlemi
            btn.draw(self.screen, self.font_small, self.money)

    def get_closest_enemy(self, sprite):
        closest = None
        min_dist = 99999
        targets = list(self.enemies)
        if self.boss: targets.append(self.boss)
        
        for t in targets:
            dist = math.hypot(t.rect.centerx - sprite.rect.centerx, t.rect.centery - sprite.rect.centery)
            if dist < min_dist:
                min_dist = dist
                closest = t
        return closest

    def reset_game(self):
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.boss_bullets = pygame.sprite.Group() 
        self.particles = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()
        self.texts = pygame.sprite.Group()
        
        self.player = None; self.boss = None
        # Skoru koru, yoksa 0 yap
        self.score = getattr(self, 'score', 0) 
        self.level_mult = 1.0; self.kill_counter = 0
        self.game_over_timer = 0; self.paused = False
        self.combo_count = 0; self.combo_timer = 0; self.max_combo = 0 
        self.emp_active = False; self.emp_radius = 0; self.emp_targets = []

        # --- BAŞARIM & OTO-KAYIT ---
        self.boss_just_killed = False     
        self.last_shot_time = time.time() 
        self.last_ulti_kill_count = 0     
        self.autosave_timer = 0
        self.autosave_interval = 60 * FPS
        self.next_boss_score = 2000

    def run(self):
        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()
            mouse_clicked = False
            
            for event in pygame.event.get():
                if event.type == pygame.VIDEORESIZE:
                    # 1. Global genişlik ve yüksekliği güncelle
                    global WIDTH, HEIGHT
                    WIDTH, HEIGHT = event.w, event.h
                    
                    # 2. Ekranı yeni boyuta göre ayarla
                    self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                    
                    # 3. Arka plan elemanlarını (Yıldızlar, Izgara) yeni alana yay
                    self.stars = [Star() for _ in range(int(WIDTH * HEIGHT / 12000))] 
                    self.grid = CyberGrid() 
                    
                    # 4. Butonları yeni merkeze taşı
                    self.create_all_buttons()
                    
                    # 5. Oyuncu ekran dışı kaldıysa içeri çek
                    if self.player:
                        self.player.rect.clamp_ip(self.screen.get_rect())

                if event.type == pygame.QUIT:
                    # Çıkarken sadece oyun içindeysek otomatik kaydedelim
                    if self.state == "GAME":
                        self.save_autosave()
                    running = False
                
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_clicked = True
                
                if event.type == pygame.KEYDOWN:
                    
                    # --- TUŞ ATAMA EKRANI ---
                    if self.state == "BINDING_KEY":
                        if self.binding_key:
                            if event.key != pygame.K_ESCAPE:
                                self.keys[self.binding_key] = event.key
                                self.create_control_buttons() 
                                self.save_data() # Ayarları kaydet
                            self.state = "SETTINGS_CONTROLS"
                            self.binding_key = None
                            self.sound.play("select")
                        continue 

                    # --- SES AYARLARI ---
                    if self.state == "SETTINGS_AUDIO":
                        if event.key in [pygame.K_LEFT, pygame.K_a]:
                            self.volume_level = max(0.0, self.volume_level - 0.1)
                            self.sound.set_master_volume(self.volume_level)
                            self.sound.play("hover")
                        elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                            self.volume_level = min(1.0, self.volume_level + 0.1)
                            self.sound.set_master_volume(self.volume_level)
                            self.sound.play("hover")
                        elif event.key == pygame.K_ESCAPE:
                            self.state = "SETTINGS"; self.selected_btn_index = 0; self.sound.play("select")
                            continue

                    # --- PAUSE (OYUN İÇİ) ---
                    if event.key == pygame.K_p and self.state == "GAME":
                        self.paused = not self.paused
                        
                    if not self.paused:
                        # Menü navigasyonu için buton listesi seçimi
                        current_buttons = []
                        is_grid_menu = False 

                        if self.state == "MENU": current_buttons = self.menu_buttons
                        elif self.state == "SETTINGS": current_buttons = self.settings_buttons
                        elif self.state == "SETTINGS_CONTROLS": 
                            current_buttons = self.control_buttons; is_grid_menu = True
                        elif "MARKET" in self.state: 
                            current_buttons = self.store_buttons; is_grid_menu = True
                        
                        # --- STANDART MENÜ NAVİGASYONU (Yukarı/Aşağı/Sağ/Sol) ---
                        if current_buttons and self.state not in ["SLOT_MENU", "CONFIRM_OVERWRITE"]:
                            if event.key in [pygame.K_UP, pygame.K_w]:
                                if is_grid_menu:
                                    new_idx = self.selected_btn_index - 2
                                    if new_idx >= 0: self.selected_btn_index = new_idx
                                    else: self.selected_btn_index = (self.selected_btn_index - 1) % len(current_buttons)
                                else:
                                    self.selected_btn_index = (self.selected_btn_index - 1) % len(current_buttons)
                                self.sound.play("hover")
                            elif event.key in [pygame.K_DOWN, pygame.K_s]:
                                if is_grid_menu:
                                    new_idx = self.selected_btn_index + 2
                                    if new_idx < len(current_buttons): self.selected_btn_index = new_idx
                                    else: self.selected_btn_index = min(len(current_buttons)-1, self.selected_btn_index + 1)
                                else:
                                    self.selected_btn_index = (self.selected_btn_index + 1) % len(current_buttons)
                                self.sound.play("hover")
                            elif is_grid_menu and event.key in [pygame.K_LEFT, pygame.K_a]:
                                if self.selected_btn_index % 2 == 1: self.selected_btn_index -= 1; self.sound.play("hover")
                            elif is_grid_menu and event.key in [pygame.K_RIGHT, pygame.K_d]:
                                if self.selected_btn_index % 2 == 0: 
                                    if self.selected_btn_index + 1 < len(current_buttons): self.selected_btn_index += 1; self.sound.play("hover")

                        # --- STATE İŞLEMLERİ ---
                        if self.state == "INTRO": self.state = "MENU"
                        
                        elif self.state == "MENU":
                            if event.key == pygame.K_RETURN:
                                btn = self.menu_buttons[self.selected_btn_index]
                                self.sound.play("select")
                                if btn.action_code == "GOTO_SLOTS":
                                    self.slot_operation = "LOAD" # Menüden geliyorsak amaç Yüklemektir
                                    self.create_slot_buttons()
                                    self.state = "SLOT_MENU"
                                    self.selected_btn_index = 0
                                elif btn.action_code == "STORE": self.state = "MARKET_MENU"
                                elif btn.action_code == "SETTINGS": 
                                    self.state = "SETTINGS"; self.selected_btn_index = 0
                                elif btn.action_code == "QUIT": running = False

                        # --- SLOT MENÜSÜ (KART SİSTEMİ) ---
                        elif self.state == "SLOT_MENU":
                            # Navigasyon (Yön tuşları)
                            if event.key in [pygame.K_RIGHT, pygame.K_d]:
                                self.selected_btn_index = (self.selected_btn_index + 1) % len(self.slot_buttons); self.sound.play("hover")
                            elif event.key in [pygame.K_LEFT, pygame.K_a]:
                                self.selected_btn_index = (self.selected_btn_index - 1) % len(self.slot_buttons); self.sound.play("hover")
                            elif event.key in [pygame.K_DOWN, pygame.K_s]:
                                self.selected_btn_index = (self.selected_btn_index + 1) % len(self.slot_buttons); self.sound.play("hover")
                            elif event.key in [pygame.K_UP, pygame.K_w]:
                                self.selected_btn_index = (self.selected_btn_index - 1) % len(self.slot_buttons); self.sound.play("hover")

                            elif event.key == pygame.K_RETURN:
                                btn = self.slot_buttons[self.selected_btn_index]
                                
                                # Eğer buton disabled ise (Save modunda Auto-Save'e basarsa) işlem yapma
                                if btn.disabled:
                                    self.sound.play("error")
                                    continue
                                
                                self.sound.play("select")
                                
                                if btn.action_code == "BACK_MENU":
                                    self.state = "MENU"; self.selected_btn_index = 0
                                    
                                # --- MANUEL SLOTLAR (1, 2, 3) ---
                                elif btn.action_code.startswith("SLOT_") and "AUTO" not in btn.action_code:
                                    slot_num = int(btn.action_code.split("_")[1])
                                    self.current_slot = slot_num
                                    filename = self.get_save_path(f"save_{slot_num}.json")
                                    
                                    if self.slot_operation == "SAVE":
                                        if os.path.exists(filename): self.pending_slot = slot_num; self.state = "CONFIRM_OVERWRITE"
                                        else: self.save_data(); self.state = "MENU"; self.texts.add(FloatingText("GAME SAVED", WIDTH//2, HEIGHT//2, GREEN, 40))
                                    else: # LOAD
                                        if os.path.exists(filename): self.load_data()
                                        else: self.wipe_save_data()
                                        self.reset_game(); self.state = "SELECT"
                                
                            # --- AUTO-SAVE SLOTU İŞLEMİ ---
                                elif btn.action_code == "SLOT_AUTO":
                                    # SENARYO 1: KAYIT MODU (SAVE)
                                    if self.slot_operation == "SAVE":
                                        self.sound.play("error")
                                        self.texts.add(FloatingText("SYSTEM ONLY", btn.rect.centerx, btn.rect.top, RED))
                                    
                                    # SENARYO 2: YÜKLEME MODU (LOAD)
                                    else:
                                        filename = self.get_save_path("autosave.json")
                                        if os.path.exists(filename):
                                            try:
                                                with open(filename, "r") as f:
                                                    data = json.load(f)
                                                    self.money = data.get("money", 0)
                                                    self.score = data.get("score", 0)
                                                    self.stats.update(data.get("stats", {}))
                                                    self.volume_level = data.get("volume", 1.0)
                                                    self.keys.update(data.get("keys", {}))
                                                    
                                                    for ach in self.achievement_manager.achievements:
                                                        ach.unlocked = False
                                                    saved_ids = data.get("achievements", [])
                                                    for ach in self.achievement_manager.achievements:
                                                        if ach.id in saved_ids:
                                                            ach.unlocked = True
                                                
                                                print("Otomatik kayıt başarıyla yüklendi.")
                                                self.sound.play("select")
                                                self.reset_game()
                                                self.state = "SELECT"
                                                
                                            except Exception as e: 
                                                print(f"Auto Save yükleme hatası: {e}")
                                                self.sound.play("error")
                                                self.texts.add(FloatingText("CORRUPTED DATA", btn.rect.centerx, btn.rect.top, RED))
                                        else:
                                            self.sound.play("error")
                                            self.texts.add(FloatingText("EMPTY SLOT", btn.rect.centerx, btn.rect.top, RED))

                                # --- SİLME İŞLEMİ ---
                                elif btn.action_code.startswith("DEL_"):
                                    self.pending_slot = int(btn.action_code.split("_")[1])
                                    self.state = "CONFIRM_DELETE"
                                    self.sound.play("select")    
                            
                            elif event.key == pygame.K_ESCAPE:
                                self.state = "MENU"; self.selected_btn_index = 0; self.sound.play("select")

                        # --- ONAY EKRANI (OVERWRITE) ---
                        elif self.state == "CONFIRM_OVERWRITE":
                            if event.key == pygame.K_y: # YES
                                self.current_slot = self.pending_slot
                                self.save_data()
                                self.state = "MENU"
                                self.sound.play("powerup")
                                self.texts.add(FloatingText("GAME SAVED", WIDTH//2, HEIGHT//2, GREEN, 40))
                            elif event.key in [pygame.K_n, pygame.K_ESCAPE]: # NO
                                self.state = "SLOT_MENU"
                                self.sound.play("select")

                        elif self.state == "CONFIRM_DELETE":
                            if event.key == pygame.K_y: # YES (Onay)
                                # Dosyayı sil
                                f_path = self.get_save_path(f"save_{self.pending_slot}.json")
                                if os.path.exists(f_path):
                                    os.remove(f_path)
        
                                # UI Güncelle ve Bildirim Ver
                                self.create_slot_buttons() # Slotları yenile (Empty yazsın)
                                self.sound.play("error")   # Silinme sesi
                                self.texts.add(FloatingText("SLOT DELETED", WIDTH//2, HEIGHT//2, RED, 40))
                                self.state = "SLOT_MENU"
        
                            elif event.key in [pygame.K_n, pygame.K_ESCAPE]: # NO (İptal)
                                self.state = "SLOT_MENU"
                                self.sound.play("select")
                        
                        elif self.state == "SETTINGS":
                            if event.key == pygame.K_RETURN:
                                btn = self.settings_buttons[self.selected_btn_index]
                                self.sound.play("select")
                                if btn.action_code == "AUDIO": self.state = "SETTINGS_AUDIO"
                                elif btn.action_code == "CONTROLS": 
                                    self.state = "SETTINGS_CONTROLS"; self.selected_btn_index = 0
                                elif btn.action_code == "BACK_MENU": self.state = "MENU"
                            elif event.key == pygame.K_ESCAPE:
                                self.state = "MENU"; self.selected_btn_index = 0; self.sound.play("select")

                        elif self.state == "SETTINGS_CONTROLS":
                            if event.key == pygame.K_RETURN:
                                btn = self.control_buttons[self.selected_btn_index]
                                self.sound.play("select")
                                if btn.action_code == "BACK_SETTINGS": self.state = "SETTINGS"; self.selected_btn_index = 0
                                elif btn.action_code.startswith("BIND_"):
                                    self.binding_key = btn.action_code.split("_")[1]; self.state = "BINDING_KEY"
                            elif event.key == pygame.K_ESCAPE:
                                self.state = "SETTINGS"; self.selected_btn_index = 0; self.sound.play("select")

                        elif self.state == "SELECT":
                            if event.key in [pygame.K_LEFT, pygame.K_a]: self.player_type = (self.player_type - 1) % 4; self.sound.play("hover")
                            elif event.key in [pygame.K_RIGHT, pygame.K_d]: self.player_type = (self.player_type + 1) % 4; self.sound.play("hover")
                            elif event.key == pygame.K_RETURN:
                                self.sound.play("select"); self.reset_game(); self.spawn_player(); self.state = "GAME"
                            elif event.key == pygame.K_ESCAPE:
                                # Geri dönünce Slot ekranına at
                                self.slot_operation = "LOAD"
                                self.create_slot_buttons()
                                self.state = "SLOT_MENU"
                                self.sound.play("select")
                                
                        elif self.state == "GAME":
                             if event.key == self.keys["SHOP"]:
                                 self.state = "MARKET_INGAME"; self.sound.play("select")
                             
                             if event.key == self.keys["MENU"]:
                                 self.save_autosave()
                                 self.slot_operation = "SAVE"
                                 self.create_slot_buttons()
                                 self.state = "SLOT_MENU"
                                 self.selected_btn_index = 0
                                 self.sound.play("select")

                             if event.key == self.keys["SHOOT"]:
                                self.last_shot_time = time.time()
                                bullets = self.player.shoot()
                                for b in bullets:
                                    self.all_sprites.add(b); self.bullets.add(b)
                                    if bullets:
                                        s_name = "sniper" if self.player.type == 3 else "laser"
                                        self.sound.play(s_name)
                             
                             if event.key == self.keys["ULTI"]:
                                 if self.player.ulti_power >= self.player.max_ulti:
                                     self.player.ulti_power = 0
                                     self.sound.play("ulti")
                                     self.boss_bullets.empty(); self.emp_active = True; self.emp_radius = 50
                                     self.emp_targets = list(self.enemies) + ([self.boss] if self.boss else [])
                                     self.last_ulti_kill_count = 0 
                                     for e in self.enemies:
                                         e.hp -= 100
                                         self.particles.add(Particle(e.rect.centerx, e.rect.centery, CYAN, 2))
                                         if e.hp <= 0:
                                             self.last_ulti_kill_count += 1
                                             e.kill(); self.score += e.score_val; self.sound.play("explosion")
                                     if self.boss:
                                         self.boss.hp -= 200
                                         self.particles.add(Particle(self.boss.rect.centerx, self.boss.rect.centery, CYAN, 3))
                                     self.shake_time = 30
                                     self.texts.add(FloatingText("STORM UNLEASHED!", WIDTH//2, HEIGHT//2, ELECTRIC_CYAN, 40))
                                     if self.last_ulti_kill_count >= 3:
                                         self.texts.add(FloatingText(f"{self.last_ulti_kill_count} KILLS!", WIDTH//2, HEIGHT//2 + 40, YELLOW, 30))

                        elif "MARKET" in self.state:
                            # --- 1. KLAVYE KISAYOLLARI ---
                            if event.type == pygame.KEYDOWN:
                                # ESC Tuşu: Geldiği yere (Menü veya Oyun) geri döner
                                if event.key == pygame.K_ESCAPE:
                                    self.save_data() 
                                    self.state = "MENU" if self.state == "MARKET_MENU" else "GAME"
                                    self.sound.play("select")
                                    continue 

                                # SHOP Tuşu (Varsayılan 'I'): Sadece oyun içindeyken kapatır
                                elif self.state == "MARKET_INGAME" and event.key == self.keys["SHOP"]:
                                    self.save_data()
                                    self.state = "GAME"
                                    self.sound.play("select")
                                    continue

                            # --- 2. SATIN ALMA İŞLEMİ (MOUSE VE ENTER) ---
                            # Enter'a basıldı mı kontrolü (Mouse tıklamasında hata vermemesi için ayrıldı)
                            is_enter_key = (event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN)
                            
                            # Mouse tıklandıysa VEYA Enter'a basıldıysa işlem yap
                            if is_enter_key or mouse_clicked:
                                
                                # Hangi butona tıklandığını seçili indeksten al
                                btn = self.store_buttons[self.selected_btn_index]

                                # BACK Butonu kontrolü
                                if btn.action_code == "BACK":
                                    self.save_data() 
                                    self.state = "MENU" if self.state == "MARKET_MENU" else "GAME"
                                    self.sound.play("select")
                                    continue 
                                
                                processed = False # İşlem yapıldı mı bayrağı
                                
                                # --- TİP A: ÖZEL EŞYALAR (Toggle/Buy) ---
                                
                                # 1. DOUBLE SHOT (ÇİFT ATEŞ)
                                if btn.action_code == "BUY_DOUBLE":
                                    processed = True
                                    if self.stats['double_shot']: # Zaten varsa Tak/Çıkar
                                        # Durumu tersine çevir
                                        new_state = not self.stats.get('active_double', True)
                                        self.stats['active_double'] = new_state
                                        
                                        # CANLI GÜNCELLEME
                                        if self.player: self.player.double_shot = new_state
                                        
                                        self.sound.play("select")
                                    elif self.money >= btn.cost: # Yoksa Satın Al
                                        self.money -= btn.cost; self.sound.play("powerup")
                                        self.stats['double_shot'] = True
                                        self.stats['active_double'] = True
                                        
                                        # CANLI GÜNCELLEME
                                        if self.player: self.player.double_shot = True
                                    else: self.sound.play("error")

                                # 2. DRONE (SALDIRI DRONE'U)
                                elif btn.action_code == "BUY_DRONE":
                                    processed = True
                                    if self.stats['has_drone']:
                                        new_state = not self.stats.get('active_drone', True)
                                        self.stats['active_drone'] = new_state
                                        
                                        # CANLI GÜNCELLEME
                                        if self.player: self.player.has_drone = new_state
                                        
                                        self.sound.play("select")
                                    elif self.money >= btn.cost:
                                        self.money -= btn.cost; self.sound.play("powerup")
                                        self.stats['has_drone'] = True
                                        self.stats['active_drone'] = True
                                        
                                        # CANLI GÜNCELLEME
                                        if self.player: self.player.has_drone = True
                                    else: self.sound.play("error")

                                # 3. MISSILE (GÜDÜMLÜ FÜZE)
                                elif btn.action_code == "BUY_MISSILE":
                                    processed = True
                                    if self.stats['has_missiles']:
                                        new_state = not self.stats.get('active_missile', True)
                                        self.stats['active_missile'] = new_state
                                        
                                        # CANLI GÜNCELLEME
                                        if self.player: self.player.has_missiles = new_state
                                        
                                        self.sound.play("select")
                                    elif self.money >= btn.cost:
                                        self.money -= btn.cost; self.sound.play("powerup")
                                        self.stats['has_missiles'] = True
                                        self.stats['active_missile'] = True
                                        
                                        # CANLI GÜNCELLEME
                                        if self.player: self.player.has_missiles = True
                                    else: self.sound.play("error")

                                # --- TİP B: STANDART GELİŞTİRMELER (Sadece Satın Al) ---
                                elif not processed and not btn.disabled and self.money >= btn.cost:
                                    self.money -= btn.cost; self.sound.play("powerup")
                                    
                                    if btn.action_code == "BUY_DMG": 
                                        self.stats['upgrade_dmg'] += 10
                                        if self.player: self.player.dmg += 10
                                        
                                    elif btn.action_code == "BUY_HP": 
                                        self.stats['upgrade_hp'] += 50
                                        if self.player: 
                                            self.player.max_hp += 50
                                            self.player.hp += 50
                                            
                                    elif btn.action_code == "BUY_SPD": 
                                        self.stats['upgrade_speed'] += 1
                                        if self.player: self.player.speed += 1
                                        
                                    elif btn.action_code == "BUY_RATE": 
                                        self.stats['upgrade_firerate'] += 2
                                    
                                # Para Yetmiyorsa
                                elif not processed and self.money < btn.cost:
                                    self.sound.play("error")
                                
                                self.save_data() # Her işlemden sonra kaydet

                        elif self.state == "GAMEOVER":
                            if event.key == pygame.K_r:
                                self.slot_operation = "SAVE"
                                self.create_slot_buttons()
                                self.state = "SLOT_MENU"
                                self.selected_btn_index = 0
                                self.sound.play("select")

            # --- GÜNCELLEME (UPDATE) ---
            shake_x, shake_y = self.screen_shake()
            
            if self.paused:
                self.draw_text("PAUSED", self.font_title, WHITE, WIDTH//2, HEIGHT//2)
                pygame.display.flip(); self.clock.tick(FPS); continue

            if self.state == "INTRO":
                self.intro_timer += 1
                if self.intro_timer % 30 == 0 and self.intro_step < 4:
                    self.sound.play_intro(self.intro_step); self.intro_step += 1
                if self.intro_timer > 180: self.state = "MENU"

            elif self.state == "MENU":
                for i, btn in enumerate(self.menu_buttons):
                    if btn.rect.collidepoint(mouse_pos):
                        if self.selected_btn_index != i: self.sound.play("hover")
                        self.selected_btn_index = i
                    btn.selected = (i == self.selected_btn_index)
                    if btn.selected and mouse_clicked:
                        self.sound.play("select")
                        if btn.action_code == "GOTO_SLOTS":
                            self.slot_operation = "LOAD"
                            self.create_slot_buttons()
                            self.state = "SLOT_MENU"
                            self.selected_btn_index = 0
                        elif btn.action_code == "STORE": self.state = "MARKET_MENU"
                        elif btn.action_code == "SETTINGS": self.state = "SETTINGS"; self.selected_btn_index = 0
                        elif btn.action_code == "QUIT": running = False
                self.grid.update(0.5); 
                for s in self.stars: s.update(False)
            
            elif self.state == "SLOT_MENU":
                self.grid.update(0.5)
                for i, btn in enumerate(self.slot_buttons):
                    # Mouse butonun üzerindeyse seçili yap
                    if btn.rect.collidepoint(mouse_pos): 
                        self.selected_btn_index = i
                    
                    btn.selected = (i == self.selected_btn_index)
                    
                    # --- TIKLAMA KONTROLÜ ---
                    if btn.selected and mouse_clicked:
                        self.sound.play("select")
                        
                        # 1. GERİ DÖNÜŞ
                        if btn.action_code == "BACK_MENU":
                            self.state = "MENU"; self.selected_btn_index = 0
                        
                        # 2. NORMAL SLOTLAR (1, 2, 3)
                        elif btn.action_code.startswith("SLOT_") and "AUTO" not in btn.action_code:
                            slot_num = int(btn.action_code.split("_")[1])
                            self.current_slot = slot_num
                            filename = self.get_save_path(f"save_{slot_num}.json")
                            if self.slot_operation == "SAVE":
                                if os.path.exists(filename): self.pending_slot = slot_num; self.state = "CONFIRM_OVERWRITE"
                                else: self.save_data(); self.state = "MENU"; self.texts.add(FloatingText("GAME SAVED", WIDTH//2, HEIGHT//2, GREEN, 40))
                            else: # LOAD
                                if os.path.exists(filename): self.load_data()
                                else: self.wipe_save_data()
                                self.reset_game(); self.state = "SELECT"

                        # 3. AUTO-SAVE SLOTU
                        elif btn.action_code == "SLOT_AUTO":
                            if self.slot_operation == "SAVE":
                                self.sound.play("error")
                                self.texts.add(FloatingText("SYSTEM ONLY", btn.rect.centerx, btn.rect.top, RED))
                            else:
                                filename = self.get_save_path("autosave.json")
                                if os.path.exists(filename):
                                    # Yükleme ve Başlatma Mantığı
                                    try:
                                        with open(filename, "r") as f:
                                            data = json.load(f)
                                            self.money = data.get("money", 0)
                                            self.score = data.get("score", 0)
                                            self.stats.update(data.get("stats", {}))
                                            self.volume_level = data.get("volume", 1.0)
                                            self.keys.update(data.get("keys", {}))
                                            for ach in self.achievement_manager.achievements:
                                                ach.unlocked = False
                                            saved_ids = data.get("achievements", [])
                                            for ach in self.achievement_manager.achievements:
                                                if ach.id in saved_ids: ach.unlocked = True
                                        
                                        self.reset_game()
                                        self.state = "SELECT"
                                    except: self.sound.play("error")
                                else:
                                    self.sound.play("error")
                                    self.texts.add(FloatingText("EMPTY SLOT", btn.rect.centerx, btn.rect.top, RED))

                        # 4. SİLME BUTONLARI
                        elif btn.action_code.startswith("DEL_"):
                            self.pending_slot = int(btn.action_code.split("_")[1])
                            self.state = "CONFIRM_DELETE"; self.sound.play("select")

            elif self.state == "SELECT":
                # Geri butonu hover kontrolü
                if self.btn_select_back.rect.collidepoint(mouse_pos):
                    self.btn_select_back.selected = True
                    if mouse_clicked:
                        self.sound.play("select"); self.slot_operation = "LOAD"; self.create_slot_buttons(); self.state = "SLOT_MENU"
                else: self.btn_select_back.selected = False

            elif self.state == "SETTINGS":
                self.grid.update(0.5)
                for i, btn in enumerate(self.settings_buttons):
                    if btn.rect.collidepoint(mouse_pos): self.selected_btn_index = i
                    btn.selected = (i == self.selected_btn_index)
                    if btn.selected and mouse_clicked:
                        self.sound.play("select")
                        if btn.action_code == "AUDIO": self.state = "SETTINGS_AUDIO"
                        elif btn.action_code == "CONTROLS": self.state = "SETTINGS_CONTROLS"; self.selected_btn_index = 0
                        elif btn.action_code == "BACK_MENU": self.state = "MENU"; self.selected_btn_index = 0
            
            elif self.state == "SETTINGS_AUDIO":
                self.grid.update(0.5)
                bar_rect = pygame.Rect(WIDTH//2 - 200, 250, 400, 40)
                if pygame.mouse.get_pressed()[0]:
                    if bar_rect.collidepoint(mouse_pos) or (mouse_pos[1] > 240 and mouse_pos[1] < 300):
                        rel_x = mouse_pos[0] - bar_rect.x
                        self.volume_level = max(0.0, min(1.0, rel_x / 400))
                        self.sound.set_master_volume(self.volume_level)
                for btn in self.audio_buttons:
                    btn.selected = btn.rect.collidepoint(mouse_pos)
                    if btn.selected and mouse_clicked:
                        self.sound.play("select")
                        if btn.action_code == "BACK_SETTINGS": self.state = "SETTINGS"; self.selected_btn_index = 0

            elif self.state == "SETTINGS_CONTROLS" or self.state == "BINDING_KEY":
                self.grid.update(0.5)
                for i, btn in enumerate(self.control_buttons):
                    if self.state == "BINDING_KEY": btn.selected = False 
                    else: 
                        if btn.rect.collidepoint(mouse_pos): self.selected_btn_index = i
                        btn.selected = (i == self.selected_btn_index)
                    if btn.selected and mouse_clicked:
                        self.sound.play("select")
                        if btn.action_code == "BACK_SETTINGS": self.state = "SETTINGS"; self.selected_btn_index = 0
                        elif btn.action_code.startswith("BIND_"): self.binding_key = btn.action_code.split("_")[1]; self.state = "BINDING_KEY"

            elif "MARKET" in self.state:
                self.grid.update(0.5)
                for i, btn in enumerate(self.store_buttons):
                    if btn.rect.collidepoint(mouse_pos): self.selected_btn_index = i
                    btn.selected = (i == self.selected_btn_index)
                    if btn.selected and mouse_clicked:
                        fake_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN); pygame.event.post(fake_event)

            elif self.state == "GAME" or self.state == "DYING":
                self.grid.update(2.0 if self.player and self.player.is_dashing else 1.0)
                for s in self.stars: s.update(True) 
                
                if self.state == "GAME":
                    if self.emp_active:
                        self.emp_radius += 25 
                        if self.emp_radius > WIDTH * 1.2: self.emp_active = False; self.emp_targets = []

                    if self.combo_timer > 0: self.combo_timer -= 1
                    else: self.combo_count = 0
                    
                    if self.player.has_drone and self.player.drone_cooldown == 0:
                        target = self.get_closest_enemy(self.player)
                        if target:
                            dx = target.rect.centerx - self.player.rect.centerx; dy = target.rect.centery - self.player.rect.centery
                            dist = math.hypot(dx, dy)
                            if dist > 0:
                                vx = (dx / dist) * 12; vy = (dy / dist) * 12
                                b = Bullet(self.player.rect.centerx + math.cos(math.radians(self.player.drone_angle))*40, 
                                           self.player.rect.centery + math.sin(math.radians(self.player.drone_angle))*40, 
                                           10, CYAN, vx, vy, (4, 4))
                                self.bullets.add(b); self.all_sprites.add(b)
                                self.player.drone_cooldown = 40; self.sound.play("drone")
                    
                    if self.player.has_missiles and self.player.missile_cooldown == 0:
                         target = self.get_closest_enemy(self.player)
                         if target:
                             b = Bullet(self.player.rect.centerx, self.player.rect.centery, 30, RED, vx=0, vy=-5, size=(8,8), is_missile=True, target=target)
                             self.bullets.add(b); self.all_sprites.add(b)
                             self.player.missile_cooldown = 90; self.sound.play("missile")

                    if not self.boss:
                        # EĞER SKOR HEDEFİ GEÇTİYSE BOSS GELSİN
                        if self.score >= self.next_boss_score: 
                            self.boss = Boss()
                            self.all_sprites.add(self.boss)
                            self.enemies.empty() 
                            
                        # Boss gelmediyse normal düşman üretmeye devam et
                        elif len(self.enemies) < 8 + int(self.level_mult) and random.randint(0, 50) == 0:
                            d = Enemy(self.level_mult); self.enemies.add(d); self.all_sprites.add(d)
                    
                    for enemy in self.enemies:
                        bullet = enemy.update()
                        if bullet: self.boss_bullets.add(bullet); self.all_sprites.add(bullet); self.sound.play("enemy_shoot")

                    # --- BOSS GÜNCELLEME BLOĞU ---
                    if self.boss:
                        # 1. Player'ın konumunu belirle (Nişan alabilmesi için)
                        # Eğer oyuncu ölüyse veya "dash" atıyorsa (görünmezse) boss kör atış yapsın
                        target_rect = self.player.rect if (self.player and self.player.visible) else None

                        # 2. Boss'u güncelle ve oluşturduğu mermi listesini al
                        boss_created_bullets = self.boss.update(target_rect)

                        # 3. Eğer Boss ateş ettiyse gelen mermileri oyuna ekle
                        if boss_created_bullets:
                            for b in boss_created_bullets:
                                self.boss_bullets.add(b)
                                self.all_sprites.add(b)
                            
                            # 4. Ses Efektleri
                            if len(boss_created_bullets) > 1:
                                self.sound.play("enemy_shoot") 
                            else:
                                self.sound.play("sniper")

                    self.all_sprites.update(); self.texts.update()

                    # --- BAŞARIM VE OTO-KAYIT ---
                    self.achievement_manager.update(self)
                    self.boss_just_killed = False 
                    self.autosave_timer += 1
                    if self.autosave_timer >= self.autosave_interval:
                        self.save_autosave()
                        self.autosave_timer = 0
                        self.texts.add(FloatingText("AUTO BACKUP", WIDTH - 80, HEIGHT - 30, ORANGE, 14, vy=0, life=60))

                    # --- GANİMET SİSTEMİ ---
                    hits = pygame.sprite.groupcollide(self.enemies, self.bullets, False, True)
                    for enemy, bullet_list in hits.items():
                        for b in bullet_list:
                            dmg = b.damage
                            # Kritik vuruş şansı
                            is_crit = random.random() < 0.15 
                            if is_crit: 
                                dmg *= 2; self.sound.play("crit")
                                self.texts.add(FloatingText("CRIT!", enemy.rect.centerx, enemy.rect.top-20, RED, 24, vy=-4))
                            
                            enemy.hp -= dmg
                            # Vuruş efekti
                            for _ in range(3): self.particles.add(Particle(enemy.rect.centerx, enemy.rect.centery, enemy.color))
                        
                        # Düşman öldü mü?
                        if enemy.hp <= 0:
                            enemy.kill(); self.sound.play("explosion")
                            
                            # 1. KOMBO SİSTEMİ
                            self.player.add_ulti(5)
                            self.combo_count += 1
                            if self.combo_count > self.max_combo: self.max_combo = self.combo_count
                            self.combo_timer = 120 
                            
                            if self.combo_count > 1:
                                self.texts.add(FloatingText(f"{self.combo_count}x COMBO!", enemy.rect.centerx, enemy.rect.centery - 20, CYAN, 24))
                                if self.combo_count % 5 == 0: self.sound.play("combo")

                            # 2. PARA HESAPLAMA
                            base_money = 5 # Normal (Kırmızı) -> 5$
                            
                            if enemy.type == "fast": 
                                base_money = 15 # Hızlı (Turuncu) -> 15$
                            elif enemy.type == "tank": 
                                base_money = 25 # Tank (Yeşil) -> 25$
                            
                            # Kombo Çarpanını Uygula
                            # Örnek: 10 Kombo varsa (2.0x), Kırmızı gemi 20$ verir.
                            multiplier = 1 + (self.combo_count * 0.1) 
                            coin_amount = int(base_money * multiplier)
                            
                            # 3. JACKPOT (%5 Şansla 3 Katı Para)
                            if random.random() < 0.05:
                                coin_amount *= 3
                                self.texts.add(FloatingText("JACKPOT!", enemy.rect.centerx, enemy.rect.top - 40, YELLOW, 30, vy=-3))
                                self.sound.play("coin") 

                            # Parayı Cüzdana Ekle
                            self.money += coin_amount
                            self.sound.play("coin")
                            self.texts.add(FloatingText(f"+${coin_amount}", enemy.rect.centerx, enemy.rect.centery, YELLOW))
                            
                            # Skoru Ekle
                            self.score += int(enemy.score_val * multiplier)

                            # 4. POWERUP (Can/Kalkan) Düşürme Şansı
                            if random.random() < 0.15: 
                                p = PowerUp(enemy.rect.centerx, enemy.rect.centery)
                                self.powerups.add(p); self.all_sprites.add(p)

                    if self.boss:
                        boss_hits = pygame.sprite.spritecollide(self.boss, self.bullets, True)
                        for b in boss_hits:
                            dmg = b.damage
                            if random.random() < 0.15: 
                                dmg *= 2; self.sound.play("crit")
                                self.texts.add(FloatingText("CRIT!", self.boss.rect.centerx + random.randint(-40,40), self.boss.rect.centery, RED, 30, vy=-5))
                            self.boss.hp -= dmg; self.sound.play("boss_hit")
                            self.particles.add(Particle(b.rect.centerx, b.rect.y, YELLOW))
                        if self.boss.hp <= 0:
                            self.boss.kill()
                            self.boss = None
                            self.score += 5000
                            self.money += 1000
                            self.next_boss_score = self.score + 2000
                            self.boss_just_killed = True # Başarım için
                            self.level_mult += 0.5; self.shake_time = 40; self.sound.play("explosion")
                            self.player.add_ulti(50)
                            for _ in range(50): self.particles.add(Particle(WIDTH//2, 100, ORANGE, speed_mult=2.0))

                    p_hits = pygame.sprite.spritecollide(self.player, self.powerups, True)
                    for p in p_hits:
                        if p.type == "health":
                            self.sound.play("powerup"); self.player.hp = min(self.player.hp + 30, self.player.max_hp)
                            self.texts.add(FloatingText("+HP", p.rect.centerx, p.rect.top, GREEN))
                        elif p.type == "shield":
                            self.sound.play("shield_get"); self.player.activate_shield()
                            self.texts.add(FloatingText("SHIELD ACTIVATED!", p.rect.centerx, p.rect.top, SHIELD_BLUE))

                    total_dmg = 0
                    if pygame.sprite.spritecollide(self.player, self.enemies, True): total_dmg += 30
                    if pygame.sprite.spritecollide(self.player, self.boss_bullets, True): total_dmg += 20
                    if self.boss and self.player.rect.colliderect(self.boss.rect): total_dmg += 5

                    if total_dmg > 0:
                        is_hit, hull_damaged, shield_hit = self.player.take_damage(total_dmg)
                        if is_hit:
                            self.shake_time = 10
                            if shield_hit: self.sound.play("shield_hit")
                            if hull_damaged:
                                self.sound.play("explosion")
                                if self.player.hp <= 0:
                                    self.state = "DYING"; self.player.visible = False; self.sound.play("explosion")
                                    self.shake_time = 60; self.game_over_timer = 120
                                    for _ in range(100): self.particles.add(Particle(self.player.rect.centerx, self.player.rect.centery, self.player.color, speed_mult=3.0))
                    
                    elif self.player.is_dashing and self.player.dash_timer == 9: self.sound.play("dash")

                elif self.state == "DYING":
                    self.all_sprites.update(); self.game_over_timer -= 1
                    if self.game_over_timer <= 0: 
                        self.state = "GAMEOVER"
                        self.save_autosave()

                
                for p in self.particles: 
                     if p not in self.all_sprites: self.all_sprites.add(p)

            # --- ÇİZİM (DRAW) ---
            self.grid.draw(self.screen)
            
            if self.state == "INTRO":
                for i in range(10):
                    c = random.randint(50, 255)
                    pygame.draw.rect(self.screen, (0, c, 0), (random.randint(0, WIDTH), random.randint(0, HEIGHT), 5, 20))
                alpha = min(255, self.intro_timer * 2)
                title = self.font_title.render("NEON DEFENDER", True, (alpha, alpha, alpha))
                sub = self.font_small.render("Press ENTER to skip", True, GRAY)
                self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 250))
                if self.intro_timer > 50: self.screen.blit(sub, (WIDTH//2 - sub.get_width()//2, 500))

            elif self.state == "MENU":
                for s in self.stars: s.draw(self.screen)
                self.draw_text("NEON DEFENDER", self.font_title, CYAN, WIDTH//2, 150)
                for btn in self.menu_buttons: btn.draw(self.screen, self.font_large)
                self.draw_text("Written by: c005", self.font_small, GRAY, WIDTH - 120, HEIGHT - 20)

            elif self.state == "SLOT_MENU":
                title = getattr(self, 'slot_menu_title', "SELECT SAVE SLOT")
                self.draw_text(title, self.font_title, WHITE, WIDTH//2, 60)
                
                for btn in self.slot_buttons:
                    btn.draw(self.screen, self.font_large)
                    
                    # Kartların içine detay yaz
                    if hasattr(btn, 'info_text'):
                        lines = btn.info_text.split('\n')
                        cy = btn.rect.centery
                        
                        # Eğer bu Auto-Save butonuysa, yazıları biraz yukarıdan başlat (Ortalamak için)
                        # Çünkü 3 satırımız var, merkezden başlarsak aşağı kayar.
                        total_height = len(lines) * 25
                        start_y = cy - (total_height // 2) + 10
                        
                        for idx, line in enumerate(lines):
                            # --- RENK VE FONT SEÇİMİ ---
                            is_header = False
                            
                            # 1. Başlıklar: Eğer buton seçiliyse (üzerine gelindiyse) BEYAZ yap, yoksa kendi rengini kullan.
                            if "SLOT" in line and "AUTO" not in line: 
                                col = WHITE if btn.selected else ELECTRIC_CYAN
                                font = self.font_large; is_header = True
                                
                            elif "EMPTY" in line: 
                                col = GRAY; font = self.font_large; is_header = True
                                
                            elif "AUTO" in line: 
                                col = WHITE if btn.selected else ORANGE 
                                font = self.font_large; is_header = True
                            
                            # 2. Detaylar (Score, Cash) -> Küçük ve Bilgi Rengi
                            elif "Score" in line: col = GREEN; font = self.font_small
                            elif "Cash" in line: col = YELLOW; font = self.font_small
                            elif "System" in line: col = RED; font = self.font_small
                            elif "New Game" in line: col = (100, 100, 100); font = self.font_small
                            else: col = WHITE; font = self.font_small
                            
                            # Satır Aralığı
                            offset_y = idx * 28 
                            self.draw_text(line, font, col, btn.rect.centerx, start_y + offset_y)
                            

            elif self.state == "CONFIRM_OVERWRITE":
                # Arkaplanı biraz karart
                overlay = pygame.Surface((WIDTH, HEIGHT))
                overlay.set_alpha(150)
                overlay.fill(BLACK)
                self.screen.blit(overlay, (0,0))
                # Kutu
                pygame.draw.rect(self.screen, DARK_RED, (WIDTH//2 - 200, HEIGHT//2 - 100, 400, 200), border_radius=20)
                pygame.draw.rect(self.screen, RED, (WIDTH//2 - 200, HEIGHT//2 - 100, 400, 200), 4, border_radius=20)
                self.draw_text("OVERWRITE SLOT?", self.font_large, WHITE, WIDTH//2, HEIGHT//2 - 50)
                self.draw_text("Current progress will be lost!", self.font_small, YELLOW, WIDTH//2, HEIGHT//2)
                self.draw_text("Press [Y] YES  /  [N] NO", self.font_large, WHITE, WIDTH//2, HEIGHT//2 + 60)
        
            elif self.state == "CONFIRM_DELETE":
                # Arkaplanı karart
                overlay = pygame.Surface((WIDTH, HEIGHT))
                overlay.set_alpha(180)
                overlay.fill(BLACK)
                self.screen.blit(overlay, (0,0))
    
                # Kırmızı Uyarı Kutusu
                box_w, box_h = 420, 240
                box_x, box_y = WIDTH//2 - box_w//2, HEIGHT//2 - box_h//2
    
                # Kutu Çizimi
                pygame.draw.rect(self.screen, (40, 0, 0), (box_x, box_y, box_w, box_h), border_radius=15)
                pygame.draw.rect(self.screen, RED, (box_x, box_y, box_w, box_h), 3, border_radius=15)
    
                 # Yazılar
                self.draw_text("DELETE SAVE DATA?", self.font_large, RED, WIDTH//2, box_y + 50)
                self.draw_text(f"Slot {self.pending_slot} will be lost permanently!", self.font_small, WHITE, WIDTH//2, box_y + 100)
    
                # Tuşlar
                self.draw_text("[Y] DELETE", self.font_large, RED, WIDTH//2 - 90, box_y + 170)
                self.draw_text("[N] CANCEL", self.font_large, GREEN, WIDTH//2 + 90, box_y + 170)

            elif self.state == "SETTINGS":
                self.draw_text("SETTINGS", self.font_title, WHITE, WIDTH//2, 100)
                for btn in self.settings_buttons: btn.draw(self.screen, self.font_large)

            elif self.state == "SETTINGS_AUDIO":
                self.draw_text("AUDIO SETTINGS", self.font_title, WHITE, WIDTH//2, 100)
                bar_width = 400; bar_height = 40; bar_x = WIDTH//2 - bar_width//2; bar_y = 250
                pygame.draw.rect(self.screen, GRAY, (bar_x, bar_y, bar_width, bar_height))
                pygame.draw.rect(self.screen, GREEN, (bar_x, bar_y, bar_width * self.volume_level, bar_height))
                pygame.draw.rect(self.screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 3)
                self.draw_text(f"VOLUME: {int(self.volume_level * 100)}%", self.font_large, WHITE, WIDTH//2, 200)
                self.draw_text("Use Mouse or Arrow Keys to Adjust", self.font_small, GRAY, WIDTH//2, 320)
                for btn in self.audio_buttons: btn.draw(self.screen, self.font_large)

            elif self.state == "SETTINGS_CONTROLS" or self.state == "BINDING_KEY":
                self.draw_text("CONTROLS", self.font_title, WHITE, WIDTH//2, 60)
                if self.state == "BINDING_KEY":
                    pygame.draw.rect(self.screen, BLACK, (0, 0, WIDTH, HEIGHT), 0)
                    self.draw_text(f"PRESS NEW KEY FOR: {self.binding_key}", self.font_large, ELECTRIC_CYAN, WIDTH//2, HEIGHT//2)
                    self.draw_text("Press ESC to Cancel", self.font_small, GRAY, WIDTH//2, HEIGHT//2 + 50)
                else:
                    for btn in self.control_buttons: btn.draw(self.screen, self.font_small)

            elif "MARKET" in self.state:
                self.draw_store_screen()

            elif self.state == "SELECT":
                self.draw_text("SELECT SHIP", self.font_large, WHITE, WIDTH//2, 50)
                ships = [
                    {"name": "INTERCEPTOR", "desc": "Balanced", "col": BLUE},
                    {"name": "DESTROYER", "desc": "Tanky & Slow", "col": PURPLE},
                    {"name": "SPEEDER", "desc": "Fast & Fragile", "col": YELLOW},
                    {"name": "SNIPER", "desc": "One Shot", "col": GREEN}
                ]
                sel = ships[self.player_type]
                pygame.draw.rect(self.screen, sel["col"], (WIDTH//2 - 100, 150, 200, 200), 2)
                pygame.draw.rect(self.screen, sel["col"], (WIDTH//2 - 50, 200, 100, 100))
                self.draw_text(f"< {sel['name']} >", self.font_large, sel["col"], WIDTH//2, 400)
                self.draw_text(sel["desc"], self.font_small, WHITE, WIDTH//2, 450)
                shoot_key = pygame.key.name(self.keys['SHOOT']).upper(); ulti_key = pygame.key.name(self.keys['ULTI']).upper()
                self.draw_text(f"Shoot: {shoot_key} | Ulti: {ulti_key}", self.font_small, GRAY, WIDTH//2, 550)
                
                # Geri Butonunu Çiz
                self.btn_select_back.draw(self.screen, self.font_small)

            elif self.state == "GAME" or self.state == "DYING":
                # 1. Izgarayı titret
                self.grid.draw(self.screen, shake_x, shake_y) 
                
                # 2. Yıldızları titret
                for s in self.stars: s.draw(self.screen, shake_x, shake_y)
                
                # 3. Oyuncu izini (Trail) titret
                if self.player and len(self.player.trail) > 1:
                    shaken_trail = [(tx + shake_x, ty + shake_y) for tx, ty in self.player.trail]
                    pygame.draw.lines(self.screen, self.player.color, False, shaken_trail, 3)
                
                # 4. EMP (Ulti) efektini titret
                if self.emp_active and self.player:
                    center_pos = (self.player.rect.centerx + shake_x, self.player.rect.centery + shake_y)
                    pygame.draw.circle(self.screen, ELECTRIC_CYAN, center_pos, int(self.emp_radius), 5)
                    pygame.draw.circle(self.screen, WHITE, center_pos, int(self.emp_radius)-5, 2)
                    # Yıldırım efektleri için hedef koordinatları da kaydırmak gerekir ama karmaşık olmaması için merkez yeterli
                    
                # 5. Tüm Sprite'ları (Gemi, Mermi, Düşman) titret
                for spr in self.all_sprites: 
                    # blit yaparken koordinata shake ekliyoruz (Sprite'ın kendi rect'ini bozmuyoruz)
                    self.screen.blit(spr.image, (spr.rect.x + shake_x, spr.rect.y + shake_y))
                
                # 6. Drone'u titret
                if self.player and self.player.has_drone and self.player.visible:
                    dx = self.player.rect.centerx + math.cos(math.radians(self.player.drone_angle))*40 + shake_x
                    dy = self.player.rect.centery + math.sin(math.radians(self.player.drone_angle))*40 + shake_y
                    pygame.draw.circle(self.screen, CYAN, (int(dx), int(dy)), 5)
                
                # 7. Uçan Yazıları (Floating Text) titret
                for txt in self.texts: 
                    self.screen.blit(txt.image, (txt.rect.x + shake_x, txt.rect.y + shake_y))
                
                if self.player:
                    pygame.draw.rect(self.screen, GRAY, (20, 20, 200, 20), border_radius=5)
                    hp_pct = max(0, self.player.hp / self.player.max_hp)
                    hp_col = GREEN if hp_pct > 0.5 else (ORANGE if hp_pct > 0.2 else RED)
                    pygame.draw.rect(self.screen, hp_col, (20, 20, 200 * hp_pct, 20), border_radius=5)
                    ulti_pct = self.player.ulti_power / self.player.max_ulti
                    pygame.draw.rect(self.screen, GRAY, (20, 45, 150, 10), border_radius=3)
                    pygame.draw.rect(self.screen, ULTI_COLOR, (20, 45, 150 * ulti_pct, 10), border_radius=3)
                    if ulti_pct >= 1: u_key = pygame.key.name(self.keys['ULTI']).upper(); self.draw_text(f"ULTI READY [{u_key}]", self.font_small, ULTI_COLOR, 95, 65)
                    if self.player.shield_active:
                        shield_time_pct = max(0, self.player.shield_timer / self.player.max_shield_time)
                        pygame.draw.rect(self.screen, BLACK, (20, 80, 200, 8)) 
                        pygame.draw.rect(self.screen, SHIELD_BLUE, (20, 80, 200 * shield_time_pct, 8)) 
                        self.draw_text("SHIELD ACTIVE", self.font_small, SHIELD_BLUE, 120, 95)
                    self.draw_text(f"HP: {int(self.player.hp)}", self.font_small, WHITE, 230, 30, False)
                    self.draw_text(f"SCORE: {self.score}", self.font_large, WHITE, WIDTH - 120, 30)
                    self.draw_text(f"${self.money}", self.font_large, YELLOW, WIDTH - 120, 70)
                    if self.combo_count > 1: self.draw_text(f"x{self.combo_count}", self.font_title, CYAN, WIDTH - 60, 150)
                    dash_cd_pct = 1 - (self.player.dash_cooldown / 120)
                    if dash_cd_pct >= 1: d_key = pygame.key.name(self.keys['DASH']).upper(); self.draw_text(f"DASH READY [{d_key}]", self.font_small, CYAN, WIDTH//2, HEIGHT-30)
                    if self.boss: self.boss.draw_health(self.screen)
                    
                    self.achievement_manager.draw_notification(self.screen, WIDTH, HEIGHT)

            elif self.state == "GAMEOVER":
                self.draw_text("MISSION FAILED", self.font_title, RED, WIDTH//2, 200)
                self.draw_text(f"Final Score: {self.score}", self.font_large, WHITE, WIDTH//2, 300)
                self.draw_text(f"Max Combo: {self.max_combo}", self.font_small, CYAN, WIDTH//2, 350)
                self.draw_text(f"Money Kept: ${self.money}", self.font_small, YELLOW, WIDTH//2, 400)
                self.draw_text("Press 'R' to Return to Menu", self.font_small, GRAY, WIDTH//2, 500)

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    Game().run()
