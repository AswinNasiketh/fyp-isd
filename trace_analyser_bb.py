#Basic Block Sequence Identifier

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

with open('sim.trace', 'r') as reader:
    line = reader.readline()

    fields = line.split() #splits line into list, delimiter is spaces by default

    opcode = fields[3]

    
