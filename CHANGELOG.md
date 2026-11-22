# Changelog

## 1.4.1

First public release.

- Plays a sound when the Poised buff lands on you. It waits for the buff itself, which usually arrives about half a second after full Energy out of combat.
- Options page (Esc > Options > AddOns > Poised Alert, or `/poised`): sound on or off, seven built-in sounds with a preview, any SoundKit ID, your own `poised.ogg`, the volume channel, and a debug readout.
- "Only while stealthed" (also `/poised stealth`), off by default. It plays only when Poised arrives while you're in Stealth, or when you go into Stealth with Poised already up.
- Every built-in sound comes from the original game, because Forever's files don't have later expansions' sounds. If a sound can't play, previews say so in chat and the alert uses the ready check chime instead.
- An icon and a Rogue group in the in-game addon list.
- Stays quiet, without errors, when the game hides buffs from addons (boss encounters, PvP matches), and catches up afterwards.

Versions 1.0 to 1.4.0 were private test builds.
