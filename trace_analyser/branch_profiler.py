#Backward Branch Sequence Identifier

#64 bit hexadecimal string to 64 bit signed integer
def hex2sint(hex):
    dec_num = int(hex, base=16)
    if dec_num >= 0x8000000000000000:
        dec_num -= 0x10000000000000000

    return dec_num


class BranchProfileEntry:

    def __init__(self, instr_addr, target):
        self.branch_instr_addr = instr_addr
        self.branch_target = target
        self.num_branch_taken = 1

    def increment_taken_count(self):
        self.num_branch_taken += 1

class BranchProfile:
    def __init__(self):

        
        self.branches = []

        self.branch_opcodes = [
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

        self.process_next_iter = False
        self.addr_next_iter = ""

    def is_branch_cached(self, addr):
        for branch_profile in self.branches:
            if branch_profile.branch_instr_addr == addr:
                return branch_profile

        return False

    def add_new_branch_profile(self, instr_addr, target):
        self.branches.append(BranchProfileEntry(instr_addr, target))

    def process_on_next_line(self, addr):
        self.process_next_iter = True
        self.addr_next_iter = addr

    def process_trace_line(self, line):
        fields = line.split() #splits line into list, delimiter is spaces by default

        instr_addr = fields[0].split('=')[1] 
        # print(instr_addr)

        #processing for previous line if required
        if self.process_next_iter:
            self.process_next_iter = False
            #only add backward branches
            if hex2sint(instr_addr) < hex2sint(self.addr_next_iter):
                self.add_new_branch_profile(self.addr_next_iter, instr_addr)           
               
        branch_entry = self.is_branch_cached(instr_addr)
        if branch_entry != False:
            branch_entry.increment_taken_count()
        else:
            #check if backward branch and add to list
            opcode = fields[1]
            
            if opcode in self.branch_opcodes:
                # print("new instr found opcode:", instr_addr )
                if opcode == "c.j" or opcode == "c.jal" or opcode == "c.jr" or opcode == "c.jalr" or opcode == "jalr" or opcode == "jal" or "j": #unconditional branches
                    self.process_on_next_line(instr_addr)
                elif opcode == "c.beqz":
                    rs1_val = fields[-1].split('=')[1]
                    if rs1_val == 0:
                        self.process_on_next_line(instr_addr)
                
                elif opcode == "c.bnez":
                    rs1_val = fields[-1].split('=')[1]
                    if rs1_val != 0:
                        self.process_on_next_line(instr_addr)
                
                elif opcode == "beq":
                    rs1_val = fields[-2].split('=')[1]
                    rs2_val = fields[-1].split('=')[1]

                    if rs1_val == rs2_val:
                        self.process_on_next_line(instr_addr)
                
                elif opcode == "bne":
                    rs1_val = fields[-2].split('=')[1]
                    rs2_val = fields[-1].split('=')[1]

                    if rs1_val != rs2_val:
                        self.process_on_next_line(instr_addr)

                elif opcode == "blt":
                    rs1_val = fields[-2].split('=')[1]
                    rs2_val = fields[-1].split('=')[1]

                    #by default python converts hex to uint
                    
                    if hex2sint(rs1_val) < hex2sint(rs2_val):
                        self.process_on_next_line(instr_addr)
                elif opcode == "bge":

                    rs1_val = fields[-2].split('=')[1]
                    rs2_val = fields[-1].split('=')[1]
                    
                    if hex2sint(rs1_val) >= hex2sint(rs2_val):
                        self.process_on_next_line(instr_addr)
                
                elif opcode == "bltu":
                    rs1_val = fields[-2].split('=')[1]
                    rs2_val = fields[-1].split('=')[1]
                    
                    if rs1_val < rs2_val:
                        self.process_on_next_line(instr_addr)
    

                elif opcode == "bgeu":
                    rs1_val = fields[-2].split('=')[1]
                    rs2_val = fields[-1].split('=')[1]
                    
                    if rs1_val >= rs2_val:
                        self.process_on_next_line(instr_addr)

    def print_profile(self):
        for entry in self.branches:
            print("Branch Instr Addr:", entry.branch_instr_addr,
            "Branch Target:", entry.branch_target,
            "Number of times taken:", entry.num_branch_taken)

    def dump_profile(self):
        with open("branch.profile", 'w') as writer:
            for entry in self.branches:
                write_string = "Branch Instr Addr: " + entry.branch_instr_addr + ", Branch Target: " + entry.branch_target + ", Number of times taken: " + str(entry.num_branch_taken) + "\n"
                writer.write(write_string)
