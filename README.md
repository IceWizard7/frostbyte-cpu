# Before trying to create or run a program, read this whole page!
DISCLAIMER: Basic Assembly / Programming Skills are assumed

## What's in this repo?

All the supporting code I wrote for my Minecraft CPU.

- assembler_to_schematic/
- |- assembler.py - A script to convert assembly files (.txt) to machine code files (.txt)
- |- generator.py - A script to convert machine code files (.txt) to worldedit schematics (.schem)
- |- main.py - A script to convert assembly files (.txt) to worldedit schematics (.schem) (Using assembler.py, then generator.py)
- |- \_\_init\_\_.py - A file to mark the directory as a Python package


- static/* - A folder containing CSS and Images for the Simulator


- templates/* - A folder containing HTML Templates for the Simulator


- app.py - Start script for the Simulator

## How can I create a program?

To create a new program, simply create a new text file (with the .txt extension), and open the file with any text editor. \
For more information, look into the ISA. (Will be added soon)

### Syntax

Every instruction is written with an opcode followed by the operands. For example

``add r3 r1 r2``

will compute r3 = r1 + r2 (This could be counter-intuitive for some!), as  described in the Description column.

### Labels

Labels are supported and represented using a dot followed by the label. They can either be on their own line, or before an instruction on the same line. A label will always resolve to its absolute address (All jumps are absolute). Example:

```
adi r1 r0 10
adi r2 r0 1

.loop # Label on an own line
sub r1 r1 r2
beq .exit
jmp .loop

.exit hlt # Label on the same line as an instruction
```

### Definitions

Definitions of positive integer values are supported. Example:

```
define apple 5
```

Any future references to apple will resolve to 5.

### Symbols

Opcodes need to be written as their 3-letter mnemonic. \
Registers need to be written as r0 through r31. \
Immediates need to be written as decimal. \
Ports need to be written as p0 through p7. \
Comments need to be started with a #.

## How can I run a program?

- Clone this repository
- Install all dependencies using
```pip install -r requirements.txt```

### 1. Running a program on the simulator

- Execute the app.py script
- Drag and drop the Assembler file in the dashed-outline box
- Press "Continue"

Notes:
When re-running app.py, make sure to refresh the web page on the client, to ensure the speed is up-to-date.\
When changing speeds, it might need 2-3 Seconds to update. To overcome this, you can alternatively press "Stop" and then "Continue". \
The generated Minecraft schematic files can be found in programs/

### 2. Running a program on the Minecraft CPU
DISCLAIMER: This will be **extremely slow**, as the CPU completes 1 instruction every ~20 at vanilla speeds. See the next section for speedup methods.

- Execute the app.py script
- Drag and drop the Assembler file in the dashed-outline box
- Press "Generate Schematic"
- Drag and drop the resulting Program\_\[Time\] file into .minecraft/config/worldedit/schematics
- Download the CPU from the world download (Will be added soon)
- Go to the coordinates XYZ (Will be added soon). You should be standing on a redstone lamp.
- Run //schem load Program\_\[Time\]
- Run //paste -s
- Run //update
- Head to the input controller and press the "Run Program" button!

### Speedup Method #1 - /tick speed

In newer versions of minecraft, you can run
``/tick speed [X]`` to increase the tick speed.

Alternatively, you can use [Carpet](https://www.curseforge.com/minecraft/mc-mods/carpe)

### Speedup Method #2 - MCHPRS
DISCLAIMER: These instructions may not be up-to-date and are for **Windows** only!

[MCHPRS](https://github.com/MCHPR/MCHPRS/releases) is a custom server designed to speedup redstone to incredible speed.

- Grab the [latest release](https://github.com/MCHPR/MCHPRS/releases)
- Run the just-downloaded .exe
- A server console should launch. Test connecting to the server by joining the multiplayer ip ```localhost```. Also, new folders/files should have also been created. One of these folders should be called "schems"
- Go back to the cpu in singleplayer. You should have your program already pasted in and updated. Create a worldedit selection of the entire computer. Run ``//copy``, and ```//schem save [name]```
- Transfer the newly created schematic from .minecraft/config/worldedit/schematics to the MCHPRS "schems"-folder
- Join the server again. Run ```//load [name]```, and ```//paste```
- Use ```/rtps [X]``` to set the redstone ticks per second, or ```/rtps unlimited``` for maximum speed.



### Example Programs
(Will be added soon)


## License

This project is licensed under a custom **MIT-style license** with the following restrictions:
- No commercial use
- Attribution to **IceWizard7** is required in all copies, forks, and modified versions
- You may not claim authorship or original ownership of this software

See [LICENSE](./LICENSE) for full details.
