import pygame
import time

class Achievement:
    def __init__(self, id, title, description, condition_func):
        self.id = id
        self.title = title
        self.description = description
        self.condition_func = condition_func
        self.unlocked = False
        self.unlock_time = 0

class AchievementManager:
    def __init__(self):
        self.achievements = []
        self.queue = [] 
        self.notification_duration = 3
        
        # --- BAŞARIMLAR ---
        self.add("first_blood", "ACEMİ AVCI", "İlk düşmanını yok et.", 
                 lambda game: game.kill_counter >= 1)
        
        self.add("sniper_elite", "SABIRLI SAVAŞÇI", "1000 skor yap.",
                 lambda game: game.score >= 1000 and game.player.hp >= game.player.max_hp)
        
        self.add("money_maker", "PARA BABASI", "Cüzdanında 1000$ biriktir.",
                 lambda game: game.money >= 1000)
        
        self.add("combo_master", "KOMBO USTASI", "25x Kombo yap.",
                 lambda game: game.combo_count >= 25)
        
        # KIL PAYI (Near Death Experience)
        # Şart: Canın %20'nin altındayken Boss'u yok et.
        # Mantık: Boss yeni öldüyse (flag) ve Can < MaxCan * 0.20 ise
        self.add("near_death", "KIL PAYI", "Canın %20 altındayken Boss yok et.",
                 lambda game: getattr(game, 'boss_just_killed', False) and \
                              game.player.hp < (game.player.max_hp * 0.20))

        # PASİFİST (Pacifist)
        # Şart: 60 saniye boyunca hiç ateş etmeden hayatta kal.
        # Mantık: Oyun zamanı - Son ateş zamanı > 60
        self.add("pacifist", "PASİFİST", "60sn boyunca ateş etmeden hayatta kal.",
                 lambda game: (time.time() - getattr(game, 'last_shot_time', time.time())) > 60)

        # ULTİ USTASI (Ulti Master)
        # Şart: Tek bir ulti ile 5 veya daha fazla düşmanı yok et.
        # Mantık: Son ulti ile öldürülen > 5
        self.add("ulti_master", "ULTİ USTASI", "Tek Ulti ile 5+ düşman yok et.",
                 lambda game: getattr(game, 'last_ulti_kill_count', 0) >= 5)

        # TAM TEÇHİZAT (Fully Loaded)
        # Şart: Double Shot, Drone ve Füzelerin hepsi açık olsun.
        self.add("fully_loaded", "TAM TEÇHİZAT", "Tüm silah sistemlerini satın al.",
                 lambda game: game.stats['double_shot'] and game.stats['has_drone'] and game.stats['has_missiles'])

        # IŞIK HIZI (Light Speed)
        # Şart: Hız geliştirmesini 5. seviyeye (veya belli bir değere) çıkar.
        self.add("light_speed", "IŞIK HIZI", "Hızını maksimum seviyeye çıkar.",
                 lambda game: game.stats['upgrade_speed'] >= 5) # 5 kez satın alınca

        # SİBER MİLYONER (Cyber Millionaire)
        # Şart: 5000$ biriktir. (Para Babası'nın bir üstü)
        self.add("cyber_millionaire", "SİBER MİLYONER", "Cüzdanında 5000$ biriktir.",
                 lambda game: game.money >= 5000)


    def add(self, id, title, desc, condition):
        self.achievements.append(Achievement(id, title, desc, condition))

    def update(self, game):
        for ach in self.achievements:
            if not ach.unlocked:
                try:
                    if ach.condition_func(game):
                        self.unlock(ach, game)
                except Exception as e:
                    # Hata olursa sessizce geçer oyun çökmez
                    pass

    def unlock(self, achievement, game):
        achievement.unlocked = True
        achievement.unlock_time = time.time()
        self.queue.append(achievement)
        if hasattr(game, 'sound'): game.sound.play("powerup")

    def draw_notification(self, screen, width, height):
        if not self.queue: return
        ach = self.queue[0]
        if time.time() - ach.unlock_time < self.notification_duration:
            # TASARIM
            box_w, box_h = 320, 80; x = width - box_w - 20; y = height - box_h - 20
            s = pygame.Surface((box_w, box_h)); s.set_alpha(230); s.fill((10, 10, 30))
            screen.blit(s, (x, y))
            pygame.draw.rect(screen, (0, 255, 255), (x, y, box_w, box_h), 2)
            try: font1 = pygame.font.SysFont("Verdana", 16, bold=True); font2 = pygame.font.SysFont("Verdana", 12)
            except: font1 = pygame.font.Font(None, 24); font2 = pygame.font.Font(None, 20)
            screen.blit(font1.render("BAŞARIM AÇILDI!", True, (255, 215, 0)), (x+10, y+10))
            screen.blit(font2.render(ach.title, True, (0, 255, 255)), (x+10, y+35))
            screen.blit(font2.render(ach.description, True, (200, 200, 200)), (x+10, y+55))
        else: self.queue.pop(0)
