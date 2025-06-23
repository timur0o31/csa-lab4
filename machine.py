import sys
from isa.isa import Opcode, from_bytes_to_data, from_bytes_to_instructions,data_to_bytes, instr_to_bytes
from signals import Signal, ProcessorState
import logging

class DataPath:
    def __init__(self,data, stack_capacity,IO_Controller):
        self.data_memory = data
        self.stack_size = stack_capacity
        self.stack = [0] * stack_capacity
        self.tos = 0
        self.data_address = 0
        self.CU_arg = 0
        self.result_alu = 0
        self.flags = {"Z":0, "N":0, "C":0}
        self.stack_pointer = -1
        self.INT_MAX = 2**32 - 1
        self.IO_Controller = IO_Controller

    def signal_memory_store(self):
        addr = self.data_address
        assert -1 < addr < len(self.data_memory), ""
        self.data_memory[addr] = self.tos

    def signal_latch_stack(self):
        self.stack[self.stack_pointer] = self.tos

    def signal_latch_data_address(self):
        self.data_address = self.tos

    def latch_sp(self, sel: Signal):
        if sel == Signal.SEL_SP_NEXT:
            assert self.stack_pointer < len(self.stack), "stack capacity exceeded"
            self.stack_pointer += 1
        elif Signal.SEL_SP_PREV == sel:
            assert self.stack_pointer >= 0, "negative stack pointer was received"
            self.stack[self.stack_pointer] = 0
            self.stack_pointer -= 1

    def latch_tos(self, sel : Signal):
        if sel == Signal.SEL_TOS_STACK:
            self.tos = self.stack[self.stack_pointer]
        elif sel == Signal.SEL_TOS_CU_ARG:
            self.tos = self.CU_arg
        elif sel == Signal.SEL_TOS_ALU:
            self.tos = self.result_alu
        elif sel == Signal.SEL_TOS_MEM:
            self.tos = self.data_memory[self.data_address]
        elif sel == Signal.SEL_TOS_IN:
            self.tos = self.IO_Controller.input(self.CU_arg)

    def signal_alu_binary(self,opcode):
        assert self.stack_pointer >= 1, f"Not enough elements on stack {self.stack_pointer}, {self.stack}"
        a = self.tos
        b = self.stack[self.stack_pointer]
        result = 0
        if opcode == Opcode.ADD:
            result = a + b
            self.flags["C"] = int(result > 0xFFFFFFFF)
            result &= 0xFFFFFFFF
        elif opcode == Opcode.SUB:
            result = a - b
        elif opcode == Opcode.AND:
            result = a & b
        elif opcode == Opcode.OR:
            result = a | b
        elif opcode == Opcode.MUL:
            result = a * b
            result &= 0xFFFFFFFF
        elif opcode == Opcode.MULH:
            wide = a * b
            result = (wide >> 32) & 0xFFFFFFFF
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

    def signal_latch_zero_flag(self):
        self.flags["Z"] = int(self.tos == 0)
    def signal_latch_negative_flag(self):
        self.flags["N"] = int(self.tos < 0)
    def signal_write_port(self):
        self.IO_Controller.output(self.CU_arg, self.tos)
    def stack_swap(self):
        assert self.stack_pointer >= 0, "data stack underflow"
        self.stack[self.stack_pointer], self.tos = self.tos, self.stack[self.stack_pointer]


class IOController:
    def __init__(self,io_ports):
        self.io_ports = io_ports  #port -> list
    def push_input_buf(self,port,value):
        self.io_ports[port].append(value)
    def input(self, port):
        return self.io_ports[port].pop(0)
    def output(self,port,value):
        self.io_ports[port].append(chr(value))



class Control_Unit:
    def __init__(self,program_memory,data_path: DataPath, call_stack_capacity, input_timetable, interrupt_handler_address):
        self.IF = False
        self.INTR = False
        self.interrupt_handler_address = interrupt_handler_address
        self.input_timetable = input_timetable
        self.scp = -1
        self.program = program_memory
        self.pc = 0
        self.call_stack = [0] * call_stack_capacity
        self.data_path = data_path
        self._tick = 0
        self.step = 0
        self.state = ProcessorState.NORMAL
        self.return_addr = 0

    def tick(self):
        self._tick += 1
    def latch_pc(self, sel: Signal):
        if sel == Signal.SEL_PC_NEXT:
            self.pc += 1
        elif sel == Signal.SEL_PC_TOS:
            self.pc = self.data_path.tos
        elif sel == Signal.SEL_PC_INT:
            self.pc = self.interrupt_handler_address
        elif sel == Signal.SEL_PC_RET:
            self.pc = self.call_stack[self.scp]
    def latch_scp(self, sel: Signal):
        if sel == Signal.SEL_SCP_NEXT:
            assert self.scp < len(self.call_stack), "call stack capacity exceeded"
            self.scp += 1
            self.call_stack[self.scp] = self.pc + 1
        elif sel == Signal.SEL_SCP_PREV:
            assert self.scp >= 0, "negative call stack pointer was received"
            self.call_stack[self.scp] = 0
            self.scp -= 1

    def signal_store_pc(self):
        self.call_stack[self.scp] = self.pc
    def signal_enable_interrupts(self):
        self.IF = True
    def signal_disable_interrupts(self):
        self.IF = False
    def signal_set_INTR(self):
        self.INTR = True
    def signal_reset_INTR(self):
        self.INTR = False
    def check_interrupt_request(self):
        if self._tick not in self.input_timetable.keys():
            return
        if not self.IF:
            return
        port, value = self.input_timetable[self._tick]
        self.data_path.IO_Controller.push_input_buf(port, value)
        self.signal_set_INTR()
    def decode_and_execute_instruction(self):
        self.check_interrupt_request()
        if self.INTR and self.step == 0:
                self.return_addr = self.pc
                self.latch_pc(Signal.SEL_PC_INT)
                self.state = ProcessorState.INTERRUPTION
                self.tick()
                self.step = 0
                self.signal_reset_INTR()
                return

        instr = self.program[self.pc]
        opcode = instr["opcode"]
        if opcode == Opcode.HALT:
            raise StopIteration()
        if opcode is Opcode.IRET:
            self.pc = self.return_addr
            self.state = ProcessorState.NORMAL
            self.step = 0
            self.tick()
            return

        if opcode is Opcode.EINT:
            self.signal_enable_interrupts()
            self.latch_pc(Signal.SEL_PC_NEXT)
            self.step = 0
            self.tick()
            return

        if opcode is Opcode.DINT:
            self.signal_disable_interrupts()
            self.latch_pc(Signal.SEL_PC_NEXT)
            self.step = 0
            self.tick()
            return

        if opcode == Opcode.JUMP:
            self.latch_pc(Signal.SEL_PC_TOS)
            self.data_path.latch_tos(Signal.SEL_TOS_STACK)
            self.data_path.latch_sp(Signal.SEL_SP_PREV)
            self.step = 0
            self.tick()
            return

        if opcode == Opcode.JZ:
            if self.step == 0:
                self.data_path.signal_latch_zero_flag()
                self.data_path.latch_tos(Signal.SEL_TOS_STACK)
                self.data_path.latch_sp(Signal.SEL_SP_PREV)
                self.step = 1
                self.tick()
                return
            if self.step == 1:
                if self.data_path.flags["Z"]:
                    self.latch_pc(Signal.SEL_PC_TOS)
                else:
                    self.latch_pc(Signal.SEL_PC_NEXT)
                self.data_path.latch_tos(Signal.SEL_TOS_STACK)
                self.data_path.latch_sp(Signal.SEL_SP_PREV)
                self.step = 0
                self.tick()
                return

        if opcode == Opcode.JN:
            if self.step == 0:
                self.data_path.signal_latch_negative_flag()
                self.data_path.latch_tos(Signal.SEL_TOS_STACK)
                self.data_path.latch_sp(Signal.SEL_SP_PREV)
                self.step = 1
                self.tick()
                return
            if self.step == 1:
                if self.data_path.flags["N"]:
                    self.latch_pc(Signal.SEL_PC_TOS)
                else:
                    self.latch_pc(Signal.SEL_PC_NEXT)
                self.data_path.latch_tos(Signal.SEL_TOS_STACK)
                self.data_path.latch_sp(Signal.SEL_SP_PREV)
                self.step = 0
                self.tick()
                return

        if opcode == Opcode.LIT:
            self.data_path.CU_arg = instr["arg"]
            self.data_path.latch_sp(Signal.SEL_SP_NEXT)
            self.data_path.signal_latch_stack()
            self.data_path.latch_tos(Signal.SEL_TOS_CU_ARG)
            self.latch_pc(Signal.SEL_PC_NEXT)
            self.step = 0
            self.tick()
            return
        if opcode == Opcode.CALL:
            self.latch_scp(Signal.SEL_SCP_NEXT)
            self.latch_pc(Signal.SEL_PC_TOS)
            self.data_path.latch_tos(Signal.SEL_TOS_STACK)
            self.data_path.latch_sp(Signal.SEL_SP_PREV)
            self.step = 0
            self.tick()
            return
        if opcode == Opcode.RET:
            self.latch_pc(Signal.SEL_PC_RET)
            self.latch_scp(Signal.SEL_SCP_PREV)
            self.step = 0
            self.tick()
            return

        if opcode == Opcode.LOAD:
            if self.step == 0:
                self.data_path.signal_latch_data_address()
                self.step = 1
                self.tick()
                return
            if self.step == 1:
                self.data_path.latch_tos(Signal.SEL_TOS_MEM)
                self.latch_pc(Signal.SEL_PC_NEXT)
                self.step = 0
                self.tick()
                return

        if opcode == Opcode.STORE:
            if self.step == 0:
                self.data_path.signal_latch_data_address()
                self.data_path.latch_tos(Signal.SEL_TOS_STACK)
                self.data_path.latch_sp(Signal.SEL_SP_PREV)
                self.step = 1
                self.tick()
                return
            if self.step == 1:
                self.data_path.signal_memory_store()
                self.data_path.latch_tos(Signal.SEL_TOS_STACK)
                self.data_path.latch_sp(Signal.SEL_SP_PREV)
                self.latch_pc(Signal.SEL_PC_NEXT)
                self.step = 0
                self.tick()
                return

        if opcode == Opcode.IN:
            self.data_path.CU_arg = instr["arg"]
            self.data_path.latch_sp(Signal.SEL_SP_NEXT)
            self.data_path.signal_latch_stack()
            self.data_path.latch_tos(Signal.SEL_TOS_IN)
            self.latch_pc(Signal.SEL_PC_NEXT)
            self.step = 0
            self.tick()
            print(self.data_path.stack[0:5], self.data_path.tos)
            return

        if opcode == Opcode.OUT:
            self.data_path.CU_arg = instr["arg"]
            assert 1 <= self.data_path.CU_arg <= 7, f"OUT supports ports 1–7. Got port={self.data_path.CU_arg}"
            self.data_path.signal_write_port()
            self.data_path.latch_tos(Signal.SEL_TOS_STACK)
            self.data_path.latch_sp(Signal.SEL_SP_PREV)
            self.latch_pc(Signal.SEL_PC_NEXT)
            self.step = 0
            self.tick()
            return
        if opcode in {Opcode.ADD, Opcode.SUB, Opcode.MUL, Opcode.DIV, Opcode.OR, Opcode.AND, Opcode.XOR, Opcode.MULH}:
                self.data_path.signal_alu_binary(opcode)
                self.data_path.latch_sp(Signal.SEL_SP_PREV)
                self.data_path.latch_tos(Signal.SEL_TOS_ALU)
                self.latch_pc(Signal.SEL_PC_NEXT)
                self.step = 0
                self.tick()
                return

        if opcode in {Opcode.INC, Opcode.DEC, Opcode.NOT}:
            if self.step == 0:
                self.data_path.signal_alu(opcode)
                self.data_path.latch_tos(Signal.SEL_TOS_ALU)
                self.latch_pc(Signal.SEL_PC_NEXT)
                self.step = 0
                self.tick()
                return
        if opcode == Opcode.NOP:
            self.latch_pc(Signal.SEL_PC_NEXT)
            self.step = 0
            self.tick()
            return
        if opcode==Opcode.DUP:
            self.data_path.latch_sp(Signal.SEL_SP_NEXT)
            self.data_path.signal_latch_stack()
            self.latch_pc(Signal.SEL_PC_NEXT)
            self.step = 0
            self.tick()
            return
        if opcode==Opcode.SWAP:
            self.data_path.stack_swap()
            self.latch_pc(Signal.SEL_PC_NEXT)
            self.step = 0
            self.tick()
            pass
        if opcode == Opcode.DROP:
            self.data_path.latch_tos(Signal.SEL_TOS_STACK)
            self.data_path.latch_sp(Signal.SEL_SP_PREV)
            self.latch_pc(Signal.SEL_PC_NEXT)
            self.step = 0
            self.tick()
            return

    def __repr__(self):
        state_repr = "STATE: {}\tTICK: {:3} PC: {:3}/{} ADDR: {:3} MEM_OUT: {:3} TOS: {:3} SP: {:3}".format(
            self.state,
            self._tick,
            self.pc,
            self.step,
            self.data_path.data_address,
            self.data_path.data_memory[self.data_path.data_address],
            self.data_path.tos,
            self.data_path.stack_pointer,

        )

        instr = self.program[self.pc]
        opcode = instr["opcode"]
        instr_repr = str(opcode)
        if "arg" in instr:
            instr_repr += "{}".format(instr["arg"])

        instr_hex = f"{hex(instr_to_bytes(instr))}"

        return "{}\t {:3}\t {}".format(state_repr, instr_repr, instr_hex)


def simulation(code, data, handler_addr,schedule,limit):
    Io_Controller = IOController({0: list(), 1:list(), 2:list()})
    dataPath = DataPath(data,25, Io_Controller)
    control_Unit = Control_Unit(code, dataPath, 10, schedule, handler_addr)
    logging.debug("%s", control_Unit)
    try:
        while control_Unit._tick < limit:
            control_Unit.decode_and_execute_instruction()
            logging.debug("%s", control_Unit)
    except EOFError:
        logging.warning("Input buffer is empty!")
    except StopIteration:
        pass
    if control_Unit._tick >= limit:
        logging.warning("Limit exceeded!")
    logging.info("output_buffer: %s", repr("".join(Io_Controller.io_ports[1])))
    return "".join(Io_Controller.io_ports[1]), control_Unit._tick

def read_input_schedule(filename):
    schedule = dict()
    with open(filename) as f:
        for line in f:
            tick, port, value = line.strip().split()
            if value == "\\0":
                value = 0
            else:
                value = ord(value)
            tick, port = int(tick), int(port)
            schedule[tick] = [port,value]
    return schedule
def main(code_file,data_file, input_file=None):
    code, handl_addr = from_bytes_to_instructions(code_file)
    data = from_bytes_to_data(data_file)
    if input_file is not None:
        schedule = read_input_schedule(input_file)
    else:
        schedule = dict()
    output, ticks = simulation(code,data,handl_addr,schedule,3000)
    print("".join(output))
    print("ticks:", ticks)
if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    if len(sys.argv) >= 4:
        main(sys.argv[1], sys.argv[2],sys.argv[3])
    else:
        main(sys.argv[1],sys.argv[2])