
from trace_analyser.trace_utils import get_base_instr
#todo: needs to be updated with correct values of taiga cpu
fetch_latency = 1
decode_issue_latency = 2

CPU_CLK_FREQ = 1000000 #1MHz
RECONF_TIME_PER_FRAME = 0.000010
FRAMES_PER_FU = 3 #todo: replace with a dictionary with actual frames per FU
RECONF_START_PENALTY = 0.000100

#*instruction list from https://www.cl.cam.ac.uk/teaching/1617/ECAD+Arch/files/docs/RISCVGreenCardv8-20151013.pdf
#* mappings are guesses

#*mapping from instruction to functional unit for accelerator
ins2funcacc = {
    #*RV64I
    "lb": "ls",
    "lh": "ls",
    "lw": "ls",
    "ld": "ls",
    "lbu": "ls",
    "lhu": "ls",
    "lwu": "ls",
    "ldu": "ls",
    "sb": "ls",
    "sh": "ls",
    "sw": "ls",
    "sd": "ls",
    "fld": "ls",
    "fsd": "ls",
    "sll": "alu",
    "slli": "alu",
    "srli": "alu",
    "srl": "alu",
    "sra": "alu",
    "srai": "alu",
    "sllw": "alu",
    "slliw": "alu",
    "srliw": "alu",
    "srlw": "alu",
    "sraw": "alu",
    "sraiw": "alu",
    "slld": "alu",
    "sllid": "alu",
    "srlid": "alu",
    "srld": "alu",
    "srad": "alu",
    "sraid": "alu",
    "add": "alu",
    "addi": "alu",
    "sub": "alu",
    "lui": "alu",
    "auipc": "alu",
    "addw": "alu",
    "addiw": "alu",
    "subw": "alu",
    "addd": "alu",
    "addid": "alu",
    "subd": "alu",
    "xor": "alu",
    "xori": "alu",
    "or": "alu",
    "ori": "alu",
    "and": "alu",
    "andi": "alu",
    "slt": "alu",
    "slti": "alu",
    "sltu": "alu",
    "sltiu": "alu",
    "beq": "br",
    "bne": "br",
    "blt": "br",
    "bge": "br",
    "bltu": "br",
    "bgeu": "br",
    "jal": "br",
    "jalr": "br",
    "fence": "csr", #todo:unknown unit for this instr
    "fence.i": "csr",
    "scall": "csr",
    "sbreak": "csr",
    "rdcycle": "csr",
    "rdcycleh": "csr",
    "rdtime": "csr",
    "rdtimeh": "csr",
    "rdinstret": "csr",
    "rdinstreth": "csr",
    #*RV64M
    "mul": "mul",
    "mulw": "mul",
    "muld": "mul",
    "mulh": "mul",
    "mulhu": "mul",
    "mulhsu": "mul",
    "div": "div",
    "divw": "div",
    "divd": "div",
    "divu": "div",
    "rem": "div",
    "remu": "div",
    "remw": "div",
    "remuw": "div",
    "remd": "div",
    "remud": "div",
    #*RV64A
    "lr.w": "ls",
    "lr.d": "ls",
    "sc.w": "ls",
    "sc.d": "ls",
    "amoswap.w": "ls",
    "amoadd.w": "ls",
    "amoxor.w": "ls",
    "amoand.w": "ls",
    "amoor.w": "ls",
    "amomin.w": "ls",
    "amomax.w": "ls",
    "amominu.w": "ls",
    "amomaxu.w": "ls",
    "amoswap.d": "ls",
    "amoadd.d": "ls",
    "amoxor.d": "ls",
    "amoand.d": "ls",
    "amoor.d": "ls",
    "amomin.d": "ls",
    "amomax.d": "ls",
    "amominu.d": "ls",
    "amomaxu.d": "ls",
    #*RVC
    "c.lw": "ls",
    "c.lwsp": "ls",
    "c.ld": "ls",
    "c.ldsp": "ls",
    "c.sw": "ls",
    "c.swsp": "ls",
    "c.sd": "ls",
    "c.fld": "ls",
    "c.fsd": "ls",
    "c.sdsp": "ls",
    "c.fldsp": "ls",
    "c.fsdsp": "ls",
    "c.add": "alu",
    "c.addw": "alu",
    "c.addi": "alu",
    "c.addiw": "alu",
    "c.addi16sp": "alu",
    "c.addi4spn": "alu",
    "c.li": "alu",
    "c.lui": "alu",
    "c.mv": "alu",
    "c.sub": "alu",
    "c.slli": "alu",
    "c.beqz": "br",
    "c.bnez": "br",
    "c.j": "br",
    "c.jr": "br",
    "c.jal": "br",
    "c.jalr": "br",
    "c.ebreak": "alu",
    #*RV Privileged
    "csrrw": "csr",
    "csrrs": "csr",
    "csrrc": "csr",
    "csrrwi": "csr",
    "csrrsi": "csr",
    "csrrci": "csr",
    "ecall": "csr",
    "ebreak": "csr",
    "eret": "csr",
    "mrts": "csr",
    "mrth": "csr",
    "hrts": "csr",
    "wfi": "csr",
    "sfence.vm": "csr",
    #*MISC
    "sc.w.aq": "ls"
} 

#*mapping from instruction to functional unit for cpu
ins2funccpu = ins2funcacc

#*mapping of functional units to latency for accelerator
func2latacc = {
    "br": 1,
    "alu":1,
    "csr":2,
    "mul":2,
    "div":34,
    "ls": 4
} 

#*mapping of functional units to latency for cpu (includes fecth->dispatch latency)
func2latcpu = {
    "br": 1 + fetch_latency + decode_issue_latency,
    "alu":1 + fetch_latency + decode_issue_latency,
    "csr":2 + fetch_latency + decode_issue_latency,
    "mul":2 + fetch_latency + decode_issue_latency,
    "div":34 + fetch_latency + decode_issue_latency,
    "ls": 4 + fetch_latency + decode_issue_latency
} 

def get_ins_func_acc(instr):
    if "c." == instr[0:2]:
        if not instr in ins2funcacc.keys():
            instr = instr[2:] #strip compressed instruction prefix
    instr = get_base_instr(instr)
    return ins2funcacc[instr]

def get_ins_lat_acc(instr):
    if "c." == instr[0:2]:
        if not instr in ins2funcacc.keys():
            instr = instr[2:] #strip compressed instruction prefix
    instr = get_base_instr(instr)
    return func2latacc[ins2funcacc[instr]]


def get_ins_lat_cpu(instr):
    if "c." == instr[0:2]:
        if not instr in ins2funccpu.keys():
            instr = instr[2:] #strip compressed instruction prefix

    instr = get_base_instr(instr)
    return func2latcpu[ins2funccpu[instr]]

#todo:in future these dictionaries will be updated with different latencies for accelerator and CPU
#todo:CPU will use full functional unit latencies
#todo:accelerator will only use latencies of part of functional unit responsible for instruction