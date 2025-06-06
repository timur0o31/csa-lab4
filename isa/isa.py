from enum import Enum
class Opcode(str, Enum):
    LIT = "lit"
    STORE = "store" # !
    LOAD = "load" #@
    IN = "in"
    OUT = "out"
    ADD = "add" # +
    ADD2 = "add2" #2+
    SUB = "sub" #-
    MUL = "mul" #*
    DIV = "div" #/
    INC = "inc"
    DEC = "dec"
    AND = "and"
    OR = "or"
    XOR = "xor"
    NOT = "not"
    JUMP = "jump"
    CALL = "call"
    JZ = "jz"
    JN = "jn"
    RET = "ret" # ;
    SWAP = "swap"
    DUP = "dup"
    DROP = "drop"
    RINT = "rint"
    EINT = "eint"
    DINT = "dint"
    HALT = "halt"
    def __str__(self):
        return str(self.value)
opcode_to_binary = {
    Opcode.LIT: 0x01,
    Opcode.STORE: 0x02,
    Opcode.LOAD: 0x03,
    Opcode.IN: 0x04,
    Opcode.OUT: 0x05,
    Opcode.ADD: 0x06,
    Opcode.ADD2: 0x07,
    Opcode.SUB: 0x08,
    Opcode.MUL: 0x09,
    Opcode.DIV: 0x0A,
    Opcode.INC: 0x0B,
    Opcode.DEC: 0x0C,
    Opcode.AND: 0x0D,
    Opcode.OR: 0x0E,
    Opcode.XOR: 0x0F,
    Opcode.NOT: 0x10,
    Opcode.JUMP: 0x11,
    Opcode.CALL: 0x12,
    Opcode.JZ: 0x13,
    Opcode.JN: 0x14,
    Opcode.RET: 0x15,
    Opcode.SWAP: 0x16,
    Opcode.DUP: 0x17,
    Opcode.DROP: 0x18,
    Opcode.RINT: 0x19,
    Opcode.EINT: 0x1A,
    Opcode.DINT: 0x1B,
    Opcode.HALT: 0x1C,
}
binary_to_opcode = {
    0x01: Opcode.LIT,
    0x02: Opcode.STORE,
    0x03: Opcode.LOAD,
    0x04: Opcode.IN,
    0x05: Opcode.OUT,
    0x06: Opcode.ADD,
    0x07: Opcode.ADD2,
    0x08: Opcode.SUB,
    0x09: Opcode.MUL,
    0x0A: Opcode.DIV,
    0x0B: Opcode.INC,
    0x0C: Opcode.DEC,
    0x0D: Opcode.AND,
    0x0E: Opcode.OR,
    0x0F: Opcode.XOR,
    0x10: Opcode.NOT,
    0x11: Opcode.JUMP,
    0x12: Opcode.CALL,
    0x13: Opcode.JZ,
    0x14: Opcode.JN,
    0x15: Opcode.RET,
    0x16: Opcode.SWAP,
    0x17: Opcode.DUP,
    0x18: Opcode.DROP,
    0x19: Opcode.RINT,
    0x1A: Opcode.EINT,
    0x1B: Opcode.DINT,
    0x1C: Opcode.HALT
}
def instructions_to_bytes(instructions: list[dict]) -> bytes: #происходит правильный перевод для операндов в обратный код
    binary_bytes = bytearray()
    for instr in instructions:
        if instr.get("opcode") == Opcode.LIT:
            arg  = instr.get("arg",0)
            if not -(1<<25) <= arg < (1<<25):
                raise ValueError("Lit argument out of 26-bit range")
            arg &= (1 << 26) - 1
            binary_instr = (opcode_to_binary[Opcode.LIT] << 26) | arg
        else:
            opcode = opcode_to_binary[instr.get("opcode")] & 0x3F
            binary_instr = opcode << 26
        binary_bytes.extend([
            (binary_instr >> 24) & 0xFF, (binary_instr >> 16) & 0xFF, (binary_instr >> 8) & 0xFF,binary_instr & 0xFF
        ])
    return bytes(binary_bytes)

def data_to_bytes(data: list[int]) -> bytes: #отрицательные числа корректно записываются в байты
    binary_bytes = bytearray()
    for value in data:
        binary_bytes.extend([
            (value >> 24) & 0xFF,
            (value >> 16) & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF
        ])
    return bytes(binary_bytes)

def write_instructions(filename,instructions):
    with open(filename,"wb") as file:
        file.write(instructions_to_bytes(instructions))

def write_data(filename,data):
    with open(filename,"wb") as file:
        file.write(data_to_bytes(data))

def from_bytes_to_instructions(filename): # корректно, строки аккуратно
    with open(filename, "rb") as file:
        binary_bytes = file.read()
        instructions = []
        for i in range(0, len(binary_bytes), 4):
            word = (
                    (binary_bytes[i] << 24) |
                    (binary_bytes[i + 1] << 16) |
                    (binary_bytes[i + 2] << 8) |
                    binary_bytes[i + 3]
            )
            opcode_val = (word >> 26) & 0x3F
            opcode = binary_to_opcode.get(opcode_val, opcode_val)
            if opcode == Opcode.LIT:
                arg = word & 0x3FFFFFF
                if arg & (1<<25):
                    arg -= 1<<26
                instructions.append({"opcode": Opcode.LIT, "arg": arg})
            else:
                instructions.append({"opcode": opcode})
    return instructions

def bytes_to_int(byte_arr: bytes) -> int: #корректно
    word = (
            (byte_arr[0] << 24) |
            (byte_arr[1] << 16) |
            (byte_arr[2] << 8) |
            byte_arr[3]
    )
    if word & (1 << 31):
        word -= 1 << 32
    return word

def from_bytes_to_data(filename): #корректный перевод
    with open(filename, "rb") as file:
        bytes_array = file.read()
        data = []
        for i in range(0,len(bytes_array),4):
            word = (bytes_to_int(bytes_array[i:i+4]))
            data.append(word)
    return data
