-- The settings panel: Options > AddOns > Poised Alert (or type /poised).
-- Built with Blizzard's Settings API, so it looks and behaves like the game's own options.

local addonName, ns = ...

ns.settings = {}  -- the setting objects, by key, so slash commands can update the panel

-- The popup behind the "Enter ID" button.
-- The game reuses one popup frame for every dialog, so this doesn't change
-- the text box's limits (they'd carry over to Blizzard's own dialogs).
-- ns.UseSound checks the typed ID instead.
StaticPopupDialogs["POISEDALERT_SOUND_ID"] = {
    text = "Enter a SoundKit ID for the Poised alert.\nYou can find IDs on wowhead.com/forever/sounds.",
    button1 = ACCEPT,
    button2 = CANCEL,
    hasEditBox = 1,
    editBoxInstructions = "SoundKit ID",
    OnShow = function(dialog)
        local editBox = dialog:GetEditBox()
        editBox:SetText(tostring(ns.Get("sound")))
        editBox:HighlightText()
        editBox:SetFocus()
    end,
    -- Returning true keeps the box open, so a mistyped ID can be fixed.
    OnAccept = function(dialog)
        return not ns.UseSound(tonumber(dialog:GetEditBox():GetText()))
    end,
    EditBoxOnEnterPressed = function(editBox)
        if ns.UseSound(tonumber(editBox:GetText())) then
            editBox:GetParent():Hide()
        end
    end,
    EditBoxOnEscapePressed = StaticPopup_StandardEditBoxOnEscapePressed,
    EditBoxOnTextChanged = StaticPopup_StandardNonEmptyTextHandler,
    timeout = 0,
    whileDead = 1,
    hideOnEscape = 1,
}

-- Throws away saved values the panel can't use (a hand-edited or damaged
-- file), so it starts from the default instead of breaking.
local function CleanSavedSettings(db)
    for key, default in pairs(ns.DEFAULTS) do
        if type(db[key]) ~= type(default) then
            db[key] = nil
        end
    end
    if db.sound ~= nil and not ns.IsValidSoundID(db.sound) then db.sound = nil end
    if db.channel ~= nil and not ns.IsValidChannel(db.channel) then db.channel = nil end
    if db.sound ~= nil and ns.RETIRED_SOUNDS[db.sound] then
        db.sound = nil
        ns.Print("your alert sound isn't in Forever's files, so it's back to " .. ns.SoundName(ns.DEFAULTS.sound) .. ".")
    end
end

-- Your saved settings (PoisedAlertDB) only exist once the game has loaded
-- this addon, so the panel is built at that moment.
EventUtil.ContinueOnAddOnLoaded(addonName, function()
    PoisedAlertDB = PoisedAlertDB or {}
    CleanSavedSettings(PoisedAlertDB)

    local category, layout = Settings.RegisterVerticalLayoutCategory("Poised Alert")

    -- Each setting reads and writes one field of PoisedAlertDB.
    local function AddSetting(key, label, varType)
        local setting = Settings.RegisterAddOnSetting(category, "POISEDALERT_" .. key:upper(),
            key, PoisedAlertDB, varType, label, ns.DEFAULTS[key])
        ns.settings[key] = setting
        return setting
    end

    -----------------------------------------------------------------------
    layout:AddInitializer(CreateSettingsListSectionHeaderInitializer("Alert"))

    local enabled = AddSetting("enabled", "Play a sound when Poised is ready", Settings.VarType.Boolean)
    local enabledInit = Settings.CreateCheckbox(category, enabled,
        "Turn the Poised sound on or off.")

    -- Controls passed to DependsOnEnabled grey out while the alert is off.
    local function IsEnabled()
        return enabled:GetValue()
    end
    local function DependsOnEnabled(initializer)
        initializer:SetParentInitializer(enabledInit, IsEnabled)
        return initializer
    end

    local stealthOnly = AddSetting("stealthOnly", "Only while stealthed", Settings.VarType.Boolean)
    DependsOnEnabled(Settings.CreateCheckbox(category, stealthOnly,
        "Only play the sound while you're in Stealth: when Poised arrives while you're stealthed, or when you go into Stealth with Poised already up. Useful if you don't want it after every fight."))

    -----------------------------------------------------------------------
    layout:AddInitializer(CreateSettingsListSectionHeaderInitializer("Sound"))

    local sound = AddSetting("sound", "Sound", Settings.VarType.Number)
    local function SoundOptions()
        local container = Settings.CreateControlTextContainer()
        local current, listed = sound:GetValue(), false
        for _, s in ipairs(ns.SUGGESTIONS) do
            container:Add(s.id, s.name, s.desc .. " SoundKit " .. s.id .. ".")
            listed = listed or s.id == current
        end
        if not listed then  -- an ID you typed yourself
            container:Add(current, "Custom (" .. current .. ")", "A SoundKit ID you entered.")
        end
        return container:GetData()
    end
    DependsOnEnabled(Settings.CreateDropdown(category, sound, SoundOptions,
        "What plays when Poised is ready. Picking a sound plays it."))

    -- Picking a sound in the list plays it, so you can audition them.
    -- If it can't play, chat says so instead of leaving you guessing.
    sound:SetValueChangedCallback(function(_, value)
        if not ns.quiet and not ns.TryPlay(value) then
            ns.Print(ns.SoundName(value) .. " didn't play. " .. ns.WHY_SILENT
                .. " Until you pick one that plays, the alert uses the ready check chime.")
        end
    end)

    local testButton = CreateSettingsButtonInitializer("Preview", "Play",
        function() ns.Preview() end,
        "Play the alert exactly as it will sound in game.", true)
    layout:AddInitializer(DependsOnEnabled(testButton))

    local idButton = CreateSettingsButtonInitializer("Other sound", "Enter ID...",
        function() StaticPopup_Show("POISEDALERT_SOUND_ID") end,
        "Use any SoundKit ID, for example one you found on wowhead.com/forever/sounds.", true)
    layout:AddInitializer(DependsOnEnabled(idButton))

    local channel = AddSetting("channel", "Volume channel", Settings.VarType.String)
    local function ChannelOptions()
        local container = Settings.CreateControlTextContainer()
        for _, c in ipairs(ns.CHANNELS) do
            container:Add(c.value, c.label, c.tip)
        end
        return container:GetData()
    end
    DependsOnEnabled(Settings.CreateDropdown(category, channel, ChannelOptions,
        "Which volume slider in Options > Audio controls the alert."))

    local customFile = AddSetting("customFile", "Use my own poised.ogg", Settings.VarType.Boolean)
    DependsOnEnabled(Settings.CreateCheckbox(category, customFile,
        "Put a sound file named poised.ogg in the " .. addonName .. " addon folder, then restart the game. If it can't play, the sound above plays instead."))

    -----------------------------------------------------------------------
    layout:AddInitializer(CreateSettingsListSectionHeaderInitializer("Troubleshooting"))

    local debug = AddSetting("debug", "List new buffs in chat", Settings.VarType.Boolean)
    Settings.CreateCheckbox(category, debug,
        "Prints each buff you gain with its spell ID, and how long after full Energy Poised arrived. Works even while the sound is off.")

    Settings.RegisterAddOnCategory(category)
    ns.category = category
end)
