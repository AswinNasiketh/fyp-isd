class AccleratedSequence:
    def __init__(self, branch_address, branch_target_addr):
        self.branch_address = branch_address
        self.branch_target_addr = branch_target_addr
        self.hits = 0
        
    def shift_num_hits_right(self):
        self.hits = self.hits >> 1

    def increment_hits(self):
        self.hits += 1

class SequenceSelector:
    def __init__(self, num_accelerators, bprof_size):
        self.num_accelerators = num_accelerators
        self.accelerating_sequences = [AccleratedSequence("0", "0") for i in range(self.num_accelerators)]
        self.hit_saturate_limit = 16
        self.bprof_size = bprof_size
    
    def shift_hits_right(self):
        for seq in self.accelerating_sequences:
            seq.shift_num_hits_right()
        
    def update_accelerated_sequences(self, trace_line, branch_profile, seq_profiles):

        instr_addr = trace_line.split()[0].split("=")[-1]

        #measuring hits for currently accelerated sequences
        for seq in self.accelerating_sequences:
            if seq.branch_address == instr_addr:
                seq.increment_hits()

                if seq.hits >= self.hit_saturate_limit:
                    self.shift_hits_right()
                
                break
        
        self.accelerating_sequences.sort(key= lambda s: s.hits, reverse=True)
        
        top_branches = branch_profile.get_n_most_executed_branches(self.bprof_size)

        branch_addresses = [b.branch_instr_addr for b in top_branches]
        #calculated advantage of accelerating a particular sequence
        acc_advantage = []
        for addr in branch_addresses:
            acc_advantage.append((addr, seq_profiles[addr].cpu_time - seq_profiles[addr].acc_time))
        
        acc_advantage.sort(key= lambda x: x[1], reverse=True)
        #trim accerating sequences to number of available accelerators
        acc_advantage = acc_advantage[0:self.num_accelerators]
        #extract branch instruction addresses
        seqs_to_accelerate = [prof[0] for prof in acc_advantage]
        acc_seq_addresses = [s.branch_address for s in self.accelerating_sequences]

        #find list of new sequences to accelerate 
        new_seqs_to_accelerate = list(set(seqs_to_accelerate) - set(acc_seq_addresses))
        new_seq_branch_targets = {}

        #identify branch targets for accelerating sequences
        for new_seq in new_seqs_to_accelerate:
            for branch in top_branches:
                if branch.branch_instr_addr == new_seq:
                    new_seq_branch_targets[new_seq] = branch.branch_target

        #replacing accelerating sequences
        for count, new_seq_addr in enumerate(new_seqs_to_accelerate):
            new_acc_seq = AccleratedSequence(new_seq_addr, new_seq_branch_targets[new_seq_addr])
            # print("New Sequence Starting at:", new_seq_addr)
            # print("Replaces Sequence Starting at:", self.accelerating_sequences[-(count+1)].branch_address)
            self.accelerating_sequences[-(count+1)] = new_acc_seq
