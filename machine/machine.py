import sys

from isa.isa import Opcode, from_bytes_to_data, from_bytes_to_instructions
from signals import Signal

class DataPath:
    stack: list[int] = None
    stack_pointer: int = None
    stack_size: int = None
    tos: int = None
    result_alu: int = None
    CU_arg: int = None
    data_memory: list[int] = None
    INT_MAX: int = None
    io_ports: dict[int, list[str]]= None
    def __init__(self,data,devices,stack_capacity):
        self.data_memory = data
        self.stack_size = stack_capacity
        self.stack = [0] * stack_capacity
        self.tos = 0
        self.CU_arg = 0
        self.result_alu = 0
        self.flags = {"Z":0, "N":0}
        self.stack_pointer = 0
        self.INT_MAX = 2**32 - 1
        self.io_ports = devices

    def stack_push(self,value):
        assert self.stack_pointer < self.stack_size, "data stack overflow"
        self.stack[self.stack_pointer] = value
        self.stack_pointer += 1

    def stack_pop(self):
        assert self.stack_pointer >= 0, "data stack underflow"
        value = self.stack[self.stack_pointer]
        #self.stack[self.stack_pointer] = 0
        self.stack_pointer -= 1
        return value
    def stack_top(self):
        return self.stack[self.stack_pointer]

    def latch_stack(self):
        self.stack[self.stack_pointer] = self.tos

    def latch_sp(self, sel: Signal):
        if sel == Signal.SEL_SP_NEXT:
            assert self.stack_pointer < len(self.stack), "stack capacity exceeded"
            self.stack_pointer += 1
        elif Signal.SEL_SP_PREV in sel:
            assert self.stack_pointer >= 0, "negative stack pointer was received"
            self.stack[self.stack_pointer-1] = 0
            self.stack_pointer -= 1

    def latch_tos(self, sel : Signal):
        if sel == Signal.SEL_TOS_SREG:
            self.tos = self.stack_pop()
        elif sel == Signal.SEL_TOS_CU_ARG:
            self.tos = self.CU_arg
        elif sel == Signal.SEL_TOS_SYNC:
            self.tos = self.stack_top()
        elif sel == Signal.SEL_TOS_ALU:
            self.tos = self.result_alu
        elif sel == Signal.SEL_TOS_IO:
            self.tos = self.io_ports[self.tos].pop()
        elif sel == Signal.SEL_TOS_MEM:
            self.tos = self.data_memory

    def signal_alu_binary(self,opcode):
        assert self.stack_pointer >= 2, "Not enough elements on stack"
        a = self.tos
        b = self.stack[self.stack_pointer - 2]
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
        assert self.stack_pointer >= 2, "data stack underflow"
        self.tos, self.stack[self.stack_pointer-2] = self.stack[self.stack_pointer-2], self.tos
    def stack_dup(self):
        self.stack_push(self.tos)

class Control_Unit:
    pc = None
    program = None
    data_path: DataPath = None
    call_stack = None
    step = None
    _tick = None
    state = None
    def __init__(self,program_memory,data_path: DataPath, call_stack_capacity, input_timetable, interrupt_handler_address):
        self.IF = True
        self.INTR = False
        self.interrupt_handler_address = interrupt_handler_address
        self.input_timetable = input_timetable
        self.in_interrupt = False
        self.program = program_memory
        self.pc = 0
        self.call_stack = [0] * call_stack_capacity
        self.data_path = data_path
        self._tick = 0
        self.step = 0
        self.state = 0
        self.MAX_NESTED = 1
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

    def signal_latch_pc_interrupt_buffer(self):
        self.pc_interrupt_buffer = self.pc

    def signal_set_IF(self, IF: bool): # Разрешает или же запрещает прерывания
        self.IF = IF

    def check_interrupt_request(self):
        if self._tick not in self.input_timetable:
            return
        if not self.IF:
            return
        if self.nested_lvl >= self.MAX_NESTED:
            return
        self.INTR = True
    def decode_and_execute_instruction(self, instr):
        self.check_interrupt_request()
        if self.INTR and self.step == 0 and self.state==0:
            if self.step == 0:
                self.data_path.signal_store_registers()
                self.signal_latch_pc_interrupt_buffer()
                self.tick()
                return
            if self.step == 1:
                self.signal_latch_pc_intr()
                self.state = 2
                self.step = 0
                self.tick()
                return

        opcode = instr.opcode
        if opcode == Opcode.HALT:
            raise StopIteration()
        if instr.opcode is Opcode.RINT:
            self.data_path.signal_restore_registers()
            self.signal_latch_pc_interrupt_buffer()
            self.state = 0
            self.step = 0
            self.tick()
            return

        if instr.opcode is Opcode.EINT:
            self.signal_set_IF(True)
            self.signal_latch_pc()
            self.step = 0
            self.tick()
            return

        if instr.opcode is Opcode.DINT:
            self.signal_set_IF(False)
            self.signal_latch_pc()
            self.step = 0
            self.tick()
            return

        if opcode == Opcode.JUMP:
            self.data_path.latch_tos(Signal.SEL_TOS_SREG)
            self.signal_latch_pc(self.data_path.tos)
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
            self.data_path.CU_arg = instr.arg
            self.data_path.latch_tos(Signal.SEL_TOS_CU_ARG)
            self.signal_latch_pc()
            self.step = 0
            self.tick()
            return

        if opcode == Opcode.CALL:
            if self.step == 0:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG)
                self.step = 1
                self.tick()
                return
            if self.step == 1:
                assert len(self.call_stack) < self.MAX_NESTED
                self.call_stack[self.nested_lvl] = self.pc + 1
                self.nested_lvl +=1
                self.signal_latch_pc(self.data_path.tos)
                self.step = 0
                self.tick()
                return
        if opcode == Opcode.RET:
            assert self.nested_lvl <= 0
            self.nested_lvl -= 1
            return_addr = self.call_stack[self.nested_lvl]
            self.signal_latch_pc(return_addr)
            self.step = 0
            self.tick()

        if opcode == Opcode.LOAD:
            if self.step == 0:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG) #значение адреса
                self.data_path.latch_data_address(self.data_path.tos)
                self.step = 1
                self.tick()
                return
            if self.step == 1:
                self.data_path.signal_data_memory_load()
                self.data_path.latch_tos(Signal.SEL_TOS_MEM)
                self.signal_latch_pc(self.pc+1)
                self.step = 0
                self.tick()
                return

        if opcode == Opcode.STORE:
            if self.step == 0:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG) #адрес
                self.data_path.latch_data_address(self.data_path.tos) #меняю регистр ad
                self.step = 1
                self.tick()
                return
            if self.step == 1:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG) # значение данных
                self.data_path.signal_memory_store()
                self.signal_latch_pc(self.pc+1)
                self.step = 0
                self.tick()
                return

        if opcode == Opcode.IN:
            self.data_path.latch_tos(Signal.SEL_TOS_SREG)
            """
            if port in self.data_path.io_ports and self.data_path.io_ports[port]:
                value = ord(self.data_path.io_ports[port].pop(0))
            else:
                value = 0
            """
            self.data_path.latch_tos(Signal.SEL_TOS_IO)
            self.data_path.latch_stack()
            self.data_path.latch_sp(Signal.SEL_SP_NEXT)
            self.signal_latch_pc(self.pc+1)
            self.tick()
            return

        if opcode == Opcode.OUT:
            if self.step == 0:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG)
                self.data_path.write_buffer = self.data_path.tos
                self.step=1
                self.tick()
                return
            if self.step == 1:
                self.data_path.latch_tos(Signal.SEL_TOS_SREG)
                port = self.data_path.tos
                value = self.data_path.write_buffer
                if port in self.data_path.io_ports:
                    self.data_path.io_ports[port].append(chr(value%256))
                else:
                    self.data_path.io_ports[port] = [chr(value%256)]
                self.signal_latch_pc(self.pc+1)
                self.step = 0
                self.tick()
                return

        if opcode in {Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV, Opcode.OR, Opcode.AND, Opcode.XOR}:
                self.data_path.signal_alu_binary(opcode)
                self.data_path.latch_sp(Signal.SEL_SP_PREV)
                self.data_path.latch_tos(Signal.SEL_TOS_ALU)
                self.data_path.latch_stack()
                self.step = 0
                self.tick()
                self.signal_latch_pc()
                return
        #подумать над атомарностью операций сложения и т.д.
        if opcode in {Opcode.INC, Opcode.DEC, Opcode.NOT}:
                self.data_path.signal_alu(opcode)
                self.data_path.latch_tos(Signal.SEL_TOS_ALU)
                self.data_path.latch_stack()
                self.step = 0
                self.tick()
                return

        if opcode==Opcode.DUP:

                return
        if opcode==Opcode.SWAP:

        if opcode == Opcode.DROP:
            self.data_path.latch_tos(Signal.SEL_TOS_S)





def simulation(code, input_tokens, data_memory_size, limit):
    pass

def main(code_file,data_file, input_file):
    with open(code_file, "rb") as f:
        binary_code = f.read()
    code = from_bytes_to_instructions(binary_code)
    with open(data_file, "rb") as f:
        binary_data = f.read()
    data = from_bytes_to_data(binary_data)

    with open(input_file, encoding="utf-8") as f:
        input_text = f.read()
        input_token = []
        for char in input_text:
            input_token.append(char)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
    main(sys.argv[1], sys.argv[2])