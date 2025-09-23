from colorama import Fore, Style
import re

OPCODES = {'NOP': '00000',
           'ADD': '00001',  # ALU Instructions (TYPE RA)
           'SUB': '00010',
           'XOR': '00011',
           'OR': '00100',
           'AND': '00101',
           'RSH': '00110',
           'ADI': '00111',  # Immediate Instructions (TYPE I)
           'ST': '01000',  # Data Memory Instructions (TYPE RD)
           'LD': '01001',
           'PT-ST': '01010',  # Port Instructions (TYPE IO)
           'PT-LD': '01011',
           'JMP': '01100',  # Jump Instructions (TYPE J)
           'CAL': '01101',
           'RET': '01110',
           'BEQ': '01111',
           'BNE': '10000',
           'BLT': '10001',
           'BGT': '10010',
           'HLT': '10011'
           }


def read_assembly_file(assembly_file):
    with open(assembly_file, 'r') as file:
        return [line.strip() for line in file if line.strip()]


def remove_comments(lines):
    return [line.split('#')[0].strip() for line in lines if line.split('#')[0].strip()]


def extract_definitions(lines):
    definitions = {}
    for line in lines:
        if line.startswith('define '):
            _, key, value = line.split()
            definitions[key] = value
    return definitions


def replace_definitions(lines, definitions):
    result = []
    for line in lines:
        tokens = line.split()
        if line.startswith('define '):
            continue
        new_tokens = []
        for token in tokens:
            if token in definitions:
                new_tokens.append(definitions[token])
            else:
                new_tokens.append(token)

        result.append(' '.join(new_tokens))
    return result


def extract_labels(lines):
    labels = {}
    instruction_address = 0

    for idx, line in enumerate(lines):
        parts = line.split()

        if not parts:
            continue

        if parts[0].startswith('.'):
            label_name = parts[0]
            if len(parts) > 1:
                labels[label_name] = str(instruction_address)
                instruction_address += 1
            else:
                labels[label_name] = str(instruction_address)
        else:
            instruction_address += 1

    return labels


def replace_labels(lines, labels):
    result = []
    for line in lines:
        tokens = line.split()
        if line.startswith('.'):
            if len(tokens) == 1:
                continue  # line is only a label, skip it
            tokens = tokens[1:]
        new_tokens = []
        for token in tokens:
            if token in labels:
                new_tokens.append(labels[token])
            else:
                new_tokens.append(token)
        result.append(' '.join(new_tokens))
    return result


def extract_characters(lines):
    tokens_re = re.compile(r'"[^"]*"|\S+')

    result = []
    for line in lines:
        tokens = tokens_re.findall(line)
        new_tokens = []
        for token in tokens:
            if token.startswith('"') and token.endswith('"'):
                inner = token[1:-1]  # content inside quotes
                if len(inner) != 1:
                    raise ValueError(f'{Fore.RED}Fatal Error. Character "{inner}" not in supported characters (A-Z, Space){Style.RESET_ALL}')
                new_tokens.append(char_to_num(inner))
            else:
                new_tokens.append(token)
        result.append(" ".join(new_tokens))
    return result


def char_to_num(char: str) -> str:
    if char == ' ':
        return '0'
    if char.isalpha():
        return str(ord(char.upper()) - ord('A') + 1)
    raise ValueError(f'{Fore.RED}Fatal Error. Character "{char}" not in supported characters (A-Z, Space){Style.RESET_ALL}')


def preprocess_assembly(assembly_file):
    lines = read_assembly_file(assembly_file)
    lines = remove_comments(lines)

    definitions = extract_definitions(lines)
    lines = replace_definitions(lines, definitions)

    labels = extract_labels(lines)
    lines = replace_labels(lines, labels)

    lines = extract_characters(lines)

    return lines


def write_machine_code(machine_code, machine_code_file):
    with open(machine_code_file, 'w') as file:
        for line in machine_code:
            file.write(line + '\n')


def translate_instruction_to_machine_code(instruction):
    parts = instruction.split()
    opcode = OPCODES[parts[0]]

    if instruction.startswith('NOP'):  # No Operation Instruction (TYPE -)
        return 32 * '0'
    elif instruction.startswith('ADD ') or instruction.startswith('SUB') or instruction.startswith('XOR') or instruction.startswith('OR') or instruction.startswith('AND'):  # ALU Instructions (TYPE RA) [Except for RSH]
        return 12 * '0' + format(int(parts[3][1:]), '05b') + format(int(parts[2][1:]), '05b') + format(int(parts[1][1:]), '05b') + opcode
    elif instruction.startswith('RSH '):  # RSH, only 1 Argument
        return 17 * '0' + format(int(parts[2][1:]), '05b') + format(int(parts[1][1:]), '05b') + opcode
    elif instruction.startswith('ADI '):  # Immediate Instructions (TYPE I)
        return 1 * '0' + format(int(parts[3]), '016b') + format(int(parts[2][1:]), '05b') + format(int(parts[1][1:]), '05b') + opcode
    elif instruction.startswith('ST '):  # Data Memory Instructions (TYPE RD) [Only ST]
        return 4 * '0' + format(int(parts[3]), '08b') + format(int(parts[2][1:]), '05b') + format(int(parts[1][1:]), '05b') + 5 * '0' + opcode
    elif instruction.startswith('LD '):  # Data Memory Instructions (TYPE RD) [Only LD]
        return 4 * '0' + format(int(parts[3]), '08b') + format(int(parts[2][1:]), '05b') + 5 * '0' + format(int(parts[1][1:]), '05b') + opcode
    elif instruction.startswith('PT-ST'):  # I/O Instructions (TYPE IO) [Only PT-ST]
        return 14 * '0' + format(int(parts[2][1:]), '03b') + format(int(parts[1][1:]), '05b') + 5 * '0' + opcode
    elif instruction.startswith('PT-LD'):  # I/O Instructions (TYPE IO) [Only PT-LD]
        return 11 * '0' + format(int(parts[2][1:]), '03b') + 3 * '0' + 5 * '0' + format(int(parts[1][1:]), '05b') + opcode
    elif instruction.startswith('JMP ') or instruction.startswith('CAL ') or instruction.startswith('BEQ ') or instruction.startswith('BNE ') or instruction.startswith('BLT ') or instruction.startswith('BGT '):  # Jump Instructions (TYPE J) [Except RET]
        return 16 * '0' + format(int(parts[1]), '011b') + opcode
    elif instruction.startswith('RET'):  # RET Instruction (TYPE J)
        return 27 * '0' + opcode
    elif instruction.startswith('HLT'):  # Halt Instruction (TYPE -)
        return 27 * '0' + opcode
    else:
        raise ValueError(f'{Fore.RED}Fatal Error. Instruction {instruction} not found.{Style.RESET_ALL}')


def generate_machine_code(assembly_file) -> list[str]:
    machine_code = []

    try:
        processed_lines = preprocess_assembly(assembly_file)
    except FileNotFoundError:
        raise FileNotFoundError('Fatal Error. File "{assembly_file}"was not found. Perhaps create it?')

    for line in processed_lines:
        machine_code.append(translate_instruction_to_machine_code(line.upper()))

    print(f'{Fore.LIGHTGREEN_EX}Successfully generated Machine Code!{Style.RESET_ALL}')
    return machine_code
