# -*- coding: utf-8 -*-
"""
Repair-Fix UART analyzer — аналізатор UART-логу EC.
© 2026 Repair-Fix, https://repair-fix.pp.ua
License: GNU GPL v3 or later (see LICENSE). Вільна програма, без гарантій.
Профіль: Steam Deck OLED (Galileo, EC ITE IT81302).

Кольори:
  зелений  — етап пройдено / подія в нормі
  жовтий   — щось не підключено або не видно (АКБ, дисплей, SSD, контролер)
  червоний — помилка або зависання
  сірий    — рядок без розшифровки

Потрібно: Python 3.8+, pyserial (pip install pyserial).
"""
import re
import sys
import time
import queue
import threading
import datetime
import webbrowser
import os

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import serial
    import serial.tools.list_ports
except ImportError:  # програма відкриває файли логів і без pyserial
    serial = None

APP_NAME = "Repair-Fix UART analyzer"
APP_VER = "1.4.2"
APP_SITE = "https://repair-fix.pp.ua"
APP_COPY = "© 2026 Repair-Fix · repair-fix.pp.ua"

OK, WARN, ERR, INFO, PLAIN = "ok", "warn", "err", "info", "plain"

# ---------------------------------------------------------------- тексти UI
UI = {
    "ru": {
        "port": "Порт:", "baud": "Скорость:", "refresh": "Обновить",
        "connect": "Подключить", "disconnect": "Отключить",
        "open": "Открыть лог…", "save": "Сохранить лог…", "clear": "Очистить",
        "lang": "Язык:", "profile": "Профиль:",
        "stage": "Этап", "status": "Состояние", "time": "Время, с", "ref": "Ожидалось, с", "dev": "Δ, с", "slow": "отклонение", "sec": "с",
        "log": "Лог", "decoded": "Расшифровка",
        "no_serial": "Модуль pyserial не установлен. Установите: pip install pyserial\nОткрытие файлов лога работает и без него.",
        "no_port": "Выберите COM-порт.",
        "open_fail": "Не удалось открыть порт {p}:\n{e}",
        "connected": "Подключено: {p} @ {b}", "disconnected": "Отключено",
        "file_loaded": "Файл разобран: {f}",
        "wait": "ожидание…", "not_seen": "не видно",
        "saved": "Сохранено: {f}",
        "verdict_ok": "Плата прошла запуск до ОС. Замечаний нет.",
        "verdict_warn": "Плата запускается, но есть замечания (жёлтые этапы).",
        "verdict_err": "Есть ошибки или зависание (красные этапы).",
        "verdict_run": "Идёт запуск…",
        "hint": "Подсказка:",
        "wiring": "Распиновка UART", "wiring_title": "Распиновка UART Steam Deck",
        "wiring_text": "Точка «UART RX» на плате → вход RX адаптера USB-UART (EC передаёт, адаптер принимает).\nGND → GND адаптера. TX адаптера не подключать.\nАдаптер 3,3 В (не 5 В), 115200, 8N1. Сначала подключите и запустите запись, потом подавайте АКБ / зарядку.",
        "lcd_note": "Steam Deck LCD — EC ITE IT5570. Анализатор настроен на OLED: на LCD лог может отличаться.",
        "oled_note": "Steam Deck OLED — EC ITE IT81302.",
    },
    "uk": {
        "port": "Порт:", "baud": "Швидкість:", "refresh": "Оновити",
        "connect": "Підключити", "disconnect": "Відключити",
        "open": "Відкрити лог…", "save": "Зберегти лог…", "clear": "Очистити",
        "lang": "Мова:", "profile": "Профіль:",
        "stage": "Етап", "status": "Стан", "time": "Час, с", "ref": "Очікувано, с", "dev": "Δ, с", "slow": "відхилення", "sec": "с",
        "log": "Лог", "decoded": "Розшифровка",
        "no_serial": "Модуль pyserial не встановлено. Встановіть: pip install pyserial\nВідкриття файлів логу працює і без нього.",
        "no_port": "Виберіть COM-порт.",
        "open_fail": "Не вдалося відкрити порт {p}:\n{e}",
        "connected": "Підключено: {p} @ {b}", "disconnected": "Відключено",
        "file_loaded": "Файл розібрано: {f}",
        "wait": "очікування…", "not_seen": "не видно",
        "saved": "Збережено: {f}",
        "verdict_ok": "Плата пройшла запуск до ОС. Зауважень немає.",
        "verdict_warn": "Плата запускається, але є зауваження (жовті етапи).",
        "verdict_err": "Є помилки або зависання (червоні етапи).",
        "verdict_run": "Триває запуск…",
        "hint": "Підказка:",
        "wiring": "Розпіновка UART", "wiring_title": "Розпіновка UART Steam Deck",
        "wiring_text": "Точка «UART RX» на платі → вхід RX адаптера USB-UART (EC передає, адаптер приймає).\nGND → GND адаптера. TX адаптера не підключати.\nАдаптер 3,3 В (не 5 В), 115200, 8N1. Спочатку підключіть і запустіть запис, потім подавайте АКБ / зарядку.",
        "lcd_note": "Steam Deck LCD — EC ITE IT5570. Аналізатор налаштовано на OLED: на LCD лог може відрізнятися.",
        "oled_note": "Steam Deck OLED — EC ITE IT81302.",
    },
    "en": {
        "port": "Port:", "baud": "Baud:", "refresh": "Refresh",
        "connect": "Connect", "disconnect": "Disconnect",
        "open": "Open log…", "save": "Save log…", "clear": "Clear",
        "lang": "Language:", "profile": "Profile:",
        "stage": "Stage", "status": "Status", "time": "Time, s", "ref": "Expected, s", "dev": "Δ, s", "slow": "deviation", "sec": "s",
        "log": "Log", "decoded": "Decoded",
        "no_serial": "pyserial is not installed. Install it: pip install pyserial\nOpening log files works without it.",
        "no_port": "Select a COM port.",
        "open_fail": "Cannot open port {p}:\n{e}",
        "connected": "Connected: {p} @ {b}", "disconnected": "Disconnected",
        "file_loaded": "File analyzed: {f}",
        "wait": "waiting…", "not_seen": "not detected",
        "saved": "Saved: {f}",
        "verdict_ok": "The board boots to the OS. No remarks.",
        "verdict_warn": "The board boots, but there are remarks (yellow stages).",
        "verdict_err": "Errors or a hang detected (red stages).",
        "verdict_run": "Booting…",
        "hint": "Hint:",
        "wiring": "UART pinout", "wiring_title": "Steam Deck UART pinout",
        "wiring_text": "Board point \u201cUART RX\u201d → RX input of the USB-UART adapter (EC transmits, adapter receives).\nGND → adapter GND. Do not connect adapter TX.\n3.3 V adapter (not 5 V), 115200, 8N1. Connect and start capture first, then apply battery / charger.",
        "lcd_note": "Steam Deck LCD — EC ITE IT5570. The analyzer is tuned for OLED: the LCD log may differ.",
        "oled_note": "Steam Deck OLED — EC ITE IT81302.",
    },
}

# ---------------------------------------------------------------- етапи
# key, ru, uk, en, еталонний час (лог «без АКБ і контролерів»)
STAGES = [
    # key, ru, uk, en, еталон від старту EC (с), еталон від G3→S5 (с), допуск (с)
    ("ec",      "Старт EC (RO → RW)",              "Старт EC (RO → RW)", "EC start (RO → RW)",              0.006, None, None),
    ("boardid", "Board ID (ревизия платы)",         "Board ID (ревізія плати)", "Board ID (board revision)",         0.29,  None, None),
    ("panel",   "Дисплей (Panel ID)",               "Дисплей (Panel ID)", "Display (Panel ID)",               0.29,  None, None),
    ("battery", "АКБ",                              "АКБ", "Battery",                              None,  None, None),
    ("ac",      "Зарядка (AC in)",                  "Зарядка (AC in)", "Charger (AC in)",                  None,  None, None),
    ("pd",      "USB-PD контракт",                  "USB-PD контракт", "USB-PD contract",                  None,  None, None),
    ("g3s5",    "G3 → S5 (дежурные шины)",          "G3 → S5 (чергові шини)", "G3 → S5 (standby rails)",           None,  0.0,   None),
    ("rsmrst",  "RSMRST → APU",                     "RSMRST → APU", "RSMRST → APU",                     None,  1.102, 0.05),
    ("s5",      "S5 готово",                        "S5 готово", "S5 ready",                        None,  1.240, 0.05),
    ("s3",      "S5 → S3 (память)",                 "S5 → S3 (пам'ять)", "S5 → S3 (memory)",                None,  1.336, 0.05),
    ("s0",      "S3 → S0 (ядро APU, PWROK)",        "S3 → S0 (ядро APU, PWROK)", "S3 → S0 (APU core, PWROK)",        None,  1.537, 0.05),
    ("vwrst",   "PSP / ABL → VW PLTRST",            "PSP / ABL → VW PLTRST", "PSP / ABL → VW PLTRST",            None,  19.90, 1.5),
    ("bios1",   "BIOS, проход 1",                   "BIOS, прохід 1", "BIOS, pass 1",                   None,  20.18, 1.5),
    ("warm",    "Тёплый сброс (Pin PLTRST)",        "Тепле скидання (Pin PLTRST)", "Warm reset (Pin PLTRST)",      None,  21.21, 1.5),
    ("abl",     "ABL: тренировка памяти",           "ABL: тренування пам'яті", "ABL: memory training",          None,  21.21, 1.5),
    ("bios2",   "BIOS, проход 2",                   "BIOS, прохід 2", "BIOS, pass 2",                   None,  37.79, 2.0),
    ("video",   "BDS: видео / логотип",             "BDS: відео / логотип", "BDS: video / logo",             None,  40.95, 2.0),
    ("usb",     "USB-устройства (контроллер)",      "USB-пристрої (контролер)", "USB devices (controller)",         None,  None, None),
    ("boot",    "Загрузочное устройство (SSD)",     "Завантажувальний пристрій (SSD)", "Boot device (SSD)",  None,  41.9,  2.0),
    ("os",      "ОС стартовала (ACPI enable)",      "ОС стартувала (ACPI enable)", "OS started (ACPI enable)",      None,  42.4,  2.0),
]
STAGE_KEYS = [s[0] for s in STAGES]

# еталонні інтервали (с) для перевірки таймінгів
REF_S0_TO_VW = 18.37      # S0 → VW PLTRST (PSP/ABL)
REF_VW_TO_PIN = 1.31      # VW PLTRST → Pin PLTRST
LIVE_SEQ_TIMEOUT = 3.0    # секвенсор: немає нового кроку N с — зависання
LIVE_PSP_TIMEOUT = 40.0   # S0 → немає PLTRST
LIVE_BIOS_TIMEOUT = 30.0  # BIOS: немає нового POST-коду

# ---------------------------------------------------------------- POST-коди
# 16-бітний код 0xYYXX із запису «P80 : [XX,YY]»
# Insyde H2O (PostCode.h) — 0x02XX; AMD AGESA — за серверними мануалами Gigabyte (EPYC),
# для Van Gogh номери можуть відрізнятися.
POST = {
    0x0209: ("Insyde SEC: кеш BIOS ROM, конец SEC", "Insyde SEC: кеш BIOS ROM, кінець SEC", "Insyde SEC: BIOS ROM cache, end of SEC"),
    0x0280: ("Insyde PEI: тест памяти", "Insyde PEI: тест пам'яті", "Insyde PEI: memory test"),
    0x0283: ("Insyde PEI: кеширование памяти", "Insyde PEI: кешування пам'яті", "Insyde PEI: memory cache setup"),
    0x0244: ("Insyde DXE: SMM Access", "Insyde DXE: SMM Access", "Insyde DXE: SMM Access"),
    0x024D: ("Insyde DXE: MTC", "Insyde DXE: MTC", "Insyde DXE: MTC"),
    0x0251: ("Insyde DXE: 8259", "Insyde DXE: 8259", "Insyde DXE: 8259"),
    0x0252: ("Insyde DXE: инициализация RTC", "Insyde DXE: ініціалізація RTC", "Insyde DXE: RTC init"),
    0x0259: ("Insyde DXE: Legacy BIOS", "Insyde DXE: Legacy BIOS", "Insyde DXE: Legacy BIOS"),
    0x0211: ("Insyde BDS: сервис горячих клавиш", "Insyde BDS: сервіс гарячих клавіш", "Insyde BDS: hotkey service"),
    0x0216: ("Insyde BDS: клавиатурный контроллер", "Insyde BDS: клавіатурний контролер", "Insyde BDS: keyboard controller"),
    0x0217: ("Insyde BDS: видео (дисплей)", "Insyde BDS: відео (дисплей)", "Insyde BDS: video (display)"),
    0x0218: ("Insyde BDS: вывод ошибок", "Insyde BDS: вивід помилок", "Insyde BDS: error output device"),
    0x021A: ("Insyde BDS: USB-шина", "Insyde BDS: USB-шина", "Insyde BDS: USB bus"),
    0x021B: ("Insyde BDS: USB-устройства", "Insyde BDS: USB-пристрої", "Insyde BDS: USB devices"),
    0x021D: ("Insyde BDS: логотип", "Insyde BDS: логотип", "Insyde BDS: logo"),
    0x0220: ("Insyde BDS: контроллер SIO (EC)", "Insyde BDS: контролер SIO (EC)", "Insyde BDS: SIO controller (EC)"),
    0x0227: ("Insyde BDS: список загрузочных устройств", "Insyde BDS: список завантажувальних пристроїв", "Insyde BDS: boot device list"),
    0x02F9: ("Insyde: НЕТ ЗАГРУЗОЧНОГО УСТРОЙСТВА", "Insyde: НЕМАЄ ЗАВАНТАЖУВАЛЬНОГО ПРИСТРОЮ", "Insyde: NO BOOT DEVICE"),
    0x02FB: ("Insyde: запуск UEFI-загрузчика", "Insyde: запуск UEFI-завантажувача", "Insyde: UEFI bootloader start"),
    0x02A7: ("Insyde SMM: ОС включила ACPI", "Insyde SMM: ОС увімкнула ACPI", "Insyde SMM: OS enabled ACPI"),
    0xE001: ("AMD ABL: структуры памяти", "AMD ABL: структури пам'яті", "AMD ABL: memory structures"),
    0xE014: ("AMD ABL: PMU, до загрузки прошивки (тренировка)", "AMD ABL: PMU, до завантаження прошивки (тренування)", "AMD ABL: PMU, before firmware load (training)"),
    0xE015: ("AMD ABL: PMU, после загрузки прошивки", "AMD ABL: PMU, після завантаження прошивки", "AMD ABL: PMU, after firmware load"),
    0xE03E: ("AMD ABL: чтение SPD", "AMD ABL: читання SPD", "AMD ABL: SPD read"),
    0xE090: ("AMD ABL: ранний GNB", "AMD ABL: ранній GNB", "AMD ABL: early GNB"),
    0xE091: ("AMD ABL: ранний интерфейс GNB", "AMD ABL: ранній інтерфейс GNB", "AMD ABL: early GNB interface"),
    0xE099: ("AMD ABL: отладочный код GNB", "AMD ABL: налагоджувальний код GNB", "AMD ABL: GNB debug code"),
    0xE0BE: ("AMD ABL: конец ABL 2", "AMD ABL: кінець ABL 2", "AMD ABL: end of ABL 2"),
    0xE0C2: ("AMD ABL: ключи UMC", "AMD ABL: ключі UMC", "AMD ABL: UMC keys"),
    0xE0C9: ("AMD ABL: тест памяти (холодный старт)", "AMD ABL: тест пам'яті (холодний старт)", "AMD ABL: memory test (cold boot)"),
    0xE0D1: ("AMD ABL: конец ABL 4", "AMD ABL: кінець ABL 4", "AMD ABL: end of ABL 4"),
    0xE0D2: ("AMD ABL: инициализация памяти ABL 2", "AMD ABL: ініціалізація пам'яті ABL 2", "AMD ABL: ABL 2 memory init"),
    0xA002: ("AMD: выход из модуля ACPI", "AMD: вихід із модуля ACPI", "AMD: ACPI module exit"),
    0xA52C: ("AMD PSP: выход из Boot Services → ОС", "AMD PSP: вихід із Boot Services → ОС", "AMD PSP: ExitBootServices → OS"),
    0xA545: ("AMD PSP: fTPM DXE", "AMD PSP: fTPM DXE", "AMD PSP: fTPM DXE"),
    0xA59E: ("AMD PSP: мейлбокс", "AMD PSP: мейлбокс", "AMD PSP: mailbox"),
    0xA5F0: ("AMD PSP: команда fTPM", "AMD PSP: команда fTPM", "AMD PSP: fTPM command"),
    0xA5F3: ("AMD PSP: ответ fTPM", "AMD PSP: відповідь fTPM", "AMD PSP: fTPM response"),
    0xA914: ("AMD NBIO: старт SMU", "AMD NBIO: старт SMU", "AMD NBIO: SMU start"),
    0xA915: ("AMD NBIO: выход SMU", "AMD NBIO: вихід SMU", "AMD NBIO: SMU exit"),
    0xA921: ("AMD NBIO: IOMMU", "AMD NBIO: IOMMU", "AMD NBIO: IOMMU"),
    0xA923: ("AMD NBIO: APCB DXE", "AMD NBIO: APCB DXE", "AMD NBIO: APCB DXE"),
    0xA955: ("AMD NBIO: линии PCIe (DXIO)", "AMD NBIO: лінії PCIe (DXIO)", "AMD NBIO: PCIe lanes (DXIO)"),
    0xAC70: ("AMD CCX: запуск ядер", "AMD CCX: запуск ядер", "AMD CCX: starting cores"),
    0xAF15: ("AMD FCH: выход DXE", "AMD FCH: вихід DXE", "AMD FCH: DXE exit"),
}
# коди помилок (червоні)
POST_ERR = {
    0xE0F9: ("AMD ABL: ОШИБКА тренировки памяти (PMU)", "AMD ABL: ПОМИЛКА тренування пам'яті (PMU)", "AMD ABL: memory training ERROR (PMU)"),
    0xA1F9: ("AMD: ОШИБКА тренировки памяти (PMU)", "AMD: ПОМИЛКА тренування пам'яті (PMU)", "AMD: memory training ERROR (PMU)"),
    0x024C: ("Insyde DXE: ошибка Variable Service (NVRAM)", "Insyde DXE: помилка Variable Service (NVRAM)", "Insyde DXE: Variable Service error (NVRAM)"),
    0x021C: ("Insyde BDS: нет консоли (видео/клавиатура)", "Insyde BDS: немає консолі (відео/клавіатура)", "Insyde BDS: no console (video/keyboard)"),
    0x0286: ("Insyde PEI: образ восстановления не найден", "Insyde PEI: образ відновлення не знайдено", "Insyde PEI: recovery image not found"),
}
MODULES = {0xE0: "AMD ABL", 0xA5: "AMD PSP", 0xA9: "AMD NBIO", 0xAA: "AMD NBIO",
           0xAC: "AMD CCX", 0xAD: "AMD DF", 0xAF: "AMD FCH", 0xA0: "AMD AGESA", 0xA1: "AMD AGESA"}

# ---------------------------------------------------------------- підказки секвенсора
# (фаза, крок від, крок до): (ru, uk). Сигнали — за референсом Chromebook, «предп.»
SEQ_HINTS = [
    ("G3->S5", 0, 3, ("дежурные шины / EN_PP3300 (шар K11)", "чергові шини / EN_PP3300 (кулька K11)", "standby rails / EN_PP3300 (ball K11)")),
    ("G3->S5", 4, 5, ("PGOOD 3,3 В / 5 В (PG_PP50, шар C15), EN 5V_S5", "PGOOD 3,3 В / 5 В (PG_PP50, кулька C15), EN 5V_S5", "PGOOD 3.3 V / 5 V (PG_PP50, ball C15), EN 5V_S5")),
    ("G3->S5", 6, 6, ("RSMRST_PWRGD_L (B14): дежурное питание APU", "RSMRST_PWRGD_L (B14): чергове живлення APU", "RSMRST_PWRGD_L (B14): APU standby power")),
    ("G3->S5", 7, 16, ("ответ APU после RSMRST: SLP_SUS_L (F8)", "відповідь APU після RSMRST: SLP_SUS_L (F8)", "APU response after RSMRST: SLP_SUS_L (F8)")),
    ("S5->S3", 0, 1, ("SLP_S4_L / SLP_S5 от APU (G11)", "SLP_S4_L / SLP_S5 від APU (G11)", "SLP_S4_L / SLP_S5 from APU (G11)")),
    ("S5->S3", 2, 9, ("шины памяти LPDDR5, PG_DRAM_OD (G2)", "шини пам'яті LPDDR5, PG_DRAM_OD (G2)", "LPDDR5 memory rails, PG_DRAM_OD (G2)")),
    ("S3->S0", 0, 1, ("SLP_S3_L от APU (B10)", "SLP_S3_L від APU (B10)", "SLP_S3_L from APU (B10)")),
    ("S3->S0", 2, 17, ("шины ядра APU (VDDCR_CPU / SOC / GFX)", "шини ядра APU (VDDCR_CPU / SOC / GFX)", "APU core rails (VDDCR_CPU / SOC / GFX)")),
    ("S3->S0", 18, 18, ("ALL_SYS_PWRGD (B2): PGOOD всех шин", "ALL_SYS_PWRGD (B2): PGOOD усіх шин", "ALL_SYS_PWRGD (B2): PGOOD of all rails")),
    ("S3->S0", 19, 20, ("PWROK в APU (P9)", "PWROK в APU (P9)", "PWROK to APU (P9)")),
]


def L(lang, ru, uk, en=None):
    if lang == "ru":
        return ru
    if lang == "en" and en is not None:
        return en
    return uk


class Analyzer:
    """Розбір рядків логу. feed() повертає (рівень, розшифровка) і оновлює етапи."""

    TS = re.compile(r"\[(\d+\.\d+)")
    P80 = re.compile(r"P80 : \[(0x[0-9a-fA-F]+),(0x[0-9a-fA-F]+)\]")

    def __init__(self, lang="uk"):
        self.lang = lang
        self.reset()

    def reset(self):
        self.stages = {k: [None, "", None] for k in STAGE_KEYS}  # рівень, текст, час
        self.t = None              # останній час EC
        self.phase = None          # G3->S5 / S5->S3 / S3->S0
        self.step = None           # останній P_Seq
        self.state = None          # S5 / S3 / S0 / G3
        self.t_s0 = None
        self.t_vw = None
        self.warm_done = False
        self.last_post = None
        self.battery_ok = None
        self._last_bat = None
        self.nlines = 0
        self.events = []           # (рівень, текст) — для підказки

    def tr(self, ru, uk, en=None):
        return L(self.lang, ru, uk, en)

    def set(self, key, level, text="", t=None, force=False):
        cur = self.stages[key]
        rank = {None: 0, OK: 1, WARN: 2, ERR: 3}
        if cur[0] == level and cur[2] is not None:
            if text:
                cur[1] = text  # той самий рівень — оновлюємо лише текст, час першої події лишаємо
            return
        if force or cur[0] is None or rank[level] > rank.get(cur[0], 0):
            self.stages[key] = [level, text, t if t is not None else self.t]

    def seq_hint(self):
        if self.phase is None or self.step is None:
            return ""
        for ph, a, b, txt in SEQ_HINTS:
            if ph == self.phase and a <= self.step <= b:
                return L(self.lang, *txt)
        return ""

    def decode_post(self, lo, hi):
        v = (hi << 8) | lo
        i = {"ru": 0, "uk": 1, "en": 2}[self.lang]
        if v in POST_ERR:
            return v, ERR, POST_ERR[v][i]
        if v in POST:
            lvl = WARN if v == 0x02F9 else OK
            return v, lvl, POST[v][i]
        mod = MODULES.get(hi)
        if mod:
            return v, PLAIN, mod + self.tr(": код не расшифрован", ": код не розшифровано", ": code not decoded")
        return v, PLAIN, self.tr("код не расшифрован", "код не розшифровано", "code not decoded")

    def feed(self, line):
        line = line.rstrip("\r\n")
        m = self.TS.search(line)
        if m:
            try:
                tv = float(m.group(1))
                if tv < 4000:  # 4294.967295 — сміття до старту таймера
                    self.t = tv
            except ValueError:
                pass
        s = line
        out = []  # (рівень, текст)

        self.nlines = getattr(self, "nlines", 0) + 1
        if any(ord(c) > 126 for c in s) and self.nlines <= 2:
            out.append((INFO, self.tr("мусор при подключении UART (норма)", "сміття під час підключення UART (норма)", "garbage on UART connect (normal)")))
        elif any(ord(c) > 126 for c in s):
            out.append((WARN, self.tr("помехи на UART (проверьте землю и скорость)", "завади на UART (перевірте землю і швидкість)", "UART noise (check ground and baud rate)")))

        if "UART initialized after reboot" in s:
            if self.stages["s0"][0] is not None:
                out.append((ERR, self.tr("EC ПЕРЕЗАГРУЗИЛСЯ во время работы", "EC ПЕРЕЗАВАНТАЖИВСЯ під час роботи", "EC REBOOTED while running")))
                self.events.append(out[-1])
            else:
                out.append((INFO, self.tr("старт EC", "старт EC", "EC start")))
        if re.search(r"Reset cause:.*(watchdog|panic|hard|brownout)", s, re.I):
            out.append((ERR, self.tr("аварийная причина сброса EC", "аварійна причина скидання EC", "abnormal EC reset cause")))
            self.events.append(out[-1])
        if re.search(r"\b(panic|exception|assert fail|watchdog)\b", s, re.I) and "Reset cause" not in s:
            out.append((ERR, self.tr("сбой прошивки EC", "збій прошивки EC", "EC firmware fault")))
            self.events.append(out[-1])

        if "Jumping to image RW" in s or "system_run_image_rw" in s:
            self.set("ec", OK, "RO → RW")
            out.append((OK, self.tr("EC перешёл в RW", "EC перейшов у RW", "EC jumped to RW")))

        m = re.search(r"BoardID average 3 times :(\d+) mV", s)
        if m:
            mv = int(m.group(1))
            if 2800 <= mv <= 3150:
                self.set("boardid", OK, f"{mv} mV (EV2)")
                out.append((OK, f"Board ID {mv} mV"))
            else:
                self.set("boardid", WARN, f"{mv} mV")
                out.append((WARN, self.tr(f"Board ID {mv} mV — нетипичная ревизия или делитель", f"Board ID {mv} mV — нетипова ревізія або дільник", f"Board ID {mv} mV — unusual revision or divider")))

        m = re.search(r"Get Panel_ID :(\d+) mV", s)
        if m:
            mv = int(m.group(1))
            if mv < 1500:
                self.set("panel", OK, self.tr(f"подключён ({mv} mV)", f"підключено ({mv} mV)", f"connected ({mv} mV)"))
                out.append((OK, self.tr("дисплей подключён", "дисплей підключено", "display connected")))
            else:
                self.set("panel", WARN, self.tr(f"не виден ({mv} mV)", f"не видно ({mv} mV)", f"not detected ({mv} mV)"))
                out.append((WARN, self.tr("дисплей не подключён (Panel ID ~3 В)", "дисплей не підключено (Panel ID ~3 В)", "display not connected (Panel ID ~3 V)")))

        m = re.search(r"bat:(\d),ac:(\d),\(err:(\d+)\)", s)
        if m and m.group(0) == getattr(self, "_last_bat", None):
            m = None  # повтор того самого статусу — не засмічуємо лог
            out.append((PLAIN, ""))
        elif m:
            self._last_bat = m.group(0)
            bat, ac, err = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if bat and err == 0:
                self.battery_ok = True
                self.set("battery", OK, self.tr("на связи", "на зв'язку", "responding"), force=True)
                out.append((OK, self.tr("АКБ на связи", "АКБ на зв'язку", "battery responding")))
            elif bat and err:
                if not self.battery_ok:
                    self.set("battery", WARN, self.tr("не отвечает (нет АКБ?)", "не відповідає (немає АКБ?)", "not responding (no battery?)"))
                out.append((WARN, self.tr("нет связи с АКБ (норма, если АКБ отключена)", "немає зв'язку з АКБ (норма, якщо АКБ відключено)", "no battery communication (normal if battery is disconnected)")))
            else:
                out.append((INFO, self.tr("статус питания", "статус живлення", "power status")))
        if "charge problem" in s:
            out.append((WARN, self.tr("АКБ не отвечает по SMBus", "АКБ не відповідає по SMBus", "battery does not answer on SMBus")))
        m = re.search(r"charge_request\((\d+)mV, (\d+)mA\)", s)
        if m:
            self.battery_ok = True
            self.set("battery", OK, self.tr(f"заряд {int(m.group(1))/1000:.1f} В", f"заряд {int(m.group(1))/1000:.1f} В", f"charging {int(m.group(1))/1000:.1f} V"), force=True)
            out.append((OK, self.tr(f"заряд {m.group(1)} мВ / {m.group(2)} мА", f"заряд {m.group(1)} мВ / {m.group(2)} мА", f"charging {m.group(1)} mV / {m.group(2)} mA")))
        if "Battery MOS status" in s or "enable PSYS" in s:
            out.append((OK, self.tr("переход на питание от АКБ", "перехід на живлення від АКБ", "switched to battery power")))

        if "evt 'AC in' assert" in s:
            self.set("ac", OK)
            out.append((OK, self.tr("зарядка подключена", "зарядку підключено", "charger connected")))
        if "evt 'AC in' de-assert" in s:
            out.append((INFO, self.tr("зарядка отключена", "зарядку відключено", "charger disconnected")))
        m = re.search(r"pd_connected voltage = (\d+)\s*,current = (\d+)", s)
        if m:
            mv, ma = int(m.group(1)), int(m.group(2))
            txt = f"{mv/1000:.0f} V / {ma/1000:.1f} A" if self.lang == "en" else f"{mv/1000:.0f} В / {ma/1000:.1f} А"
            if mv >= 9000:
                self.set("pd", OK, txt)
                out.append((OK, "USB-PD " + txt))
            else:
                self.set("pd", WARN, txt)
                out.append((WARN, self.tr(f"USB-PD только {txt}: слабый БП или кабель", f"USB-PD лише {txt}: слабкий БЖ або кабель", f"USB-PD only {txt}: weak charger or cable")))

        m = re.search(r"power state (\d+) = ([A-Z0-9>\-]+)", s)
        if m:
            st = m.group(2)
            if st == "G3->S5":
                self.phase, self.step = "G3->S5", None
                self.set("g3s5", OK, self.tr("старт", "старт", "start"))
            elif st == "S5->S3":
                self.phase, self.step = "S5->S3", None
            elif st == "S3->S0":
                self.phase, self.step = "S3->S0", None
            elif st == "S5" and "0x0003" in s:
                self.set("s5", OK); self.phase = None; self.state = "S5"
            elif st == "S3":
                self.set("s3", OK); self.phase = None; self.state = "S3"
            elif st == "S0":
                self.set("s0", OK); self.phase = None; self.state = "S0"; self.t_s0 = self.t
            elif st in ("S5->G3", "G3") and self.stages["s0"][0] is not None:
                self.state = "G3"
                out.append((WARN, self.tr("система выключилась (→ G3)", "система вимкнулася (→ G3)", "system powered off (→ G3)")))
            elif st == "S0->S3":
                out.append((WARN, self.tr("уход в сон / выключение (S0 → S3)", "перехід у сон / вимкнення (S0 → S3)", "going to sleep / shutdown (S0 → S3)")))
            out.append((OK, self.tr(f"состояние: {st}", f"стан: {st}", f"state: {st}")))

        m = re.search(r"P_Seq (\d+)", s)
        if m:
            self.step = int(m.group(1))
            out.append((OK, f"{self.phase or ''} P_Seq {self.step}"))
        if "RTC reset deassert" in s:
            out.append((OK, self.tr("сброс RTC снят", "скидання RTC знято", "RTC reset released")))
        if "5V_S5_ON" in s:
            out.append((OK, self.tr("включена 5V_S5", "увімкнено 5V_S5", "5V_S5 enabled")))
        if "S5_ON_Here" in s:
            out.append((OK, self.tr("дежурные шины S5 в норме", "чергові шини S5 у нормі", "S5 standby rails OK")))
        if "RSMRST_High_Here" in s:
            self.set("rsmrst", OK)
            out.append((OK, self.tr("RSMRST отпущен — APU получил дежурку", "RSMRST відпущено — APU отримав чергове живлення", "RSMRST released — APU has standby power")))

        if "VW PLTRST_L deasserted" in s:
            self.t_vw = self.t
            d = (self.t - self.t_s0) if (self.t is not None and self.t_s0 is not None) else None
            if d is not None and d > REF_S0_TO_VW * 1.4:
                self.set("vwrst", WARN, self.tr(f"через {d:.1f} с (эталон {REF_S0_TO_VW:.1f})", f"через {d:.1f} с (еталон {REF_S0_TO_VW:.1f})", f"after {d:.1f} s (reference {REF_S0_TO_VW:.1f})"))
                out.append((WARN, self.tr("PLTRST позже эталона: долгая тренировка памяти", "PLTRST пізніше за еталон: довге тренування пам'яті", "PLTRST later than reference: long memory training")))
            else:
                self.set("vwrst", OK, self.tr(f"через {d:.1f} с после S0", f"через {d:.1f} с після S0", f"{d:.1f} s after S0") if d is not None else "")
                out.append((OK, self.tr("APU прошёл PSP/ABL, x86 стартует", "APU пройшов PSP/ABL, x86 стартує", "APU passed PSP/ABL, x86 starts")))
        if "Pin PLTRST_L deasserted" in s:
            self.warm_done = True
            self.set("warm", OK)
            out.append((OK, self.tr("тёплый сброс платформы (норма для AMD)", "тепле скидання платформи (норма для AMD)", "platform warm reset (normal for AMD)")))

        m = self.P80.search(s)
        if m:
            lo, hi = int(m.group(1), 16), int(m.group(2), 16)
            v, lvl, txt = self.decode_post(lo, hi)
            self.last_post = (v, txt)
            out.append((lvl, f"0x{v:04X} {txt}"))
            if lvl == ERR:
                self.events.append((ERR, f"0x{v:04X} {txt}"))
            if hi == 0xE0 and v not in POST_ERR:
                self.set("abl", OK)
            if v in POST_ERR and hi in (0xE0, 0xA1):
                self.set("abl", ERR, txt)
            if v in (0x0280, 0x0283):
                self.set("bios2" if self.warm_done else "bios1", OK)
            if v in (0x0252, 0x024D) and self.warm_done:
                self.set("bios2", OK)
            if v in (0x0217, 0x021D):
                self.set("video", OK)
            if v == 0x021C:
                self.set("video", ERR, txt)
            if v in (0x021A, 0x021B):
                self.set("usb", OK, self.tr("найдены", "знайдено", "found"))
            if v == 0x02F9:
                self.set("boot", WARN, self.tr("SSD не виден", "SSD не видно", "SSD not detected"))
            if v in (0x02FB, 0xA52C):
                self.set("boot", OK, self.tr("загрузчик запущен", "завантажувач запущено", "bootloader started"))
            if v == 0x02A7:
                self.set("boot", OK, self.tr("загрузчик запущен", "завантажувач запущено", "bootloader started"))
                self.set("os", OK, "ACPI enable")
                if self.stages["usb"][0] is None:
                    self.set("usb", WARN, self.tr("не видно (нет платы контроллера?)", "не видно (немає плати контролера?)", "not detected (controller board missing?)"))

        if re.search(r"KS (disable|dPsable)", s) and self.stages["os"][0] == OK:
            out.append((OK, self.tr("ядро Linux работает с i8042", "ядро Linux працює з i8042", "Linux kernel talks to i8042")))

        if not out:
            return PLAIN, ""
        rank = {PLAIN: 0, INFO: 1, OK: 2, WARN: 3, ERR: 4}
        lvl = max((o[0] for o in out), key=lambda x: rank[x])
        return lvl, " · ".join(o[1] for o in out if o[1])

    # ---- перевірка зависань: elapsed — секунд без нових рядків (живий режим)
    def check_hang(self, elapsed, final=False):
        """Повертає (рівень, підказка) або None. final=True — кінець файлу."""
        lvl_hang = WARN if final else ERR
        tail = self.tr("лог обрывается", "лог обривається", "log ends") if final else self.tr("нет новых строк", "немає нових рядків", "no new lines")
        if self.phase is not None and (final or elapsed > LIVE_SEQ_TIMEOUT):
            hint = self.seq_hint()
            key = {"G3->S5": "rsmrst" if self.stages["rsmrst"][0] is None else "s5", "S5->S3": "s3", "S3->S0": "s0"}[self.phase]
            txt = self.tr(f"секвенсор встал: {self.phase}, P_Seq {self.step}", f"секвенсор зупинився: {self.phase}, P_Seq {self.step}", f"sequencer stopped: {self.phase}, P_Seq {self.step}")
            if hint:
                txt += self.tr(f". EC ждёт (предп.): {hint}", f". EC чекає (припущ.): {hint}", f". EC waits for (assumed): {hint}")
            self.set(key, lvl_hang, txt, force=True)
            return lvl_hang, f"{tail}: {txt}"
        if self.phase is None and self.state in ("S5", "S3") and self.stages["s0"][0] is None \
                and (final or elapsed > LIVE_SEQ_TIMEOUT):
            if self.state == "S5":
                txt = self.tr("стоит в S5: APU не снимает SLP_S5/SLP_S4 (G11) — проверьте дежурку APU, RSMRST, кнопку PWR_BTN (J5)",
                              "стоїть у S5: APU не знімає SLP_S5/SLP_S4 (G11) — перевірте чергове живлення APU, RSMRST, кнопку PWR_BTN (J5)", "stuck in S5: APU does not release SLP_S5/SLP_S4 (G11) — check APU standby power, RSMRST, PWR_BTN (J5)")
                key = "s3"
            else:
                txt = self.tr("стоит в S3: APU не снимает SLP_S3 (B10)", "стоїть у S3: APU не знімає SLP_S3 (B10)", "stuck in S3: APU does not release SLP_S3 (B10)")
                key = "s0"
            self.set(key, lvl_hang, txt, force=True)
            return lvl_hang, f"{tail}: {txt}"
        if self.state == "S0" and self.t_vw is None and (final or elapsed > LIVE_PSP_TIMEOUT):
            txt = self.tr("нет PLTRST после S0: APU не стартует (PSP, память, SPI-флеш BIOS)",
                          "немає PLTRST після S0: APU не стартує (PSP, пам'ять, SPI-флеш BIOS)", "no PLTRST after S0: APU does not start (PSP, memory, BIOS SPI flash)")
            self.set("vwrst", lvl_hang, txt, force=True)
            return lvl_hang, f"{tail}: {txt}"
        if self.t_vw is not None and self.stages["os"][0] is None and self.stages["boot"][0] != WARN \
                and (final or elapsed > LIVE_BIOS_TIMEOUT):
            last = f"0x{self.last_post[0]:04X} {self.last_post[1]}" if self.last_post else "—"
            txt = self.tr(f"BIOS встал на коде {last}", f"BIOS зупинився на коді {last}", f"BIOS stopped at code {last}")
            for k in ("abl", "bios2", "video", "boot", "os"):
                if self.stages[k][0] is None:
                    self.set(k, lvl_hang, txt, force=True)
                    break
            return lvl_hang, f"{tail}: {txt}"
        return None

    def timing(self):
        """key -> (очікуваний час, відхилення, поза допуском)."""
        res = {}
        g = self.stages["g3s5"][2] if self.stages["g3s5"][0] else None
        for key, ru, uk, en, ref_abs, ref_rel, tol in STAGES:
            lvl, _, t = self.stages[key]
            exp = None
            if ref_rel is not None and g is not None:
                exp = g + ref_rel
            elif ref_abs is not None:
                exp = ref_abs
            dev = (t - exp) if (exp is not None and t is not None and lvl == OK) else None
            res[key] = (exp, dev, bool(tol and dev is not None and abs(dev) > tol))
        return res

    def verdict(self):
        lv = [v[0] for v in self.stages.values()]
        if any(v[2] for v in self.timing().values()):
            lv.append(WARN)
        if ERR in lv:
            return ERR
        if self.stages["os"][0] == OK:
            return WARN if WARN in lv else OK
        return WARN if WARN in lv else INFO


# ======================================================================== GUI
COL = {OK: "#2ecc71", WARN: "#f1c40f", ERR: "#ff5252", INFO: "#8ab4f8", PLAIN: "#9aa3ad"}
BG = "#0e1116"


class App:
    def __init__(self, root):
        self.root = root
        self.lang = "uk"
        self.an = Analyzer(self.lang)
        self.q = queue.Queue()
        self.ser = None
        self.reader = None
        self.running = False
        self.last_rx = None
        self.raw = []
        self.hang_reported = None
        root.title(f"{APP_NAME} — Steam Deck OLED — {APP_COPY}")
        root.geometry("1480x800")
        try:  # іконка вікна — той самий icon.ico, що й у .exe
            ico = resource_path("icon.ico")
            if os.path.exists(ico):
                root.iconbitmap(default=ico)
        except Exception:
            pass
        root.minsize(980, 560)
        self.build()
        self.refresh_ports()
        self.root.after(50, self.poll)
        self.root.after(500, self.tick)

    # ------------------------------------------------------------ побудова UI
    def t(self, k):
        return UI[self.lang][k]

    def build(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("Treeview", rowheight=24, font=("Segoe UI", 10))
        st.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        top = ttk.Frame(self.root, padding=(8, 6))
        top.pack(fill="x")
        self.lb_port = ttk.Label(top); self.lb_port.pack(side="left")
        self.cb_port = ttk.Combobox(top, width=28, state="readonly"); self.cb_port.pack(side="left", padx=4)
        self.bt_ref = ttk.Button(top, command=self.refresh_ports); self.bt_ref.pack(side="left")
        self.lb_baud = ttk.Label(top); self.lb_baud.pack(side="left", padx=(12, 0))
        self.cb_baud = ttk.Combobox(top, width=8, values=["115200", "57600", "38400", "19200", "9600", "230400", "460800", "921600"])
        self.cb_baud.set("115200"); self.cb_baud.pack(side="left", padx=4)
        self.bt_conn = ttk.Button(top, command=self.toggle); self.bt_conn.pack(side="left", padx=(8, 0))
        self.bt_wire = ttk.Button(top, command=self.show_wiring); self.bt_wire.pack(side="left", padx=(4, 0))
        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=10)
        self.bt_open = ttk.Button(top, command=self.open_file); self.bt_open.pack(side="left")
        self.bt_save = ttk.Button(top, command=self.save_file); self.bt_save.pack(side="left", padx=4)
        self.bt_clear = ttk.Button(top, command=self.clear); self.bt_clear.pack(side="left")
        self.cb_lang = ttk.Combobox(top, width=4, state="readonly", values=["UA", "RU", "EN"])
        self.cb_lang.set("UA"); self.cb_lang.pack(side="right")
        self.cb_lang.bind("<<ComboboxSelected>>", self.change_lang)
        self.lb_lang = ttk.Label(top); self.lb_lang.pack(side="right", padx=4)

        self.verdict = tk.Label(self.root, anchor="w", padx=10, pady=6, font=("Segoe UI", 12, "bold"), fg="#111")
        self.verdict.pack(fill="x")

        pw = ttk.PanedWindow(self.root, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        left = ttk.Frame(pw)
        self.txt = tk.Text(left, bg=BG, fg="#d6dbe1", insertbackground="#fff", wrap="none",
                           font=("Consolas", 10), undo=False)
        ys = ttk.Scrollbar(left, orient="vertical", command=self.txt.yview)
        xs = ttk.Scrollbar(left, orient="horizontal", command=self.txt.xview)
        self.txt.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.txt.grid(row=0, column=0, sticky="nsew"); ys.grid(row=0, column=1, sticky="ns"); xs.grid(row=1, column=0, sticky="ew")
        left.rowconfigure(0, weight=1); left.columnconfigure(0, weight=1)
        for k, c in COL.items():
            self.txt.tag_configure(k, foreground=c)
            self.txt.tag_configure(k + "_d", foreground=c, font=("Segoe UI", 9, "italic"))
        self.txt.tag_configure("ts", foreground="#5b6470")
        self.txt.configure(state="disabled")
        pw.add(left, weight=3)

        right = ttk.Frame(pw)
        self.tree = ttk.Treeview(right, columns=("st", "t", "ref", "dev"), show="tree headings", height=22)
        self.tree.column("#0", width=215, stretch=True)
        self.tree.column("st", width=215, stretch=True)
        self.tree.column("t", width=80, anchor="e", stretch=False)
        self.tree.column("ref", width=95, anchor="e", stretch=False)
        self.tree.column("dev", width=70, anchor="e", stretch=False)
        for k, c in COL.items():
            self.tree.tag_configure(k, background={OK: "#d8f5e3", WARN: "#fff3c4", ERR: "#ffd9d9", INFO: "#e6eefc", PLAIN: "#f2f3f5"}[k])
        self.tree.pack(fill="both", expand=True)
        pw.add(right, weight=2)

        bottom = ttk.Frame(self.root)
        bottom.pack(fill="x")
        self.status = ttk.Label(bottom, anchor="w", padding=(10, 4))
        self.status.pack(side="left", fill="x", expand=True)
        link = tk.Label(bottom, text=APP_COPY, fg="#0a5cff", cursor="hand2", padx=10, font=("Segoe UI", 9, "underline"))
        link.pack(side="right")
        link.bind("<Button-1>", lambda e: webbrowser.open(APP_SITE))
        self.apply_lang()

    def apply_lang(self):
        self.an.lang = self.lang
        self.lb_port.configure(text=self.t("port")); self.lb_baud.configure(text=self.t("baud"))
        self.bt_ref.configure(text=self.t("refresh")); self.bt_wire.configure(text=self.t("wiring"))
        self.bt_conn.configure(text=self.t("disconnect") if self.running else self.t("connect"))
        self.bt_open.configure(text=self.t("open")); self.bt_save.configure(text=self.t("save"))
        self.bt_clear.configure(text=self.t("clear")); self.lb_lang.configure(text=self.t("lang"))
        self.tree.heading("#0", text=self.t("stage")); self.tree.heading("st", text=self.t("status"))
        self.tree.heading("t", text=self.t("time")); self.tree.heading("ref", text=self.t("ref")); self.tree.heading("dev", text=self.t("dev"))
        self.render_stages()

    def change_lang(self, _=None):
        self.lang = {"RU": "ru", "EN": "en"}.get(self.cb_lang.get(), "uk")
        self.apply_lang()
        if self.raw and not self.running:  # перерозбір тексту новою мовою
            lines = list(self.raw)
            self.clear(keep_raw=False)
            for ln in lines:
                self.add_line(ln, live=False)
            self.finish_file()

    # ------------------------------------------------------------ схема підключення
    def show_wiring(self):
        try:
            import wiring_images as wi
        except ImportError:
            wi = None
        win = tk.Toplevel(self.root)
        win.title(self.t("wiring_title"))
        win.transient(self.root)
        tk.Label(win, text=self.t("wiring_text"), justify="left", anchor="w", wraplength=780,
                 font=("Segoe UI", 10), padx=12, pady=10).pack(fill="x")
        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._wire_imgs = []
        for title, attr, note in (("Steam Deck OLED", "OLED", "oled_note"), ("Steam Deck LCD", "LCD", "lcd_note")):
            fr = ttk.Frame(nb, padding=6)
            if wi is not None:
                img = tk.PhotoImage(data="".join(getattr(wi, attr)))
                self._wire_imgs.append(img)
                tk.Label(fr, image=img).pack()
            tk.Label(fr, text=self.t(note), anchor="w", font=("Segoe UI", 10, "bold"), pady=6).pack(fill="x")
            nb.add(fr, text=title)

    # ------------------------------------------------------------ порт
    def refresh_ports(self):
        if serial is None:
            self.cb_port["values"] = []
            return
        ports = [f"{p.device} — {p.description}" for p in serial.tools.list_ports.comports()]
        self.cb_port["values"] = ports
        if ports and not self.cb_port.get():
            self.cb_port.set(ports[0])

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        if serial is None:
            messagebox.showerror(APP_NAME, self.t("no_serial")); return
        sel = self.cb_port.get()
        if not sel:
            messagebox.showwarning(APP_NAME, self.t("no_port")); return
        port = sel.split(" — ")[0]
        try:
            baud = int(self.cb_baud.get())
            self.ser = serial.Serial(port, baud, timeout=0.2)
        except Exception as e:
            messagebox.showerror(APP_NAME, self.t("open_fail").format(p=port, e=e)); return
        self.clear()
        self.running = True
        self.last_rx = time.time()
        self.reader = threading.Thread(target=self.read_loop, daemon=True)
        self.reader.start()
        self.bt_conn.configure(text=self.t("disconnect"))
        self.status.configure(text=self.t("connected").format(p=port, b=baud))

    def stop(self):
        self.running = False
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass
        self.ser = None
        self.bt_conn.configure(text=self.t("connect"))
        self.status.configure(text=self.t("disconnected"))

    def read_loop(self):
        buf = b""
        while self.running:
            try:
                chunk = self.ser.read(256)
            except Exception as e:
                self.q.put(("__err__", str(e))); break
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                ln, buf = buf.split(b"\n", 1)
                self.q.put(("line", ln.decode("latin-1")))

    def poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "line":
                    # періодичний статус АКБ не рахуємо як «рух» запуску
                    if not re.match(r"\s*(bat:\d|charge_request)", val):
                        self.last_rx = time.time()
                    self.add_line(val, live=True)
                else:
                    self.stop(); self.status.configure(text=val)
        except queue.Empty:
            pass
        self.root.after(50, self.poll)

    def tick(self):
        if self.running and self.last_rx:
            r = self.an.check_hang(time.time() - self.last_rx)
            if r and r != self.hang_reported:
                self.hang_reported = r
                self.write_note(*r)
                self.render_stages()
        self.root.after(500, self.tick)

    # ------------------------------------------------------------ лог
    def add_line(self, ln, live):
        ln = ln.rstrip("\r")
        if not ln.strip():
            return
        self.raw.append(ln)
        lvl, dec = self.an.feed(ln)
        self.hang_reported = None
        self.txt.configure(state="normal")
        stamp = datetime.datetime.now().strftime("%H:%M:%S ") if live else ""
        if stamp:
            self.txt.insert("end", stamp, "ts")
        self.txt.insert("end", ln, lvl)
        if dec:
            self.txt.insert("end", "   ← " + dec, lvl + "_d")
        self.txt.insert("end", "\n")
        self.txt.configure(state="disabled")
        self.txt.see("end")
        self.render_stages()

    def write_note(self, lvl, text):
        self.txt.configure(state="normal")
        self.txt.insert("end", "▶ " + text + "\n", lvl)
        self.txt.configure(state="disabled")
        self.txt.see("end")
        self.status.configure(text=self.t("hint") + " " + text)

    def render_stages(self):
        self.tree.delete(*self.tree.get_children())
        tm = self.an.timing()
        for key, ru, uk, en, ref_abs, ref_rel, tol in STAGES:
            lvl, text, t = self.an.stages[key]
            exp, dev, bad = tm[key]
            name = {"ru": ru, "uk": uk, "en": en}[self.lang]
            st = text or {OK: "OK", WARN: self.t("not_seen"), ERR: "!"}.get(lvl, self.t("wait"))
            tag = lvl or PLAIN
            if bad:
                tag = WARN
                st = f"{st} · {self.t('slow')} {dev:+.2f} {self.t('sec')}"
            self.tree.insert("", "end", text=name, values=(
                st,
                f"{t:.3f}" if (t is not None and lvl) else "",
                f"{exp:.2f}" if exp is not None else "",
                f"{dev:+.3f}" if dev is not None else ""), tags=(tag,))
        v = self.an.verdict()
        msg = {OK: "verdict_ok", WARN: "verdict_warn", ERR: "verdict_err", INFO: "verdict_run"}[v]
        bg = {OK: "#d8f5e3", WARN: "#fff3c4", ERR: "#ffd9d9", INFO: "#e6eefc"}[v]
        self.verdict.configure(text=self.t(msg), bg=bg)

    def open_file(self):
        fn = filedialog.askopenfilename(filetypes=[("Log", "*.txt *.log"), ("*", "*.*")])
        if fn:
            self.load_path(fn)

    def load_path(self, fn):
        if self.running:
            self.stop()
        with open(fn, "rb") as f:
            blob = f.read()
        try:
            data = blob.decode("utf-8")
        except UnicodeDecodeError:
            data = blob.decode("latin-1")
        self.clear()
        for ln in data.splitlines():
            self.add_line(ln, live=False)
        self.finish_file()
        self.status.configure(text=self.t("file_loaded").format(f=fn))

    def finish_file(self):
        r = self.an.check_hang(0, final=True)
        if r:
            self.write_note(*r)
        self.render_stages()

    def save_file(self):
        fn = filedialog.asksaveasfilename(defaultextension=".txt",
                                          initialfile=datetime.datetime.now().strftime("deck_uart_%Y%m%d_%H%M%S.txt"))
        if not fn:
            return
        with open(fn, "w", encoding="utf-8") as f:
            f.write("\n".join(self.raw) + "\n")
        self.status.configure(text=self.t("saved").format(f=fn))

    def clear(self, keep_raw=False):
        self.an.reset()
        if not keep_raw:
            self.raw = []
        self.txt.configure(state="normal"); self.txt.delete("1.0", "end"); self.txt.configure(state="disabled")
        self.render_stages()


def resource_path(name):
    """Файл поруч зі скриптом або всередині .exe (PyInstaller --add-data)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, "frozen", False) else __file__)))
    return os.path.join(base, name)


def main():
    root = tk.Tk()
    app = App(root)
    if len(sys.argv) > 1:  # файл логу можна перетягнути на .exe
        root.after(200, lambda: app.load_path(sys.argv[1]))
    root.mainloop()


if __name__ == "__main__":
    main()
