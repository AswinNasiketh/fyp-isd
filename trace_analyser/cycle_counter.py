#This class will measure the improvement in cycle count
class CycleCounter:

    def __init__(self, num_accelerators):
        self.non_accelerated_cycles = 0
        self.accelerated_cycles = 0


        # self.accelerator_used = [False for i in range(num_accelerators)]

    def count_line(self, trace_line, accelerated_seqs):
        count_in_accelerated = True

        for seq in accelerated_seqs:
            
            pc_addr = int(trace_line.split()[0].split("=")[-1] , base=16)
            range_start = int(seq.branch_target_addr, base=16)
            range_stop = int(seq.branch_address, base=16)

            if pc_addr >= range_start and pc_addr < range_stop:
                count_in_accelerated = False

        self.non_accelerated_cycles += 1
        if count_in_accelerated:
            self.accelerated_cycles += 1

    def print_cycles(self):
        print("Non accelerated cycles", self.non_accelerated_cycles)
        print("Accelerated cycles", self.accelerated_cycles)