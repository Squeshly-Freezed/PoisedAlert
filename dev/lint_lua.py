"""Lints WoW addon Lua files with luacheck, run inside Lua 5.1 (WoW's Lua version).
Usage: python3 -I lint_lua.py <luacheck_src_dir> <file.lua> [more.lua ...]
WoW's own globals are declared below so luacheck only flags real problems."""
import sys, pathlib
from lupa.lua51 import LuaRuntime

luacheck_src = pathlib.Path(sys.argv[1]).resolve()
files = [pathlib.Path(p) for p in sys.argv[2:]]

# Globals this addon creates or writes into (allowed to be set).
WRITABLE = ["PoisedAlertDB", "SLASH_POISEDALERT1", "SlashCmdList", "StaticPopupDialogs"]
# Blizzard functions and tables the addon reads (checked against Forever's UI source / API docs).
READ_ONLY = [
    "CreateFrame", "GetTime", "InCombatLockdown", "PlaySound", "PlaySoundFile", "issecretvalue",
    "strtrim", "Settings", "EventUtil", "StaticPopup_Show", "StaticPopup_StandardEditBoxOnEscapePressed",
    "StaticPopup_StandardNonEmptyTextHandler", "CreateSettingsButtonInitializer",
    "CreateSettingsListSectionHeaderInitializer", "ACCEPT", "CANCEL", "C_UnitAuras",
    "C_RestrictedActions", "Enum", "UnitPower", "UnitPowerMax", "C_Timer", "IsStealthed",
]

lua = LuaRuntime()
g = lua.globals()
g.LC_PATH = str(luacheck_src)
lua.execute(r"""
package.path = LC_PATH .. "/?.lua;" .. LC_PATH .. "/?/init.lua;" .. package.path
package.preload["lfs"] = function() return { _VERSION = "LuaFileSystem stub" } end
""")
luacheck = lua.eval('require("luacheck")')

def lua_list(items):
    t = lua.table()
    for i, item in enumerate(items, 1):
        t[i] = item
    return t

opts = lua.table()
opts["std"] = "lua51"
opts["globals"] = lua_list(WRITABLE)
opts["read_globals"] = lua_list(READ_ONLY)
opts["max_line_length"] = False
opts["unused_args"] = False   # event handlers take (self, event, ...) on purpose

sources = lua_list([f.read_text(encoding="utf-8") for f in files])
report = luacheck.check_strings(sources, opts)

total = 0
for i, f in enumerate(files, 1):
    issues = report[i]
    n = len(issues)
    total += n
    for j in range(1, n + 1):
        w = issues[j]
        print(f"{f.name}:{w.line}:{w.column}: ({w.code}) {luacheck.get_message(w)}")
print(f"{total} warning(s) in {len(files)} file(s)")
sys.exit(1 if total else 0)
