from . import assembler
from . import schematic_generator

# This Script converts FROSTBYTE Assembler -> Schematic for the FROSTBYTE CPU
#
# Enter your assembly_to_schematic code (into "assembly.txt")
# Then it gets converted to machine code (into "machine_code.txt")
# Then it gets converted to a Minecraft Schematic that you can paste in with Worldedit (into programs/Program_[Time])


def generate():
    assembler.generate_machine_code()
    schematic_generator.generate_schematic()


if __name__ == '__main__':
    generate()
