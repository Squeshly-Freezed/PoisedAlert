-- Poised Alert for WoW: Forever
-- Plays a sound the moment the rogue Poised buff appears on you.
-- Change the settings in Options > AddOns > Poised Alert, or type /poised.
--
-- How it decides: it waits for the game to actually put the Poised buff on you
-- (usually about half a second after you reach full Energy out of combat) and
-- plays the sound at that moment. Energy is only read for the debug readout.
-- With "Only while stealthed" on, it plays only in Stealth: when Poised arrives
-- while you're stealthed, or when you go into Stealth with Poised already up.

-- Every file in an addon gets the same two values: the addon's folder name and
-- a shared table (ns). Settings.lua reads what this file puts in ns.
local addonName, ns = ...

local POISED_NAME     = "Poised"  -- the buff's name (change it if your game isn't in English)
local POISED_SPELL_ID = 1328826   -- the Poised buff's spell ID, confirmed in game; the name check is a backup

local REPEAT_GUARD = 3  -- seconds: never sound twice within this long
local FLICKER      = 1  -- seconds: Poised vanishing and coming straight back is the same buff
local LOAD_WINDOW  = 3  -- seconds after a loading screen when a full buff refresh is just a catch-up

-- Starting values for the settings panel. Your choices are saved in PoisedAlertDB.
ns.DEFAULTS = {
    enabled     = true,
    stealthOnly = false,     -- only sound when you're in Stealth
    sound       = 7080,      -- a one-hand blade cutting air
    channel     = "Master",
    customFile  = false,     -- play poised.ogg from this folder instead
    debug       = false,
}

ns.CUSTOM_FILE    = "Interface\\AddOns\\" .. addonName .. "\\poised.ogg"
ns.FALLBACK_SOUND = 8960  -- the ready check chime is always in the game

-- Sounds offered in the panel. These are SoundKit IDs; hear them at wowhead.com/forever/sound=ID
-- Forever's game files only have the original game's sounds, so every one of
-- these comes from it. Sounds added in later expansions are silent in Forever.
ns.SUGGESTIONS = {
    { id = 7080, name = "Blade whoosh",      desc = "A one-hand blade whooshing through the air." },
    { id = 7081, name = "Heavy whoosh",      desc = "A two-handed weapon whooshing through the air." },
    { id = 3091, name = "Special swing",     desc = "A warrior's special-attack weapon swing." },
    { id = 700,  name = "Blade drawn",       desc = "A metal blade drawn from its sheath." },
    { id = 698,  name = "Blade sheathed",    desc = "A metal blade slid into its sheath." },
    { id = 3175, name = "Map ping",          desc = "The minimap ping." },
    { id = 8960, name = "Ready check chime", desc = "The ready check sound." },
}

-- Sounds from earlier test versions that turned out to be silent in Forever
-- (Slow whoosh, Spell-swords and Wind gust, all from later expansions).
-- A saved choice of one goes back to the default.
ns.RETIRED_SOUNDS = { [19062] = true, [75718] = true, [206046] = true }

-- Why a sound might not play, for chat messages.
ns.WHY_SILENT = "Forever only has the original game's sounds, so it may not be here (or your sound is muted)."

-- Volume channels the game accepts, in the order the panel lists them.
ns.CHANNELS = {
    { value = "Master",   label = "Master", tip = "Plays even if Sound Effects are turned down." },
    { value = "SFX",      label = "Sound Effects" },
    { value = "Dialog",   label = "Dialog" },
    { value = "Ambience", label = "Ambience" },
    { value = "Music",    label = "Music" },
}

function ns.Print(msg)
    print("|cfffff468Poised Alert:|r " .. msg)
end

-- Reads a setting. Before your saved settings load, it returns the default.
function ns.Get(key)
    local db = PoisedAlertDB
    if db and db[key] ~= nil then
        return db[key]
    end
    return ns.DEFAULTS[key]
end

-- Changes a setting. Once the panel exists it goes through the panel, so the
-- panel always shows the current value. 'quiet' skips the sound preview.
function ns.SetOption(key, value, quiet)
    local setting = ns.settings and ns.settings[key]
    if not setting then
        PoisedAlertDB = PoisedAlertDB or {}
        PoisedAlertDB[key] = value
        return
    end
    ns.quiet = quiet
    local ok, err = pcall(setting.SetValue, setting, value)
    ns.quiet = nil  -- always reset, even if SetValue failed
    if not ok then error(err, 2) end
end

-- A usable SoundKit ID is a whole number from 1 up. The upper limit also
-- rejects "inf", which Lua happily turns into a number.
function ns.IsValidSoundID(id)
    return type(id) == "number" and id >= 1 and id <= 2147483647 and id == math.floor(id)
end

function ns.IsValidChannel(value)
    for _, c in ipairs(ns.CHANNELS) do
        if c.value == value then return true end
    end
    return false
end

function ns.SoundName(id)
    for _, s in ipairs(ns.SUGGESTIONS) do
        if s.id == id then
            return s.name .. " (" .. id .. ")"
        end
    end
    return "sound " .. tostring(id)
end

-- Plays a SoundKit and tells you whether the game actually played it.
-- A missing sound (or a muted game) returns false instead of erroring.
function ns.TryPlay(soundKit)
    local ok, willPlay = pcall(PlaySound, soundKit, ns.Get("channel"))
    return ok and willPlay and true or false
end

-- Your own file if that's switched on, then your pick, then the ready check
-- chime, so the alert never goes silent because one of them is missing.
-- If it had to skip one, it returns a note saying so (previews print it).
local function PlayAlertSound()
    local skipped = {}
    if ns.Get("customFile") then
        local ok, willPlay = pcall(PlaySoundFile, ns.CUSTOM_FILE, ns.Get("channel"))
        if ok and willPlay then return nil end
        skipped[#skipped + 1] = "poised.ogg"
    end
    local sound = ns.Get("sound")
    if ns.TryPlay(sound) then
        if #skipped > 0 then
            return "poised.ogg didn't play, so " .. ns.SoundName(sound) .. " played instead."
        end
        return nil
    end
    skipped[#skipped + 1] = ns.SoundName(sound)
    if ns.TryPlay(ns.FALLBACK_SOUND) then
        return table.concat(skipped, " and ") .. " didn't play, so the ready check chime played instead."
    end
    return "no sound played. Check your volume in Options > Audio."
end

-- The panel's Play button and /poised test. Previews don't count toward the
-- repeat guard, so testing the sound can never swallow a real alert.
function ns.Preview()
    local note = PlayAlertSound()
    if note then ns.Print(note) end
end

local lastAlert = -math.huge
local function Alert()
    local now = GetTime()
    if now - lastAlert < REPEAT_GUARD then return end
    lastAlert = now
    PlayAlertSound()
end

-- Used by the panel's "Enter ID" box and by /poised use.
-- Returns true if the ID was saved, false if it wasn't a usable ID.
function ns.UseSound(id)
    if not ns.IsValidSoundID(id) then
        ns.Print("that isn't a sound ID. Use a whole number, like 700.")
        return false
    end
    local played = ns.TryPlay(id)
    ns.SetOption("sound", id, true)  -- quiet: it just played
    if played then
        ns.Print("Poised will now play " .. ns.SoundName(id) .. ".")
    else
        ns.Print("saved " .. id .. ", but it didn't play. " .. ns.WHY_SILENT .. " Until it plays, the ready check chime plays instead.")
    end
    return true
end

-- Returns false if the panel doesn't exist (so /poised can print help instead).
function ns.OpenSettings()
    if not ns.category then return false end
    if InCombatLockdown() then
        ns.Print("the settings can't open during combat. Try again after the fight.")
    else
        Settings.OpenToCategory(ns.category:GetID())
    end
    return true
end

---------------------------------------------------------------------------
-- Watching for the buff
---------------------------------------------------------------------------

-- Since Midnight, the game hides buff data from addons as "secret values"
-- during combat, boss encounters, challenge-mode dungeons and PvP matches.
-- Touching a secret value throws an error, so these checks come first.
local function IsSecret(value)
    return issecretvalue ~= nil and issecretvalue(value)
end

local RESTRICTION = Enum and Enum.AddOnRestrictionType
local function BuffsHidden()
    if InCombatLockdown() then return true end
    if not (RESTRICTION and C_RestrictedActions and C_RestrictedActions.IsAddOnRestrictionActive) then
        return false
    end
    for _, kind in ipairs({ RESTRICTION.Combat, RESTRICTION.Encounter, RESTRICTION.ChallengeMode, RESTRICTION.PvPMatch }) do
        if C_RestrictedActions.IsAddOnRestrictionActive(kind) then
            return true
        end
    end
    return false
end

local function IsPoised(aura)
    if IsSecret(aura.spellId) or IsSecret(aura.name) then
        return false
    end
    return aura.spellId == POISED_SPELL_ID or aura.name == POISED_NAME
end

-- True while the game counts you as stealthed. Older clients answer 1 instead
-- of true, so any "yes" counts. A hidden (secret) answer counts as no.
local function InStealth()
    if not IsStealthed then return false end
    local stealthed = IsStealthed()
    if IsSecret(stealthed) then return false end
    return stealthed and true or false
end

local poisedAuraID      -- the Poised buff's instance ID while it's on you, otherwise nil
local poisedGoneAt = -math.huge
local fullEnergyAt      -- when you reached full Energy out of combat (debug readout only)
local worldLoadedAt     -- when the last loading screen finished (nil until the first one does)
local wasStealthed = false  -- whether you were stealthed when we last checked
local hiddenNoted = false

-- True during and just after a loading screen, when buff updates are the game
-- catching the addon up rather than Poised arriving.
local function JustLoaded(now)
    return not worldLoadedAt or now - worldLoadedAt <= LOAD_WINDOW
end

-- Looks through your buffs for Poised and returns it (or nil).
local function FindPoised()
    for i = 1, 255 do
        local aura = C_UnitAuras.GetAuraDataByIndex("player", i, "HELPFUL")
        if not aura then return nil end
        local ok, isPoised = pcall(IsPoised, aura)
        if ok and isPoised then return aura end
    end
end

-- Silently re-reads your buffs, for moments when the addon couldn't watch:
-- after combat, after a loading screen, and when the game stops hiding buffs.
local function Resync()
    if BuffsHidden() then return end
    hiddenNoted = false
    local aura = FindPoised()
    poisedAuraID = aura and aura.auraInstanceID
end

local ENERGY = Enum and Enum.PowerType and Enum.PowerType.Energy or 3
local function UpdateFullEnergy()
    if BuffsHidden() then fullEnergyAt = nil return end
    local current, max = UnitPower("player", ENERGY), UnitPowerMax("player", ENERGY)
    if IsSecret(current) or IsSecret(max) then fullEnergyAt = nil return end
    if max > 0 and current >= max then
        fullEnergyAt = fullEnergyAt or GetTime()
    else
        fullEnergyAt = nil
    end
end

local function Describe(aura)
    return ("new buff: %s (spell ID %s)"):format(tostring(aura.name), tostring(aura.spellId))
end

-- The Poised buff just went on.
local function PoisedArrived(aura)
    -- With "Only while stealthed" on, this waits until you go into Stealth.
    local waitForStealth = ns.Get("stealthOnly") and not InStealth()
    if ns.Get("debug") then
        local timing = fullEnergyAt and ("%.2f s after full Energy"):format(GetTime() - fullEnergyAt)
            or "time since full Energy unknown"
        local note = (ns.Get("enabled") and waitForStealth) and " No sound until you go into Stealth." or ""
        ns.Print(("Poised is up (spell ID %s), %s.%s"):format(tostring(aura.spellId), timing, note))
    end
    if ns.Get("enabled") and not waitForStealth then
        Alert()
    end
end

local function OnAuraUpdate(info)
    if BuffsHidden() then
        if ns.Get("debug") and not InCombatLockdown() and not hiddenNoted then
            hiddenNoted = true
            ns.Print("the game is hiding buffs from addons right now (boss fight or PvP match), so Poised can't be seen here.")
        end
        return  -- Resync catches up once buffs are visible again
    end
    if not info then return end

    local now = GetTime()

    -- A full refresh lists every buff you have. Right after a loading screen
    -- that's a catch-up, not Poised arriving, so it only updates what we know.
    if info.isFullUpdate then
        local aura = FindPoised()
        local isNew = aura and not poisedAuraID and not JustLoaded(now)
        poisedAuraID = aura and aura.auraInstanceID
        if isNew then PoisedArrived(aura) end
        return
    end

    -- Was Poised already on you before this update? If the game swaps it for a
    -- fresh copy in one go, that's a refresh, not a new Poised.
    local wasUp = poisedAuraID ~= nil

    if poisedAuraID and info.removedAuraInstanceIDs then
        for _, id in ipairs(info.removedAuraInstanceIDs) do
            if id == poisedAuraID then
                poisedAuraID = nil
                poisedGoneAt = now
            end
        end
    end

    for _, aura in ipairs(info.addedAuras or {}) do
        local ok, isPoised = pcall(IsPoised, aura)
        if ok and isPoised then
            poisedAuraID = aura.auraInstanceID
            if not wasUp and now - poisedGoneAt > FLICKER and worldLoadedAt then
                PoisedArrived(aura)
            elseif ns.Get("debug") then
                ns.Print(("Poised refreshed (spell ID %s), no sound."):format(tostring(aura.spellId)))
            end
        elseif ns.Get("debug") then
            local described, text = pcall(Describe, aura)
            if described then ns.Print(text) end
        end
    end
end

local handlers = {}

function handlers.UNIT_AURA(unit, info)
    OnAuraUpdate(info)
end

function handlers.UNIT_POWER_FREQUENT(unit, powerType)
    if powerType == "ENERGY" then
        UpdateFullEnergy()
    end
end

function handlers.PLAYER_ENTERING_WORLD()
    worldLoadedAt = GetTime()
    wasStealthed = InStealth()
    Resync()
    UpdateFullEnergy()
end

-- With "Only while stealthed" on, going into Stealth with Poised already up
-- is the moment you're ready to open, so that plays the sound.
-- Only a real step into Stealth counts: not a repeat event while you're
-- already stealthed, and not the game catching up after a loading screen.
function handlers.UPDATE_STEALTH()
    local stealthed = InStealth()
    local steppedIn = stealthed and not wasStealthed
    wasStealthed = stealthed
    if not (steppedIn and worldLoadedAt) then return end
    if not (ns.Get("enabled") and ns.Get("stealthOnly")) then return end
    if BuffsHidden() or not poisedAuraID then return end
    if ns.Get("debug") then
        ns.Print("you went into Stealth with Poised up.")
    end
    Alert()
end

function handlers.PLAYER_REGEN_DISABLED()
    fullEnergyAt = nil  -- in combat, so the "out of combat at full Energy" clock stops
end

function handlers.PLAYER_REGEN_ENABLED()
    Resync()
    UpdateFullEnergy()
end

-- Fired as the game starts or stops hiding data from addons. Wait one frame so
-- the change has fully happened, then catch up.
function handlers.ADDON_RESTRICTION_STATE_CHANGED(kind, state)
    local inactive = Enum and Enum.AddOnRestrictionState and Enum.AddOnRestrictionState.Inactive
    if inactive == nil or state == inactive then
        C_Timer.After(0, function()
            Resync()
            UpdateFullEnergy()
        end)
    end
end

local frame = CreateFrame("Frame")
frame:RegisterUnitEvent("UNIT_AURA", "player")
frame:RegisterUnitEvent("UNIT_POWER_FREQUENT", "player")
frame:RegisterEvent("PLAYER_ENTERING_WORLD")
frame:RegisterEvent("PLAYER_REGEN_DISABLED")
frame:RegisterEvent("PLAYER_REGEN_ENABLED")
frame:RegisterEvent("UPDATE_STEALTH")
pcall(frame.RegisterEvent, frame, "ADDON_RESTRICTION_STATE_CHANGED")  -- only on clients that have it

frame:SetScript("OnEvent", function(self, event, ...)
    handlers[event](...)
end)

---------------------------------------------------------------------------
-- Slash commands
---------------------------------------------------------------------------

local function PrintHelp()
    ns.Print("/poised - open the settings")
    ns.Print("/poised test - play the alert")
    ns.Print("/poised stealth - only sound while stealthed, on or off")
    ns.Print("/poised sounds - list sounds to try")
    ns.Print("/poised try ID - hear a sound")
    ns.Print("/poised use ID - make it the alert sound")
    ns.Print("/poised reset - go back to the default sound")
    ns.Print("/poised debug - list buffs in chat as they appear")
end

SLASH_POISEDALERT1 = "/poised"
SlashCmdList.POISEDALERT = function(msg)
    local cmd, arg = strtrim(msg or ""):lower():match("^(%S*)%s*(.-)$")
    local id = tonumber(arg)

    if cmd == "" then
        if not ns.OpenSettings() then PrintHelp() end

    elseif cmd == "test" then
        ns.Preview()

    elseif cmd == "stealth" then
        ns.SetOption("stealthOnly", not ns.Get("stealthOnly"))
        ns.Print(ns.Get("stealthOnly")
            and "now only plays while you're stealthed (when Poised arrives in Stealth, or when you go into Stealth with it up)."
            or "now plays whenever Poised is ready, stealthed or not.")

    elseif cmd == "sounds" then
        ns.Print("sounds to try (yours is " .. ns.Get("sound") .. "):")
        for _, s in ipairs(ns.SUGGESTIONS) do
            print(("    %d  %s"):format(s.id, s.desc))
        end
        ns.Print("hear one with /poised try ID, keep it with /poised use ID")

    elseif cmd == "try" and id then
        if not ns.TryPlay(id) then
            ns.Print(arg .. " didn't play. " .. ns.WHY_SILENT)
        end

    elseif cmd == "use" and id then
        ns.UseSound(id)

    elseif cmd == "reset" then
        ns.SetOption("sound", ns.DEFAULTS.sound, true)
        ns.Print("back to the default sound, " .. ns.SoundName(ns.DEFAULTS.sound) .. ".")

    elseif cmd == "debug" then
        ns.SetOption("debug", not ns.Get("debug"))
        ns.Print(ns.Get("debug") and "debug on. New buffs, and when Poised arrives, will be listed in chat." or "debug off.")

    else
        PrintHelp()
    end
end
