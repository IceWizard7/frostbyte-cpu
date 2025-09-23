from . import assembler
from . import schematic_generator

# This Script converts FROSTBYTE Assembler -> Schematic for the FROSTBYTE CPU
#
# Enter your assembly_to_schematic code (into the specified assembly_file)
# Then it gets converted to machine code (gets returned from generate_machine_code)
# Then it gets converted to a Minecraft Schematic that you can paste in with Worldedit (into programs/Program_[Time])

def generate(assembly_file: str) -> None:
    machine_code = assembler.generate_machine_code(assembly_file)
    schematic_generator.generate_schematic(machine_code)


if __name__ == '__main__':
    generate('assembly_to_schematic/assembly.txt')
