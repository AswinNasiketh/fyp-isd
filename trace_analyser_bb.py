#Basic Block Sequence Identifier


branches = []

class BranchProfileEntry:

    def __init__(self, instr_addr, target):
        self.branch_instr_addr = instr_addr
        self.branch_target = target
        self.num_branch_taken = 1

    def increment_taken_count(self):
        self.num_branch_taken += 1

def is_branch_cached(addr):
    for branch_profile in branches:
        if branch_profile.branch_instr_addr == addr:
            return branch_profile

    return False

def add_new_branch_profile(instr_addr, target):
    branches.append(BranchProfileEntry(instr_addr, target))


branch_opcodes = [
    'c.j',
    'c.jal',
    'c.jr',
    'c.jalr',
    'c.beqz',
    'c.bnez',
    'jal',
    'jalr',
    'j',
    'beq',
    'bne',
    'blt',
    'bge',
    'bltu',
    'bgeu'
    ]




process_next_iter = False
opcode_next_iter = ""
addr_next_iter = ""
target_next_iter = ""

with open('trace_files/sim3.trace', 'r') as reader:
    for line in reader:
        fields = line.split() #splits line into list, delimiter is spaces by default

        instr_addr = fields[0].split('=')[1] 

        #processing for previous line if required
        if process_next_iter:
            process_next_iter = False
            if opcode_next_iter == "jalr":
                add_new_branch_profile(addr_next_iter, instr_addr)           
           
    
        branch_entry = is_branch_cached(instr_addr)
        if branch_entry != False:
            branch_entry.increment_taken_count()
        else:
            #check if backward branch and add to list
            opcode = fields[1]

            branch_target = ""

            if opcode in branch_opcodes:
                if opcode == "c.jr" or opcode == "c.jalr":
                    branch_target = fields[-1].split('=')[1] #annotated rs1_val
                    add_new_branch_profile(instr_addr, branch_target)
                elif opcode == "jalr":
                    process_next_iter = True
                    opcode_next_iter = opcode
                    addr_next_iter = instr_addr



    
        

    
