from enum import Enum, auto
class Signal(str, Enum):
    SEL_TOS_STACK = auto()
    SEL_TOS_ALU = auto()
    SEL_TOS_CU_ARG = auto()
    SEL_TOS_IN  = auto()
    SEL_SP_PREV = auto()
    SEL_SP_NEXT = auto()
    SEL_TOS_SYNC = auto()
    SEL_TOS_MEM = auto()
    SEL_PC_INT = auto()
    SEL_PC_NEXT = auto()
    SEL_PC_TOS = auto()
    SEL_PC_RET = auto()
    SEL_SCP_PREV = auto()
    SEL_SCP_NEXT = auto()
class ProcessorState(Enum):
    NORMAL = 0
    INTERRUPTION = 1