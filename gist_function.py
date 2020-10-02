#!/usr/bin/env python3
import re
import ipaddress
import time
import pymysql
import pexpect
from private import *

uzel_int_dict={7: 'ge-1/0/0', 8: 'ge-1/0/0', 25: 'ge-1/0/0', 30: 'ge-1/0/0', 39: 'ge-1/1/0', 42: 'ge-1/0/0', 44: 'ge-1/0/9', 45: 'ge-1/0/9', 47: 'ge-1/0/9', 49: 'ge-1/0/9', 50: 'ge-1/1/9', 52: 'ge-1/0/9', 55: 'ge-5/1/1'}

jun_int_dict={'192.168.28.129': 'ge-1/0/0', '192.168.30.128': 'ge-1/0/0', '192.168.64.129': 'ge-1/0/0', '192.168.74.128': 'ge-1/0/0', '192.168.92.129': 'ge-1/1/0', '192.168.100.128': 'ge-1/0/0', '192.168.2.38': 'ge-1/0/9', '192.168.2.42': 'ge-1/0/9', '192.168.2.36': 'ge-1/0/9', '192.168.2.40': 'ge-1/0/9', '192.168.2.35': 'ge-1/1/9', '192.168.2.28': 'ge-5/1/1'}
          
sub_template=('''interface {intf}
encapsulation dot1Q {vlan}
ip vrf forwarding i-net
ip tcp adjust-mss 1432
no snmp trap link-status
no ip proxy-arp
 ip address {ip} {mask} {sec}
exit''')    

add_ip_template=('''interface {intf}
ip tcp adjust-mss 1432
no snmp trap link-status
no ip proxy-arp
 ip address {ip} {mask} sec
exit''')    
  
jun_int_template=('''
set interfaces {intf} unit {vlan} vlan-id {vlan}
set interfaces {intf} unit {vlan} family inet address {addr}''')

def cisco_l3(nets):
    if len(nets)==0:
        return()
    with pexpect.spawn(f"telnet 192.168.2.19") as cli:
        if (cisco_logon(cli)!=True):
            print(f"{uzel_addr} connection failed")
            return
        print("Connected 192.168.2.19")
        add_candidate=[]
        for net in nets:
            net=ipaddress.ip_network(net)
            add_candidate.append(f"ip route vrf i-net {net[0]} {net.netmask} 172.16.14.50")
        cisco_apply_strings(cli, add_candidate)
        print("\n+\t".join(add_candidate))
        cisco_write(cli)
    
          
def sql_get_data(dict_db,sql_query): 
    #print(dict_db['addr'], dict_db['user'], dict_db['pass'], dict_db['db'])
    conn=pymysql.connect(dict_db['addr'], dict_db['user'], dict_db['pass'], dict_db['db'])
    with conn.cursor() as curs: 
        curs.execute(sql_query) 
        result=curs.fetchall() 
    return(result) 


def cisco_main(uzel_addr, link=[], client=[], remove=[], vlan=''):
    try:
        ipaddress.ip_address(uzel_addr)
    except ValueError:
        print("incorrect uzel_ip")
        return()
    print(f"connecting {uzel_addr}...")
    add_candidate=[]
    remove_candidate=[]
    remove_confirmed=[]
    with pexpect.spawn(f"telnet {uzel_addr}") as cli:
        if (cisco_logon(cli)!=True):
            print(f"{uzel_addr} connection failed")
            return
        if len(remove) > 0:
            remove_string=cisco_get_config(cli, remove)
            for idx in range(len(remove_string)):
                if ("secondary" in remove_string[idx])&("ip " in remove_string[idx]):
                    remove_string[idx]=("no "+remove_string[idx][:-10])
                elif "ip " in remove_string[idx]:
                    remove_string[idx]=("no "+remove_string[idx])
            cisco_apply_strings(cli, remove_string)
            print("-\t"+"\n\t".join(remove_string))
            cisco_write(cli)
        if vlan=='':
            return()
        if len(link+client)==0:
            return()
        

        subintf=(cisco_get_phy_port(cli)+'.'+vlan)
        remove_candidate=cisco_get_config(cli, link+client)
        #check for removing  primary ip
        #swap_intf=[]
        for line in remove_candidate:
            if "Gig" in line:
                swap_intf=line
           # if (line in add_candidate)&("ip " in line)&(swap_intf==("interface "+subintf)):
           #     continue
           # if ("ip address" in line)&("second" not in line):
           #     cisco_primary_ip_swap(cli, swap_intf)
            if ("ip " in line)&("sec" in line):
                remove_confirmed.append("no "+line[:-10])
            elif ("ip " in line)&("sec" not in line):
                remove_confirmed.append("no "+line)
            else:
                remove_confirmed.append(line)
        cisco_apply_strings(cli,remove_confirmed)

        ##count ip address on interface
        check_intf=[]
        check_intf=cli_parse_strings(cli,f"sh run int {subintf}" ,'#', 'ip add')
            #check if afready exists

        if len(check_intf)==0:
            #create_new        
            if len(link)>0:
                link_net=ipaddress.ip_network(link[0])
                add_candidate=sub_template.format(intf=subintf, vlan=vlan, ip=link_net[1], mask=link_net.netmask, sec='')
                add_candidate=add_candidate.split('\n')
                for line in client:
                    cl_net=ipaddress.ip_network(line)
                    add_candidate.append(f"ip route vrf i-net {cl_net[0]} {cl_net.netmask} {link_net[2]}")
            else:
                cl_net=ipaddress.ip_network(client[0])
                add_candidate=sub_template.format(intf=subintf, vlan=vlan, ip=cl_net[1], mask=cl_net.netmask, sec='')
                add_candidate=add_candidate.split('\n')
                if len(client) > 1:
                    for net in client:
                        #print(net)
                        if net!=client[0]:
                            add_candidate.insert(-1,f" ip address {ipaddress.ip_network(net)[1]} {ipaddress.ip_network(net).netmask} sec")
        ##add to existing interface
        else: 
            if len(link)>0:
                link_net=ipaddress.ip_network(link[0])
                add_candidate=add_ip_template.format(intf=subintf, ip=link_net[1], mask=link_net.netmask)
                add_candidate=add_candidate.split('\n')
                for line in client:
                    cl_net=ipaddress.ip_network(line)
                    add_candidate.append(f"ip route vrf i-net {cl_net[0]} {cl_net.netmask} {link_net[2]}")
            else:
                add_candidate=[f'interface {subintf}']        
                for net in client:
                    net=ipaddress.ip_network(net)
                    add_candidate.append(f" ip address {net[1]} {net.netmask} secondary")
                add_candidate.append("exit")
                
    
        cisco_apply_strings(cli,add_candidate)
        

        
        print("-"*20+"\n-")
        print("\n-\t".join(remove_confirmed))
        print("\n\n"+"+"*20+"\n+")       
        print("\n+\t".join(add_candidate))

        cisco_write(cli)
        #remove_candidate=cisco_get_config(cli, link+client)
        #print(check_intf)
        #print(remove_candidate)
#        if len(link) > 0
            #check if afready exists
    return()   

def jun_ip_intf(net):
    intf_ip=str(ipaddress.ip_network(net)[1])+net[-3:]
    return(intf_ip) 
    


def jun_main(uzel_addr, link=[], client=[], remove=[], vlan=''):
    try:
        ipaddress.ip_address(uzel_addr)
    except ValueError:
        print("incorrect uzel_ip")
        return()
    print(f"connecting {uzel_addr}...")    
    add_candidate=[]
    remove_candidate=[]
    remove_confirmed=[]
    with pexpect.spawn(f"ssh -o \"StrictHostKeyChecking=no\" {tac_username}@{uzel_addr}") as cli:

        if (jun_logon(cli)!=True):
            print(f"{uzel_addr} connection failed")
            return
        if len(remove) > 0:
            remove_string=jun_get_config(cli, remove)
            for idx in range(len(remove_string)):
                    remove_string[idx]=("delete "+remove_string[idx][3:])
            jun_apply_strings(cli, remove_string)
            print("-\t"+"\n\t".join(remove_string))
        if vlan=='':
            print("no vlan defined!!!\n\nExiting...")
            return()
        if len(link+client)==0:
            return()
        

        #subintf=(cisco_get_phy_port(cli)+'.'+vlan)
        remove_candidate=jun_get_config(cli, link+client)
        subintf=(f'interface {jun_int_dict[uzel_addr]}.{vlan}')
        if (int(vlan)>1499)&(int(vlan)<3000):
            vlan_id=(f'vlan-tags outer 379 inner {vlan}')
        else:
            vlan_id=(f" vlan-id {vlan}")
        
        if len(link)>0:
            link_ip=jun_ip_intf(link[0])
            add_candidate=[(f"set {subintf} family inet address {link_ip}")]
            add_candidate.append(f"set {subintf} {vlan_id}")
            add_candidate.append(f"set routing-instances I-NET {subintf}")
            net_nexthop=ipaddress.ip_network(link[0])[2]
            for line in client:
                cl_net=jun_ip_intf(line)
                add_candidate.append(f"set routing-instances I-NET routing-options static route {line} next-hop {net_nexthop}")
        else:
                add_candidate=[f"set {subintf} {vlan_id}"]
                add_candidate.append(f"set routing-instances I-NET {subintf}")
                
                for net in client:
                    client_ip=jun_ip_intf(net)
                    add_candidate.append(f"set {subintf} family inet address {client_ip}")
#        print(remove_candidate)            
    

        for line in remove_candidate:
            if "set" not in line:
                continue
            if line in add_candidate:
                continue
            remove_confirmed.append("delete "+line[3:])


        
        
        jun_apply_strings(cli,remove_confirmed+add_candidate)

    return()   




def cisco_primary_ip_swap(cli, intf):
    check_intf=cli_parse_strings(cli,f"sh run {intf}" ,'#', 'ip add')
    if len(check_intf) > 1:
        conf_swap=[]
        conf_swap.append(intf)
        conf_swap.append(check_intf[0][:-10])
        conf_swap.append(check_intf[-1]+" sec")
        print(conf_swap)
        cisco_apply_strings(cli, conf_swap)
        return()
    return() 
    
def cisco_apply_strings(conn, conf_strings):
    #data check
    if type(conf_strings) !=list: return()
    if (len(conf_strings) == 0):
        return(False)    
    conn.sendline("conf t")
    time.sleep(1)
    conn.expect("fig\)#")
    for line in conf_strings:
        if "Gi" in line:
            current_intf=line
        conn.sendline(line)
        match=conn.expect(["#","deleting primary"])
        if match==0: 
            print("send  "+line)
            continue
        elif match==1:
            conn.expect("#")
            #print(current_intf)
            swap_ip=cli_parse_strings(conn, f"do sh run {current_intf} | i addr", "#", "ip add")
            #print(swap_ip)
            swap_ip_line=swap_ip[0][:-10]
            conn.sendline(swap_ip_line)
            #print(swap_ip_line)
            conn.expect("#") 
    conn.sendline("end")
    conn.expect("#")
    return()

def cisco_write(conn):
    conn.sendline("copy run start")
    conn.expect("Destination filename")
    conn.sendline("\r\n")
    conn.expect("OK")
    return()
    
       

    
def cisco_logon(ssh):
    ssh.expect("sername:") 
    ssh.sendline(tac_username)
    ssh.expect("assword:") 
    ssh.sendline(tac_pssw) 
    #time.sleep(1)  
    match=ssh.expect(["#", pexpect.TIMEOUT, pexpect.EOF])
    if match==0:
        #print("connected sucsesfully")
        return(True)
    return(False)
      

def jun_apply_strings(ssh, conf_strings):
    #data check
    if type(conf_strings) !=list: 
       return()

    if (len(conf_strings) == 0):
        print("nothing to apply")
        return()
    ssh.sendline("conf private") 
    time.sleep(1)   
    ssh.expect("# $") 
    for line in conf_strings: 
        ssh.sendline(line) 
        ssh.expect("# $") 
        print("send  "+line) 
    ssh.sendline("show| compare") 
    ssh.expect("# $")
    compare_str=ssh.before  
    ssh.sendline("commit and-quit") 
    time.sleep(5) 
    #print(conf_strings) 
    match=ssh.expect(["commit complete","failed"])
    if match== 0:
        print(compare_str.decode(encoding="utf-8"))
        return()
    if match==1:
        print("commit error")
        return(False)
    return ()                

def jun_logon(ssh):
    ssh.expect("assword:")
    ssh.sendline(tac_pssw)
    time.sleep(1)  
    match=ssh.expect(["> $", pexpect.TIMEOUT, pexpect.EOF])
    if match==0:
        print("connected sucsesfully")
        return(True)
    return(False)  



def jun_get_config(cli, nets):
    #data check
    conf_strings=[]
    if type(nets) !=list: 
        return()
    if len(nets)==0:
        return(False)
   
    for net in nets:
  #search static

        command=(f"show configuration routing-instances I-NET routing-options static | display set | match {net}")    
        conf_strings=conf_strings+cli_parse_strings(cli,command,'> $', net)            
        ip_net=ipaddress.ip_network(net)
        
   #search_connected
        command=(f"show route table I-NET.inet.0 protocol direct {net} terse | match {net}")
        intf= cli_parse_regexp(cli,command,"> $", 'ge-[\d/.]*')
        command=(f"sh conf int {intf} | display set | m {ip_net[1]} ")
        conf_strings=conf_strings+cli_parse_strings(cli,command,'> $', f"{str(ip_net[1])}/")
    return(conf_strings)

        
def output_decode(cli_output):
    cli_output=cli_output.decode(encoding="utf-8")
    cli_output=cli_output.splitlines()
    return(cli_output)

def cli_parse_regexp(cli,send_line,prompt,search_line):
    return_line=''
    cli.sendline(send_line)
    cli.expect(prompt)
    result=cli.before
    result=output_decode(result)
    if (len(result) > 0): 
        for line in result:
            try:
                match=re.search(search_line, line)
                return_line=match.group()
                return(return_line)
            except AttributeError:
                continue
    return(False)

def cli_parse_strings(cli, send_line, prompt, search_line):
    return_line=[]
    cli.sendline(send_line)
    cli.expect(prompt)
    result=cli.before
    result=output_decode(result)
    #print(result)
    if (len(result) > 0): 
        for line in result:    
            if (search_line in line):
                return_line.append(line)
        return(return_line)
    return(False)
    
               
def cisco_get_phy_port(cli):
    intf=''
    cli.sendline("sh ip route 0.0.0.0 | i 172")
    cli.expect("#") 
    result=cli.before
    result=output_decode(result)
    match=re.search('[\d\.]+', str(result[1]))
    def_route=match.group()
    cli.sendline(f"sh ip route   {def_route} | i Gi")
    cli.expect("#") 
    result=cli.before
    result=output_decode(result)
    #print(result)
    match=re.search('Gi\w+[\d/]*\d', str(result[1]))
    intf=match.group()
    return(intf)


def cisco_get_config(cli, nets):
    #data check
    conf_strings=[]
    if type(nets) !=list: 
        return()
    if len(nets)==0:
        return(False)
    for net in nets:
   #search static
        net=ipaddress.ip_network(net) 
        command=(f"show run | i {net[0]} ")    
        conf_strings=conf_strings+cli_parse_strings(cli,command,'#', f'{net[0]} 255')           
        ip_net=ipaddress.ip_network(net)
         
    #search_connected
        command=(f"sh ip route vrf i-net connected | i {net[0]}/")
        intf= cli_parse_regexp(cli,command,"#", 'Gi\S+')
        if intf != False:
            command=(f"sh run  int {intf} | i ip address {net[1]} ")
            ip_string=cli_parse_strings(cli, command, "#", f"ip address {net[1]} 255")
            conf_strings.append("interface "+intf)
            conf_strings=conf_strings+ip_string
            conf_strings.append("exit")
    return(conf_strings)
