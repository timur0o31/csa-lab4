from enum import Enum, auto
class Signal(Enum,str):
    SEL_TOS_SREG = auto()
    SEL_TOS_ALU = auto()
    SEL_TOS_CU_ARG = auto()
    SEL_TOS_IO = auto()
    SEL_SP_PREV = auto()
    SEL_SP_NEXT = auto()
    SEL_TOS_SYNC = auto()
    SEL_TOS_MEM = auto()