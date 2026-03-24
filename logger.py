import logging
import os
from datetime import datetime

# --- Vytvoření složky pro logy ---
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Název souboru podle aktuálního data a času
log_filename = os.path.join(LOG_DIR, f"session_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")

# --- Konfigurace loggeru ---
logger = logging.getLogger("SpeedHell")
logger.setLevel(logging.DEBUG)

# Formát zpráv
formatter = logging.Formatter(
    fmt="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

# Handler pro soubor
file_handler = logging.FileHandler(log_filename, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Handler pro konzoli (jen INFO a výše)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


# --- Herní události ---

def log_player_death(room: int, score: int, time_ms: int):
    logger.warning(
        f"HRÁČ ZEMŘEL | místnost={room} | skóre={score} | čas={time_ms // 1000}:{time_ms % 1000:03d}"
    )

def log_room_cleared(room: int, time_ms: int):
    logger.info(
        f"MÍSTNOST VYČIŠTĚNA | místnost={room} | čas={time_ms // 1000}:{time_ms % 1000:03d}"
    )

def log_room_entered(room: int):
    logger.info(f"VSTUP DO MÍSTNOSTI | místnost={room}")

def log_game_over(victory: bool, score: int, time_ms: int):
    result = "VÝHRA" if victory else "PROHRA"
    logger.info(
        f"KONEC HRY [{result}] | skóre={score} | celkový čas={time_ms // 1000}:{time_ms % 1000:03d}"
    )


# --- Hráčovy akce ---

def log_shot_fired(ammo_left: int):
    logger.debug(f"STŘELBA | zbývá nábojů={ammo_left}")

def log_reload(ammo: int):
    logger.debug(f"PŘEBITÍ | náboje obnoveny na {ammo}")

def log_dash():
    logger.debug("DASH | hráč použil dash")

def log_aoe_used(enemies_killed: int, time_ms: int):
    logger.info(
        f"AOE SCHOPNOST | zabito nepřátel={enemies_killed} | čas={time_ms // 1000}:{time_ms % 1000:03d}"
    )
