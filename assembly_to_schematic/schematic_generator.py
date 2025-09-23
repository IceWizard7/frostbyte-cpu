import mcschematic
import datetime
from colorama import Fore, Style

xz_locations = []
y_locations = [-3, -5, -7, -9, -13, -15, -17, -19, -21, -23, -25, -29, -31, -33, -35, -37, -39, -41, -45, -47, -49, -51, -53, -55, -57, -61, -63, -65, -67, -69, -71, -73]

for i in range(32):
    for j in range(64):
        xz_locations.append((3 + i*6, 0 + -j*2))


def generate_schematic(machine_code):
    schematic_file = f'Program_{datetime.datetime.now().strftime("%d_%m_%y-%H_%M_%S")}'

    schem = mcschematic.MCSchematic()

    clean_content = []
    for line in machine_code:
        clean_content.append(line.replace('\n', ''))  # Remove new lines

    if any(len(item) != 32 for item in clean_content):  # Too many / too few characters at one line
        indices = [i for i, item in enumerate(clean_content) if len(item) != 32]
        raise (ValueError, f'{Fore.RED}Fatal Error. Line wrong length at {indices = }.{Style.RESET_ALL}')

    if len(clean_content) > 2048:  # Too many lines
        raise (ValueError, f'{Fore.RED}Fatal Error. Too many lines. {len(clean_content)} (received) > 2048 (maximum) Lines.{Style.RESET_ALL}')

    for address in range(len(clean_content)):
        for y_pos, bit in enumerate(clean_content[address]):
            if bit == '0':
                block_data = 'minecraft:white_wool'  # "0"
            elif bit == '1':
                block_data = 'minecraft:repeater[facing=west]'  # "1"
            else:
                raise (ValueError, f'{Fore.RED}Fatal Error. {address = }, {y_pos}: Bit not 1 or 0.{Style.RESET_ALL}')
            schem.setBlock((xz_locations[address][0], y_locations[y_pos], xz_locations[address][1]), blockData=block_data)
            schem.setBlock((xz_locations[address][0], y_locations[y_pos] - 1, xz_locations[address][1]), blockData='minecraft:magenta_wool')

    schem.save('programs', schematic_file, mcschematic.Version.JE_1_20_4)

    print(f'{Fore.LIGHTGREEN_EX}Successfully generated Schematic! ({schematic_file}){Style.RESET_ALL}')
    # print(f'Paste with:')
    # print(f'//schematic load {filename}')
    # print(f'//paste -a')
