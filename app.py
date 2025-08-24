from flask import Flask, render_template, request
from flask_socketio import SocketIO
import threading
from colorama import Fore, Style
import time
import random
from assembly_to_schematic import generator
import copy
import re

app = Flask(__name__)
socketio = SocketIO(app)

SAVE_PATH = 'saved_input.txt'


class Simulator:
    def __init__(self, speed):
        self.REGISTERS = {f'R{i}': 16 * '0' for i in range(32)}
        self.DATA_MEMORY_ADDRESSES = {f'D{i}': 16 * '0' for i in range(256)}
        self.PORTS_WRITE_ONLY = {f'P{i}': 16 * '0' for i in range(8)}
        self.PORTS_READ_ONLY = {f'P{i}': 16 * '0' for i in range(8)}
        self.PORTS_READ_ONLY['P1'] = format(random.randint(0, 65535), '016b')  # Start with random 16-bit Number
        self.ALU_FLAGS = {'BEQ': False, 'BNE': False, 'BLT': False, 'BGT': False}
        self.call_stack = []
        self.simulation_running = False
        self.program_counter = 16 * '0'  # To not re-write int_to_bin & bin_to_int, we consider this a 16-bit Number. Doesn't change anything.

        self.screen_data: list[list[int]] = [[0 for _ in range(31)] for _ in range(31)]
        self.screen_buffer: list[list[int]] = [[0 for _ in range(31)] for _ in range(31)]
        self.screen_d_latch_data = 0
        self.screen_x = 0
        self.screen_y = 0
        self.letters_data = ['_' for _ in range(11)]
        self.letters_buffer = ['_' for _ in range(11)]
        self.letters_pointer = 0
        self.number = '___'
        self.big_number = '_____'

        self.OPERATIONS = ['NOP', 'ADD', 'SUB', 'XOR', 'OR', 'AND', 'RSH', 'ADI', 'ST', 'LD', 'PT-ST', 'PT-LD', 'JMP', 'CAL',
                           'RET', 'BEQ', 'BNE', 'BLT', 'BGT', 'HLT']

        self.speed = speed
        self.controller = {'UP': 0, 'RIGHT': 0, 'DOWN': 0, 'LEFT': 0, 'START': 0, 'SELECT': 0, 'Y': 0, 'X': 0}

    def read_assembly_file(self, filename='saved_input.txt'):
        with open(filename, 'r') as file:
            return [line.strip() for line in file if line.strip()]

    def remove_comments(self, lines):
        return [line.split('#')[0].strip() for line in lines if line.split('#')[0].strip()]

    def extract_definitions(self, lines):
        definitions = {}
        for line in lines:
            if line.startswith('define '):
                _, key, value = line.split()
                definitions[key] = value
        return definitions

    def replace_definitions(self, lines, definitions):
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

    def extract_labels(self, lines):
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

    def replace_labels(self, lines, labels):
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

    def extract_characters(self, lines):
        tokens_re = re.compile(r'"[^"]*"|\S+')

        result = []
        for line in lines:
            tokens = tokens_re.findall(line)
            new_tokens = []
            for token in tokens:
                if token.startswith('"') and token.endswith('"'):
                    inner = token[1:-1]  # content inside quotes
                    if len(inner) != 1:
                        raise (ValueError, f'{Fore.RED}Fatal Error. Character "{inner}" not in supported characters (A-Z, Space){Style.RESET_ALL}')
                    new_tokens.append(self.char_to_num(inner))
                else:
                    new_tokens.append(token)
            result.append(" ".join(new_tokens))
        return result

    def preprocess_assembly(self):
        lines = self.read_assembly_file()
        lines = self.remove_comments(lines)

        definitions = self.extract_definitions(lines)
        lines = self.replace_definitions(lines, definitions)

        labels = self.extract_labels(lines)
        lines = self.replace_labels(lines, labels)

        lines = self.extract_characters(lines)

        return lines

    def bin_to_char(self, bin_str: str) -> str:
        bin_to_char = {
            '00001': 'A', '00010': 'B', '00011': 'C', '00100': 'D', '00101': 'E',
            '00110': 'F', '00111': 'G', '01000': 'H', '01001': 'I', '01010': 'J',
            '01011': 'K', '01100': 'L', '01101': 'M', '01110': 'N', '01111': 'O',
            '10000': 'P', '10001': 'Q', '10010': 'R', '10011': 'S', '10100': 'T',
            '10101': 'U', '10110': 'V', '10111': 'W', '11000': 'X', '11001': 'Y',
            '11010': 'Z', '00000': ' '
        }

        return bin_to_char[bin_str]

    def char_to_num(self, char: str) -> str:
        if char == ' ':
            return '0'
        if char.isalpha():
            return str(ord(char.upper()) - ord('A') + 1)
        raise (ValueError, f'{Fore.RED}Fatal Error. Character "{char}" not in supported characters (A-Z, Space){Style.RESET_ALL}')

    def bin_to_int(self, bin_str):
        return int(bin_str, 2)

    def int_to_bin(self, val):
        return format(val & 0xFFFF, '016b')

    def update_alu_flags(self, result_bin):
        # Minecraft Implementation

        self.ALU_FLAGS = {'BEQ': False, 'BNE': False, 'BLT': False, 'BGT': False}

        if result_bin[0] == '1':
            self.ALU_FLAGS['BLT'] = True

        if result_bin == 16 * '0':
            self.ALU_FLAGS['BEQ'] = True

        if not self.ALU_FLAGS['BEQ']:
            self.ALU_FLAGS['BNE'] = True

        if self.ALU_FLAGS['BEQ'] is False and self.ALU_FLAGS['BLT'] is False:
            self.ALU_FLAGS['BGT'] = True

    def execute_instruction(self, instruction):
        parts = instruction.split()
        operation = parts[0]
        mask = 0xFFFF  # Ensure 16 Bit Result
        jump_instruction = False

        if operation not in self.OPERATIONS:
            raise (ValueError, f'{Fore.RED}Fatal Error. Operation {operation} not in Operations {self.OPERATIONS}{Style.RESET_ALL}')

        match operation:
            case 'NOP':
                pass
            case 'ADD':
                self.REGISTERS[parts[1]] = self.int_to_bin(
                    (self.bin_to_int(self.REGISTERS[parts[2]]) + self.bin_to_int(self.REGISTERS[parts[3]])) & mask
                )
                self.update_alu_flags(self.REGISTERS[parts[1]])
            case 'SUB':
                self.REGISTERS[parts[1]] = self.int_to_bin(
                    (self.bin_to_int(self.REGISTERS[parts[2]]) - self.bin_to_int(self.REGISTERS[parts[3]])) & mask
                )
                self.update_alu_flags(self.REGISTERS[parts[1]])
            case 'XOR':
                self.REGISTERS[parts[1]] = self.int_to_bin(
                    (self.bin_to_int(self.REGISTERS[parts[2]]) ^ self.bin_to_int(self.REGISTERS[parts[3]])) & mask
                )
                self.update_alu_flags(self.REGISTERS[parts[1]])
            case 'OR':
                self.REGISTERS[parts[1]] = self.int_to_bin(
                    (self.bin_to_int(self.REGISTERS[parts[2]]) | self.bin_to_int(self.REGISTERS[parts[3]])) & mask
                )
                self.update_alu_flags(self.REGISTERS[parts[1]])
            case 'AND':
                self.REGISTERS[parts[1]] = self.int_to_bin(
                    (self.bin_to_int(self.REGISTERS[parts[2]]) & self.bin_to_int(self.REGISTERS[parts[3]])) & mask
                )
                self.update_alu_flags(self.REGISTERS[parts[1]])
            case 'RSH':
                self.REGISTERS[parts[1]] = self.int_to_bin(
                    (self.bin_to_int(self.REGISTERS[parts[2]]) >> 1) & mask
                )
                self.update_alu_flags(self.REGISTERS[parts[1]])
            case 'ADI':
                self.REGISTERS[parts[1]] = self.int_to_bin(
                    (self.bin_to_int(self.REGISTERS[parts[2]]) + int(parts[3])) & mask
                )
                self.update_alu_flags(self.REGISTERS[parts[1]])
            case 'ST':
                self.DATA_MEMORY_ADDRESSES['D' + str(
                    self.bin_to_int(self.REGISTERS[parts[2]]) + int(parts[3])
                )] = self.REGISTERS[parts[1]]
            case 'LD':
                self.REGISTERS[parts[1]] = self.DATA_MEMORY_ADDRESSES['D' + str(
                    self.bin_to_int(self.REGISTERS[parts[2]]) + int(parts[3])
                )]
            case 'PT-ST':
                self.port_store(parts[2][1:], self.REGISTERS[parts[1]])
            case 'PT-LD':
                self.port_load(parts[2][1:], parts[1])
            case 'JMP':
                self.program_counter = self.int_to_bin(int(parts[1]))
                jump_instruction = True
            case 'CAL':
                self.call_stack.append(self.int_to_bin(
                    self.bin_to_int(self.program_counter) + 1
                ))
                self.program_counter = self.int_to_bin(int(parts[1]))
                jump_instruction = True
            case 'RET':
                self.program_counter = self.call_stack.pop()
                jump_instruction = True
            case 'BEQ':
                if self.ALU_FLAGS['BEQ']:
                    self.program_counter = self.int_to_bin(int(parts[1]))
                    jump_instruction = True
            case 'BNE':
                if self.ALU_FLAGS['BNE']:
                    self.program_counter = self.int_to_bin(int(parts[1]))
                    jump_instruction = True
            case 'BLT':
                if self.ALU_FLAGS['BLT']:
                    self.program_counter = self.int_to_bin(int(parts[1]))
                    jump_instruction = True
            case 'BGT':
                if self.ALU_FLAGS['BGT']:
                    self.program_counter = self.int_to_bin(int(parts[1]))
                    jump_instruction = True
            case 'HLT':
                self.simulation_running = False
                jump_instruction = True  # In case Program gets continued again, Halt will be spammed

        self.PORTS_READ_ONLY['P1'] = format(random.randint(0, 65535), '016b')  # Generate Random Number at Port 1 for each clock cycle

        if self.REGISTERS['R0'] != 16 * '0':
            self.REGISTERS['R0'] = 16 * '0'  # Make sure r0 is always 0

        if self.DATA_MEMORY_ADDRESSES['D0'] != 16 * '0':
            self.DATA_MEMORY_ADDRESSES['D0'] = 16 * '0'  # Make sure d0 is always 0

        if len(self.call_stack) > 16:
            self.call_stack = self.call_stack[-16:]  # Max 16 Layers Deep

        if not jump_instruction:
            self.program_counter = self.int_to_bin(
                self.bin_to_int(self.program_counter) + 1
            )

    def port_load(self, address, bin_reg_address):
        bin_address = self.int_to_bin(int(address))[13:16]

        value = 16 * '0'

        match bin_address:
            case '000':
                self.controller = {'UP': self.controller['UP'],
                                   'RIGHT': self.controller['RIGHT'],
                                   'DOWN': self.controller['DOWN'],
                                   'LEFT': self.controller['LEFT'],
                                   'START': 0, 'SELECT': 0, 'Y': 0, 'X': 0}

                value = (8 * '0' + str(simulator.controller['X']) + str(simulator.controller['Y']) +
                         str(simulator.controller['SELECT']) + str(simulator.controller['START']) +
                         str(simulator.controller['LEFT']) + str(simulator.controller['DOWN']) +
                         str(simulator.controller['RIGHT']) + str(simulator.controller['UP']))

                self.PORTS_READ_ONLY[f'P{address}'] = value
                # Bit 1 (LSB): D-Pad Up
                # Bit 2: D-Pad Right
                # Bit 3: D-Pad Down
                # Bit 4: D-Pad Left
                # Bit 5: Start
                # Bit 6: Select
                # Bit 7: Y
                # Bit 8 (MSB): X
            case '001':
                value = self.PORTS_READ_ONLY[f'P{address}']

        self.REGISTERS[bin_reg_address] = value

    def port_store(self, address, bin_value):
        bin_address = self.int_to_bin(int(address))[13:16]

        # print(f'Port Store, {address = }, {bin_value = }')

        self.PORTS_WRITE_ONLY[f'P{address}'] = bin_value

        match bin_address:
            case '000':  # Format: XXXXXXXXXXXXXX (14), Clear Letter Buffer (1), Update Letter Buffer (1)
                if bin_value[15] == '1':  # Update Letter Buffer
                    self.letters_data = self.letters_buffer
                if bin_value[14] == '1':  # Clear Letter Buffer
                    self.letters_pointer = 0
                    self.letters_buffer = self.letters_buffer = ['_' for _ in range(11)]
            case '001':  # Format: XXXXXXXXXXX (11), Character (5)
                char = self.bin_to_char(bin_value[11:16])
                self.letters_buffer[self.letters_pointer] = char
                self.letters_pointer += 1
                if self.letters_pointer > 10:
                    self.letters_pointer = 0
            case '010':  # Format: XXXXXX (6), Sign Mode (1), Enable (1), Number (8)
                self.number = str(format(self.bin_to_int(bin_value[8:16]), '03d'))
                self.big_number = str(format(self.bin_to_int(bin_value), '05d'))  # <- 16 Bit Testing Display

                if bin_value[6] == '1':  # Sign Mode
                    self.number = str(format(int(self.number), '03d') if int(self.number) < 128 else format(int(self.number) - 256, '04d'))
                if bin_value[7] == '0':  # Disable
                    self.number = '___'
            case '011':  # Format: XXXXXX (6), X (5), Y (5)
                self.screen_x = self.bin_to_int(bin_value[6:11])
                self.screen_y = self.bin_to_int(bin_value[11:16])
                # print(self.screen_x, self.screen_y)
            case '100':  # Draws the Pixel on store with any value
                try:
                    self.screen_buffer[31 - self.screen_y][31 - self.screen_x] = self.screen_d_latch_data
                except IndexError:
                    self.display_error_message(f'Screen Coordinates: [X: {self.screen_x}, Y: {self.screen_y}] not found. X, Y must be in range [1;31]')
                    return
            case '101':  # Format: XXXXXXXXXXXXXXX (15), Screen Data Value (1)
                self.screen_d_latch_data = int(bin_value[15])
            case '110':  # Sets all Pixels on store with any value
                for x in range(31):
                    for y in range(31):
                        self.screen_buffer[y][x] = self.screen_d_latch_data
            case '111':  # Pushes the Buffer on store with any value
                self.screen_data = copy.deepcopy(self.screen_buffer)

    def reset_simulation(self):
        global simulator

        self.simulation_running = False

        simulator = Simulator(simulator.speed)

        _ = simulator.return_info(emit=True)

    def step_simulation(self):
        self.simulation_running = False

        processed_lines = self.preprocess_assembly()

        try:
            current_instruction = processed_lines[self.bin_to_int(self.program_counter)]
        except IndexError:
            self.display_error_message('No halt at the end of the program')
            return

        self.execute_instruction(current_instruction.upper())

        _ = self.return_info(emit=True)

    def break_simulation(self):
        self.simulation_running = False

        _ = self.return_info(emit=True)

    def run_simulation(self):
        self.simulation_running = True

        processed_lines = self.preprocess_assembly()

        next_time = time.perf_counter()

        while self.simulation_running:
            if not self.simulation_running:
                break  # Exits, if no longer running

            interval = 1 / max(1, self.speed)  # Interval between executes, re-calculate every time, also avoids ZeroDivisionError

            now = time.perf_counter()

            if now < next_time:
                sleep_duration = next_time - now
                time.sleep(sleep_duration)
            else:
                next_time = now  # catch up if we lag

            if not self.simulation_running:
                break  # Exits, if no longer running

            try:
                current_instruction = processed_lines[self.bin_to_int(self.program_counter)]
            except IndexError:
                self.display_error_message('No halt at the end of the program')
                return

            self.execute_instruction(current_instruction.upper())

            _ = self.return_info(emit=True)

            next_time += interval

    def return_info(self, emit: bool):
        decimal_info_list = [
            {f'{key[0]}{format(int(key[1:]), "02d")}': f'{format(self.bin_to_int(value), "05d")}' for key, value in
             self.REGISTERS.items()},
            {f'{key[0]}{format(int(key[1:]), "01d")}': f'{format(self.bin_to_int(value), "05d")}' for key, value in
             self.PORTS_READ_ONLY.items()},
            {f'{key[0]}{format(int(key[1:]), "01d")}': f'{format(self.bin_to_int(value), "05d")}' for key, value in
             self.PORTS_WRITE_ONLY.items()},
            {f'{key[0]}{format(int(key[1:]), "03d")}': f'{format(self.bin_to_int(value), "05d")}' for key, value in
             self.DATA_MEMORY_ADDRESSES.items()},
            {key: str(value) for key, value in self.ALU_FLAGS.items()},  # Return it in a string-form
            f'{format(self.bin_to_int(self.program_counter), "04d")}',
            {f'{format(key, "02d")}': format(self.bin_to_int(self.call_stack[key]), '04d') if key < len(self.call_stack) else '0000' for key in range(16)},  # replace with call_stack dict
            self.screen_data,
            ''.join(self.letters_data),
            self.number,
            self.simulation_running,
            self.bin_to_int(self.program_counter),
            self.preprocess_assembly(),
            self.big_number
        ]

        if emit:
            socketio.emit('simulation_update', {
                'pc': decimal_info_list[5],
                'registers': decimal_info_list[0],
                'ps': decimal_info_list[1],
                'pd': decimal_info_list[2],
                'data_memory': decimal_info_list[3],
                'alu_flags': decimal_info_list[4],
                'call_stack': decimal_info_list[6],
                'letters': decimal_info_list[8],
                'number': decimal_info_list[9],
                'screen_data': decimal_info_list[7],
                'int_pc': decimal_info_list[11],
                'preprocessed_assembly': decimal_info_list[12],
                'big_number': decimal_info_list[13]
            })

        return decimal_info_list

    def generate_schematic(self):
        with open(SAVE_PATH, 'r') as file:
            code = file.read()

        with open('assembly_to_schematic/assembly.txt', 'w') as file:
            for line in code:
                file.write(line)
        try:
            generator.generate()
        except Exception:
            self.display_error_message('Schematic generation failed')
            return '', 500 # Internal Server Error
        else:
            socketio.emit('generate_schematic_successful')

        return '', 204 # No Content

    def display_error_message(self, message):
        socketio.emit('error_message', {'message': message})


simulator = Simulator(1)  # Standard Speed


@socketio.on('reset_simulation')
def handle_reset():
    simulator.reset_simulation()


@socketio.on('step_simulation')
def handle_step():
    simulator.step_simulation()


@socketio.on('stop_simulation')
def handle_stop():
    simulator.break_simulation()


@socketio.on('continue_simulation')
def handle_continue():
    threading.Thread(target=simulator.run_simulation, daemon=True).start()


@socketio.on('generate_schematic')
def handle_generate_schematic():
    return simulator.generate_schematic()


@socketio.on('update_speed')
def handle_update_speed(data):
    speed = data.get('speed')
    print(f'Updating speed from {simulator.speed} -> {speed}')
    simulator.speed = int(speed)


@socketio.on('request_update')
def handle_request_update():
    print(f'Requested an Update')
    simulator.return_info(emit=True)


@socketio.on('controller_update')
def handle_controller_update(data):
    # print(f'controller update: {data}')
    controller_data = data.get('controller')
    # print(f'frontend: {controller_data} sent this.')
    simulator.controller = {'UP': controller_data['UP'], 'RIGHT': controller_data['RIGHT'],
                            'DOWN': controller_data['DOWN'], 'LEFT': controller_data['LEFT'],
                            'START': (controller_data['START'] or simulator.controller['START']),
                            'SELECT': (controller_data['SELECT'] or simulator.controller['SELECT']),
                            'Y': (controller_data['Y'] or simulator.controller['Y']),
                            'X': (controller_data['X'] or simulator.controller['X'])}
    value = (8 * '0' + str(simulator.controller['X']) + str(simulator.controller['Y']) +
             str(simulator.controller['SELECT']) + str(simulator.controller['START']) +
             str(simulator.controller['LEFT']) + str(simulator.controller['DOWN']) +
             str(simulator.controller['RIGHT']) + str(simulator.controller['UP']))
    simulator.PORTS_READ_ONLY['P0'] = value
    simulator.return_info(emit=True)
    # print(f'backend: {simulator.controller} updated this.')


@app.route('/save', methods=['POST'])
def save_via_fetch():
    code_input = request.form.get('codeInput', '').replace('\r\n', '\n').rstrip()
    with open(SAVE_PATH, 'w') as f:
        f.write(code_input)

    simulator.reset_simulation()
    return '', 204


@app.route('/', methods=['GET'])
def ui_index():
    saved_code = ''
    try:
        with open(SAVE_PATH, 'r') as file:
            saved_code = file.read()
    except FileNotFoundError:
        raise (ValueError, f'{Fore.RED}Fatal Error. File "{SAVE_PATH}"was not found. Perhaps create it?{Style.RESET_ALL}')

    decimal_info_list = simulator.return_info(emit=False)

    return render_template(
        'index.html',
        saved_text=saved_code,
        registers=decimal_info_list[0],
        ps=decimal_info_list[1],
        pd=decimal_info_list[2],
        data_memory=decimal_info_list[3],
        alu_flags=decimal_info_list[4],
        pc=decimal_info_list[5],
        call_stack=decimal_info_list[6],
        screen_data=decimal_info_list[7],
        letters=decimal_info_list[8],
        number=decimal_info_list[9],
        big_number=decimal_info_list[13],
        preprocessed_assembly=simulator.preprocess_assembly()
    )


@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    content = ""

    if file and file.filename.endswith('.txt'):
        content = file.read().decode('utf-8')
        content = content.replace('\r\n', '\n').rstrip()
        with open(SAVE_PATH, 'w') as f:
            f.write(content)

    simulator.reset_simulation()

    socketio.emit('update_code', {'content': content})

    return '', 204


if __name__ == '__main__':
    socketio.run(app=app, host="0.0.0.0", port=5001, debug=True, allow_unsafe_werkzeug=True)
