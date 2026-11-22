# Poised Alert

Plays a sound the moment the rogue Poised buff lands on you, so you know your opener is ready without watching your buffs.

No setup needed: install it and it works. Poised usually shows up about half a second after you reach full Energy out of combat. Poised Alert waits for the buff itself instead of guessing from your Energy, so the sound plays when Poised is really there.

- **Seven sounds to pick from**: two blade whooshes, a weapon swing, a blade being drawn or sheathed, the map ping and the ready check chime. Or use any other SoundKit ID, or your own sound file.
- **Only while stealthed** (optional): plays only when Poised arrives while you're in Stealth, or when you go into Stealth with Poised already up, so it doesn't play after every fight.
- **Plays on the Master channel** by default, so you hear it even with Sound Effects turned down.
- **Backup sound**: if your chosen sound can't play, the ready check chime plays instead, and previews tell you in chat.
- **No double sounds**: Poised being refreshed, or flickering off and straight back on, doesn't count as new, and the alert never plays twice within 3 seconds.

## Install

Copy the `PoisedAlert` folder into the `Interface\AddOns` folder your other Forever addons are in (usually `World of Warcraft\_forever_\Interface\AddOns`), then restart the game or type `/reload`.

## Options

Type `/poised`, or open Esc > Options > AddOns > Poised Alert, to turn the sound on or off, pick and preview it, enter a SoundKit ID (find them at wowhead.com/forever/sounds), choose the volume channel, and switch on "Only while stealthed".

## Commands

| Command | What it does |
| --- | --- |
| `/poised` | Open the options. |
| `/poised help` | List the commands in chat. |
| `/poised test` | Play the alert. |
| `/poised stealth` | "Only while stealthed" on or off. |
| `/poised sounds` | List the built-in sounds and their IDs. |
| `/poised try 700` | Hear a sound without keeping it. |
| `/poised use 700` | Make a sound the alert. |
| `/poised reset` | Go back to the default sound. |
| `/poised debug` | List each new buff in chat, and how long after full Energy Poised arrived. |

## Your own sound

Name a sound file `poised.ogg` and put it in the `PoisedAlert` folder. Restart the game (a `/reload` doesn't pick up new files), then tick "Use my own poised.ogg" in the options. If your file can't play, the sound you picked in the list plays instead.

## How it works

- `UNIT_AURA` on you: Poised Alert looks for a new buff named Poised (or its spell ID, 1328825) and remembers that copy of the buff, so a refresh isn't mistaken for a new Poised.
- Forever hides buff details from addons during combat, boss encounters, challenge-mode dungeons and PvP matches. Poised Alert checks `C_RestrictedActions.IsAddOnRestrictionActive` before reading your buffs, and quietly catches up once they're visible again.
- `IsStealthed()` and `UPDATE_STEALTH` drive "Only while stealthed".
- `PlaySound` plays the sound on the channel you chose and reports whether it played, which is how the backup chime knows to step in.

## Notes

- There's no alert in battlegrounds, because the game hides buffs from addons during PvP matches.
- Forever only has the original game's sounds, so SoundKit IDs from later expansions won't play. Look IDs up on wowhead.com/forever/sounds rather than the retail list.
- Poised is matched by its spell ID as well as its English name, so it should work on other language clients too.
- Your settings are saved for your whole account.
