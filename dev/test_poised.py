"""Runs Poised Alert in Lua 5.1 (WoW's Lua version) with stand-ins for the WoW API.
Stand-ins copy the real behaviour documented in Blizzard's Forever UI source and
generated API docs: the UNIT_AURA payload, aura lookups, addon restrictions,
Settings type checks and asserts, and the popup's accept/keep-open rule."""
import sys, pathlib
from lupa.lua51 import LuaRuntime

ADDON = pathlib.Path(sys.argv[1])
CORE = (ADDON / "PoisedAlert.lua").read_text(encoding="utf-8")
SETTINGS = (ADDON / "Settings.lua").read_text(encoding="utf-8")
TOC = (ADDON / "PoisedAlert.toc").read_text(encoding="utf-8")

STUBS = r"""
calls, printed, opened, popups, timers, registeredEvents = {}, {}, {}, {}, {}, {}
clock, inCombat, customExists = 0, false, false
missing, broken = {}, {}
energy, maxEnergy = 100, 100
stealthed = false           -- what IsStealthed() returns
playerAuras = {}            -- what C_UnitAuras.GetAuraDataByIndex("player", i, "HELPFUL") returns
activeRestrictions = {}     -- AddOnRestrictionType -> true while active
SECRET = setmetatable({}, {__tostring = function() return "<secret>" end})
issecretvalue = function(v) return v == SECRET end
ACCEPT, CANCEL = "Accept", "Cancel"

Enum = {
  AddOnRestrictionType = { Combat = 0, Encounter = 1, ChallengeMode = 2, PvPMatch = 3, Map = 4, Chat = 5 },
  AddOnRestrictionState = { Inactive = 0, Activating = 1, Active = 2 },
  PowerType = { Energy = 3 },
}
C_RestrictedActions = {}
function C_RestrictedActions.IsAddOnRestrictionActive(kind) return activeRestrictions[kind] == true end
C_UnitAuras = {}
function C_UnitAuras.GetAuraDataByIndex(unit, i, filter)
  assert(unit == "player" and filter == "HELPFUL")
  return playerAuras[i]
end
function UnitPower(unit, kind) assert(unit == "player" and kind == 3) return energy end
function UnitPowerMax(unit, kind) assert(unit == "player" and kind == 3) return maxEnergy end
C_Timer = {}
function C_Timer.After(delay, fn) timers[#timers+1] = fn end
function runTimers() local t = timers; timers = {}; for _, fn in ipairs(t) do fn() end end

function GetTime() return clock end
function InCombatLockdown() return inCombat end
function IsStealthed() return stealthed end
function PlaySound(id, ch)
  if broken[id] then error("bad sound kit") end
  calls[#calls+1] = "PlaySound " .. tostring(id) .. " " .. tostring(ch)
  if missing[id] then return nil end
  return true, 1
end
function PlaySoundFile(p, ch) calls[#calls+1] = "PlaySoundFile " .. p .. " " .. tostring(ch); return customExists end
function print(...) local t = {} for i = 1, select("#", ...) do t[#t+1] = tostring(select(i, ...)) end printed[#printed+1] = table.concat(t, " ") end
function strtrim(s) return (s:gsub("^%s+", ""):gsub("%s+$", "")) end
SlashCmdList = {}
frame = nil
rejectEvent = nil
function CreateFrame()
  local f = {unitEvents = {}}
  function f:RegisterUnitEvent(e, ...) self.unitEvents[e] = {...} end
  function f:RegisterEvent(e)
    if e == rejectEvent then error("Attempt to register unknown event \"" .. e .. "\"") end
    registeredEvents[e] = true
  end
  function f:SetScript(name, fn) self[name] = fn end
  frame = f
  return f
end

-- EventUtil -----------------------------------------------------------------
loadedCallbacks = {}
EventUtil = {}
function EventUtil.ContinueOnAddOnLoaded(name, cb) loadedCallbacks[name] = cb end
function addonLoaded() loadedCallbacks["PoisedAlert"]() end

-- Settings API (behaviour copied from Blizzard_Settings_Shared) -------------
registered, layoutItems = {}, {}
Settings = { VarType = { Boolean = "boolean", String = "string", Number = "number" } }
local function NewInitializer(kind, data)
  local init = { kind = kind, data = data }
  function init:SetParentInitializer(parent, predicate)
    assert(parent, "parent required")
    if parent == self then error("initializer cannot be self") end
    self.parent, self.predicate = parent, predicate
  end
  function init:GetSetting() return self.data.setting end
  return init
end
function Settings.RegisterVerticalLayoutCategory(name)
  local category = { name = name }
  function category:GetID() return 4242 end
  local layout = {}
  function layout:AddInitializer(init) layoutItems[#layoutItems+1] = init; return init end
  categoryObj = category
  return category, layout
end
function Settings.RegisterAddOnCategory(category) addonCategory = category end
function Settings.OpenToCategory(id) opened[#opened+1] = id end
function Settings.RegisterAddOnSetting(category, variable, key, tbl, varType, name, default)
  assert(category == categoryObj, "wrong category")
  assert(type(tbl) == "table", "'variableTbl' argument must be a table.")
  assert(type(default) == varType, "default doesn't match type for " .. variable)
  assert(registered[variable] == nil, "duplicate variable " .. variable)
  if tbl[key] == nil then tbl[key] = default end
  local s = { variable = variable, key = key, tbl = tbl, varType = varType, name = name, default = default, callbacks = {} }
  function s:GetValue() return self.tbl[self.key] end
  function s:GetVariableType() return self.varType end
  function s:SetValue(value)
    if type(value) ~= self.varType then
      error(("Setting '%s' expected %s, got %s"):format(self.name, self.varType, type(value)))
    end
    self.tbl[self.key] = value
    for _, cb in ipairs(self.callbacks) do cb(self, value) end
  end
  function s:SetValueToDefault() self:SetValue(self.default) end
  function s:SetValueChangedCallback(cb) self.callbacks[#self.callbacks+1] = cb end
  registered[variable] = s
  return s
end
function Settings.CreateCheckbox(category, setting, tooltip)
  assert(setting:GetVariableType() == "boolean")
  local init = NewInitializer("checkbox", { setting = setting, tooltip = tooltip })
  layoutItems[#layoutItems+1] = init
  return init
end
function Settings.CreateDropdown(category, setting, options, tooltip)
  assert(options ~= nil)
  local init = NewInitializer("dropdown", { setting = setting, options = options, tooltip = tooltip })
  layoutItems[#layoutItems+1] = init
  return init
end
function Settings.CreateControlTextContainer()
  local c = { data = {} }
  function c:Add(value, label, tooltip) self.data[#self.data+1] = { value = value, label = label, text = label, tooltip = tooltip } end
  function c:GetData() return self.data end
  return c
end
function CreateSettingsListSectionHeaderInitializer(name, tooltip)
  return NewInitializer("header", { name = name, tooltip = tooltip })
end
function CreateSettingsButtonInitializer(name, buttonText, buttonClick, tooltip, addSearchTags)
  assert(addSearchTags ~= nil, "addSearchTags must be passed")
  return NewInitializer("button", { name = name, buttonText = buttonText, buttonClick = buttonClick, tooltip = tooltip })
end

-- StaticPopup (Forever's version: dialog:GetEditBox(), OnAccept returning true keeps it open)
StaticPopupDialogs = {}
function StaticPopup_StandardEditBoxOnEscapePressed(editBox) editBox:GetParent():Hide() end
function StaticPopup_StandardNonEmptyTextHandler() end
function StaticPopup_Show(which, a1, a2, data)
  local info = assert(StaticPopupDialogs[which], "no dialog " .. which)
  local dialog = { which = which, shown = true, data = data }
  local editBox = { text = "", numeric = false, focused = false }
  function editBox:SetNumeric(v) self.numeric = v end
  function editBox:SetText(t) self.text = t end
  function editBox:GetText() return self.text end
  function editBox:HighlightText() end
  function editBox:SetFocus() self.focused = true end
  function editBox:GetParent() return dialog end
  function dialog:GetEditBox() return editBox end
  function dialog:Hide() self.shown = false end
  if info.OnShow then info.OnShow(dialog, data) end
  popups[#popups+1] = dialog
  return dialog
end
function clickAccept(dialog)   -- mirrors StaticPopup.lua: hide = not OnAccept(dialog, data, data2)
  local info = StaticPopupDialogs[dialog.which]
  if not info.OnAccept(dialog, dialog.data, dialog.data2) then dialog:Hide() end
end
function openIDBox() StaticPopup_Show("POISEDALERT_SOUND_ID"); return popups[#popups] end

-- Event helpers ---------------------------------------------------------------
function event(name, ...) frame.OnEvent(frame, name, ...) end
function aura(name, id, instance) return { name = name, spellId = id, auraInstanceID = instance, isHelpful = true } end
function poised(instance) return aura("Poised", 1328825, instance) end
function addAura(a) playerAuras[#playerAuras+1] = a; event("UNIT_AURA", "player", { isFullUpdate = false, addedAuras = { a } }) end
function dropAura(instance)
  for i, a in ipairs(playerAuras) do if a.auraInstanceID == instance then table.remove(playerAuras, i) break end end
  event("UNIT_AURA", "player", { isFullUpdate = false, removedAuraInstanceIDs = { instance } })
end
function swapAura(oldInstance, newAura)   -- one update that removes the old copy and adds a new one
  for i, a in ipairs(playerAuras) do if a.auraInstanceID == oldInstance then table.remove(playerAuras, i) break end end
  playerAuras[#playerAuras+1] = newAura
  event("UNIT_AURA", "player", { isFullUpdate = false, removedAuraInstanceIDs = { oldInstance }, addedAuras = { newAura } })
end
function fullRefresh() event("UNIT_AURA", "player", { isFullUpdate = true }) end
function setEnergy(v) energy = v; event("UNIT_POWER_FREQUENT", "player", "ENERGY") end
function setStealth(v) stealthed = v; event("UPDATE_STEALTH") end
function slash(s) SlashCmdList.POISEDALERT(s) end
function findItem(kind, field, value)
  for _, it in ipairs(layoutItems) do
    if it.kind == kind and (field == nil or it.data[field] == value or (it.data.setting and it.data.setting.variable == value)) then return it end
  end
end
function loadAddon()
  NS = {}
  assert(loadstring(SRC_CORE, "PoisedAlert.lua"))("PoisedAlert", NS)
  assert(loadstring(SRC_SETTINGS, "Settings.lua"))("PoisedAlert", NS)
end
"""

failures = 0
def check(label, cond):
    global failures
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures += 1

def fresh(saved=None, before=None, core=CORE):
    lua = LuaRuntime()
    lua.execute(STUBS)
    g = lua.globals()
    g.SRC_CORE, g.SRC_SETTINGS = core, SETTINGS
    if before: lua.execute(before)
    if saved: lua.execute(saved)
    lua.execute("loadAddon()")
    return lua

def ncalls(lua): return lua.eval("#calls")
def last_call(lua): return lua.eval("calls[#calls]")
def last_print(lua): return lua.eval("printed[#printed]") or ""
def all_prints(lua): return "\n".join(lua.eval("printed").values())
def db(lua, key): return lua.eval(f"PoisedAlertDB and PoisedAlertDB.{key}")
def played_since(lua, before): return ncalls(lua) - before

# --- .toc ---------------------------------------------------------------------------
check(".toc: Forever interface 16001, saves PoisedAlertDB, version 1.4.1",
      "## Interface: 16001" in TOC and "## SavedVariables: PoisedAlertDB" in TOC and "## Version: 1.4.1" in TOC)
check(".toc: icon and category for the in-game addon list",
      "## IconTexture: Interface\\Icons\\Ability_Stealth" in TOC and "## Category: Rogue" in TOC)
check(".toc loads the core before the settings panel", TOC.index("PoisedAlert.lua") < TOC.index("Settings.lua"))

# --- Loading and the panel --------------------------------------------------------------
lua = fresh()
check("registers the events it needs",
      all(lua.eval(f"registeredEvents.{e}") for e in
          ["PLAYER_ENTERING_WORLD", "PLAYER_REGEN_DISABLED", "PLAYER_REGEN_ENABLED", "UPDATE_STEALTH",
           "ADDON_RESTRICTION_STATE_CHANGED"])
      and lua.eval("frame.unitEvents.UNIT_AURA[1]") == "player"
      and lua.eval("frame.unitEvents.UNIT_POWER_FREQUENT[1]") == "player")
lua.execute("slash('')")
check("/poised before the panel exists prints help", "/poised test" in all_prints(lua))
lua.execute("addonLoaded()")
check("registers the six settings with their defaults",
      sorted(lua.eval("registered").keys()) == sorted(["POISEDALERT_ENABLED", "POISEDALERT_STEALTHONLY",
          "POISEDALERT_SOUND", "POISEDALERT_CHANNEL", "POISEDALERT_CUSTOMFILE", "POISEDALERT_DEBUG"])
      and db(lua, "enabled") is True and db(lua, "stealthOnly") is False
      and db(lua, "sound") == 7080 and db(lua, "channel") == "Master"
      and db(lua, "customFile") is False and db(lua, "debug") is False)
order = [lua.eval(f"layoutItems[{i}].kind") for i in range(1, lua.eval("#layoutItems") + 1)]
check("panel order: header, toggle, stealth, header, sound, play, enter ID, channel, own file, header, debug",
      order == ["header", "checkbox", "checkbox", "header", "dropdown", "button", "button", "dropdown",
                "checkbox", "header", "checkbox"])
lua.execute("enabledInit = findItem('checkbox', 'setting', 'POISEDALERT_ENABLED')")
deps = lua.eval("(function() local n = 0 for _, it in ipairs(layoutItems) do if it.parent == enabledInit then n = n + 1 end end return n end)()")
check("stealth and sound controls (6) grey out with the toggle; debug doesn't",
      deps == 6 and lua.eval("findItem('checkbox', 'setting', 'POISEDALERT_STEALTHONLY').parent == enabledInit") and lua.eval("findItem('checkbox', 'setting', 'POISEDALERT_DEBUG').parent") is None)
opts = lua.eval("findItem('dropdown', 'setting', 'POISEDALERT_SOUND').data.options()")
check("sound list: 7 named sounds, tooltips carry the SoundKit ID",
      [opts[i].label for i in range(1, len(opts) + 1)] == ["Blade whoosh", "Heavy whoosh", "Special swing",
          "Blade drawn", "Blade sheathed", "Map ping", "Ready check chime"] and "SoundKit 700." in opts[4].tooltip)
# Forever only has the original game's sounds. Its SoundKit IDs are all below about 9000
# (The Burning Crusade's Karazhan sounds start at 9100); later ones were silent in game.
ids = [opts[i].value for i in range(1, len(opts) + 1)]
check("every built-in sound is an original-game ID, and none is a retired silent one",
      all(i < 9000 for i in ids) and not any(lua.eval(f"NS.RETIRED_SOUNDS[{i}]") for i in ids))
chan = lua.eval("findItem('dropdown', 'setting', 'POISEDALERT_CHANNEL').data.options()")
check("channel list comes from the shared list: Master, SFX, Dialog, Ambience, Music",
      [chan[i].value for i in range(1, len(chan) + 1)] == ["Master", "SFX", "Dialog", "Ambience", "Music"])
check("own-file path and tooltip use the addon's folder name",
      lua.eval("NS.CUSTOM_FILE") == "Interface\\AddOns\\PoisedAlert\\poised.ogg"
      and "PoisedAlert addon folder" in lua.eval("findItem('checkbox', 'setting', 'POISEDALERT_CUSTOMFILE').data.tooltip"))

# --- Following the actual buff ------------------------------------------------------
lua.execute("clock = 5; addAura(poised(1))")
check("during the loading screen Poised is noted but doesn't sound", ncalls(lua) == 0)
lua.execute("clock = 10; event('PLAYER_ENTERING_WORLD')")
check("entering the world with Poised already up stays quiet", ncalls(lua) == 0)

lua.execute("clock = 20; dropAura(1)")
b = ncalls(lua)
lua.execute("clock = 30; addAura(poised(2))")
check("Poised going on plays the sound (7080 on Master)", played_since(lua, b) == 1 and last_call(lua) == "PlaySound 7080 Master")

b = ncalls(lua)
lua.execute("clock = 40; swapAura(2, poised(3))")
check("the game swapping Poised for a fresh copy in one update is a refresh, not a new alert", played_since(lua, b) == 0)

lua.execute("clock = 50; dropAura(3); clock = 50.5; addAura(poised(4))")
check("Poised flickering off and straight back on (under 1 s) doesn't re-sound", played_since(lua, b) == 0)

lua.execute("clock = 60; dropAura(4); clock = 68; addAura(poised(5))")
check("used up and back later: sounds again", played_since(lua, b) == 1)

b = ncalls(lua)
lua.execute("clock = 69; dropAura(5); clock = 70.5; addAura(poised(6))")
check("never twice within 3 s, even if it really came back", played_since(lua, b) == 0)

b = ncalls(lua)
lua.execute("""clock = 80; inCombat = true; event('PLAYER_REGEN_DISABLED')
  dropAura(6)                       -- consumed by the opener; addon can't watch in combat
  clock = 100; inCombat = false; event('PLAYER_REGEN_ENABLED')
  clock = 101; addAura(poised(7))""")
check("after combat it re-reads your buffs, so the next Poised still sounds", played_since(lua, b) == 1)

b = ncalls(lua)
lua.execute("""clock = 110; dropAura(7)
  clock = 120; playerAuras[#playerAuras+1] = poised(8); fullRefresh()""")
check("Poised arriving in a full refresh (outside a loading screen) still sounds", played_since(lua, b) == 1)

b = ncalls(lua)
lua.execute("""clock = 200; dropAura(8); event('PLAYER_ENTERING_WORLD')
  clock = 201; playerAuras[#playerAuras+1] = poised(9); fullRefresh()
  clock = 205; addAura(poised(10))""")
check("a full refresh just after a loading screen is a catch-up, and a later copy is a refresh", played_since(lua, b) == 0)

b = ncalls(lua)
lua.execute("""clock = 300; dropAura(9); dropAura(10)
  addAura(aura('Stealth', 1784, 11)); fullRefresh()
  addAura({ name = SECRET, spellId = SECRET, auraInstanceID = 12 })
  local boom = setmetatable({}, { __index = function() error('secret value!') end })
  event('UNIT_AURA', 'player', { isFullUpdate = false, addedAuras = { boom } })""")
check("other buffs, secret values and an aura that throws are all ignored safely", played_since(lua, b) == 0)

# --- When the game hides buffs (boss fights, PvP matches) -----------------------------------
lua.execute("slash('debug')")
b, p = ncalls(lua), lua.eval("#printed")
lua.execute("""clock = 400; activeRestrictions[Enum.AddOnRestrictionType.PvPMatch] = true
  addAura(poised(13)); addAura(aura('Sprint', 2983, 14))""")
pvp_prints = [lua.eval(f"printed[{i}]") for i in range(p + 1, lua.eval("#printed") + 1)]
check("in a PvP match it stays silent without errors", played_since(lua, b) == 0)
check("debug explains once that the game is hiding buffs",
      sum("hiding buffs" in x for x in pvp_prints) == 1)
lua.execute("""activeRestrictions[Enum.AddOnRestrictionType.PvPMatch] = nil
  event('ADDON_RESTRICTION_STATE_CHANGED', Enum.AddOnRestrictionType.PvPMatch, Enum.AddOnRestrictionState.Inactive)""")
check("when the match ends it waits a frame before catching up", lua.eval("#timers") == 1)
lua.execute("runTimers(); clock = 410; addAura(poised(15))")
check("...then knows Poised is already up, so the next copy doesn't re-sound", played_since(lua, b) == 0)
lua.execute("event('ADDON_RESTRICTION_STATE_CHANGED', Enum.AddOnRestrictionType.Combat, Enum.AddOnRestrictionState.Activating)")
check("a restriction starting doesn't trigger a catch-up", lua.eval("#timers") == 0)

# --- Debug readout: time from full Energy to the buff -------------------------------------
lua.execute("""clock = 500; dropAura(13); dropAura(15)
  setEnergy(40); clock = 506.0; setEnergy(100)
  clock = 506.52; addAura(poised(16))""")
check("debug shows how long after full Energy Poised arrived",
      "Poised is up (spell ID 1328825), 0.52 s after full Energy." in all_prints(lua))
lua.execute("clock = 520; dropAura(16); inCombat = true; event('PLAYER_REGEN_DISABLED'); inCombat = false; clock = 530; addAura(poised(17))")
check("combat resets the Energy clock", "time since full Energy unknown" in last_print(lua))
lua.execute("clock = 535; swapAura(17, poised(18))")
check("debug notes refreshes too", "Poised refreshed (spell ID 1328825), no sound." in last_print(lua))

b = ncalls(lua)
lua.execute("registered.POISEDALERT_ENABLED:SetValue(false); clock = 600; dropAura(18); clock = 610; addAura(poised(19))")
check("with the sound off, debug still reports Poised but nothing plays",
      played_since(lua, b) == 0 and "Poised is up" in last_print(lua))
lua.execute("registered.POISEDALERT_ENABLED:SetValue(true); slash('debug')")

# --- Previews never swallow a real alert ------------------------------------------------------
lua.execute("clock = 690; dropAura(19)")
b = ncalls(lua)
lua.execute("clock = 700.5; findItem('button', 'buttonText', 'Play').data.buttonClick(); clock = 701; addAura(poised(20))")
check("pressing Play and then Poised arriving a second later plays both", played_since(lua, b) == 2)

lua.execute("registered.POISEDALERT_SOUND:SetValue(700)")
check("picking a sound in the list previews it", last_call(lua) == "PlaySound 700 Master")
lua.execute("missing[3175] = true; registered.POISEDALERT_SOUND:SetValue(3175)")
check("picking a sound that won't play says so in chat", "Map ping (3175) didn't play." in last_print(lua))
p = lua.eval("#printed")
lua.execute("missing[3175] = nil; registered.POISEDALERT_SOUND:SetValue(700)")
check("...and picking one that plays prints nothing", lua.eval("#printed") == p)
lua.execute("registered.POISEDALERT_CHANNEL:SetValue('SFX'); clock = 800; dropAura(20); clock = 810; addAura(poised(21))")
check("the alert uses the picked sound and channel", last_call(lua) == "PlaySound 700 SFX")
lua.execute("registered.POISEDALERT_CHANNEL:SetValue('Master')")
lua.execute("registered.POISEDALERT_CUSTOMFILE:SetValue(true); customExists = true; slash('test')")
check("own poised.ogg plays when switched on", last_call(lua) == "PlaySoundFile Interface\\AddOns\\PoisedAlert\\poised.ogg Master")
lua.execute("customExists = false; slash('test'); registered.POISEDALERT_CUSTOMFILE:SetValue(false)")
check("falls back to the picked sound when poised.ogg can't play, and Play says so",
      last_call(lua) == "PlaySound 700 Master"
      and "poised.ogg didn't play, so Blade drawn (700) played instead." in last_print(lua))
lua.execute("missing[700] = true; slash('test')")
check("Play says when your sound didn't play and the ready check chime covered for it",
      last_call(lua) == "PlaySound 8960 Master"
      and "Blade drawn (700) didn't play, so the ready check chime played instead." in last_print(lua))
lua.execute("missing[8960] = true; slash('test'); missing[700] = nil; missing[8960] = nil")
check("if nothing plays at all, Play points you to the volume settings", "Options > Audio" in last_print(lua))

# --- Enter ID box ---------------------------------------------------------------------------
lua.execute("dlg = openIDBox()")
check("Enter ID opens pre-filled and focused, leaving the shared box's limits alone",
      lua.eval("dlg:GetEditBox().text") == "700" and lua.eval("dlg:GetEditBox().focused") is True
      and lua.eval("dlg:GetEditBox().numeric") is False
      and lua.eval("StaticPopupDialogs.POISEDALERT_SOUND_ID.maxLetters") is None)
bad = ["", "abc", "0", "-5", "2.5", "nan", "inf", "1e309", "99999999999"]
kept_open = True
for s in bad:
    lua.execute(f"dlg = openIDBox(); dlg:GetEditBox():SetText('{s}'); clickAccept(dlg)")
    kept_open = kept_open and lua.eval("dlg.shown") is True
check("bad IDs (incl. inf and 1e309) are refused, the box stays open to fix them",
      kept_open and db(lua, "sound") == 700)
lua.execute("dlg = openIDBox(); eb = dlg:GetEditBox(); eb:SetText('abc'); StaticPopupDialogs.POISEDALERT_SOUND_ID.EditBoxOnEnterPressed(eb)")
check("pressing Enter on a bad ID keeps the box open too", lua.eval("dlg.shown") is True)
b = ncalls(lua)
lua.execute("dlg = openIDBox(); dlg:GetEditBox():SetText('3091'); clickAccept(dlg)")
check("a good ID is saved, played once, and the box closes",
      db(lua, "sound") == 3091 and played_since(lua, b) == 1 and lua.eval("dlg.shown") is False)
lua.execute("dlg = openIDBox(); eb = dlg:GetEditBox(); eb:SetText('55555'); StaticPopupDialogs.POISEDALERT_SOUND_ID.EditBoxOnEnterPressed(eb)")
opts = lua.eval("findItem('dropdown', 'setting', 'POISEDALERT_SOUND').data.options()")
check("Enter saves too, and a typed ID shows in the list as Custom",
      db(lua, "sound") == 55555 and lua.eval("dlg.shown") is False and opts[len(opts)].label == "Custom (55555)")
lua.execute("missing[424242] = true; dlg = openIDBox(); dlg:GetEditBox():SetText('424242'); clickAccept(dlg)")
p = lua.eval("#printed")
lua.execute("clock = 900; dropAura(21); clock = 910; addAura(poised(22))")
check("an ID that won't play is saved with a warning, and the ready check chime covers for it",
      db(lua, "sound") == 424242 and "didn't play" in all_prints(lua) and last_call(lua) == "PlaySound 8960 Master")
check("a real alert falls back quietly, with nothing in chat", lua.eval("#printed") == p)

# --- Slash commands --------------------------------------------------------------------------
lua.execute("slash('')")
check("/poised opens the panel", lua.eval("opened[#opened]") == 4242)
lua.execute("inCombat = true; slash(''); inCombat = false")
check("/poised in combat explains instead of opening", lua.eval("#opened") == 1 and "during combat" in last_print(lua))
b = ncalls(lua)
lua.execute("slash('use 700')")
check("/poised use updates the panel and plays once", lua.eval("registered.POISEDALERT_SOUND:GetValue()") == 700 and played_since(lua, b) == 1)
lua.execute("slash('use inf')")
check("/poised use refuses inf", db(lua, "sound") == 700 and "isn't a sound ID" in last_print(lua))
lua.execute("slash('reset')")
check("/poised reset goes back to 7080 without a preview", db(lua, "sound") == 7080 and played_since(lua, b) == 1)
lua.execute("slash('try 19062')")
check("/poised try plays without changing the setting", last_call(lua) == "PlaySound 19062 Master" and db(lua, "sound") == 7080)
lua.execute("slash('help')")
check("/poised help lists the commands", "/poised use ID" in all_prints(lua) and "/poised stealth" in all_prints(lua))

# --- Only while stealthed ------------------------------------------------------------------
st = fresh()
st.execute("addonLoaded(); clock = 10; event('PLAYER_ENTERING_WORLD')")
st.execute("slash('stealth')")
check("/poised stealth turns it on and the panel shows it",
      st.eval("registered.POISEDALERT_STEALTHONLY:GetValue()") is True and "only plays while you're stealthed" in last_print(st))
st.execute("slash('debug')")
b = ncalls(st)
st.execute("clock = 20; addAura(poised(1))")
check("Poised arriving outside Stealth stays quiet, and debug says why",
      played_since(st, b) == 0 and "No sound until you go into Stealth." in last_print(st))
st.execute("clock = 25; setStealth(true)")
check("going into Stealth with Poised up plays it",
      played_since(st, b) == 1 and "went into Stealth with Poised up" in last_print(st))
st.execute("clock = 26; event('UPDATE_STEALTH')")
check("a repeat stealth event while already stealthed doesn't count", played_since(st, b) == 1)
st.execute("clock = 26.5; setStealth(false); clock = 27; setStealth(true)")
check("out and back into Stealth within 3 s: no second sound", played_since(st, b) == 1)
st.execute("clock = 35; setStealth(false); clock = 40; setStealth(true)")
check("back into Stealth later with Poised still up: plays again", played_since(st, b) == 2)

b = ncalls(st)
st.execute("clock = 50; setStealth(false); dropAura(1); clock = 55; setStealth(true)")
check("going into Stealth without Poised stays quiet", played_since(st, b) == 0)
st.execute("clock = 60; addAura(poised(2))")
check("Poised arriving while you're stealthed plays it", played_since(st, b) == 1)

b = ncalls(st)
st.execute("""clock = 70; setStealth(false); inCombat = true; event('PLAYER_REGEN_DISABLED')
  clock = 75; setStealth(true)          -- Vanish in combat
  clock = 76; setStealth(false); inCombat = false; event('PLAYER_REGEN_ENABLED')""")
check("going into Stealth in combat stays quiet", played_since(st, b) == 0)

st.execute("registered.POISEDALERT_ENABLED:SetValue(false); clock = 90; setStealth(true)")
check("with the alert off, Stealth doesn't play it", played_since(st, b) == 0)
st.execute("clock = 95; setStealth(false); dropAura(2); clock = 100; addAura(poised(3))")
check("with the alert off, debug doesn't promise a Stealth sound",
      "Poised is up" in last_print(st) and "No sound until" not in last_print(st))
st.execute("registered.POISEDALERT_ENABLED:SetValue(true)")

b = ncalls(st)
st.execute("clock = 110; stealthed = SECRET; event('UPDATE_STEALTH'); dropAura(3); clock = 120; addAura(poised(4))")
check("a hidden stealth state counts as not stealthed, without errors", played_since(st, b) == 0)
st.execute("stealthed = false; event('UPDATE_STEALTH')")

st.execute("slash('stealth')")
b = ncalls(st)
st.execute("clock = 130; dropAura(4); clock = 140; addAura(poised(5)); clock = 141; setStealth(true)")
check("/poised stealth again turns it off: Poised plays straight away, Stealth adds nothing",
      st.eval("registered.POISEDALERT_STEALTHONLY:GetValue()") is False and played_since(st, b) == 1)

old = fresh(saved="PoisedAlertDB = { stealthOnly = true }")
old.execute("addonLoaded(); event('PLAYER_ENTERING_WORLD'); clock = 20; addAura(poised(1)); clock = 25; stealthed = 1; event('UPDATE_STEALTH')")
check("an older client's 1 from IsStealthed counts as stealthed", ncalls(old) == 1)

rl = fresh(saved="PoisedAlertDB = { stealthOnly = true }",
           before="stealthed = true; playerAuras[1] = poised(1)")
rl.execute("addonLoaded(); clock = 5; event('PLAYER_ENTERING_WORLD'); clock = 6; event('UPDATE_STEALTH')")
check("a /reload while stealthed with Poised up stays quiet", ncalls(rl) == 0)
rl.execute("clock = 20; setStealth(false); clock = 25; setStealth(true)")
check("...and the next real step into Stealth plays it", ncalls(rl) == 1)
rl2 = fresh(saved="PoisedAlertDB = { stealthOnly = true }",
            before="stealthed = true; playerAuras[1] = poised(1)")
rl2.execute("addonLoaded(); fullRefresh(); event('UPDATE_STEALTH'); clock = 5; event('PLAYER_ENTERING_WORLD')")
check("a stealth event during the loading screen is ignored", ncalls(rl2) == 0)

# --- Robustness ------------------------------------------------------------------------------
ok = lua.eval("(function() return (pcall(NS.SetOption, 'sound', 'not a number', true)) end)()")
check("a failed setting change can't leave previews stuck off", ok is False and lua.eval("NS.quiet") is None)

lua2 = fresh(saved="PoisedAlertDB = { sound = '700', channel = 'Banana', enabled = 'yes', debug = 1 }")
lua2.execute("addonLoaded()")
check("damaged saved settings are reset to defaults instead of breaking the panel",
      db(lua2, "sound") == 7080 and db(lua2, "channel") == "Master" and db(lua2, "enabled") is True and db(lua2, "debug") is False)
lua3 = fresh(saved="PoisedAlertDB = { sound = math.huge }")
lua3.execute("addonLoaded()")
check("a saved infinite sound ID is reset", db(lua3, "sound") == 7080)
lua4 = fresh(saved="PoisedAlertDB = { sound = 700, channel = 'SFX' }")
lua4.execute("addonLoaded()")
check("good saved settings from earlier versions carry over", db(lua4, "sound") == 700 and db(lua4, "channel") == "SFX")
retired_ok = True
for old_id in (19062, 75718, 206046):
    m = fresh(saved=f"PoisedAlertDB = {{ sound = {old_id} }}")
    m.execute("addonLoaded()")
    retired_ok = retired_ok and db(m, "sound") == 7080 and "back to Blade whoosh (7080)." in last_print(m)
check("a saved sound that's silent in Forever goes back to the default, with a note", retired_ok)

lua5 = fresh(before="rejectEvent = 'ADDON_RESTRICTION_STATE_CHANGED'; C_RestrictedActions = nil")
lua5.execute("addonLoaded(); event('PLAYER_ENTERING_WORLD'); clock = 50; addAura(poised(1))")
check("still loads and works on a client without the restriction event or API", ncalls(lua5) == 1)
lua6 = fresh(before="issecretvalue = nil")
lua6.execute("event('PLAYER_ENTERING_WORLD'); clock = 50; addAura(poised(1))")
check("works when issecretvalue doesn't exist", ncalls(lua6) == 1)

print(f"\n{failures} failure(s)")
sys.exit(1 if failures else 0)
