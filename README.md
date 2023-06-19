# The Ultimate Wednesday

Disclaimer: I have no idea what I'm doing.

This mod gathers up some game state info and makes it available as binary data packets by various means.

If the "Write File" option is on (default off), then it will dump game state into a binary file at `Celeste/tuw_outputs/<timestamp>_<map>.dump`. The first packet dumped includes map and chapter names, but subsequent packets do not. Note that this write happens inside the game loop and is blocking, so could cause performance problems if disk IO is sufficiently slow.

The latest game state packed including map and chapter names is written a memory mapped file at `celeste_tuw` (windows) or `/tmp/celeste_tuw.share` (linux) and can be accessed by other processes (e.g. an obs script) for realtime gamestate information (see `obs_script.py` for a python example (not tested on windows)).

The mod only produces new state information while in-game and will not update in menus.

The best reference for the packet format is the actual implementation in `TheUltimateWednesdayModule.cs`. At present it consists of 4 parts: Header, Player State, Inputs, Stream Info. Each packet is preceded by an unsigned short giving its total size in bytes.

In total a packet is 74 bytes long plus the length of the current room name (with null terminator), which may add several bytes. Room names are often 3-4 characters long (a00 or a-00), though they can be longer. Assuming a 5-character room name (+1 null terminator), each packet is 80 bytes long and the mod will write 4.8 KB/s (17.28 MB/hour) to the dump file if enabled.

## Packet Format

### Header (24 bytes + room name)

|Name | Type | Offset | Description |
|----|----|---|---|
| sequence number | unsigned int (4) | 0 | a number that increases by 1 with each consecutive packet |
| timestamp | double (8) | 4 | the unix timestamp as a floating point value |
| gametime | signed long(8) | 12 | internal gametime |
| deaths | signed int (4) | 20 | current number of deaths in the chapter |
| room name | null-terminated ascii string | >= 1 | The name of the current room |

### Player State (38 bytes)

|Name | Type | Offset | Description |
|----|----|---|---|
| xpos | float(4) | 0 | Player position |
| ypos | float(4) | 4 |  |
| xvel | float(4) | 8 | Player velocity |
| yvel | float(4) | 12 |  |
| stamina | float(4) | 16 | Player stamina |
| xlift | float(4) | 20 | Liftspeed |
| ylift | float(4) | 24 |  |
| state | signed int (4) | 28 | The player state ([see source for translation](https://github.com/NoelFB/Celeste/blob/master/Source/Player/Player.cs#L140)) |
| dashes | signed int (4) | 32 | The number of dashes the player currently has |
| control flags | unsigned byte | 36 | dead, control, cutscene, transition, 0, 0, 0, 0 |
| status flags | unsigned byte | 37 | holding, crouched, facing_left, wall_left, wall_right, coyote, safe_ground, ground |

### Input State (10 bytes)

|Name | Type | Offset | Description |
|----|----|---|---|
| button flags |  unsigned byte(1) | 0 | quick restart, escape, crouch dash, talk, grab, dash, jump |
| direction flags | unsigned byte(1) | 1 | 0, 0, 0, 0, up, down, left, right |
| xaim | float (4) | 2 | Analog aim direction |
| yaim | float (4) | 6 |  |

### Stream Info
This is an arbitrary length sequence of null-terminated ascii strings. The first one is the current chapter name, and the second one is the current mod (map) name.


