import sys
from pathlib import Path
from isa.isa import (
    Opcode,
    write_instructions,
    write_data,
    from_bytes_to_instructions,
    from_bytes_to_data,
)


class ParsInstr:
    def __init__(self,opcode: Opcode, argument: str | None):
        self.opcode = opcode
        self.argument = argument


def tokenize(text):
    tokens = []
    strings = []
    in_string = False
    buf_string = ""
    i=0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            if in_string:
                strings.append(buf_string)
                tokens.append("*")
                buf_string = ""
                in_string = False
            else:
                in_string = True
            i+=1
            continue
        if in_string:
            buf_string += ch
            i += 1
            continue
        if ch == ";":
            while i<n and text[i] != "\n":
                i+=1
            continue
        elif ch in " \t\n":
            if buf_string:
                tokens.append(buf_string)
                buf_string = ""
            i += 1
            continue
        buf_string += ch
        i+=1
    if buf_string:
        tokens.append(buf_string)
    return tokens, strings


def is_number(tok: str) -> bool:
    if tok.startswith("0x"):
        try:
            int(tok,16)
            return True
        except ValueError:
            return False
    if tok.startswith("-"):
        return tok[1:].isdigit()
    return tok.isdigit()


def to_int(tok: str) -> int:
    return int(tok,0)

def symbol_to_opcode(symbol):
    return {
        "lit": Opcode.LIT,
        "!": Opcode.STORE,
        "@": Opcode.LOAD,
        "in": Opcode.IN,
        "out": Opcode.OUT,
        "+": Opcode.ADD,
        "+2": Opcode.ADD2,
        "-": Opcode.SUB,
        "*": Opcode.MUL,
        "/": Opcode.DIV,
        "inc": Opcode.INC,
        "dec": Opcode.DEC,
        "and": Opcode.AND,
        "or": Opcode.OR,
        "xor": Opcode.XOR,
        "not": Opcode.NOT,
        "jump": Opcode.JUMP,
        "call": Opcode.CALL,
        "jz": Opcode.JZ,
        "jn": Opcode.JN,
        ";": Opcode.RET,
        "dup": Opcode.DUP,
        "drop": Opcode.DROP,
        "halt": Opcode.HALT
    }.get(symbol)

def first_stage(text: str):
    labels: dict[str, int] = {}
    data_words: list[str] = []
    instrs_tmp: list[ParsInstr] = []
    current_data_addr = 0
    tokens,strings = tokenize(text)
    i = 0
    string_index = 0
    len_tokens = len(tokens)
    while i < len_tokens:
        token = tokens[i]

        # обработка переменных
        if token == "var":
            if i+2 >= len_tokens:
                sys.exit(f"syntax: var <name> <numbers>|<string>")
            name = tokens[i+1]
            if name in labels:
                sys.exit(f"duplicate symbol {name}")
            values = []
            j = i+2
            while j < len_tokens:
                v = tokens[j]
                if v == "*":
                    if string_index >= len(strings):
                        sys.exit(f" string index out of range")
                    values.extend(ord(c) for c in strings[string_index])
                    values.append(0)
                    string_index += 1
                    j += 1
                elif is_number(v):
                    values.append(to_int(v))
                    j += 1
                else:
                    break
            if not values:
                sys.exit(f" var {name} must have at least one value")
            labels[name] = current_data_addr
            data_words.extend(values)
            current_data_addr += len(values)
            i = j
            continue

        # обработка меток
        if token.endswith(":"):
            label = token[:-1]
            if label in labels:
                sys.exit(f" duplicate symbol {label}")
            labels[label] = len(instrs_tmp)
            i+=1
            continue
        #Обработка инструкций
        opcode = symbol_to_opcode(token)
        if opcode is None:
            sys.exit(f" unknown opcode '{token}'")
        i += 1
        arg_tok = None
        if opcode == Opcode.LIT:
            if i >= len_tokens:
                    sys.exit(f"lit expects literal/label")
            arg_tok = tokens[i]
            i+=1
        instrs_tmp.append(ParsInstr(opcode, arg_tok))
    return instrs_tmp, labels, data_words


def resolve_arg(arg_tok: str, labels: dict[str, int]) -> int:
    if is_number(arg_tok):
        return to_int(arg_tok)
    if arg_tok in labels:
        return labels[arg_tok]
    sys.exit(f" undefined symbol '{arg_tok}'")


def second_stage(instrs_tmp: list[ParsInstr], labels: dict[str, int]):
    final_instrs: list[dict] = []
    for ins in instrs_tmp:
        if ins.opcode == Opcode.LIT:
            arg_val = resolve_arg(ins.argument, labels)
            final_instrs.append({"opcode": Opcode.LIT, "arg": arg_val})
        else:
            final_instrs.append({"opcode": ins.opcode})
    print(final_instrs)
    return final_instrs


def assemble(source: str):
    instrs_tmp, labels,data_words = first_stage(source)
    instructions = second_stage(instrs_tmp, labels)
    return instructions, data_words


def dump_instructions(path="program.bin"):
    instrs = from_bytes_to_instructions(path)
    for i, ins in enumerate(instrs):
        if "arg" in ins:
            print(f"{i:04}: {ins['opcode']} {ins['arg']}")
        else:
            print(f"{i:04}: {ins['opcode']}")


def dump_data(path="data.bin"):
    data = from_bytes_to_data(path)
    print(f"{len(data)} данные")
    for i, val in enumerate(data):
        print(f"{i:04}: {val}")

def main():

    if len(sys.argv) != 2:
        print("usage: python assembler.py program.asm")
        sys.exit(1)
    if len(sys.argv) == 2 and sys.argv[1] == "--dump":
        dump_instructions()
        print()
        dump_data()
        sys.exit(0)

    asm_path = Path(sys.argv[1])
    asm_text = asm_path.read_text(encoding="utf-8")

    instructions, data_words = assemble(asm_text)

    write_instructions("program.bin", instructions)
    write_data("data.bin", data_words)

    print(f"✓ assembled {asm_path.name}")
    print(f"  code  : {len(instructions)} instructions  → program.bin")
    print(f"  data  : {len(data_words)} words          → data.bin")

if __name__ == "__main__":
    main()
