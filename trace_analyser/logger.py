#python module to do all printing so it can easily be redirected to a file output rather than console

#comment next 3 lines if output to console rather than file is required
import sys
sys.stdout = open('log.txt', 'w')
print('Start')

def print_line(*args):
    print_str = ""

    for strPart in args:
        print_str = print_str + str(strPart) + " "
    
    print(print_str)