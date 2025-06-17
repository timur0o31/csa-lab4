import sys

from isa.isa import Opcode, from_bytes_to_data, from_bytes_to_instructions,data_to_bytes
from signals import Signal, ProcessorState

class DataPath:
    stack: list[int] = None
    stack_pointer: int = None
    stack_size: int = None
    data_address: int = None
    tos: int = None
    result_alu: int = None
    CU_arg: int = None
    data_memory: list[int] = None
    INT_MAX: int = None
    io_ports: dict[int, list[str]]= None
    def __init__(self,data,input_buffer, stack_capacity):
        self.data_memory = data #???
        self.stack_size = stack_capacity
        self.stack = [0] * stack_capacity
        self.tos = 0
        self.data_address = 0
        self.CU_arg = 0
        self.result_alu = 0
        self.flags = {"Z":0, "N":0}
        self.stack_pointer = -1
        self.INT_MAX = 2**32 - 1
        output = list()
        self.io_ports = {0: list(), 1: output, 2: list()}
        self.input_buffer = input_buffer
    def stack_push(self,value):
        assert self.stack_pointer < self.stack_size, "data stack overflow"
        self.stack_pointer += 1
        self.stack[self.stack_pointer] = value

    def stack_pop(self):
        assert self.stack_pointer >= 0, "data stack underflow"
        value = self.stack[self.stack_pointer]
        self.stack[self.stack_pointer] = 0
        self.stack_pointer -= 1
        return value

    def stack_top(self):
        return self.stack[self.stack_pointer]

    def signal_memory_store(self):
        addr = self.data_address
        assert -1 < addr < len(self.data_memory), ""
        self.data_memory[addr] = self.tos

    def latch_stack(self):
        self.stack[self.stack_pointer] = self.tos

    def latch_data_address(self):
        self.data_address = self.tos

    def latch_sp(self, sel: Signal):
        if sel == Signal.SEL_SP_NEXT:
            assert self.stack_pointer < len(self.stack), "stack capacity exceeded"
            self.stack_pointer += 1
        elif Signal.SEL_SP_PREV == sel:
            assert self.stack_pointer >= 0, "negative stack pointer was received"
            self.stack[self.stack_pointer-1] = 0
            self.stack_pointer -= 1

    def latch_tos(self, sel : Signal):
        if sel == Signal.SEL_TOS_SREG:
            self.tos = self.stack_pop()
        elif sel == Signal.SEL_TOS_CU_ARG:
            self.tos = self.CU_arg
        elif sel == Signal.SEL_TOS_ALU:
            self.tos = self.result_alu
        elif sel == Signal.SEL_TOS_MEM:
            self.tos = self.data_memory[self.data_address]
        elif sel == Signal.SEL_TOS_IN:
            self.tos = ord(self.io_ports[self.tos].pop(0))
        elif sel == Signal.SEL_TOS_SYNC:
            self.tos = self.stack_top()

    #не забыть проверять область определния результата как 32-битное число
    def signal_alu_binary(self,opcode):
        assert self.stack_pointer >= 2, f"Not enough elements on stack {self.stack_pointer}, {self.stack}"
        a = self.tos
        b = self.stack[self.stack_pointer - 1]
        result = 0
        if opcode == Opcode.ADD:
            result = a + b
        elif opcode == Opcode.SUB:
            result = a - b
        elif opcode == Opcode.AND:
            result = a & b
        elif opcode == Opcode.OR:
            result = a | b
        elif opcode == Opcode.MUL:
            result = a * b
        elif opcode == Opcode.DIV:
            result = a//b
        elif opcode == Opcode.XOR:
            result = a ^ b
        self.result_alu = result
    def signal_alu(self,opcode):
        assert self.stack_pointer >= 0, "Not enough elements on stack"
        result = 0
        if opcode == Opcode.INC:
            result = self.tos + 1
        elif opcode == Opcode.DEC:
            result = self.tos - 1
        elif opcode == Opcode.NOT:
            result = ~self.tos & 0xFFFFFFFF
        self.result_alu = result

    def zero_flag(self):
        self.flags["Z"] = int(self.tos == 0)
    def negative_flag(self):
        self.flags["N"] = int(self.tos < 0)

    def stack_swap(self):
        assert self.stack_pointer >= 1, "data stack underflow"
        self.stack[self.stack_pointer], self.stack[self.stack_pointer-1] = self.stack[self.stack_pointer-1], self.stack[self.stack_pointer]

class Control_Unit:
    pc = None
    program = None
    data_path: DataPath = None
    call_stack = None
    step = None
    _tick = None
    state = None
    def __init__(self,program_memory,data_path: DataPath, call_stack_capacity, input_timetable, interrupt_handler_address):
        self.IF = False
        self.INTR = False
        self.interrupt_handler_address = interrupt_handler_address
        self.input_timetable = input_timetable
        self.in_interrupt = False
        self.program = program_memory
        self.pc = 0
        self.call_stack = []
        self.data_path = data_path
        self._tick = 0
        self.step = 0
        self.call_stack_capacity = call_stack_capacity
        self.state = ProcessorState.NORMAL
        self.MAX_NESTED = 3
        self.nested_lvl = 0

    def tick(self):
        self._tick += 1
    def current_tick(self):
        return self._tick
    def signal_latch_pc(self, next_pc=1):
        self.pc = next_pc
        assert self.pc < len(self.program), "out of instruction memory:"

    def signal_latch_intr(self):
        next_pc = self.interrupt_handler_address
        self.signal_latch_pc(next_pc)

    def signal_rem_int_rq(self): #Сброс сигнала запроса прерываний
        self.INTR = False
    def signal_latch_pc_intr(self):
        self.call_stack.append(self.pc)
        self.pc = self.interrupt_handler_address
    def signal_store_registers(self):
        self.call_stack.append(self.data_path.tos)
        self.call_stack.append(self.data_path.stack_pointer)
        self.call_stack.append(self.data_path.data_address)
    def signal_restore_registers(self):
        self.data_path.data_address = self.call_stack.pop()
        self.data_path.stack_pointer = self.call_stack.pop()
        self.data_path.tos = self.call_stack.pop()


    def signal_set_IF(self,flag): # Разрешает или же запрещает прерывания
        self.IF = flag
    def signal_set_INTR(self, flag):
        self.INTR = flag
    def check_interrupt_request(self):
        if self._tick not in self.input_timetable:
            return
        if not self.IF:
            return
        if self.nested_lvl >= self.MAX_NESTED: #???
            return
        value = self.data_path.input_buffer.pop(0)
        self.data_path.io_ports[0].append(value[1])
        self.signal_set_INTR(True)
    def decode_and_execute_instruction(self):
        self.check_interrupt_request()
        if self.INTR:
            if self.step == 0:
                self.signal_store_registers()
                self.tick()
                return
            if self.step == 1:
                self.signal_latch_pc_intr()
                self.state = ProcessorState.INT_BODY
                self.step = 0
                self.tick()
                self.nested_lvl += 1
                self.signal_set_INTR(False)
                return

        instr = self.program[self.pc]
        opcode = instr["opcode"]
        print(self.data_path.stack[0:10])
        print(opcode," такты:", self._tick," pc:",self.pc)
        if opcode == Opcode.LIT:
            print(instr["arg"])
        if opcode == Opcode.HALT:
            raise StopIteration()
        if opcode is Opcode.IRET:
            self.pc = self.call_stack.pop()
            self.signal_restore_registers()
            self.state = ProcessorState.NORMAL
            self.step = 0
            self.tick()
            return

        if opcode is Opcode.EINT:
            self.signal_set_IF(True)
            self.signal_latch_pc()
            self.step = 0
            self.tick()
            return

        if opcode is Opcode.DINT:
            self.signal_set_IF(False)
            self.signal_latch_pc()
            self.step = 0
            self.tick()
            return

        if opcode == Opcode.JUMP:
            self.data_path.latch_tos(Signal.SEL_TOS_SREG)
            self.signal_latch_pc(self.data_path.tos)
            self.data_path.latch_tos(Signal.SEL_TOS_ALU)
            self.step = 0
            self.tick()
            return

        if opcode == Opcode.JZ:
            if self.step == 0:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG)
                self.data_path.zero_flag()
                self.step = 1
                self.tick()
                return
            if self.step == 1:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG) #берется значение куда надо перейти
                if self.data_path.flags["Z"]:
                    self.signal_latch_pc(self.data_path.tos)
                else:
                    self.signal_latch_pc(self.pc+1)
                self.data_path.latch_tos(Signal.SEL_TOS_SYNC)
                self.step = 0
                self.tick()
                return

        if opcode == Opcode.JN:
            if self.step == 0:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG)
                self.data_path.negative_flag()
                self.step = 1
                self.tick()
                return
            if self.step == 1:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG) #берется значение куда надо перейти
                if self.data_path.flags["N"]:
                    self.signal_latch_pc(self.data_path.tos)
                else:
                    self.signal_latch_pc(self.pc+1)
                self.data_path.latch_tos(Signal.SEL_TOS_SYNC)
                self.step = 0
                self.tick()
                return

        if opcode == Opcode.LIT:
            self.data_path.CU_arg = instr["arg"]
            self.data_path.latch_tos(Signal.SEL_TOS_CU_ARG)
            self.data_path.stack_push(self.data_path.tos)
            self.signal_latch_pc(self.pc+1)
            self.step = 0
            self.tick()
            return
        if opcode == Opcode.CALL:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG)
                assert len(self.call_stack) < self.call_stack_capacity
                self.call_stack.append(self.pc + 1)
                self.signal_latch_pc(self.data_path.tos)
                self.data_path.latch_tos(Signal.SEL_TOS_SYNC)
                self.step = 0
                self.tick()
                return
        if opcode == Opcode.RET:
            assert len(self.call_stack) > 0
            return_addr = self.call_stack[self.nested_lvl]
            self.signal_latch_pc(return_addr)
            self.step = 0
            self.tick()
            return

        if opcode == Opcode.LOAD:
            if self.step == 0:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG) #адрес
                self.data_path.latch_data_address()
                self.step = 1
                self.tick()
                return
            if self.step == 1:
                self.data_path.latch_tos(Signal.SEL_TOS_MEM)
                self.data_path.stack_push(self.data_path.tos)
                self.signal_latch_pc(self.pc+1)
                self.step = 0
                self.tick()
                return

        if opcode == Opcode.STORE:
            if self.step == 0:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG) #адрес
                self.data_path.latch_data_address() #меняю регистр AR
                self.step = 1
                self.tick()
                return
            if self.step == 1:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG) # значение данных
                self.data_path.signal_memory_store()
                self.data_path.latch_tos(Signal.SEL_TOS_SYNC)
                self.signal_latch_pc(self.pc+1)
                self.step = 0
                self.tick()
                return

        if opcode == Opcode.IN:
            port = instr.arg
            assert port in self.data_path.io_ports, f"Invalid port: {port}"
            assert self.data_path.io_ports[port], f"Input buffer for port {port} is empty"
            self.data_path.latch_tos(Signal.SEL_TOS_IN)
            self.data_path.latch_stack()
            self.data_path.latch_sp(Signal.SEL_SP_NEXT)
            self.signal_latch_pc(self.pc+1)
            self.tick()
            return

        if opcode == Opcode.OUT:
                port = instr.arg
                self.data_path.latch_tos(Signal.SEL_TOS_SREG)
                value = self.data_path.tos
                assert 1 <= port <= 7, f"OUT supports ports 1–7. Got port={port}"
                self.data_path.io_ports[port].append(chr(value%256))
                self.signal_latch_pc(self.pc+1)
                self.step = 0
                self.tick()
                return

        if opcode in {Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV, Opcode.OR, Opcode.AND, Opcode.XOR}:
                self.data_path.signal_alu_binary(opcode)
                self.data_path.latch_sp(Signal.SEL_SP_PREV)
                self.data_path.latch_tos(Signal.SEL_TOS_ALU)
                self.data_path.latch_stack()
                self.signal_latch_pc(self.pc+1)
                self.step = 0
                self.tick()
                return

        if opcode in {Opcode.INC, Opcode.DEC, Opcode.NOT}:
            if self.step == 0:
                self.data_path.signal_alu(opcode)
                self.data_path.latch_tos(Signal.SEL_TOS_ALU)
                self.data_path.latch_stack()
                self.signal_latch_pc(self.pc+1)
                self.step = 0
                self.tick()
                return

        if opcode==Opcode.DUP:
            self.data_path.stack_push(self.data_path.tos)
            self.step = 0
            self.signal_latch_pc(self.pc+1)
            self.tick()
            return
        if opcode==Opcode.SWAP:
            self.data_path.stack_swap()
            self.step = 0
            self.signal_latch_pc(self.pc+1)
            self.data_path.latch_tos(Signal.SEL_TOS_SYNC)
            self.tick()
            pass
        if opcode == Opcode.DROP:
            self.data_path.stack_pop()
            self.data_path.latch_tos(Signal.SEL_TOS_SYNC)
            self.step = 0
            self.signal_latch_pc(self.pc + 1)
            self.tick()
            return


def simulation(code, data, handler_addr,input_tokens, limit):
    dataPath = DataPath(data,input_tokens,200)
    control_Unit = Control_Unit(code, dataPath, 200, [], handler_addr)
    try:
        while control_Unit._tick <limit:
            control_Unit.decode_and_execute_instruction()
    except AssertionError as e:
        print(e)
    except StopIteration as e:
        print("Success!")
    pass

def main(code_file,data_file, input_file):
    code, handl_addr = from_bytes_to_instructions(code_file)
    data = from_bytes_to_data(data_file)
    if input_file is not None:
        with open(input_file, encoding="utf-8") as f:
            input_text = f.read()
            input_token = []
            for char in input_text:
                input_token.append(char)
    simulation(code,data,handl_addr, None,100)
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2],None)