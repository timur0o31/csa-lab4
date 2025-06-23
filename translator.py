import sys
from pathlib import Path
import os
import re
from isa import (
    Opcode,
    write_instructions,
    write_data,
    write_hex_data,
    write_hex_instructions,
)

LABEL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ParsInstr:
    def __init__(self, opcode: Opcode, argument: str | None):
        self.opcode = opcode
        self.argument = argument


def tokenize(text):
    tokens = []
    strings = []
    in_string = False
    buf_string = ""
    i = 0
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
            i += 1
            continue
        if in_string:
            buf_string += ch
            i += 1
            continue
        if ch == "\\":
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif ch in " \t\n":
            if buf_string:
                tokens.append(buf_string)
                buf_string = ""
            i += 1
            continue
        buf_string += ch
        i += 1
    if buf_string:
        tokens.append(buf_string)
    return tokens, strings


def forth_to_assemble(text: str) -> str:
    tokens, strings = tokenize(text)
    proc_out = []
    global_out = []
    cur = global_out
    data_labels = set()
    func_end = None
    func_labels = set()
    need_tmp_over = False
    begin_stack = []
    if_stack = []
    uid_if_else = 0
    uid_begin_again = 0
    i = 0
    while i < len(tokens):
        if tokens[i] == "var":
            data_labels.add(tokens[i + 1])
            i += 2
        elif tokens[i] == "str":
            data_labels.add(tokens[i + 1])
            i += 3
        elif tokens[i] == "array":
            data_labels.add(tokens[i + 1])
            i += 3
        elif tokens[i] == "*2":
            need_tmp_over = True
            i += 1
        else:
            i += 1
    if need_tmp_over:
        global_out.extend(["var", "_tmp_over", "0"])
        data_labels.add("_tmp_over")
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.lstrip("-").isdigit():
            cur.append(f"lit {tok}")
            i += 1
            continue
        if tok == "var":
            name = tokens[i + 1]
            global_out.extend(["var", name, "0"])
            i += 2
            continue
        if tok == "str":
            name = tokens[i + 1]
            global_out.extend(["var", name, f'"{strings.pop(0)}"'])
            i += 3
            continue
        if tok == "array":
            name = tokens[i + 1]
            capacity = int(tokens[i + 2])
            global_out.extend(["var", name] + ["0"] * capacity)
            i += 3
            continue
        if tok == "out":
            cur.extend(["out", tokens[i + 1]])
            i += 2
            continue
        if tok == "in":
            cur.extend(["in", tokens[i + 1]])
            i += 2
            continue
        if tok == ":":
            func_end = f"{tokens[i + 1]}_end"
            cur = proc_out
            cur.append(f"{tokens[i + 1]}:")
            func_labels.add(f"{tokens[i + 1]}")
            i += 2
            continue
        if tok == ";":
            if func_end == "interrupt_handler_end":
                cur.append("iret")
            else:
                cur.append(f"{func_end}:")
                cur.append("ret")
            func_end = None
            cur = global_out
            i += 1
            continue
        if tok == "!=" or tok == ">":
            uid_if_else += 1
            else_label = f"else_{uid_if_else}"
            end_label = f"end_{uid_if_else}"
            if tok == "!=":
                cur.append(f"-")
                cur.append(f"lit else_{uid_if_else}")
                cur.append("swap")
                cur.append("jz")
            else:
                cur.append("swap")
                cur.append("-")
                cur.append(f"lit else_{uid_if_else}")
                cur.append("swap")
                cur.append("jn")
            if_stack.append((else_label, end_label, False))
            i += 2
            continue
        if tok == "else":
            else_label, end_label, _sk = if_stack.pop()
            cur.extend([f"lit {end_label}", "jump"])
            cur.append(f"{else_label}:")
            if_stack.append((else_label, end_label, True))
            i += 1
            continue
        if tok == "then":
            else_label, end_label, has_else = if_stack.pop()
            if not has_else:
                cur.append(f"{else_label}:")
                cur.append("nop")
            cur.append(f"{end_label}:")
            cur.append(f"nop")
            i += 1
            continue
        if tok == "begin":
            uid_begin_again += 1
            l_begin = f"loop_{uid_begin_again}_start"
            l_end = f"loop_{uid_begin_again}_end"
            begin_stack.append((l_begin, l_end))
            cur.append(f"{l_begin}:")
            i += 1
            continue
        if tok == "exit":
            l_begin, l_end = begin_stack[-1]
            cur.extend([f"lit {l_end}", "inc", "inc", "jump"])
            i += 1
            continue

        if tok == "again":
            l_begin, l_end = begin_stack.pop()
            cur.append(f"{l_end}:")
            cur += [f"lit {l_begin}", "jump"]
            i += 1
            continue
        if tok in data_labels:
            cur.append(f"lit {tok}")
            i += 1
            continue
        if tok in func_labels:
            cur.append(f"lit {tok}")
            cur.append(f"call")
            i += 1
            continue
        if tok == "*2":
            cur.extend(
                [
                    "dup",
                    "lit _tmp_over",
                    "!",
                    "swap",
                    "dup",
                    "lit _tmp_over",
                    "@",
                    "mulh",
                    "lit _tmp_over",
                    "!",
                    "*",
                    "lit _tmp_over",
                    "@",
                    "swap",
                ]
            )
            i += 1
            continue
        cur.append(tok)
        i += 1
    full_out = global_out + proc_out

    return "\n".join(full_out) + "\n"


def is_number(tok: str) -> bool:
    if tok.startswith("0x"):
        try:
            int(tok, 16)
            return True
        except ValueError:
            return False
    if tok.startswith("-"):
        return tok[1:].isdigit()
    return tok.isdigit()


def to_int(tok: str) -> int:
    return int(tok, 0)


def symbol_to_opcode(symbol):
    return {
        "nop": Opcode.NOP,
        "lit": Opcode.LIT,
        "!": Opcode.STORE,
        "@": Opcode.LOAD,
        "in": Opcode.IN,
        "out": Opcode.OUT,
        "+": Opcode.ADD,
        "-": Opcode.SUB,
        "*": Opcode.MUL,
        "/": Opcode.DIV,
        "inc": Opcode.INC,
        "dec": Opcode.DEC,
        "mulh": Opcode.MULH,
        "and": Opcode.AND,
        "or": Opcode.OR,
        "xor": Opcode.XOR,
        "not": Opcode.NOT,
        "jump": Opcode.JUMP,
        "call": Opcode.CALL,
        "jz": Opcode.JZ,
        "jn": Opcode.JN,
        "swap": Opcode.SWAP,
        "ret": Opcode.RET,
        "dup": Opcode.DUP,
        "drop": Opcode.DROP,
        "iret": Opcode.IRET,
        "eint": Opcode.EINT,
        "dint": Opcode.DINT,
        "halt": Opcode.HALT,
    }.get(symbol)


def first_stage(text: str):
    labels: dict[str, int] = {}
    data_words: list[str] = []
    instrs_tmp: list[ParsInstr] = []
    current_data_addr = 0
    tokens, strings = tokenize(text)
    i = 0
    string_index = 0
    len_tokens = len(tokens)
    while i < len_tokens:
        token = tokens[i]

        if token == "var":
            if i + 2 >= len_tokens:
                sys.exit(f"syntax: var <name> <numbers>|<string>")
            name = tokens[i + 1]
            if name in labels:
                sys.exit(f"duplicate symbol {name}")
            values = []
            j = i + 2
            while j < len_tokens:
                v = tokens[j]
                if v == "*":
                    if string_index >= len(strings):
                        sys.exit(f" string index out of range")
                    raw = strings[string_index]
                    processed = bytes(raw, "utf-8").decode("unicode_escape")
                    values.extend(ord(c) for c in processed)
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

        if token.endswith(":"):
            label = token[:-1]
            if not LABEL_RE.fullmatch(label):
                sys.exit(f"invalid label name '{label}' " "(label must match [A-Za-z_][A-Za-z0-9_]* )")
            if label in labels:
                sys.exit(f"duplicate symbol {label}")
            labels[label] = len(instrs_tmp)
            i += 1
            continue

        opcode = symbol_to_opcode(token)

        if opcode is None:
            sys.exit(f" unknown opcode '{token}'")
        i += 1
        arg_tok = None

        if opcode == Opcode.LIT:
            if i >= len_tokens:
                sys.exit(f"lit expects literal/label")
            arg_tok = tokens[i]
            i += 1
        elif opcode == Opcode.IN:
            if i >= len_tokens:
                sys.exit(f"input expects literal/label")
            arg_tok = tokens[i]
            if not is_number(arg_tok) or int(arg_tok) != 0:
                sys.exit(f"IN only supports port 0 (default input device). You wrote IN {arg_tok}")
            i += 1
        elif opcode == Opcode.OUT:
            if i >= len_tokens:
                sys.exit(f"output expects literal/label")
            arg_tok = tokens[i]
            if not is_number(arg_tok) or not (1 <= int(arg_tok) <= 7):
                sys.exit(f"OUT only supports port [1-7] (default input device). You wrote IN {arg_tok}")
            i += 1

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
    pc = 0
    for ins in instrs_tmp:
        if ins.opcode == Opcode.LIT:
            arg_val = resolve_arg(ins.argument, labels)
            final_instrs.append({"index": pc, "opcode": Opcode.LIT, "arg": arg_val})
        elif ins.opcode in Opcode.IN:
            final_instrs.append({"index": pc, "opcode": Opcode.IN, "arg": to_int(ins.argument)})
        elif ins.opcode == Opcode.OUT:
            final_instrs.append({"index": pc, "opcode": Opcode.OUT, "arg": to_int(ins.argument)})
        else:
            final_instrs.append({"index": pc, "opcode": ins.opcode})
        pc += 1
    return final_instrs


def check_interrupt_handler(instrs_tmp: list[ParsInstr], labels: dict[str, int]) -> tuple[bool, int | None]:
    interrupt_label = "interrupt_handler"
    interrupts_enabled = any(ins.opcode == Opcode.EINT for ins in instrs_tmp)
    if not interrupts_enabled:
        return False, None
    if interrupt_label not in labels:
        sys.exit("EINT встречается, но метка interrupt_handler не объявлена")
    start = labels[interrupt_label]
    end = min((i for i in labels.values() if i > start), default=len(instrs_tmp))
    handler_instructions = instrs_tmp[start:end]
    if not any(ins.opcode == Opcode.IRET for ins in handler_instructions):
        sys.exit("Обработчик прерывания не завершается IRET")
    return True, start


def assemble(source: str):
    instrs_tmp, labels, data_words = first_stage(source)
    intr_enabled, handler_addr = check_interrupt_handler(instrs_tmp, labels)
    instructions = second_stage(instrs_tmp, labels)
    return instructions, data_words, intr_enabled, handler_addr


def main(source, code_file, data_file):
    with open(source, encoding="utf-8") as f:
        source = f.read()

    forth_path = Path(sys.argv[1])
    forth_text = forth_path.read_text(encoding="utf-8")
    asm_text = forth_to_assemble(forth_text)
    instructions, data_words, intr, addr_handler = assemble(asm_text)

    os.makedirs(os.path.dirname(os.path.abspath(code_file)) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(data_file)) or ".", exist_ok=True)

    if code_file.endswith(".bin"):
        write_instructions(code_file, instructions, intr, addr_handler)
        write_data(data_file, data_words)
        write_hex_instructions(code_file + ".hex", instructions)
        write_hex_data(data_file + ".hex", data_words)
    print("source LoC:", len(source.split("\n")), "code instr:", len(instructions))


if __name__ == "__main__":
    assert (
        len(sys.argv) == 4
    ), "Wrong arguments: translator.py <input_file> <target_instructions_file> <target_data_file>"
    _, source, target_instructions_file, target_data_file = sys.argv
    main(source, target_instructions_file, target_data_file)
