from trace_analyser.trace_utils import get_instr_addr
import functools

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
    def __init__(self, max_area, max_accelerators, bprof_size, max_hit_count):
        self.max_area = max_area
        self.max_accelerators = max_accelerators
        self.accelerating_sequences = [AccleratedSequence("0", "0") for i in range(self.max_accelerators)]
        self.hit_saturate_limit = max_hit_count
        self.bprof_size = bprof_size
    
    def shift_hits_right(self):
        for seq in self.accelerating_sequences:
            seq.shift_num_hits_right()

    def update_hits(self, trace_line):
        instr_addr = get_instr_addr(trace_line)

        for seq in self.accelerating_sequences:
            if seq.branch_address == instr_addr:
                seq.increment_hits()

                if seq.hits >= self.hit_saturate_limit:
                    self.shift_hits_right()                
                break

    
    def caclulate_advantage(self, seq_profile):
        return seq_profile.cpu_time - seq_profile.acc_time

    def calculate_improvement(self, seq_profile, hits):
        return self.caclulate_advantage(seq_profile) * hits

    def get_replacement_seqs(self, branch_profile, seq_profiles):
        top_branches = branch_profile.get_n_most_executed_branches(self.bprof_size)
        acceleration_advantages = list(map(lambda b: (b.branch_instr_addr, self.caclulate_advantage(seq_profiles[b.branch_instr_addr])), top_branches)) #calculate advantage of accelerating each identified seq, store in tuple with its address
        acceleration_advantages.sort(key= lambda a: a[1], reverse=True)#put in descending order of advantages
        
        if len(acceleration_advantages) > self.max_accelerators:
            acceleration_advantages = acceleration_advantages[0:self.max_accelerators]# trim to maximum number of accelerators allowed
        acc_seq_addrs = [seq.branch_address for seq in self.accelerating_sequences]
        return [addr for addr, adv in acceleration_advantages if addr not in acc_seq_addrs]

    def calculate_improvement_diff(self, rep_seq, seq_profiles, branch_profile, current_acc_improvements):
        area_cost = seq_profiles[rep_seq].area_cost
        improvement_gain = self.calculate_improvement(seq_profiles[rep_seq], branch_profile.get_entry_for_addr(rep_seq).num_branch_taken)

        current_area_usage = functools.reduce(lambda area, acc_seq: area + seq_profiles[acc_seq.branch_address].area_cost, self.accelerating_sequences, 0)
        remaining_area = self.max_area - current_area_usage
        extra_area_required = area_cost - remaining_area

        improvement_loss = 0
        num_accs_to_replace = 0
        if extra_area_required <= 0:
            num_accs_to_replace = 1 #if we don't require any extra area, then there should be a dummy accelerator taking up the unused space => fill that one 
        while extra_area_required > 0 and num_accs_to_replace < self.max_accelerators:
            improvement_loss += current_acc_improvements[num_accs_to_replace][1]
            extra_area_required -= seq_profiles[current_acc_improvements[num_accs_to_replace][0]].area_cost
            num_accs_to_replace += 1
        
        if extra_area_required > 0:
            return num_accs_to_replace, -1 #negative result will be disregarded in next step 
            #todo:in reality, careful tuning of max backward branch displacement is required
        else:
            return num_accs_to_replace, improvement_gain - improvement_loss

    def get_sorted_current_improvements(self, seq_profiles):
        current_acc_improvements = list(map(lambda s: (s.branch_address, self.calculate_improvement(seq_profiles[s.branch_address], s.hits)), self.accelerating_sequences))

        current_acc_improvements.sort(key=lambda x: x[1])

        return current_acc_improvements

    def calculate_improvement_diffs(self, rep_seqs, branch_profile, seq_profiles):
        current_acc_improvements = self.get_sorted_current_improvements(seq_profiles)

        imp_diffs = []
        for addr in rep_seqs:
            num_accs_to_replace, imp_diff = self.calculate_improvement_diff(addr, seq_profiles, branch_profile, current_acc_improvements)
            if imp_diff > 0:
                imp_diffs.append((addr, num_accs_to_replace, imp_diff))

        return imp_diffs

    def replace_accelerator(self, current_acc_branch_address, new_acc):
        # print("replacing:", current_acc_branch_address, "with:", new_acc.branch_address)
        for i, acc in enumerate(self.accelerating_sequences):
            if acc.branch_address == current_acc_branch_address:
                self.accelerating_sequences[i] = new_acc
                break


    def add_accelerator(self, best_seq_to_acc, num_accs_to_replace, branch_profile, seq_profiles):
        # print("Adding accelerator for seq at:", best_seq_to_acc, "Replacing", num_accs_to_replace, "accelerators")
        current_acc_improvements = self.get_sorted_current_improvements(seq_profiles)
        # print(current_acc_improvements)

        dummy_accelerator = AccleratedSequence("0", "0")

        for i in range(num_accs_to_replace - 1):
            self.replace_accelerator(current_acc_improvements[i][0], dummy_accelerator)

        new_accelerator_bprof = branch_profile.get_entry_for_addr(best_seq_to_acc)
        new_acc = AccleratedSequence(best_seq_to_acc, new_accelerator_bprof.branch_target)
        new_acc.hits = new_accelerator_bprof.num_branch_taken

        self.replace_accelerator(current_acc_improvements[num_accs_to_replace - 1][0], new_acc)


    def update_accelerated_sequences(self, trace_line, branch_profile, seq_profiles):
        # print("New line")
        self.update_hits(trace_line)

        rep_seqs = self.get_replacement_seqs(branch_profile, seq_profiles)
        improvement_diffs = self.calculate_improvement_diffs(rep_seqs, branch_profile, seq_profiles)
        # print(len(improvement_diffs))
        #iterates until no further improvements can be made
        while len(improvement_diffs) > 0:
            best_seq_to_acc, num_accs_to_replace, _ = max(improvement_diffs, key= lambda x: x[2])
            self.add_accelerator(best_seq_to_acc, num_accs_to_replace, branch_profile, seq_profiles)

            rep_seqs = self.get_replacement_seqs(branch_profile, seq_profiles)
            improvement_diffs = self.calculate_improvement_diffs(rep_seqs, branch_profile, seq_profiles)