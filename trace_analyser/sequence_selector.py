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
    def __init__(self, num_accelerators):
        self.num_accelerators = num_accelerators
        self.accelerating_sequences = [AccleratedSequence("0", "0") for i in range(self.num_accelerators)]
        self.hit_saturate_limit = 16       
    
    def shift_hits_right(self):
        for seq in self.accelerating_sequences:
            seq.shift_num_hits_right()
        
    def update_accelerated_sequences(self, trace_line, branch_profile):

        instr_addr = trace_line.split()[0].split("=")[-1]

        for seq in self.accelerating_sequences:
            if seq.branch_address == instr_addr:
                seq.increment_hits()

                if seq.hits >= self.hit_saturate_limit:
                    self.shift_hits_right()
                
                break
        
        self.accelerating_sequences.sort(key= lambda s: s.hits, reverse=True)

        top_branches = branch_profile.get_n_most_executed_branches(self.num_accelerators)

        branch_addresses = [b.branch_instr_addr for b in top_branches]
        acc_seq_addresses = [s.branch_address for s in self.accelerating_sequences]

        new_seqs_to_accelerate = list(set(branch_addresses) - set(acc_seq_addresses))
        new_seq_branch_targets = {}

        for new_seq in new_seqs_to_accelerate:
            for branch in top_branches:
                if branch.branch_instr_addr == new_seq:
                    new_seq_branch_targets[new_seq] = branch.branch_target

        for count, new_seq_addr in enumerate(new_seqs_to_accelerate):
            new_acc_seq = AccleratedSequence(new_seq_addr, new_seq_branch_targets[new_seq_addr])
            # print("New Sequence Starting at:", new_seq_addr)
            # print("Replaces Sequence Starting at:", self.accelerating_sequences[-(count+1)].branch_address)
            self.accelerating_sequences[-(count+1)] = new_acc_seq
