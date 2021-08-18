#!/usr/bin/env python3

from gist_function import *
from sys import argv

p_size=int(argv[1])
print(p_size)

with pexpect.spawn(f"ssh -o \'StrictHostKeyChecking=no\' {tac_username}@192.168.2.26") as cli:
    good_ip=[]
    bad_ip=0 
    result={}
    jun_logon(cli)  
    with open ("loopbacks.txt", "r") as loopback:   
        for line in loopback: 
            ip_remote=line.split("/") 
            ip_remote=ip_remote[0] 
            for p_length in range(1470,p_size,2):
                print(f"ping {ip_remote} size {p_length}")
                cli.sendline(f"ping {ip_remote} size {p_length} count 5 rapid ")   
                match=cli.expect(["0 packets received","5 packets received"]) 
                if match==1:
                    continue   
                else:
                    result[ip_remote]=p_length
                    break
            cli.expect(["> $", pexpect.TIMEOUT, pexpect.EOF]) 
            continue 
        #print("\n".join(result))      
        for item in result: print(f"{item}  {result[item]} bytes failed")
        print(40*"#")
        print("Total failed:",len(result))
