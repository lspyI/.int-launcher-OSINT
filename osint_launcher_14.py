#!/usr/bin/env python3
"""
.INT OSINT Launcher — CLI-инструмент для OSINT-анализа.
Требует Python 3.7+  |  pip install rich gdown
"""

import os
import re
import sys
import time
import shutil
import subprocess
import platform
import urllib.request
import json
import tarfile
import zipfile
import datetime

# ── rich ──────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
    from rich import box
    RICH_OK = True
except ImportError:
    RICH_OK = False

# ── gdown ─────────────────────────────────────────────────────────
def _try_import_gdown():
    try:
        import gdown as _gdown
        return _gdown, True
    except ImportError:
        return None, False

gdown, GDOWN_OK = _try_import_gdown()

console = Console() if RICH_OK else None

# ═════════════════════════════════════════════════════════════════
#  ЦВЕТА / ANSI (fallback когда rich недоступен)
# ═════════════════════════════════════════════════════════════════
RESET = "\033[0m";  BOLD = "\033[1m"

def _rgb(r, g, b): return f"\033[38;2;{r};{g};{b}m"

GRAD = [
    _rgb(140, 60, 255), _rgb(160, 80, 255), _rgb(185,100,255),
    _rgb(210,110,240),  _rgb(235,100,210),  _rgb(255, 90,180),
]
CA   = _rgb(200,100,255)   # фиолетовый акцент
CP   = _rgb(255,100,190)   # розовый
CDP  = _rgb(110, 60,160)   # тёмно-фиолетовый
CW   = "\033[97m"          # белый
CGR  = "\033[90m"          # серый
CCY  = _rgb(100,220,255)   # циановый
CGRN = "\033[92m"          # зелёный  (успех)
CYEL = "\033[93m"          # жёлтый   (предупреждение)
CRED = "\033[91m"          # красный  (ошибка)


def _cp(color, text, end="\n"):
    print(f"{color}{text}{RESET}", end=end)

# ── Обёртки с rich / fallback ────────────────────────────────────
def msg_ok(text: str):
    if RICH_OK:
        console.print(f"  [bold green]✓[/bold green] [green]{text}[/green]")
    else:
        _cp(CGRN, f"  ✓ {text}")

def msg_warn(text: str):
    if RICH_OK:
        console.print(f"  [bold yellow][!][/bold yellow] [yellow]{text}[/yellow]")
    else:
        _cp(CYEL, f"  [!] {text}")

def msg_err(text: str):
    if RICH_OK:
        console.print(f"  [bold red][✗][/bold red] [red]{text}[/red]")
    else:
        _cp(CRED, f"  [✗] {text}")

def msg_info(text: str):
    if RICH_OK:
        console.print(f"  [white]{text}[/white]")
    else:
        _cp(CW, f"  {text}")

def msg_step(step: str, text: str):
    if RICH_OK:
        console.print(f"  [bold magenta]{step}[/bold magenta] [white]{text}[/white]")
    else:
        _cp(CA, f"  {step} {text}")

# ═════════════════════════════════════════════════════════════════
#  УТИЛИТЫ
# ═════════════════════════════════════════════════════════════════
def clear():
    os.system("cls" if platform.system() == "Windows" else "clear")

def pause(s=2):
    time.sleep(s)

def detect_os():
    s = platform.system().lower()
    if s == "darwin":  return "mac"
    if s == "windows": return "windows"
    return "linux"

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR     = os.path.join(BASE_DIR, "tools")
DOWNLOADS_DIR = os.path.join(TOOLS_DIR, "downloads")
RESULTS_DIR   = os.path.join(BASE_DIR, "results")

def ensure_dirs(*dirs):
    for d in dirs:
        os.makedirs(d, exist_ok=True)

def get_path(prompt="") -> str:
    raw = input(prompt).strip()
    return raw.strip("'\"")

# ═════════════════════════════════════════════════════════════════
#  ASCII-ЛОГОТИП  .INT  с градиентом
# ═════════════════════════════════════════════════════════════════
DOT_INT = [
    r"  ░░      ██╗███╗  ██╗████████╗  ",
    r"  ░░      ██║████╗ ██║╚══██╔══╝  ",
    r"  ██╗     ██║██╔██╗██║   ██║     ",
    r"  ╚═╝     ██║██║╚████║   ██║     ",
    r"  ██╗     ██║██║ ╚███║   ██║     ",
    r"  ╚═╝     ╚═╝╚═╝  ╚══╝   ╚═╝     ",
]
BT = "  ╔══════════════════════════════════════════════════════╗"
BB = "  ╚══════════════════════════════════════════════════════╝"
BE = "  ║                                                      ║"


def _row(inner_ansi: str, inner_plain_len: int, width=52):
    pad = width - inner_plain_len
    print(f"  {CDP}║{RESET}  {inner_ansi}{' ' * max(pad, 0)}  {CDP}║{RESET}")


def show_logo():
    _cp(CDP, BT)
    _cp(CDP, BE)
    for i, line in enumerate(DOT_INT):
        c = GRAD[i % len(GRAD)]
        print(f"  {CDP}║{RESET}  {BOLD}{c}{line}{RESET}  {CDP}║{RESET}")
    _cp(CDP, BE)
    ltext = "L  A  U  N  C  H  E  R"
    _row(f"{CP}{BOLD}{ltext}{RESET}", len(ltext))
    stext = "─── Open Source Intelligence ───"
    _row(f"{CDP}{stext}{RESET}", len(stext))
    _cp(CDP, BE)
    ttext = "[ ExifTool  ·  PhoneInfoga  ·  GeoOSINT ]"
    _row(f"{CA}{ttext}{RESET}", len(ttext))
    vtext = "v3.0  ·  .int launcher"
    _row(f"{CGR}{vtext}{RESET}", len(vtext))
    _cp(CDP, BE)
    _cp(CDP, BB)
    print()


def section_header(title: str):
    if RICH_OK:
        t = Text(f" {title} ", justify="center")
        t.stylize("bold magenta")
        console.print(Panel(t, border_style="dark_violet", padding=(0, 2)))
        print()
    else:
        w = 52
        _cp(CDP, f"\n  ╔{'─'*w}╗")
        pad = (w - len(title) - 2) // 2
        _cp(CA, f"  ║{' '*pad} {BOLD}{title}{RESET}{CA}{' '*(w-pad-len(title)-1)}║")
        _cp(CDP, f"  ╚{'─'*w}╝\n")


def submenu(title: str, items: list[tuple[str,str,str]]) -> str:
    """items = [(num, label, desc), ...]  Возвращает введённый номер."""
    if RICH_OK:
        t = Table(box=box.ROUNDED, border_style="dark_violet", show_header=False,
                  padding=(0, 1), expand=False)
        t.add_column(justify="center", style="bold magenta", no_wrap=True)
        t.add_column(style="bold white", no_wrap=True)
        t.add_column(style="dim white", no_wrap=True)
        for num, label, desc in items:
            t.add_row(f"[{num}]", label, desc)
        console.print(Panel(t, title=f"[bold magenta]{title}[/bold magenta]",
                            border_style="dark_violet", padding=(0, 1)))
        print()
        return input(f"  {CA}›{RESET} {CW}Выберите: {RESET}").strip()
    else:
        _cp(CDP, f"  ┌{'─'*43}┐")
        pad = (43 - len(title)) // 2
        _cp(CA, f"  │{' '*pad}{BOLD}{title}{RESET}{CA}{' '*(43-pad-len(title))}│")
        _cp(CDP, f"  ├{'─'*43}┤")
        for num, label, desc in items:
            n = f"{CP}[{CW}{BOLD}{num}{RESET}{CP}]{RESET}"
            ln = f"{CW}{BOLD}{label}{RESET}"
            dn = f"{CGR}{desc}{RESET}"
            vl = 2+len(num)+2+len(label)+2+len(desc)+1
            print(f"  {CDP}│{RESET}  {n}  {ln}  {dn}{' '*max(43-vl,1)}{CDP}│{RESET}")
        _cp(CDP, f"  └{'─'*43}┘")
        print()
        return input(f"  {CA}›{RESET} {CW}Выберите: {RESET}").strip()


# ═════════════════════════════════════════════════════════════════
#  ЗАВИСИМОСТИ: проверка и установка rich / gdown
# ═════════════════════════════════════════════════════════════════
def _pip_install(package: str) -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", package, "--quiet"],
            check=True
        )
        return True
    except Exception:
        return False


def _ensure_gdown() -> bool:
    """Гарантирует наличие gdown. При отсутствии — устанавливает и переимпортирует."""
    global gdown, GDOWN_OK
    if GDOWN_OK:
        return True
    msg_info("gdown не найден. Устанавливаю...")
    ok = _pip_install("gdown")
    if ok:
        gdown, GDOWN_OK = _try_import_gdown()
        if GDOWN_OK:
            msg_ok("gdown установлен.")
            return True
    msg_err("Не удалось установить gdown. Попробуйте вручную: pip install gdown")
    return False


def _gdown_version() -> str:
    """Возвращает версию gdown или '?'."""
    try:
        import importlib.metadata
        return importlib.metadata.version("gdown")
    except Exception:
        try:
            return gdown.__version__
        except Exception:
            return "?"


def ensure_dependencies():
    """Устанавливает rich если не установлен (gdown устанавливается отдельно перед скачиванием)."""
    global RICH_OK, console
    if RICH_OK:
        return
    print("\n  Установка зависимости: rich ...")
    r = _pip_install("rich")
    print(f"  {'✓' if r else '✗'} rich")
    if r:
        os.execv(sys.executable, [sys.executable] + sys.argv)


def _gdown_download(url: str, output: str, quiet: bool = False) -> bool:
    """
    Универсальная обёртка для gdown.download().
    Пробует с fuzzy=True (gdown >= 4.4), при TypeError — без fuzzy (старые версии).
    Выводит версию gdown перед скачиванием для отладки.
    """
    ver = _gdown_version()
    msg_info(f"gdown версия: {ver}")
    msg_info(f"URL: {url}")

    # Попытка 1 — с fuzzy (gdown >= 4.4)
    try:
        gdown.download(url, output, quiet=quiet, fuzzy=True)
        return True
    except TypeError:
        pass  # fuzzy не поддерживается — пробуем без него
    except Exception as e:
        msg_err(f"Ошибка скачивания (попытка 1): {e}")
        return False

    # Попытка 2 — без fuzzy (gdown < 4.4)
    msg_info("Параметр fuzzy не поддерживается в этой версии, повторяю без него...")
    try:
        gdown.download(url, output, quiet=quiet)
        return True
    except Exception as e:
        msg_err(f"Ошибка скачивания (попытка 2): {e}")
        return False


# ═════════════════════════════════════════════════════════════════
#  EXIFTOOL — пути
# ═════════════════════════════════════════════════════════════════
EXIFTOOL_DIR     = os.path.join(TOOLS_DIR, "exiftool")
EXIFTOOL_GDRIVE  = "https://drive.google.com/uc?export=download&id=1l-lpFYiJSqG5-vtQELNHBRO_XrOs7A4Y"
EXIFTOOL_RESULTS = os.path.join(RESULTS_DIR, "exiftool")

# Динамический путь к exiftool.exe — определяется после установки через os.walk()
# Не фиксирован: архив может распаковываться в tools/exiftool/exiftool/exiftool.exe
# или любую другую вложенную структуру.
EXIFTOOL_PATH: str | None = None


def _find_exe_recursive(search_dir: str) -> str | None:
    """
    Рекурсивно ищет exiftool.exe внутри search_dir через os.walk().
    Сначала ищет точное совпадение 'exiftool.exe',
    затем fallback — любой файл exiftool*.exe.
    """
    # Проход 1: точное имя
    for root, _, files in os.walk(search_dir):
        for f in files:
            if f.lower() == "exiftool.exe":
                return os.path.join(root, f)
    # Проход 2: любой exiftool*.exe (например exiftool(-k).exe)
    for root, _, files in os.walk(search_dir):
        for f in files:
            if f.lower().startswith("exiftool") and f.lower().endswith(".exe"):
                return os.path.join(root, f)
    return None


def resolve_exiftool_path() -> str | None:
    """
    Ищет exiftool.exe в EXIFTOOL_DIR рекурсивно.
    Обновляет глобальную EXIFTOOL_PATH и возвращает найденный путь (или None).
    """
    global EXIFTOOL_PATH
    if not os.path.isdir(EXIFTOOL_DIR):
        EXIFTOOL_PATH = None
        return None
    found = _find_exe_recursive(EXIFTOOL_DIR)
    EXIFTOOL_PATH = found
    if found:
        msg_ok(f"[+] Найден ExifTool: {found}")
    return found


def exiftool_installed() -> bool:
    """True если exiftool.exe найден где-либо внутри EXIFTOOL_DIR."""
    return resolve_exiftool_path() is not None


def get_exiftool_exe() -> str | None:
    """Возвращает актуальный путь к exiftool.exe (ищет рекурсивно)."""
    global EXIFTOOL_PATH
    if EXIFTOOL_PATH and os.path.isfile(EXIFTOOL_PATH):
        return EXIFTOOL_PATH
    return resolve_exiftool_path()


# ── Установка ────────────────────────────────────────────────────
def _unpack_archive(archive_path: str, extract_dir: str) -> bool:
    """Распаковывает zip или tar.gz в extract_dir."""
    try:
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(extract_dir)
        else:
            with tarfile.open(archive_path, "r:*") as tf:
                tf.extractall(extract_dir)
        return True
    except Exception as e:
        msg_err(f"Ошибка распаковки: {e}")
        return False


def install_exiftool() -> bool:
    """Скачивает полный архив ExifTool с Google Drive через gdown и распаковывает."""
    ensure_dirs(TOOLS_DIR, EXIFTOOL_DIR, DOWNLOADS_DIR)
    archive_path = os.path.join(DOWNLOADS_DIR, "exiftool_full.zip")
    extract_tmp  = os.path.join(DOWNLOADS_DIR, "exiftool_extracted")

    # ── Шаг 1: gdown ─────────────────────────────────────────────
    msg_step("·", "Проверка / установка gdown...")
    if not _ensure_gdown():
        return False

    # ── Шаг 2: скачивание ─────────────────────────────────────────
    msg_step("·", "Скачивание архива ExifTool с Google Drive...")
    if not _gdown_download(EXIFTOOL_GDRIVE, archive_path, quiet=False):
        return False

    if not os.path.isfile(archive_path) or os.path.getsize(archive_path) < 1024:
        msg_err("Архив не скачан или повреждён.")
        return False

    # ── Шаг 3: распаковка во временную папку ──────────────────────
    msg_step("·", f"Распаковка архива → {extract_tmp}")
    if os.path.isdir(extract_tmp):
        shutil.rmtree(extract_tmp)
    if not _unpack_archive(archive_path, extract_tmp):
        return False
    msg_ok("Распаковка завершена.")

    # ── Шаг 4: копирование полной структуры в tools/exiftool/ ─────
    msg_step("·", f"Установка файлов → {EXIFTOOL_DIR}")
    if os.path.isdir(EXIFTOOL_DIR):
        shutil.rmtree(EXIFTOOL_DIR)
    os.makedirs(EXIFTOOL_DIR, exist_ok=True)
    for item in os.listdir(extract_tmp):
        src = os.path.join(extract_tmp, item)
        dst = os.path.join(EXIFTOOL_DIR, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    # ── Шаг 5: рекурсивный поиск exiftool.exe (любая вложенность) ─
    msg_step("·", "Поиск exiftool.exe внутри tools/exiftool/ ...")
    found = resolve_exiftool_path()   # обновляет EXIFTOOL_PATH через os.walk()

    if found:
        msg_ok(f"[+] ExifTool успешно установлен.")
        return True
    else:
        msg_err("exiftool.exe не найден после установки.")
        msg_info(f"Содержимое {EXIFTOOL_DIR}:")
        for root, dirs, files in os.walk(EXIFTOOL_DIR):
            level = root.replace(EXIFTOOL_DIR, "").count(os.sep)
            indent = "  " * level
            msg_info(f"  {indent}{os.path.basename(root)}/")
            for fname in files:
                msg_info(f"  {indent}  {fname}")
        return False


# ── Удаление ─────────────────────────────────────────────────────
def uninstall_exiftool():
    """Удаляет папку tools/exiftool и временные архивы."""
    removed = False
    if os.path.isdir(EXIFTOOL_DIR):
        shutil.rmtree(EXIFTOOL_DIR)
        removed = True
    # Удаляем архивы ExifTool из downloads
    if os.path.isdir(DOWNLOADS_DIR):
        for f in os.listdir(DOWNLOADS_DIR):
            if "exiftool" in f.lower():
                fp = os.path.join(DOWNLOADS_DIR, f)
                if os.path.isfile(fp):
                    os.remove(fp)
                elif os.path.isdir(fp):
                    shutil.rmtree(fp)
    if removed:
        msg_ok("[+] ExifTool успешно удалён.")
    else:
        msg_warn("ExifTool не был установлен.")
    pause(2)


# ── Проверка / предложение установки ─────────────────────────────
def check_exiftool() -> bool:
    """Проверяет наличие, при отсутствии предлагает установить. True = готов."""
    if get_exiftool_exe() is not None:
        return True

    msg_warn("[!] ExifTool не найден.")
    ans = input(f"  {CA}Установить? (Y/N): {RESET}").strip().upper()
    if ans != "Y":
        msg_info("Возврат в меню...")
        pause(1)
        return False

    success = install_exiftool()
    if not success:
        pause(3)
        return False
    pause(2)
    return get_exiftool_exe() is not None


# ── Сохранение результата ─────────────────────────────────────────
def save_exiftool_result(output: str) -> str:
    """Сохраняет вывод в results/exiftool/YYYY-MM-DD_HH-MM-SS.txt."""
    ensure_dirs(RESULTS_DIR, EXIFTOOL_RESULTS)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fpath = os.path.join(EXIFTOOL_RESULTS, f"{ts}.txt")
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(output)
    return fpath


# ── Анализ файла ──────────────────────────────────────────────────
def exiftool_analyze() -> str | None:
    """Запускает exiftool, выводит результат. Возвращает вывод или None."""
    if RICH_OK:
        console.print(f"\n  [magenta]Перетащите изображение сюда или укажите путь к файлу:[/magenta]")
    else:
        _cp(CA, "\n  Перетащите изображение сюда или укажите путь к файлу:")

    path = get_path(f"  {CP}›{RESET} ")
    if not path:
        msg_warn("Путь не указан.")
        pause(1)
        return None
    if not os.path.isfile(path):
        msg_err(f"Файл не найден: {path}")
        pause(2)
        return None

    if RICH_OK:
        console.print(f"\n  [white]Анализ:[/white] [cyan]{path}[/cyan]")
        console.rule(style="dark_violet")
    else:
        _cp(CW, f"\n  Анализ: {CCY}{path}{RESET}")
        _cp(CDP, "  " + "─" * 54)

    try:
        exe = get_exiftool_exe()
        if not exe:
            msg_err("exiftool.exe не найден. Переустановите ExifTool.")
            pause(2)
            return None
        result = subprocess.run(
            [exe, path],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        output = result.stdout or result.stderr
    except Exception as e:
        msg_err(f"Ошибка запуска exiftool: {e}")
        pause(2)
        return None

    # Вывод с подсветкой ключ : значение
    for line in output.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            if RICH_OK:
                console.print(f"  [magenta]{key}[/magenta]:[white]{val}[/white]")
            else:
                print(f"  {CA}{key}{RESET}:{CW}{val}{RESET}")
        else:
            msg_info(line)

    if RICH_OK:
        console.rule(style="dark_violet")
    else:
        _cp(CDP, "\n  " + "─" * 54)

    return output


# ── Подменю после анализа ─────────────────────────────────────────
def exiftool_after_analysis(output: str):
    while True:
        # НЕ очищаем экран — данные остаются видны сверху
        if RICH_OK:
            console.rule(style="dark_violet")
        else:
            _cp(CDP, "\n  " + "─" * 54)
        choice = submenu("Действия", [
            ("1", "Сохранить результат в .txt", ""),
            ("2", "Новый анализ",               ""),
            ("3", "Назад",                      "в меню ExifTool"),
        ])
        if choice == "1":
            fpath = save_exiftool_result(output)
            msg_ok(f"[+] Результат сохранён:\n  {fpath}")
            pause(2)
        elif choice == "2":
            return "new"
        elif choice == "3":
            return "back"
        else:
            msg_warn("Неверный ввод.")
            pause(1)


# ═════════════════════════════════════════════════════════════════
#  EXIFTOOL — главное подменю
# ═════════════════════════════════════════════════════════════════
def run_exiftool():
    while True:
        clear()
        section_header("E X I F T O O L")

        # Статус установки
        status = "[green]установлен[/green]" if exiftool_installed() else "[red]не установлен[/red]"
        if RICH_OK:
            console.print(f"  Статус: {status}\n")
        else:
            st = "установлен" if exiftool_installed() else "не установлен"
            _cp(CGRN if exiftool_installed() else CRED, f"  Статус: {st}\n")

        choice = submenu("ExifTool", [
            ("1", "Анализ изображения",    "читать метаданные файла"),
            ("2", "Переустановить ExifTool","удалить и скачать заново"),
            ("3", "Удалить ExifTool",       "полное удаление"),
            ("4", "Назад",                  "главное меню"),
        ])

        if choice == "1":
            # Проверка / установка
            if not check_exiftool():
                continue
            # Цикл анализа
            while True:
                clear()
                section_header("E X I F T O O L  ·  Анализ")
                output = exiftool_analyze()
                if output is None:
                    break
                action = exiftool_after_analysis(output)
                if action == "back":
                    break
                # action == "new" → снова анализируем

        elif choice == "2":
            clear()
            section_header("E X I F T O O L  ·  Переустановка")
            msg_step("·", "Удаление текущей версии...")
            if os.path.isdir(EXIFTOOL_DIR):
                shutil.rmtree(EXIFTOOL_DIR)
            msg_ok("Старая версия удалена.")
            install_exiftool()
            pause(2)

        elif choice == "3":
            clear()
            section_header("E X I F T O O L  ·  Удаление")
            ans = input(f"  {CYEL}Вы уверены? (Y/N): {RESET}").strip().upper()
            if ans == "Y":
                uninstall_exiftool()
            else:
                msg_info("Отменено.")
                pause(1)

        elif choice == "4":
            return

        else:
            msg_warn("Неверный ввод.")
            pause(1)


# ═════════════════════════════════════════════════════════════════
#  PHONEINFOGA — пути и установка (без изменений)
# ═════════════════════════════════════════════════════════════════
PHONEINFOGA_DIR = os.path.join(TOOLS_DIR, "phoneinfoga")
PHONEINFOGA_EXE = os.path.join(PHONEINFOGA_DIR, "phoneinfoga.exe")


def get_phoneinfoga_exe() -> str | None:
    return PHONEINFOGA_EXE if os.path.isfile(PHONEINFOGA_EXE) else None


def install_phoneinfoga_windows() -> bool:
    msg_step("·", "Запрос к GitHub API...")
    api_url = "https://api.github.com/repos/sundowndev/phoneinfoga/releases/latest"
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "osint-launcher/3.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            release = json.loads(resp.read().decode())
    except Exception as e:
        msg_err(f"Ошибка GitHub API: {e}")
        return False

    tag = release.get("tag_name", "?")
    msg_info(f"Последний релиз: {tag}")

    asset_name = "phoneinfoga_Windows_x86_64.tar.gz"
    download_url = None
    for asset in release.get("assets", []):
        if asset.get("name") == asset_name:
            download_url = asset.get("browser_download_url")
            break

    if not download_url:
        msg_err(f"Файл '{asset_name}' не найден в релизе {tag}.")
        return False

    _cp(CCY, f"  ↓ {download_url}")
    ensure_dirs(PHONEINFOGA_DIR)
    tar_path = os.path.join(PHONEINFOGA_DIR, asset_name)

    msg_step("·", "Скачивание PhoneInfoga...")
    try:
        req2 = urllib.request.Request(download_url, headers={"User-Agent": "osint-launcher/3.0"})
        with urllib.request.urlopen(req2, timeout=60) as resp, open(tar_path, "wb") as f:
            f.write(resp.read())
    except Exception as e:
        msg_err(f"Ошибка скачивания: {e}")
        return False

    msg_step("·", "Распаковка...")
    try:
        with tarfile.open(tar_path, "r:gz") as tf:
            tf.extractall(PHONEINFOGA_DIR)
        os.remove(tar_path)
    except Exception as e:
        msg_err(f"Ошибка распаковки: {e}")
        return False

    if os.path.isfile(PHONEINFOGA_EXE):
        msg_ok(f"PhoneInfoga установлен → {PHONEINFOGA_EXE}")
        return True
    msg_err("phoneinfoga.exe не найден после распаковки.")
    return False


def check_phoneinfoga() -> str | None:
    if os.path.isfile(PHONEINFOGA_EXE):
        return PHONEINFOGA_EXE
    msg_warn("PhoneInfoga не найден в tools/phoneinfoga.")
    ans = input(f"  {CA}Установить из GitHub Releases? (Y/N): {RESET}").strip().upper()
    if ans != "Y":
        msg_info("Возврат в меню..."); pause(2); return None
    success = install_phoneinfoga_windows()
    if success:
        msg_ok("Установка завершена."); pause(3)
        return get_phoneinfoga_exe()
    msg_err("Установка не удалась."); pause(3); return None




# ═════════════════════════════════════════════════════════════════
#  GEO OSINT
# ═════════════════════════════════════════════════════════════════
def _geo_analyze(path: str) -> str | None:
    """Запускает exiftool GPS-анализ, выводит на экран, возвращает строковый результат."""
    if RICH_OK:
        console.print(f"\n  [white]Файл:[/white] [cyan]{path}[/cyan]")
        console.rule(style="dark_violet")
    else:
        _cp(CW, f"\n  Файл: {CCY}{path}{RESET}")
        _cp(CDP, "  " + "─" * 54)

    msg_step("[1/2]", "Чтение GPS-метаданных...\n")
    lat = lon = lat_ref = lon_ref = None
    raw_output_lines = []
    try:
        exe = get_exiftool_exe()
        if not exe:
            msg_err("exiftool.exe не найден. Установите ExifTool через меню.")
            return None
        result = subprocess.run(
            [exe, "-GPSLatitude", "-GPSLongitude",
             "-GPSLatitudeRef", "-GPSLongitudeRef",
             "-GPSAltitude", "-CreateDate", "-Make", "-Model", path],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        lines = result.stdout.strip().splitlines()
        for line in lines:
            raw_output_lines.append(line)
            if ":" in line:
                k, _, v = line.partition(":")
                k, v = k.strip(), v.strip()
                if RICH_OK:
                    console.print(f"  [magenta]{k}[/magenta]: [white]{v}[/white]")
                else:
                    print(f"  {CA}{k}{RESET}: {CW}{v}{RESET}")
                kl = k.lower()
                if "gps latitude" in kl and "ref" not in kl:
                    lat = v
                if "gps longitude" in kl and "ref" not in kl:
                    lon = v
                if "gps latitude ref" in kl:
                    lat_ref = v.strip().upper()
                if "gps longitude ref" in kl:
                    lon_ref = v.strip().upper()
        if not lines:
            msg_warn("GPS-метаданные не найдены.")
    except Exception as e:
        msg_err(f"Ошибка: {e}")

    def parse_gps(raw: str, ref: str | None) -> float | None:
        if not raw:
            return None
        raw = raw.strip()
        m = re.search(
            r"(\d+)\s+deg\s+(\d+)['\u2019]\s*([\d.]+)[\"''\u201d]?\s*([NSEW])?",
            raw, re.IGNORECASE
        )
        if m:
            d, mn, sec, hemi = m.groups()
            val = float(d) + float(mn) / 60 + float(sec) / 3600
            h = (hemi or ref or "").upper()
            if h in ("S", "W"):
                val = -val
            return round(val, 7)
        m2 = re.search(r"[-+]?\d+\.\d+", raw)
        if m2:
            val = float(m2.group())
            h = (ref or "").upper()
            if h in ("S", "W") and val > 0:
                val = -val
            return round(val, 7)
        return None

    result_text = "\n".join(raw_output_lines)

    if lat and lon:
        ld = parse_gps(lat, lat_ref)
        lo = parse_gps(lon, lon_ref)
        if ld is not None and lo is not None:
            osm   = f"https://www.openstreetmap.org/?mlat={ld}&mlon={lo}#map=15/{ld}/{lo}"
            gmaps = f"https://maps.google.com/?q={ld},{lo}"
            msg_ok("GPS координаты найдены!")
            if RICH_OK:
                console.print(f"\n  [magenta]Широта  [/magenta]: [white]{ld}°[/white]")
                console.print(f"  [magenta]Долгота [/magenta]: [white]{lo}°[/white]")
                console.print(f"\n  [magenta]OpenStreetMap[/magenta]: [cyan]{osm}[/cyan]")
                console.print(f"  [magenta]Google Maps  [/magenta]: [cyan]{gmaps}[/cyan]")
            else:
                print(f"\n  {CA}Широта  {RESET}: {CW}{ld}°{RESET}")
                print(f"  {CA}Долгота {RESET}: {CW}{lo}°{RESET}")
                print(f"\n  {CA}OpenStreetMap{RESET}: {CCY}{osm}{RESET}")
                print(f"  {CA}Google Maps  {RESET}: {CCY}{gmaps}{RESET}")
            result_text += f"\n\nШирота: {ld}\nДолгота: {lo}\nOpenStreetMap: {osm}\nGoogle Maps: {gmaps}"
        else:
            msg_warn("Не удалось преобразовать GPS в десятичный формат.")
            msg_info(f"Широта (raw) : {lat}  (ref: {lat_ref})")
            msg_info(f"Долгота (raw): {lon}  (ref: {lon_ref})")
    else:
        msg_step("[2/2]", "GPS не обнаружен.")
        refs = [
            ("GeoSpy AI", "https://geospy.ai"),
            ("Picarta",   "https://picarta.ai"),
            ("GeoGuessr", "https://geoguessr.com"),
        ]
        for n, u in refs:
            if RICH_OK:
                console.print(f"  [magenta]·[/magenta] [white]{n:<16}[/white][cyan]{u}[/cyan]")
            else:
                print(f"  {CP}·{RESET} {CW}{n:<16}{RESET}{CCY}{u}{RESET}")

    return result_text


def run_geo_osint():
    while True:
        clear()
        section_header("G E O   O S I N T")

        geo_installed = check_exiftool.__module__ is not None  # ExifTool — зависимость
        st = "ExifTool: " + ("[green]установлен[/green]" if exiftool_installed() else "[red]не установлен[/red]")
        if RICH_OK:
            console.print(f"  Зависимость: {st}\n")
        else:
            stxt = "ExifTool: " + ("установлен" if exiftool_installed() else "не установлен")
            _cp(CGRN if exiftool_installed() else CRED, f"  Зависимость: {stxt}\n")

        choice = submenu("GeoOSINT", [
            ("1", "Поиск координат",          "GPS из фотографии"),
            ("2", "Переустановить ExifTool",  "удалить и переустановить зависимость"),
            ("3", "Удалить ExifTool",         "удалить зависимость"),
            ("4", "Назад",                    "главное меню"),
        ])

        if choice == "1":
            if not check_exiftool():
                continue
            while True:
                clear()
                section_header("G E O   O S I N T  ·  Анализ")
                if RICH_OK:
                    console.print("  [magenta]Перетащите изображение или введите путь:[/magenta]")
                else:
                    _cp(CA, "  Перетащите изображение или введите путь:")
                path = get_path(f"  {CP}›{RESET} ")
                if not path:
                    msg_warn("Путь не указан."); break
                if not os.path.isfile(path):
                    msg_err(f"Файл не найден: {path}"); pause(2); continue

                result_text = _geo_analyze(path)
                if result_text is None:
                    break

                # Меню действий — данные остаются на экране
                while True:
                    if RICH_OK: console.rule(style="dark_violet")
                    else: _cp(CDP, "\n  " + "─"*54)
                    action = submenu("Действия", [
                        ("1", "Сохранить результат в .txt", ""),
                        ("2", "Новый поиск",                ""),
                        ("3", "Назад",                      "в меню GeoOSINT"),
                    ])
                    if action == "1":
                        ensure_dirs(RESULTS_DIR, os.path.join(RESULTS_DIR, "geosint"))
                        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                        fpath = os.path.join(RESULTS_DIR, "geosint", f"{ts}.txt")
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(result_text)
                        msg_ok(f"[+] Результат сохранён:\n  {fpath}")
                        pause(2)
                    elif action == "2":
                        break  # новый поиск → внешний while True
                    elif action == "3":
                        return  # назад в главное меню GeoOSINT
                    else:
                        msg_warn("Неверный ввод."); pause(1)
                else:
                    continue  # action == "2" — продолжить внутренний цикл
                break  # action == "3"

        elif choice == "2":
            clear()
            section_header("G E O   O S I N T  ·  Переустановка ExifTool")
            msg_step("·", "Удаление текущей версии...")
            if os.path.isdir(EXIFTOOL_DIR):
                shutil.rmtree(EXIFTOOL_DIR)
            global EXIFTOOL_PATH
            EXIFTOOL_PATH = None
            msg_ok("Старая версия удалена.")
            install_exiftool()
            pause(2)

        elif choice == "3":
            clear()
            section_header("G E O   O S I N T  ·  Удаление ExifTool")
            ans = input(f"  {CYEL}Вы уверены? (Y/N): {RESET}").strip().upper()
            if ans == "Y":
                uninstall_exiftool()
            else:
                msg_info("Отменено."); pause(1)

        elif choice == "4":
            return

        else:
            msg_warn("Неверный ввод."); pause(1)


# ═════════════════════════════════════════════════════════════════
#  PHONEINFOGA — полное подменю (аналог ExifTool)
# ═════════════════════════════════════════════════════════════════

def uninstall_phoneinfoga():
    removed = False
    if os.path.isdir(PHONEINFOGA_DIR):
        shutil.rmtree(PHONEINFOGA_DIR)
        removed = True
    if removed:
        msg_ok("[+] PhoneInfoga успешно удалён.")
    else:
        msg_warn("PhoneInfoga не был установлен.")
    pause(2)


def phoneinfoga_scan(exe: str) -> str | None:
    """Запрашивает номер, запускает scan, возвращает вывод."""
    if RICH_OK:
        console.print("  [magenta]Введите номер телефона (пример: +19999999999):[/magenta]")
    else:
        _cp(CA, "  Введите номер телефона (пример: +19999999999):")

    number = input(f"  {CP}›{RESET} ").strip()
    if not number:
        msg_warn("Номер не введён.")
        pause(1)
        return None

    if RICH_OK:
        console.print(f"\n  [white]Анализ номера:[/white] [cyan]{number}[/cyan]")
        console.rule(style="dark_violet")
    else:
        _cp(CW, f"\n  Анализ номера: {CCY}{number}{RESET}")
        _cp(CDP, "  " + "─" * 54)

    try:
        result = subprocess.run([exe, "scan", "-n", number],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        output = result.stdout or result.stderr
        for line in output.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                if RICH_OK:
                    console.print(f"  [magenta]{k}[/magenta]:[white]{v}[/white]")
                else:
                    print(f"  {CA}{k}{RESET}:{CW}{v}{RESET}")
            else:
                msg_info(line)
    except Exception as e:
        msg_err(f"Ошибка запуска phoneinfoga: {e}")
        return None

    if RICH_OK: console.rule(style="dark_violet")
    else: _cp(CDP, "\n  " + "─"*54)

    return output


def phoneinfoga_after_scan(output: str):
    """Меню после анализа номера — данные остаются на экране."""
    while True:
        if RICH_OK:
            console.rule(style="dark_violet")
        else:
            _cp(CDP, "\n  " + "─" * 54)
        choice = submenu("Действия", [
            ("1", "Сохранить результат в .txt", ""),
            ("2", "Новый поиск",                ""),
            ("3", "Назад",                      "в меню PhoneInfoga"),
        ])
        if choice == "1":
            ensure_dirs(RESULTS_DIR, os.path.join(RESULTS_DIR, "phoneinfoga"))
            ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            fpath = os.path.join(RESULTS_DIR, "phoneinfoga", f"{ts}.txt")
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(output)
            msg_ok(f"[+] Результат сохранён:\n  {fpath}")
            pause(2)
        elif choice == "2":
            return "new"
        elif choice == "3":
            return "back"
        else:
            msg_warn("Неверный ввод.")
            pause(1)


def run_phoneinfoga():
    while True:
        clear()
        section_header("P H O N E I N F O G A")

        status = "[green]установлен[/green]" if get_phoneinfoga_exe() else "[red]не установлен[/red]"
        if RICH_OK:
            console.print(f"  Статус: {status}\n")
        else:
            st = "установлен" if get_phoneinfoga_exe() else "не установлен"
            _cp(CGRN if get_phoneinfoga_exe() else CRED, f"  Статус: {st}\n")

        choice = submenu("PhoneInfoga", [
            ("1", "Поиск номеров",          "анализ номера телефона"),
            ("2", "Переустановить",          "удалить и скачать заново"),
            ("3", "Удалить PhoneInfoga",     "полное удаление"),
            ("4", "Назад",                   "главное меню"),
        ])

        if choice == "1":
            exe = check_phoneinfoga()
            if not exe:
                continue
            while True:
                clear()
                section_header("P H O N E I N F O G A  ·  Поиск")
                output = phoneinfoga_scan(exe)
                if output is None:
                    break
                action = phoneinfoga_after_scan(output)
                if action == "back":
                    break

        elif choice == "2":
            clear()
            section_header("P H O N E I N F O G A  ·  Переустановка")
            msg_step("·", "Удаление текущей версии...")
            if os.path.isdir(PHONEINFOGA_DIR):
                shutil.rmtree(PHONEINFOGA_DIR)
            msg_ok("Старая версия удалена.")
            install_phoneinfoga_windows()
            pause(2)

        elif choice == "3":
            clear()
            section_header("P H O N E I N F O G A  ·  Удаление")
            ans = input(f"  {CYEL}Вы уверены? (Y/N): {RESET}").strip().upper()
            if ans == "Y":
                uninstall_phoneinfoga()
            else:
                msg_info("Отменено.")
                pause(1)

        elif choice == "4":
            return

        else:
            msg_warn("Неверный ввод.")
            pause(1)


# ═════════════════════════════════════════════════════════════════
#  SHERLOCK  (исправленный запуск через python -m sherlock_project)
# ═════════════════════════════════════════════════════════════════
SHERLOCK_DIR      = os.path.join(TOOLS_DIR, "sherlock")
SHERLOCK_REPO_ZIP = "https://github.com/sherlock-project/sherlock/archive/refs/heads/master.zip"
SHERLOCK_RESULTS  = os.path.join(RESULTS_DIR, "sherlock")

if platform.system() == "Windows":
    _SHERLOCK_PYTHON = os.path.join(SHERLOCK_DIR, "venv", "Scripts", "python.exe")
else:
    _SHERLOCK_PYTHON = os.path.join(SHERLOCK_DIR, "venv", "bin", "python")

if platform.system() == "Windows":
    _SHERLOCK_PIP = os.path.join(SHERLOCK_DIR, "venv", "Scripts", "pip.exe")
else:
    _SHERLOCK_PIP = os.path.join(SHERLOCK_DIR, "venv", "bin", "pip")


def sherlock_installed() -> bool:
    return os.path.isdir(SHERLOCK_DIR) and os.path.isfile(_SHERLOCK_PYTHON)


def _sherlock_test() -> bool:
    """
    Проверяет работоспособность через:
      python -m sherlock_project --help
    cwd = SHERLOCK_DIR (обязательно!)
    Возвращает True при коде возврата 0.
    """
    if not os.path.isfile(_SHERLOCK_PYTHON):
        return False
    msg_step("[6/6]", "Тест: python -m sherlock_project --help ...")
    msg_info(f"  cwd: {SHERLOCK_DIR}")
    try:
        r = subprocess.run(
            [_SHERLOCK_PYTHON, "-m", "sherlock_project", "--help"],
            cwd=SHERLOCK_DIR,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30
        )
        msg_info(f"  Код завершения: {r.returncode}")
        if r.returncode != 0:
            msg_err(f"  stderr: {r.stderr[:400]}")
            return False
        return True
    except Exception as e:
        msg_err(f"  Ошибка теста: {e}")
        return False


def install_sherlock() -> bool:
    ensure_dirs(TOOLS_DIR, DOWNLOADS_DIR)
    zip_path    = os.path.join(DOWNLOADS_DIR, "sherlock_master.zip")
    extract_tmp = os.path.join(DOWNLOADS_DIR, "sherlock_extracted")

    msg_step("[1/6]", "Проверка установки...")
    msg_step("[2/6]", "Скачивание репозитория Sherlock...")
    try:
        req = urllib.request.Request(SHERLOCK_REPO_ZIP, headers={"User-Agent": "osint-launcher/3.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(zip_path, "wb") as f:
            f.write(resp.read())
    except Exception as e:
        msg_err(f"Ошибка скачивания: {e}"); return False

    msg_step("[3/6]", "Распаковка репозитория...")
    if os.path.isdir(extract_tmp): shutil.rmtree(extract_tmp)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_tmp)
        os.remove(zip_path)
    except Exception as e:
        msg_err(f"Ошибка распаковки: {e}"); return False

    # Переносим sherlock-master/ → tools/sherlock/
    if os.path.isdir(SHERLOCK_DIR): shutil.rmtree(SHERLOCK_DIR)
    items = os.listdir(extract_tmp)
    if len(items) == 1 and os.path.isdir(os.path.join(extract_tmp, items[0])):
        shutil.move(os.path.join(extract_tmp, items[0]), SHERLOCK_DIR)
    else:
        shutil.move(extract_tmp, SHERLOCK_DIR)

    msg_step("[4/6]", "Создание виртуального окружения Python...")
    try:
        subprocess.run([sys.executable, "-m", "venv",
                        os.path.join(SHERLOCK_DIR, "venv")], check=True)
    except Exception as e:
        msg_err(f"Ошибка создания venv: {e}"); return False

    msg_step("[5/6]", "Установка зависимостей...")
    # Сначала пробуем pip install -e . (pyproject.toml), затем requirements.txt
    pyproject = os.path.join(SHERLOCK_DIR, "pyproject.toml")
    if os.path.isfile(pyproject):
        msg_info("  Найден pyproject.toml — устанавливаем через pip install -e .")
        try:
            subprocess.run(
                [_SHERLOCK_PIP, "install", "-e", ".", "--quiet"],
                cwd=SHERLOCK_DIR, check=True
            )
        except Exception as e:
            msg_warn(f"  pip install -e . завершился с ошибкой: {e}")
            msg_info("  Пробуем requirements.txt как fallback...")
    # Дополнительно — requirements.txt если есть
    req_file = None
    for root, _, files in os.walk(SHERLOCK_DIR):
        if "requirements.txt" in files and "venv" not in root:
            req_file = os.path.join(root, "requirements.txt"); break
    if req_file:
        try:
            subprocess.run(
                [_SHERLOCK_PIP, "install", "-r", req_file, "--quiet"],
                check=True
            )
        except Exception as e:
            msg_warn(f"  Ошибка установки requirements.txt: {e}")

    # Тест работоспособности
    if _sherlock_test():
        msg_ok("[+] Sherlock успешно установлен.")
        return True
    msg_err("Sherlock установлен, но тест не прошёл. Попробуйте переустановить.")
    return False


def uninstall_sherlock():
    if os.path.isdir(SHERLOCK_DIR):
        shutil.rmtree(SHERLOCK_DIR)
        msg_ok("[+] Sherlock успешно удалён.")
    else:
        msg_warn("Sherlock не был установлен.")
    pause(2)


def check_sherlock() -> bool:
    if sherlock_installed():
        return True
    msg_warn("[!] Sherlock не найден.")
    ans = input(f"  {CA}Установить? (Y/N): {RESET}").strip().upper()
    if ans != "Y":
        msg_info("Возврат в меню..."); pause(1); return False
    ok = install_sherlock()
    pause(2)
    return ok and sherlock_installed()


def sherlock_search(username: str) -> str | None:
    """
    Запускает Sherlock через:
      python -m sherlock_project <username> --print-found
    Рабочий каталог (cwd) = SHERLOCK_DIR — обязательно!
    """
    cmd = [_SHERLOCK_PYTHON, "-m", "sherlock_project", username, "--print-found"]

    if RICH_OK:
        console.print(f"\n  [white]Поиск username:[/white] [cyan]{username}[/cyan]")
        console.print(f"  [dim]cwd: {SHERLOCK_DIR}[/dim]")
        console.print(f"  [dim]cmd: {' '.join(cmd)}[/dim]")
        console.rule(style="dark_violet")
    else:
        _cp(CW,  f"\n  Поиск: {CCY}{username}{RESET}")
        _cp(CGR, f"  cwd: {SHERLOCK_DIR}")
        _cp(CGR, f"  cmd: {' '.join(cmd)}")
        _cp(CDP, "  " + "─" * 54)

    lines_collected = []
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=SHERLOCK_DIR,                    # ← ключевой параметр
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace"
        )
        for line in proc.stdout:
            line = line.rstrip()
            lines_collected.append(line)
            if RICH_OK:
                if "[+]" in line:
                    console.print(f"  [green]{line}[/green]")
                elif "[!]" in line or "Error" in line.lower():
                    console.print(f"  [red]{line}[/red]")
                else:
                    console.print(f"  [white]{line}[/white]")
            else:
                color = CGRN if "[+]" in line else (CRED if "[!]" in line else CW)
                _cp(color, f"  {line}")
        proc.wait()
        # Показываем диагностику
        stderr_out = proc.stderr.read() if proc.stderr else ""
        msg_info(f"  Код завершения: {proc.returncode}")
        if stderr_out.strip():
            msg_warn(f"  stderr: {stderr_out[:600]}")
    except Exception as e:
        msg_err(f"Ошибка запуска Sherlock: {e}")
        return None

    return "\n".join(lines_collected)


def run_sherlock():
    while True:
        clear()
        section_header("S H E R L O C K")

        st_rich = "[green]установлен[/green]" if sherlock_installed() else "[red]не установлен[/red]"
        if RICH_OK:
            console.print(f"  Статус: {st_rich}\n")
        else:
            _cp(CGRN if sherlock_installed() else CRED,
                f"  Статус: {'установлен' if sherlock_installed() else 'не установлен'}\n")

        choice = submenu("Sherlock", [
            ("1", "Поиск по username",       "поиск аккаунтов на сайтах"),
            ("2", "Переустановить Sherlock",  "удалить и скачать заново"),
            ("3", "Удалить Sherlock",         "полное удаление"),
            ("4", "Назад",                    "главное меню"),
        ])

        if choice == "1":
            if not check_sherlock():
                continue
            while True:
                clear()
                section_header("S H E R L O C K  ·  Поиск")
                if RICH_OK:
                    console.print("  [magenta]Введите username:[/magenta]")
                else:
                    _cp(CA, "  Введите username:")
                username = input(f"  {CP}›{RESET} ").strip()
                if not username:
                    msg_warn("Username не введён."); break

                output = sherlock_search(username)
                if output is None:
                    break

                while True:
                    if RICH_OK: console.rule(style="dark_violet")
                    else: _cp(CDP, "\n  " + "─"*54)
                    action = submenu("Действия", [
                        ("1", "Сохранить результат в .txt", ""),
                        ("2", "Новый поиск",                ""),
                        ("3", "Назад",                      "в меню Sherlock"),
                    ])
                    if action == "1":
                        ensure_dirs(RESULTS_DIR, SHERLOCK_RESULTS)
                        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                        fpath = os.path.join(SHERLOCK_RESULTS, f"{ts}_{username}.txt")
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(output)
                        msg_ok(f"[+] Результат сохранён:\n  {fpath}")
                        pause(2)
                    elif action == "2":
                        break
                    elif action == "3":
                        return
                    else:
                        msg_warn("Неверный ввод."); pause(1)
                else:
                    continue
                break

        elif choice == "2":
            clear()
            section_header("S H E R L O C K  ·  Переустановка")
            if os.path.isdir(SHERLOCK_DIR): shutil.rmtree(SHERLOCK_DIR)
            msg_ok("Старая версия удалена.")
            install_sherlock(); pause(2)

        elif choice == "3":
            clear()
            section_header("S H E R L O C K  ·  Удаление")
            ans = input(f"  {CYEL}Вы уверены? (Y/N): {RESET}").strip().upper()
            if ans == "Y":
                uninstall_sherlock()
            else:
                msg_info("Отменено."); pause(1)

        elif choice == "4":
            return
        else:
            msg_warn("Неверный ввод."); pause(1)


# ═════════════════════════════════════════════════════════════════
#  HOLEHE
# ═════════════════════════════════════════════════════════════════
HOLEHE_DIR      = os.path.join(TOOLS_DIR, "holehe")
HOLEHE_REPO_ZIP = "https://github.com/megadose/holehe/archive/refs/heads/master.zip"
HOLEHE_RESULTS  = os.path.join(RESULTS_DIR, "holehe")

if platform.system() == "Windows":
    _HOLEHE_PYTHON = os.path.join(HOLEHE_DIR, "venv", "Scripts", "python.exe")
    _HOLEHE_PIP    = os.path.join(HOLEHE_DIR, "venv", "Scripts", "pip.exe")
else:
    _HOLEHE_PYTHON = os.path.join(HOLEHE_DIR, "venv", "bin", "python")
    _HOLEHE_PIP    = os.path.join(HOLEHE_DIR, "venv", "bin", "pip")


def holehe_installed() -> bool:
    return os.path.isdir(HOLEHE_DIR) and os.path.isfile(_HOLEHE_PYTHON)


def _holehe_test() -> bool:
    """
    Тест установки Holehe.
    Проверяем что модуль импортируется и консольный скрипт существует.
    НЕ используем python -m holehe — пакет не поддерживает прямой -m запуск.
    """
    if not os.path.isfile(_HOLEHE_PYTHON):
        return False
    try:
        r = subprocess.run(
            [_HOLEHE_PYTHON, "-c", "import holehe; print('ok')"],
            cwd=HOLEHE_DIR,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=15
        )
        return r.returncode == 0 and "ok" in r.stdout
    except Exception:
        return False


def install_holehe() -> bool:
    ensure_dirs(TOOLS_DIR, DOWNLOADS_DIR)
    zip_path    = os.path.join(DOWNLOADS_DIR, "holehe_master.zip")
    extract_tmp = os.path.join(DOWNLOADS_DIR, "holehe_extracted")

    msg_step("[1/5]", "Проверка установки...")
    msg_step("[2/5]", "Скачивание репозитория Holehe...")
    try:
        req = urllib.request.Request(HOLEHE_REPO_ZIP, headers={"User-Agent": "osint-launcher/3.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(zip_path, "wb") as f:
            f.write(resp.read())
    except Exception as e:
        msg_err(f"Ошибка скачивания: {e}"); return False

    msg_step("[3/5]", "Распаковка...")
    if os.path.isdir(extract_tmp): shutil.rmtree(extract_tmp)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_tmp)
        os.remove(zip_path)
    except Exception as e:
        msg_err(f"Ошибка распаковки: {e}"); return False

    if os.path.isdir(HOLEHE_DIR): shutil.rmtree(HOLEHE_DIR)
    items = os.listdir(extract_tmp)
    if len(items) == 1 and os.path.isdir(os.path.join(extract_tmp, items[0])):
        shutil.move(os.path.join(extract_tmp, items[0]), HOLEHE_DIR)
    else:
        shutil.move(extract_tmp, HOLEHE_DIR)

    msg_step("[4/5]", "Создание venv и установка зависимостей...")
    try:
        subprocess.run([sys.executable, "-m", "venv",
                        os.path.join(HOLEHE_DIR, "venv")], check=True)
    except Exception as e:
        msg_err(f"Ошибка создания venv: {e}"); return False

    # pip install -e . (setup.py / pyproject.toml)
    try:
        subprocess.run(
            [_HOLEHE_PIP, "install", "-e", ".", "--quiet"],
            cwd=HOLEHE_DIR, check=True
        )
    except Exception as e:
        msg_warn(f"pip install -e . ошибка: {e}")
        # fallback: requirements.txt
        req_file = None
        for root, _, files in os.walk(HOLEHE_DIR):
            if "requirements.txt" in files and "venv" not in root:
                req_file = os.path.join(root, "requirements.txt"); break
        if req_file:
            try:
                subprocess.run([_HOLEHE_PIP, "install", "-r", req_file, "--quiet"], check=True)
            except Exception as e2:
                msg_err(f"Ошибка requirements.txt: {e2}"); return False

    msg_step("[5/5]", "Проверка работоспособности...")
    if _holehe_test():
        msg_ok("[+] Holehe успешно установлен.")
        return True
    msg_err("Holehe установлен, но тест не прошёл. Попробуйте переустановить.")
    return False


def uninstall_holehe():
    if os.path.isdir(HOLEHE_DIR):
        shutil.rmtree(HOLEHE_DIR)
        msg_ok("[+] Holehe успешно удалён.")
    else:
        msg_warn("Holehe не был установлен.")
    pause(2)


def check_holehe() -> bool:
    if holehe_installed():
        return True
    msg_warn("[!] Holehe не найден.")
    ans = input(f"  {CA}Установить? (Y/N): {RESET}").strip().upper()
    if ans != "Y":
        msg_info("Возврат в меню..."); pause(1); return False
    ok = install_holehe()
    pause(2)
    return ok and holehe_installed()


def _holehe_get_cmd(email: str) -> list | None:
    """
    Возвращает правильную команду для запуска holehe.
    Порядок поиска:
      1. venv/Scripts/holehe.exe  (Windows, создаётся после pip install -e .)
      2. venv/Scripts/holehe.bat
      3. venv/bin/holehe           (Linux/Mac)
      4. python holehe/core.py     (прямой вызов модуля)
    НЕ используем python -m holehe — пакет не поддерживает -m запуск.
    """
    if platform.system() == "Windows":
        candidates = [
            os.path.join(HOLEHE_DIR, "venv", "Scripts", "holehe.exe"),
            os.path.join(HOLEHE_DIR, "venv", "Scripts", "holehe.bat"),
        ]
    else:
        candidates = [
            os.path.join(HOLEHE_DIR, "venv", "bin", "holehe"),
        ]
    for exe in candidates:
        if os.path.isfile(exe):
            return [exe, email]
    # Fallback — ищем entry point рекурсивно в исходниках
    for root, _, files in os.walk(HOLEHE_DIR):
        if "venv" in root:
            continue
        for fname in ("__main__.py", "holehe.py", "core.py"):
            if fname in files:
                return [_HOLEHE_PYTHON, os.path.join(root, fname), email]
    return None


def holehe_check_email(email: str) -> str | None:
    """
    Запускает Holehe для проверки email.
    Использует консольный скрипт из venv (НЕ python -m holehe).
    """
    cmd = _holehe_get_cmd(email)
    if cmd is None:
        msg_err("Исполняемый файл holehe не найден в venv.")
        msg_info("Попробуйте переустановить Holehe.")
        return None

    if RICH_OK:
        console.print(f"\n  [white]Проверка email:[/white] [cyan]{email}[/cyan]")
        console.print(f"  [dim]Python : {_HOLEHE_PYTHON}[/dim]")
        console.print(f"  [dim]cwd    : {HOLEHE_DIR}[/dim]")
        console.print(f"  [dim]cmd    : {' '.join(cmd)}[/dim]")
        console.rule(style="dark_violet")
    else:
        _cp(CW,  f"\n  Проверка: {CCY}{email}{RESET}")
        _cp(CGR, f"  Python : {_HOLEHE_PYTHON}")
        _cp(CGR, f"  cwd    : {HOLEHE_DIR}")
        _cp(CGR, f"  cmd    : {' '.join(cmd)}")
        _cp(CDP, "  " + "─" * 54)

    lines_collected = []
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=HOLEHE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace"
        )
        for line in proc.stdout:
            line = line.rstrip()
            lines_collected.append(line)
            if RICH_OK:
                if "[+]" in line:
                    console.print(f"  [green]{line}[/green]")
                elif "[-]" in line:
                    console.print(f"  [dim]{line}[/dim]")
                elif "[!]" in line or "error" in line.lower():
                    console.print(f"  [red]{line}[/red]")
                else:
                    console.print(f"  [white]{line}[/white]")
            else:
                color = CGRN if "[+]" in line else (CRED if "[!]" in line else CGR)
                _cp(color, f"  {line}")
        proc.wait()
        stderr_out = proc.stderr.read() if proc.stderr else ""
        msg_info(f"  Код завершения: {proc.returncode}")
        if stderr_out.strip():
            # Полный stderr без обрезки
            if RICH_OK:
                console.print(f"  [red]stderr:[/red]\n  [dim]{stderr_out}[/dim]")
            else:
                _cp(CRED, f"  stderr:\n{stderr_out}")
    except Exception as e:
        msg_err(f"Ошибка запуска Holehe: {e}")
        return None

    return "\n".join(lines_collected)


def run_holehe():
    while True:
        clear()
        section_header("H O L E H E")

        st_rich = "[green]установлен[/green]" if holehe_installed() else "[red]не установлен[/red]"
        if RICH_OK:
            console.print(f"  Статус: {st_rich}\n")
        else:
            _cp(CGRN if holehe_installed() else CRED,
                f"  Статус: {'установлен' if holehe_installed() else 'не установлен'}\n")

        choice = submenu("Holehe", [
            ("1", "Проверить Email",       "поиск регистраций по email"),
            ("2", "Переустановить Holehe", "удалить и скачать заново"),
            ("3", "Удалить Holehe",        "полное удаление"),
            ("4", "Назад",                 "главное меню"),
        ])

        if choice == "1":
            if not check_holehe():
                continue
            while True:
                clear()
                section_header("H O L E H E  ·  Проверка Email")
                if RICH_OK:
                    console.print("  [magenta]Введите Email:[/magenta]")
                    console.print("  [dim]Пример: example@gmail.com[/dim]")
                else:
                    _cp(CA, "  Введите Email:")
                    _cp(CGR, "  Пример: example@gmail.com")
                email = input(f"  {CP}›{RESET} ").strip()
                if not email:
                    msg_warn("Email не введён."); break

                output = holehe_check_email(email)
                if output is None:
                    break

                while True:
                    if RICH_OK: console.rule(style="dark_violet")
                    else: _cp(CDP, "\n  " + "─"*54)
                    action = submenu("Действия", [
                        ("1", "Сохранить результат в .txt", ""),
                        ("2", "Новый поиск",                ""),
                        ("3", "Назад",                      "в меню Holehe"),
                    ])
                    if action == "1":
                        ensure_dirs(RESULTS_DIR, HOLEHE_RESULTS)
                        ts    = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                        safe  = email.replace("@", "_at_").replace("/", "_")
                        fpath = os.path.join(HOLEHE_RESULTS, f"{ts}_{safe}.txt")
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(output)
                        msg_ok(f"[+] Результат сохранён:\n  {fpath}")
                        pause(2)
                    elif action == "2":
                        break
                    elif action == "3":
                        return
                    else:
                        msg_warn("Неверный ввод."); pause(1)
                else:
                    continue
                break

        elif choice == "2":
            clear()
            section_header("H O L E H E  ·  Переустановка")
            if os.path.isdir(HOLEHE_DIR): shutil.rmtree(HOLEHE_DIR)
            msg_ok("Старая версия удалена.")
            install_holehe(); pause(2)

        elif choice == "3":
            clear()
            section_header("H O L E H E  ·  Удаление")
            ans = input(f"  {CYEL}Вы уверены? (Y/N): {RESET}").strip().upper()
            if ans == "Y":
                uninstall_holehe()
            else:
                msg_info("Отменено."); pause(1)

        elif choice == "4":
            return
        else:
            msg_warn("Неверный ввод."); pause(1)


# ═════════════════════════════════════════════════════════════════
#  ЛОГИРОВАНИЕ
# ═════════════════════════════════════════════════════════════════
import logging as _logging
import traceback as _traceback

_LOGS_DIR = os.path.join(BASE_DIR, "logs")
ensure_dirs(_LOGS_DIR)

_log_formatter = _logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

_app_handler   = _logging.FileHandler(os.path.join(_LOGS_DIR, "app.log"),   encoding="utf-8")
_err_handler   = _logging.FileHandler(os.path.join(_LOGS_DIR, "error.log"), encoding="utf-8")
_app_handler.setFormatter(_log_formatter)
_err_handler.setFormatter(_log_formatter)
_err_handler.setLevel(_logging.ERROR)

_logger = _logging.getLogger("int_launcher")
_logger.setLevel(_logging.DEBUG)
if not _logger.handlers:
    _logger.addHandler(_app_handler)
    _logger.addHandler(_err_handler)

def log_info(msg: str):
    _logger.info(msg)

def log_error(msg: str, exc: Exception | None = None):
    _logger.error(msg)
    if exc:
        _logger.error(_traceback.format_exc())


# ═════════════════════════════════════════════════════════════════
#  MAIGRET
# ═════════════════════════════════════════════════════════════════
MAIGRET_DIR      = os.path.join(TOOLS_DIR, "maigret")
MAIGRET_RESULTS  = os.path.join(RESULTS_DIR, "maigret")
MAIGRET_REPO_ZIP = "https://github.com/soxoj/maigret/archive/refs/heads/main.zip"

if platform.system() == "Windows":
    _MAIGRET_PYTHON = os.path.join(MAIGRET_DIR, "venv", "Scripts", "python.exe")
    _MAIGRET_PIP    = os.path.join(MAIGRET_DIR, "venv", "Scripts", "pip.exe")
else:
    _MAIGRET_PYTHON = os.path.join(MAIGRET_DIR, "venv", "bin", "python")
    _MAIGRET_PIP    = os.path.join(MAIGRET_DIR, "venv", "bin", "pip")


def maigret_installed() -> bool:
    return os.path.isdir(MAIGRET_DIR) and os.path.isfile(_MAIGRET_PYTHON)


def _maigret_test() -> bool:
    if not os.path.isfile(_MAIGRET_PYTHON):
        return False
    try:
        r = subprocess.run(
            [_MAIGRET_PYTHON, "-m", "maigret", "--help"],
            cwd=MAIGRET_DIR,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30
        )
        return r.returncode == 0
    except Exception:
        return False


def install_maigret() -> bool:
    log_info("Установка Maigret...")
    ensure_dirs(TOOLS_DIR, DOWNLOADS_DIR)
    zip_path    = os.path.join(DOWNLOADS_DIR, "maigret_main.zip")
    extract_tmp = os.path.join(DOWNLOADS_DIR, "maigret_extracted")

    msg_step("[1/6]", "Проверка установки...")
    msg_step("[2/6]", "Скачивание репозитория Maigret...")
    try:
        req = urllib.request.Request(MAIGRET_REPO_ZIP, headers={"User-Agent": "osint-launcher/3.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(zip_path, "wb") as f:
            f.write(resp.read())
    except Exception as e:
        msg_err(f"Ошибка скачивания: {e}"); log_error("Maigret download", e); return False

    msg_step("[3/6]", "Распаковка...")
    if os.path.isdir(extract_tmp): shutil.rmtree(extract_tmp)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_tmp)
        os.remove(zip_path)
    except Exception as e:
        msg_err(f"Ошибка распаковки: {e}"); return False

    if os.path.isdir(MAIGRET_DIR): shutil.rmtree(MAIGRET_DIR)
    items = os.listdir(extract_tmp)
    if len(items) == 1 and os.path.isdir(os.path.join(extract_tmp, items[0])):
        shutil.move(os.path.join(extract_tmp, items[0]), MAIGRET_DIR)
    else:
        shutil.move(extract_tmp, MAIGRET_DIR)

    msg_step("[4/6]", "Создание виртуального окружения...")
    try:
        subprocess.run([sys.executable, "-m", "venv",
                        os.path.join(MAIGRET_DIR, "venv")], check=True)
    except Exception as e:
        msg_err(f"Ошибка venv: {e}"); return False

    msg_step("[5/6]", "Установка зависимостей (pip install -e .)...")
    try:
        subprocess.run([_MAIGRET_PIP, "install", "-e", ".", "--quiet"],
                       cwd=MAIGRET_DIR, check=True)
    except Exception as e:
        msg_warn(f"pip install -e . ошибка: {e}")
        # fallback: requirements.txt
        for root, _, files in os.walk(MAIGRET_DIR):
            if "requirements.txt" in files and "venv" not in root:
                req_file = os.path.join(root, "requirements.txt")
                try:
                    subprocess.run([_MAIGRET_PIP, "install", "-r", req_file, "--quiet"], check=True)
                except Exception as e2:
                    msg_warn(f"requirements.txt ошибка: {e2}")
                break

    msg_step("[6/6]", "Тест: python -m maigret --help ...")
    msg_info(f"  Python : {_MAIGRET_PYTHON}")
    msg_info(f"  cwd    : {MAIGRET_DIR}")
    if _maigret_test():
        msg_ok("[+] Maigret успешно установлен.")
        log_info("Maigret установлен.")
        return True
    msg_warn("Тест не прошёл, но файлы установлены. Попробуйте запустить вручную.")
    return maigret_installed()


def uninstall_maigret():
    if os.path.isdir(MAIGRET_DIR):
        shutil.rmtree(MAIGRET_DIR)
        msg_ok("[+] Maigret успешно удалён.")
        log_info("Maigret удалён.")
    else:
        msg_warn("Maigret не был установлен.")
    pause(2)


def maigret_search(username: str) -> tuple:
    """
    Запускает Maigret через python -m maigret <username>.
    cwd = MAIGRET_DIR (обязательно для корректной работы).
    Возвращает (вывод: str, статистика: dict).
    """
    cmd = [_MAIGRET_PYTHON, "-m", "maigret", username, "--no-color"]

    if RICH_OK:
        console.print(f"\n  [white]Поиск Maigret:[/white] [cyan]{username}[/cyan]")
        console.print(f"  [dim]Python : {_MAIGRET_PYTHON}[/dim]")
        console.print(f"  [dim]cwd    : {MAIGRET_DIR}[/dim]")
        console.print(f"  [dim]cmd    : {' '.join(cmd)}[/dim]")
        console.rule(style="dark_violet")
    else:
        _cp(CW,  f"\n  Поиск Maigret: {CCY}{username}{RESET}")
        _cp(CGR, f"  Python : {_MAIGRET_PYTHON}")
        _cp(CGR, f"  cwd    : {MAIGRET_DIR}")
        _cp(CGR, f"  cmd    : {' '.join(cmd)}")
        _cp(CDP, "  " + "─" * 54)

    lines = []; found = 0; checked = 0
    t_start = time.time()
    try:
        proc = subprocess.Popen(
            cmd, cwd=MAIGRET_DIR,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace"
        )
        for line in proc.stdout:
            line = line.rstrip(); lines.append(line)
            if "[+]" in line: found += 1
            if "Checking" in line or "checked" in line.lower(): checked += 1
            if RICH_OK:
                if "[+]" in line:   console.print(f"  [green]{line}[/green]")
                elif "[-]" in line: console.print(f"  [dim]{line}[/dim]")
                elif "[!]" in line: console.print(f"  [red]{line}[/red]")
                else:               console.print(f"  [white]{line}[/white]")
            else:
                _cp(CGRN if "[+]" in line else CW, f"  {line}")
        proc.wait()
        stderr_out = proc.stderr.read() if proc.stderr else ""
        msg_info(f"  Код завершения: {proc.returncode}")
        if stderr_out.strip():
            if RICH_OK:
                console.print(f"  [red]stderr:[/red]\n  [dim]{stderr_out}[/dim]")
            else:
                _cp(CRED, f"  stderr:\n{stderr_out}")
    except Exception as e:
        msg_err(f"Ошибка Maigret: {e}")
        log_error("Maigret run", e)
        return "", {}

    elapsed = round(time.time() - t_start, 1)
    return "\n".join(lines), {"found": found, "checked": checked, "time": elapsed}


def run_maigret():
    while True:
        clear(); section_header("M A I G R E T")
        st = "[green]установлен[/green]" if maigret_installed() else "[red]не установлен[/red]"
        if RICH_OK: console.print(f"  Статус: {st}\n")
        else: _cp(CGRN if maigret_installed() else CRED,
                  f"  Статус: {'установлен' if maigret_installed() else 'не установлен'}\n")

        choice = submenu("Maigret", [
            ("1", "Поиск по username",      "поиск аккаунтов на сайтах"),
            ("2", "Переустановить Maigret", "удалить и скачать заново"),
            ("3", "Удалить Maigret",        "полное удаление"),
            ("4", "Назад",                  "главное меню"),
        ])

        if choice == "1":
            if not maigret_installed():
                msg_warn("[!] Maigret не найден.")
                if input(f"  {CA}Установить? (Y/N): {RESET}").strip().upper() != "Y": continue
                install_maigret(); pause(2)
                if not maigret_installed(): continue
            while True:
                clear(); section_header("M A I G R E T  ·  Поиск")
                if RICH_OK: console.print("  [magenta]Введите username:[/magenta]")
                else:        _cp(CA, "  Введите username:")
                username = input(f"  {CP}›{RESET} ").strip()
                if not username: msg_warn("Username не введён."); break

                output, stats = maigret_search(username)
                if not output: break

                # Статистика
                if RICH_OK: console.rule(style="dark_violet")
                else: _cp(CDP, "\n  " + "─"*54)
                msg_ok(f"Найдено профилей : {stats.get('found', 0)}")
                msg_info(f"Проверено сайтов : {stats.get('checked', 0)}")
                msg_info(f"Время выполнения : {stats.get('time', 0)} сек")

                full = (output + f"\n\nСтатистика:\nНайдено: {stats.get('found',0)}\n"
                        f"Проверено: {stats.get('checked',0)}\nВремя: {stats.get('time',0)} сек")
                while True:
                    if RICH_OK: console.rule(style="dark_violet")
                    else: _cp(CDP, "\n  " + "─"*54)
                    action = submenu("Действия", [
                        ("1", "Сохранить результат в .txt", ""),
                        ("2", "Новый поиск",                ""),
                        ("3", "Назад",                      "в меню Maigret"),
                    ])
                    if action == "1":
                        ensure_dirs(RESULTS_DIR, MAIGRET_RESULTS)
                        ts    = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                        fpath = os.path.join(MAIGRET_RESULTS, f"{ts}_{username}.txt")
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(full)
                        msg_ok(f"[+] Результат сохранён:\n  {fpath}"); pause(2)
                    elif action == "2": break
                    elif action == "3": return
                    else: msg_warn("Неверный ввод."); pause(1)
                else: continue
                break

        elif choice == "2":
            clear(); section_header("M A I G R E T  ·  Переустановка")
            if os.path.isdir(MAIGRET_DIR): shutil.rmtree(MAIGRET_DIR)
            msg_ok("Старая версия удалена."); install_maigret(); pause(2)
        elif choice == "3":
            clear(); section_header("M A I G R E T  ·  Удаление")
            if input(f"  {CYEL}Вы уверены? (Y/N): {RESET}").strip().upper() == "Y":
                uninstall_maigret()
            else: msg_info("Отменено."); pause(1)
        elif choice == "4": return
        else: msg_warn("Неверный ввод."); pause(1)


# ═════════════════════════════════════════════════════════════════
#  EAGLEEYE
# ═════════════════════════════════════════════════════════════════
EAGLEEYE_DIR      = os.path.join(TOOLS_DIR, "eagleeye")
EAGLEEYE_RESULTS  = os.path.join(RESULTS_DIR, "eagleeye")
EAGLEEYE_REPO_ZIP = "https://github.com/ThoughtfulDev/EagleEye/archive/refs/heads/master.zip"

if platform.system() == "Windows":
    _EAGLEEYE_PYTHON = os.path.join(EAGLEEYE_DIR, "venv", "Scripts", "python.exe")
    _EAGLEEYE_PIP    = os.path.join(EAGLEEYE_DIR, "venv", "Scripts", "pip.exe")
else:
    _EAGLEEYE_PYTHON = os.path.join(EAGLEEYE_DIR, "venv", "bin", "python")
    _EAGLEEYE_PIP    = os.path.join(EAGLEEYE_DIR, "venv", "bin", "pip")


def eagleeye_installed() -> bool:
    return os.path.isdir(EAGLEEYE_DIR) and os.path.isfile(_EAGLEEYE_PYTHON)


def _eagleeye_find_entry() -> str | None:
    for name in ["start.py", "main.py", "EagleEye.py", "eagle_eye.py"]:
        for root, _, files in os.walk(EAGLEEYE_DIR):
            if "venv" in root: continue
            if name in files:
                return os.path.join(root, name)
    return None


def install_eagleeye() -> bool:
    log_info("Установка EagleEye...")
    ensure_dirs(TOOLS_DIR, DOWNLOADS_DIR)
    zip_path    = os.path.join(DOWNLOADS_DIR, "eagleeye_master.zip")
    extract_tmp = os.path.join(DOWNLOADS_DIR, "eagleeye_extracted")

    msg_step("[1/5]", "Скачивание репозитория EagleEye...")
    try:
        req = urllib.request.Request(EAGLEEYE_REPO_ZIP, headers={"User-Agent": "osint-launcher/3.0"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(zip_path, "wb") as f:
            f.write(resp.read())
    except Exception as e:
        msg_err(f"Ошибка скачивания: {e}"); return False

    msg_step("[2/5]", "Распаковка...")
    if os.path.isdir(extract_tmp): shutil.rmtree(extract_tmp)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_tmp)
        os.remove(zip_path)
    except Exception as e:
        msg_err(f"Ошибка распаковки: {e}"); return False

    if os.path.isdir(EAGLEEYE_DIR): shutil.rmtree(EAGLEEYE_DIR)
    items = os.listdir(extract_tmp)
    if len(items) == 1 and os.path.isdir(os.path.join(extract_tmp, items[0])):
        shutil.move(os.path.join(extract_tmp, items[0]), EAGLEEYE_DIR)
    else:
        shutil.move(extract_tmp, EAGLEEYE_DIR)

    msg_step("[3/5]", "Создание виртуального окружения...")
    try:
        subprocess.run([sys.executable, "-m", "venv",
                        os.path.join(EAGLEEYE_DIR, "venv")], check=True)
    except Exception as e:
        msg_err(f"Ошибка venv: {e}"); return False

    msg_step("[4/5]", "Установка зависимостей...")
    req_file = None
    for root, _, files in os.walk(EAGLEEYE_DIR):
        if "venv" in root: continue
        if "requirements.txt" in files:
            req_file = os.path.join(root, "requirements.txt"); break
    if req_file:
        try:
            subprocess.run([_EAGLEEYE_PIP, "install", "-r", req_file, "--quiet"], check=True)
        except Exception as e:
            msg_warn(f"Ошибка requirements: {e}")
    else:
        try:
            subprocess.run([_EAGLEEYE_PIP, "install", "-e", ".", "--quiet"],
                           cwd=EAGLEEYE_DIR, check=True)
        except Exception as e:
            msg_warn(f"pip install -e . ошибка: {e}")

    msg_step("[5/5]", "Тест запуска...")
    entry = _eagleeye_find_entry()
    if entry:
        msg_info(f"  Точка входа: {entry}")
        try:
            r = subprocess.run(
                [_EAGLEEYE_PYTHON, entry, "--help"],
                cwd=EAGLEEYE_DIR, capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=15
            )
            msg_info(f"  Код завершения: {r.returncode}")
        except Exception as e:
            msg_warn(f"  Тест ошибка: {e}")
    else:
        msg_warn("  Точка входа не найдена (start.py / main.py).")

    if eagleeye_installed():
        msg_ok("[+] EagleEye успешно установлен.")
        log_info("EagleEye установлен.")
        return True
    return False


def uninstall_eagleeye():
    if os.path.isdir(EAGLEEYE_DIR):
        shutil.rmtree(EAGLEEYE_DIR)
        msg_ok("[+] EagleEye успешно удалён.")
        log_info("EagleEye удалён.")
    else:
        msg_warn("EagleEye не был установлен.")
    pause(2)


def eagleeye_analyze(path: str) -> str | None:
    """
    Запускает EagleEye, ждёт завершения, возвращает полный вывод.
    Выводит stdout построчно, stderr — полностью после завершения.
    """
    entry = _eagleeye_find_entry()
    if not entry:
        msg_err("Точка входа EagleEye не найдена. Попробуйте переустановить.")
        return None

    cmd = [_EAGLEEYE_PYTHON, entry, "-f", path]

    if RICH_OK:
        console.print(f"\n  [white]Анализ:[/white] [cyan]{path}[/cyan]")
        console.print(f"  [dim]Python : {_EAGLEEYE_PYTHON}[/dim]")
        console.print(f"  [dim]cwd    : {EAGLEEYE_DIR}[/dim]")
        console.print(f"  [dim]cmd    : {' '.join(cmd)}[/dim]")
        console.rule(style="dark_violet")
    else:
        _cp(CW,  f"\n  Анализ: {CCY}{path}{RESET}")
        _cp(CGR, f"  Python : {_EAGLEEYE_PYTHON}")
        _cp(CGR, f"  cwd    : {EAGLEEYE_DIR}")
        _cp(CGR, f"  cmd    : {' '.join(cmd)}")
        _cp(CDP, "  " + "─" * 54)

    lines = []
    try:
        proc = subprocess.Popen(
            cmd, cwd=EAGLEEYE_DIR,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace"
        )
        # Читаем stdout построчно (потоково)
        for line in proc.stdout:
            line = line.rstrip(); lines.append(line)
            if RICH_OK:
                if "[+]" in line:   console.print(f"  [green]{line}[/green]")
                elif "[!]" in line: console.print(f"  [red]{line}[/red]")
                else:               console.print(f"  [white]{line}[/white]")
            else:
                _cp(CGRN if "[+]" in line else CW, f"  {line}")

        proc.wait()  # дожидаемся полного завершения
        stderr_out = proc.stderr.read() if proc.stderr else ""

        msg_info(f"  Код завершения: {proc.returncode}")

        if stderr_out.strip():
            if "API" in stderr_out or "key" in stderr_out.lower() or "token" in stderr_out.lower():
                msg_warn("EagleEye требует API-ключи для некоторых сервисов.")
                msg_info("Откройте tools/eagleeye/ и заполните config-файл.")
            # Выводим полный stderr
            if RICH_OK:
                console.print(f"  [red]stderr:[/red]\n  [dim]{stderr_out}[/dim]")
            else:
                _cp(CRED, f"  stderr:\n{stderr_out}")

        if not lines and not stderr_out:
            msg_warn("[!] EagleEye не вернул результатов.")
            return None

    except Exception as e:
        msg_err(f"Ошибка EagleEye: {e}")
        log_error("EagleEye run", e)
        return None

    return "\n".join(lines)


def run_eagleeye():
    while True:
        clear(); section_header("E A G L E E Y E")
        st = "[green]установлен[/green]" if eagleeye_installed() else "[red]не установлен[/red]"
        if RICH_OK: console.print(f"  Статус: {st}\n")
        else: _cp(CGRN if eagleeye_installed() else CRED,
                  f"  Статус: {'установлен' if eagleeye_installed() else 'не установлен'}\n")

        choice = submenu("EagleEye", [
            ("1", "Анализ изображения",       "OSINT-анализ по фото"),
            ("2", "Переустановить EagleEye",  "удалить и скачать заново"),
            ("3", "Удалить EagleEye",         "полное удаление"),
            ("4", "Назад",                    "главное меню"),
        ])

        if choice == "1":
            if not eagleeye_installed():
                msg_warn("[!] EagleEye не найден.")
                if input(f"  {CA}Установить? (Y/N): {RESET}").strip().upper() != "Y": continue
                install_eagleeye(); pause(2)
                if not eagleeye_installed(): continue
            while True:
                clear(); section_header("E A G L E E Y E  ·  Анализ")
                if RICH_OK: console.print("  [magenta]Перетащите изображение или укажите путь:[/magenta]")
                else:        _cp(CA, "  Перетащите изображение или укажите путь:")
                path = input(f"  {CP}›{RESET} ").strip().strip("'\"")
                if not path: msg_warn("Путь не указан."); break
                if not os.path.isfile(path): msg_err(f"Файл не найден: {path}"); pause(2); continue

                output = eagleeye_analyze(path)
                # Показываем меню только если анализ выполнился
                if output is None:
                    input(f"\n  {CGR}Нажмите Enter для продолжения...{RESET}")
                    break

                while True:
                    if RICH_OK: console.rule(style="dark_violet")
                    else: _cp(CDP, "\n  " + "─"*54)
                    action = submenu("Действия", [
                        ("1", "Сохранить результат в .txt", ""),
                        ("2", "Новый анализ",               ""),
                        ("3", "Назад",                      "в меню EagleEye"),
                    ])
                    if action == "1":
                        ensure_dirs(RESULTS_DIR, EAGLEEYE_RESULTS)
                        ts    = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                        fpath = os.path.join(EAGLEEYE_RESULTS, f"{ts}.txt")
                        with open(fpath, "w", encoding="utf-8") as f:
                            f.write(output)
                        msg_ok(f"[+] Результат сохранён:\n  {fpath}"); pause(2)
                    elif action == "2": break
                    elif action == "3": return
                    else: msg_warn("Неверный ввод."); pause(1)
                else: continue
                break

        elif choice == "2":
            clear(); section_header("E A G L E E Y E  ·  Переустановка")
            if os.path.isdir(EAGLEEYE_DIR): shutil.rmtree(EAGLEEYE_DIR)
            msg_ok("Старая версия удалена."); install_eagleeye(); pause(2)
        elif choice == "3":
            clear(); section_header("E A G L E E Y E  ·  Удаление")
            if input(f"  {CYEL}Вы уверены? (Y/N): {RESET}").strip().upper() == "Y":
                uninstall_eagleeye()
            else: msg_info("Отменено."); pause(1)
        elif choice == "4": return
        else: msg_warn("Неверный ввод."); pause(1)


# ═════════════════════════════════════════════════════════════════
#  PHONEINFOGA — installed helper (нужен для Settings)
# ═════════════════════════════════════════════════════════════════
def phoneinfoga_installed() -> bool:
    return os.path.isfile(PHONEINFOGA_EXE)


# ═════════════════════════════════════════════════════════════════
#  SETTINGS
# ═════════════════════════════════════════════════════════════════
_ALL_TOOLS = [
    ("ExifTool",    exiftool_installed,    install_exiftool,            EXIFTOOL_DIR),
    ("PhoneInfoga", phoneinfoga_installed, install_phoneinfoga_windows, PHONEINFOGA_DIR),
    ("Sherlock",    sherlock_installed,    install_sherlock,            SHERLOCK_DIR),
    ("Holehe",      holehe_installed,      install_holehe,              HOLEHE_DIR),
    ("Maigret",     maigret_installed,     install_maigret,             MAIGRET_DIR),
    ("EagleEye",    eagleeye_installed,    install_eagleeye,            EAGLEEYE_DIR),
]


def _tool_dir_size(tool_dir: str) -> str:
    if not os.path.isdir(tool_dir): return "—"
    try:
        total = sum(os.path.getsize(os.path.join(r, f))
                    for r, _, files in os.walk(tool_dir) for f in files)
        return f"{total//(1024*1024)} MB" if total > 1024*1024 else f"{total//1024} KB"
    except Exception:
        return "?"


def _print_tools_table():
    """Таблица статусов всех инструментов."""
    if RICH_OK:
        t = Table(box=box.SIMPLE, show_header=True, padding=(0,2), border_style="dark_violet")
        t.add_column("Инструмент",  style="magenta",   no_wrap=True)
        t.add_column("Статус",      no_wrap=True)
        t.add_column("Путь",        style="dim cyan",  no_wrap=True)
        t.add_column("Размер",      style="dim white",  justify="right")
        for name, check_fn, _, tool_dir in _ALL_TOOLS:
            try:    inst = check_fn()
            except: inst = False
            st      = "[green]✓ установлен[/green]" if inst else "[red]✗ не установлен[/red]"
            rel     = os.path.relpath(tool_dir, BASE_DIR) if os.path.isdir(tool_dir) else "—"
            sz      = _tool_dir_size(tool_dir)
            t.add_row(name, st, rel, sz)
        console.print(t)
    else:
        _cp(CDP, "  " + "─"*54)
        for name, check_fn, _, tool_dir in _ALL_TOOLS:
            try:    inst = check_fn()
            except: inst = False
            c  = CGRN if inst else CRED
            st = "✓ установлен" if inst else "✗ не установлен"
            sz = _tool_dir_size(tool_dir)
            _cp(c, f"  {name:<14} {st:<16} {sz}")
        _cp(CDP, "  " + "─"*54)


# ── Установить все ───────────────────────────────────────────────
def settings_install_all():
    clear(); section_header("S E T T I N G S  ·  Установить всё")
    to_install = []; already = 0
    for name, check_fn, install_fn, _ in _ALL_TOOLS:
        try:    inst = check_fn()
        except: inst = False
        if inst:
            msg_ok(f"{name} — уже установлен."); already += 1
        else:
            to_install.append((name, install_fn))

    if not to_install:
        msg_ok("Все инструменты уже установлены!")
        input(f"\n  {CGR}Нажмите Enter...{RESET}"); return

    print()
    if input(f"  {CA}Установить {len(to_install)} недостающих инструментов? (Y/N): {RESET}").strip().upper() != "Y":
        msg_info("Отменено."); pause(1); return

    success = 0; failed = []; total = len(to_install)
    for idx, (name, install_fn) in enumerate(to_install, 1):
        if RICH_OK: console.rule(style="dark_violet"); console.print(f"\n  [bold magenta][{idx}/{total}][/bold magenta] [white]Установка {name}...[/white]\n")
        else:       _cp(CDP,"  "+"─"*54); _cp(CA, f"\n  [{idx}/{total}] Установка {name}...\n")
        log_info(f"Установка {name}...")
        try:
            ok = install_fn()
            if ok:  success += 1; msg_ok(f"{name} установлен.")
            else:   failed.append(name); msg_warn(f"{name} — не удалось.")
        except Exception as e:
            failed.append(name); msg_err(f"{name} — ошибка: {e}"); log_error(f"Установка {name}", e)

    print()
    if RICH_OK: console.rule(style="dark_violet"); console.print(f"\n  [bold green]Установлено: {success}  Уже было: {already}  Ошибок: {len(failed)}[/bold green]")
    else:       _cp(CGRN, f"\n  Установлено: {success}  Уже было: {already}  Ошибок: {len(failed)}")
    if failed:
        if RICH_OK: console.print(f"  [yellow]Не удалось: {', '.join(failed)}[/yellow]")
        else:        _cp(CYEL, f"  Не удалось: {', '.join(failed)}")
    input(f"\n  {CGR}Нажмите Enter...{RESET}")


# ── Удалить все ──────────────────────────────────────────────────
def settings_uninstall_all():
    clear(); section_header("S E T T I N G S  ·  Удалить всё")
    if RICH_OK: console.print(f"  [bold red]Все инструменты будут удалены из папки tools/[/bold red]\n")
    else:        _cp(CRED, "  Все инструменты будут удалены из папки tools/\n")
    if input(f"  {CYEL}Вы действительно хотите удалить все инструменты? (Y/N): {RESET}").strip().upper() != "Y":
        msg_info("Отменено."); pause(1); return

    for name, _, _, tool_dir in _ALL_TOOLS:
        if os.path.isdir(tool_dir):
            try:    shutil.rmtree(tool_dir); msg_ok(f"{name} удалён."); log_info(f"{name} удалён.")
            except Exception as e: msg_err(f"{name} — ошибка: {e}"); log_error(f"Удаление {name}", e)
        else:
            msg_info(f"{name} — не установлен, пропуск.")

    # Сбрасываем кэш ExifTool
    global EXIFTOOL_PATH
    EXIFTOOL_PATH = None

    msg_ok("[+] Все инструменты удалены.")
    input(f"\n  {CGR}Нажмите Enter...{RESET}")


# ── Переустановить все ───────────────────────────────────────────
def settings_reinstall_all():
    clear(); section_header("S E T T I N G S  ·  Переустановить всё")
    if RICH_OK: console.print("  [white]Все инструменты будут удалены и установлены заново.[/white]\n")
    else:        _cp(CW, "  Все инструменты будут удалены и установлены заново.\n")
    if input(f"  {CYEL}Вы уверены? (Y/N): {RESET}").strip().upper() != "Y":
        msg_info("Отменено."); pause(1); return

    msg_step("·", "Удаление...")
    for name, _, _, tool_dir in _ALL_TOOLS:
        if os.path.isdir(tool_dir):
            try:    shutil.rmtree(tool_dir); msg_ok(f"{name} удалён.")
            except Exception as e: msg_err(f"{name}: {e}")

    global EXIFTOOL_PATH; EXIFTOOL_PATH = None

    print(); success = 0; failed = []; total = len(_ALL_TOOLS)
    for idx, (name, _, install_fn, _) in enumerate(_ALL_TOOLS, 1):
        if RICH_OK: console.rule(style="dark_violet"); console.print(f"\n  [bold magenta][{idx}/{total}][/bold magenta] [white]Установка {name}...[/white]\n")
        else:       _cp(CDP,"  "+"─"*54); _cp(CA, f"\n  [{idx}/{total}] Установка {name}...\n")
        log_info(f"Переустановка {name}...")
        try:
            ok = install_fn()
            if ok:  success += 1; msg_ok(f"{name} установлен.")
            else:   failed.append(name); msg_warn(f"{name} — не удалось.")
        except Exception as e:
            failed.append(name); msg_err(f"{name}: {e}"); log_error(f"Переустановка {name}", e)

    print()
    if RICH_OK: console.rule(style="dark_violet"); console.print(f"\n  [bold green]Переустановка завершена. Успешно: {success}/{total}[/bold green]")
    else:       _cp(CGRN, f"\n  Переустановка завершена. Успешно: {success}/{total}")
    if failed:
        if RICH_OK: console.print(f"  [yellow]Не удалось: {', '.join(failed)}[/yellow]")
        else:        _cp(CYEL, f"  Не удалось: {', '.join(failed)}")
    input(f"\n  {CGR}Нажмите Enter...{RESET}")


# ── Открыть папку Results ────────────────────────────────────────
def settings_open_results():
    clear(); section_header("S E T T I N G S  ·  Папка результатов")
    ensure_dirs(RESULTS_DIR)
    rpath = os.path.abspath(RESULTS_DIR)

    if RICH_OK: console.print(f"  [magenta]Путь:[/magenta] [cyan]{rpath}[/cyan]\n")
    else:        _cp(CA, f"  Путь: {CCY}{rpath}{RESET}\n")

    # Статистика по подпапкам
    txt_total = 0
    if os.path.isdir(RESULTS_DIR):
        if RICH_OK:
            t = Table(box=box.SIMPLE, show_header=True, padding=(0,2), border_style="dark_violet")
            t.add_column("Папка",      style="magenta"); t.add_column("TXT-файлов", justify="right"); t.add_column("Размер", justify="right", style="dim white")
            for entry in sorted(os.scandir(RESULTS_DIR), key=lambda e: e.name):
                if not entry.is_dir(): continue
                txts = [f for _, _, files in os.walk(entry.path) for f in files if f.endswith(".txt")]
                sz = sum(os.path.getsize(os.path.join(r,f)) for r,_,files in os.walk(entry.path) for f in files)
                txt_total += len(txts)
                sz_s = f"{sz//1024} KB" if sz < 1024*1024 else f"{sz//(1024*1024)} MB"
                t.add_row(entry.name, str(len(txts)), sz_s)
            console.print(t)
            console.print(f"\n  [white]Всего TXT-файлов: [cyan]{txt_total}[/cyan][/white]")
        else:
            _cp(CDP,"  "+"─"*54)
            for entry in sorted(os.scandir(RESULTS_DIR), key=lambda e: e.name):
                if not entry.is_dir(): continue
                txts = [f for _,_,files in os.walk(entry.path) for f in files if f.endswith(".txt")]
                txt_total += len(txts)
                _cp(CW, f"  {entry.name:<20}  {len(txts)} TXT-файлов")
            _cp(CDP,"  "+"─"*54)
            _cp(CW, f"  Всего TXT: {txt_total}")

    print()
    if input(f"  {CA}Открыть в проводнике? (Y/N): {RESET}").strip().upper() == "Y":
        try:    os.startfile(rpath) if platform.system()=="Windows" else subprocess.Popen(["open" if platform.system()=="Darwin" else "xdg-open", rpath])
        except Exception as e: msg_err(f"Не удалось открыть: {e}")
    input(f"\n  {CGR}Нажмите Enter...{RESET}")


# ── Открыть папку Tools ──────────────────────────────────────────
def settings_open_tools():
    clear(); section_header("S E T T I N G S  ·  Папка инструментов")
    ensure_dirs(TOOLS_DIR)
    tpath = os.path.abspath(TOOLS_DIR)

    if RICH_OK: console.print(f"  [magenta]Путь:[/magenta] [cyan]{tpath}[/cyan]\n")
    else:        _cp(CA, f"  Путь: {CCY}{tpath}{RESET}\n")

    _print_tools_table()
    print()

    if input(f"  {CA}Открыть в проводнике? (Y/N): {RESET}").strip().upper() == "Y":
        try:    os.startfile(tpath) if platform.system()=="Windows" else subprocess.Popen(["open" if platform.system()=="Darwin" else "xdg-open", tpath])
        except Exception as e: msg_err(f"Не удалось открыть: {e}")
    input(f"\n  {CGR}Нажмите Enter...{RESET}")


# ── Информация об инструментах ───────────────────────────────────
def settings_info():
    clear(); section_header("S E T T I N G S  ·  Информация об инструментах")
    _print_tools_table()
    input(f"\n  {CGR}Нажмите Enter...{RESET}")


# ── Очистить TXT ─────────────────────────────────────────────────
def settings_clear_txt():
    clear(); section_header("S E T T I N G S  ·  Очистить TXT-отчёты")
    if not os.path.isdir(RESULTS_DIR):
        msg_warn("[!] Папка results/ не найдена.")
        input(f"\n  {CGR}Нажмите Enter...{RESET}"); return

    txt_files = [os.path.join(r, f)
                 for r, _, files in os.walk(RESULTS_DIR)
                 for f in files if f.lower().endswith(".txt")]

    if not txt_files:
        msg_warn("[!] TXT-файлы не найдены.")
        input(f"\n  {CGR}Нажмите Enter для продолжения...{RESET}"); return

    if RICH_OK:
        console.print(f"  [white]Найдено TXT-файлов: [cyan]{len(txt_files)}[/cyan][/white]\n")
        for fp in txt_files[:20]: console.print(f"  [dim]  · {os.path.relpath(fp, BASE_DIR)}[/dim]")
        if len(txt_files) > 20: console.print(f"  [dim]  ... и ещё {len(txt_files)-20}[/dim]")
    else:
        _cp(CW, f"\n  Найдено TXT: {len(txt_files)}\n")
        for fp in txt_files[:20]: _cp(CGR, f"    · {os.path.relpath(fp, BASE_DIR)}")
        if len(txt_files) > 20: _cp(CGR, f"    ... и ещё {len(txt_files)-20}")

    print()
    if input(f"  {CYEL}Вы действительно хотите удалить все TXT-отчёты? (Y/N): {RESET}").strip().upper() != "Y":
        msg_info("Отменено."); pause(1); return

    deleted = 0; skipped = 0
    for fp in txt_files:
        try:
            os.remove(fp); deleted += 1
        except Exception as e:
            skipped += 1
            try:
                with open(os.path.join(_LOGS_DIR, "error.log"), "a", encoding="utf-8") as lf:
                    lf.write(f"[clear_txt] {fp}: {e}\n")
            except Exception: pass

    msg_ok(f"[+] Удалено файлов: {deleted}")
    if skipped: msg_warn(f"[!] Пропущено: {skipped}")
    input(f"\n  {CGR}Нажмите Enter для продолжения...{RESET}")


# ── Главное подменю Settings ─────────────────────────────────────
def run_settings():
    while True:
        clear(); section_header("S E T T I N G S")

        inst_count = sum(1 for _, chk, _, _ in _ALL_TOOLS if (lambda c: (lambda: False)() if not c else c())(chk))
        # Корректный подсчёт
        inst_count = 0
        for _, chk, _, _ in _ALL_TOOLS:
            try:
                if chk(): inst_count += 1
            except Exception: pass
        total = len(_ALL_TOOLS)

        c_count = CGRN if inst_count == total else CYEL
        if RICH_OK:
            col = "green" if inst_count == total else "yellow"
            console.print(f"  Инструменты: [{col}]{inst_count}/{total} установлено[/{col}]\n")
        else:
            _cp(c_count, f"  Инструменты: {inst_count}/{total} установлено\n")

        choice = submenu("Settings", [
            ("1", "Установить все инструменты",      "скачать недостающие"),
            ("2", "Удалить все инструменты",         "полная очистка tools/"),
            ("3", "Переустановить все инструменты",  "удалить и скачать заново"),
            ("4", "Открыть папку Results",           "results/"),
            ("5", "Открыть папку Tools",             "tools/"),
            ("6", "Информация об инструментах",      "статус и пути"),
            ("7", "Очистить все TXT-отчёты",         "удалить *.txt из results/"),
            ("8", "Назад",                           "главное меню"),
        ])

        if   choice == "1": settings_install_all()
        elif choice == "2": settings_uninstall_all()
        elif choice == "3": settings_reinstall_all()
        elif choice == "4": settings_open_results()
        elif choice == "5": settings_open_tools()
        elif choice == "6": settings_info()
        elif choice == "7": settings_clear_txt()
        elif choice == "8": return
        else: msg_warn("Неверный ввод."); pause(1)


# ═════════════════════════════════════════════════════════════════
#  ПРОВЕРКА ИНСТРУМЕНТОВ ПРИ ЗАПУСКЕ
# ═════════════════════════════════════════════════════════════════
def startup_tools_check():
    missing = []
    for name, check_fn, install_fn, _ in _ALL_TOOLS:
        try:
            if not check_fn(): missing.append((name, install_fn))
        except Exception:
            missing.append((name, install_fn))

    if not missing: return

    clear(); show_logo()

    if RICH_OK:
        console.rule(style="dark_violet")
        console.print(f"\n  [bold yellow]Проверка инструментов при запуске[/bold yellow]\n")
        console.print(f"  Не установлено: [bold red]{len(missing)}[/bold red] из [white]{len(_ALL_TOOLS)}[/white]\n")
        for name, check_fn, _, _ in _ALL_TOOLS:
            try:    inst = check_fn()
            except: inst = False
            st = "[green]✓  установлен[/green]" if inst else "[red]✗  не установлен[/red]"
            console.print(f"  {st}   [white]{name}[/white]")
        console.print()
        console.rule(style="dark_violet")
        console.print(f"\n  [bold magenta]Установить все отсутствующие инструменты сейчас?[/bold magenta]")
        console.print(f"  [cyan]Будет установлено: {', '.join(n for n,_ in missing)}[/cyan]\n")
        console.print(f"  [dim]Это необязательно — каждый инструмент можно установить[/dim]")
        console.print(f"  [dim]отдельно из его меню или через Settings → Установить все.[/dim]\n")
    else:
        _cp(CDP,"  "+"─"*54)
        _cp(CYEL, f"\n  Проверка инструментов при запуске")
        _cp(CW,   f"  Не установлено: {len(missing)} из {len(_ALL_TOOLS)}\n")
        for name, check_fn, _, _ in _ALL_TOOLS:
            try:    inst = check_fn()
            except: inst = False
            _cp(CGRN if inst else CRED, f"  {'✓' if inst else '✗'}  {name}")
        print()
        _cp(CA,  f"\n  Установить все отсутствующие инструменты сейчас?")
        _cp(CGR, f"  Это необязательно — можно установить позже через Settings.\n")

    if input(f"  {CA}Установить сейчас? (Y/N): {RESET}").strip().upper() != "Y":
        if RICH_OK: console.print(f"\n  [dim]Пропущено. Используйте Settings → Установить все.[/dim]\n")
        else:        _cp(CGR, "\n  Пропущено. Используйте Settings → Установить все.\n")
        pause(1); return

    success = 0; failed = []; total = len(missing)
    for idx, (name, install_fn) in enumerate(missing, 1):
        if RICH_OK: console.rule(style="dark_violet"); console.print(f"\n  [bold magenta][{idx}/{total}][/bold magenta] [white]Установка {name}...[/white]\n")
        else:       _cp(CDP,"  "+"─"*54); _cp(CA, f"\n  [{idx}/{total}] Установка {name}...\n")
        log_info(f"Стартовая установка {name}...")
        try:
            ok = install_fn()
            if ok:  success += 1; msg_ok(f"{name} установлен.")
            else:   failed.append(name); msg_warn(f"{name} — не удалось.")
        except Exception as e:
            failed.append(name); msg_err(f"{name}: {e}"); log_error(f"Стартовая установка {name}", e)

    print()
    if RICH_OK: console.rule(style="dark_violet"); console.print(f"\n  [bold green]Установлено: {success}/{total}[/bold green]")
    else:       _cp(CGRN, f"\n  Установлено: {success}/{total}")
    if failed:
        if RICH_OK: console.print(f"  [yellow]Не удалось: {', '.join(failed)}[/yellow]\n  [dim]Попробуйте позже через Settings.[/dim]")
        else:        _cp(CYEL, f"  Не удалось: {', '.join(failed)}")
    input(f"\n  {CGR}Нажмите Enter для перехода в главное меню...{RESET}")


# ═════════════════════════════════════════════════════════════════
#  ГЛАВНОЕ МЕНЮ
# ═════════════════════════════════════════════════════════════════
def show_main_menu() -> str:
    show_logo()
    return submenu("M A I N   M E N U", [
        ("1", "ExifTool",    "метаданные файлов"),
        ("2", "PhoneInfoga", "поиск номеров"),
        ("3", "GeoOSINT",    "геолокация по фото"),
        ("4", "Sherlock",    "поиск по username"),
        ("5", "Holehe",      "проверка email"),
        ("6", "Maigret",     "поиск по username (расширенный)"),
        ("7", "EagleEye",    "OSINT-анализ изображений"),
        ("8", "Settings",    "настройки и управление"),
        ("9", "Exit",        "выход"),
    ])


# ═════════════════════════════════════════════════════════════════
#  ЗАПУСК
# ═════════════════════════════════════════════════════════════════
def check_admin():
    if detect_os() == "windows":
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            msg_warn("Рекомендуется запуск от имени администратора.")
            pause(2)
    else:
        try:
            if os.geteuid() != 0:
                msg_warn("Для установки могут потребоваться права sudo.")
                pause(2)
        except AttributeError:
            pass


_LOGS_DIR = os.path.join(BASE_DIR, "logs")

def main():
    if detect_os() == "windows":
        os.system("color")
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 7)
        except Exception: pass
        try: sys.stdout.reconfigure(encoding="utf-8")
        except Exception: pass

    ensure_dirs(os.path.join(BASE_DIR, "results"),
                os.path.join(BASE_DIR, "tools"),
                _LOGS_DIR)

    ensure_dependencies()
    log_info("=== .INT Launcher запущен ===")
    check_admin()
    startup_tools_check()

    _HANDLERS = {
        "1": ("ExifTool",    run_exiftool),
        "2": ("PhoneInfoga", run_phoneinfoga),
        "3": ("GeoOSINT",    run_geo_osint),
        "4": ("Sherlock",    run_sherlock),
        "5": ("Holehe",      run_holehe),
        "6": ("Maigret",     run_maigret),
        "7": ("EagleEye",    run_eagleeye),
        "8": ("Settings",    run_settings),
    }

    while True:
        clear()
        choice = show_main_menu()

        if choice == "9":
            clear()
            if RICH_OK: console.print(f"\n  [bold magenta]До свидания![/bold magenta]\n")
            else:        _cp(CP, f"\n  {BOLD}До свидания!{RESET}\n")
            log_info("Программа завершена.")
            sys.exit(0)

        if choice not in _HANDLERS:
            msg_warn("Неверный ввод."); pause(1); continue

        name, handler = _HANDLERS[choice]
        if RICH_OK: console.print(f"  [dim]Запуск модуля: {name}[/dim]")
        else:        _cp(CGR, f"  Запуск модуля: {name}")
        log_info(f"Запуск модуля: {name}")

        try:
            handler()
        except Exception as e:
            msg_err(f"Необработанная ошибка в модуле '{name}': {e}")
            log_error(f"Модуль {name}", e)
            input(f"\n  {CGR}Нажмите Enter для возврата в меню...{RESET}")


if __name__ == "__main__":
    main()

