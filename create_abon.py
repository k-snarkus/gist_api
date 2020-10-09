#!/usr/bin/env python3

from gist_function import  * 
from sys import argv

help_msg='''
**********************************
USAGE:
./create_abon.py $modul_id \n
-a\t\tuse all client subnets (by default affect /24 prefixes only)
-h, --help\tshow this message\n
**********************************'''

flag_list=argv
help_flag=False
all_net_flag=False

if ("-h" in flag_list) or ("help" in flag_list):
    raise SystemExit(help_msg)

if ("-a" in flag_list): all_net_flag=True

try:
    org_id = argv[1]
except IndexError:
    raise SystemExit(help_msg)
if org_id.isdigit() !=True:
    print("\n\nERROR: non-numeric modul_id\n")
    raise SystemExit(help_msg)




def main():
#get  nets
    query=(f"select net from link where id_org='{org_id}' and net like '%/30'")
    link_net=sql_get_data(modul_db,query)
    #select /24 client net
    query=(f"select net from client where id_org='{org_id}' and net like '%/24'")
    if (all_net_flag):
        #select all
        query=(f"select net from client where id_org='{org_id}'")
    client_net=sql_get_data(modul_db,query)
    
    
    def unpack_sql(sql_result):
        sql_result=list(sql_result)
        if len(sql_result) > 0:
            for idx in  range(len(sql_result)):
                sql_result[idx]=sql_result[idx][0] 
        return(sql_result)
    
    link_net=unpack_sql(link_net)
    if len(link_net) > 1:
        print("Too many link nets")
        raise ValueError
    client_net=unpack_sql(client_net)
    nets=link_net+client_net
    #chech for empty array
    ipaddress.ip_network(nets[0])
    #search in routes if exist
    
    net_found=[]   
    for net in nets: 
        query=(f"SELECT net, ip_route, protocol FROM route INNER JOIN uzel ON route.cisco collate utf8_general_ci = uzel.name  collate utf8_general_ci  WHERE (route='S' or route='C') AND valid='1' and net='{net}'") 
        result=sql_get_data(arp_db, query) 
        if len(result) > 0:
            for i in result:
                net_found.append(i)
            #print(net_found)
             
    #get vlan and uzel_addr from modul
    query=(f"select vlan, `uzel`.ip from org inner join uzel on org.uzel=uzel.id where org.id='{org_id}' and actual='1'")
    org_vlan,org_uzel=sql_get_data(modul_db, query)[0]
    #exceptiom for TTK-L3
    if org_uzel=="192.168.2.19":
        print("please use l3 static routes script")
        return()
    if org_vlan.isdigit() != True:
        print("incorrect vlan ID")
        raise ValueError    
    print("INPUT DATA:")
    print(link_net)
    print(client_net)
    print(org_vlan)
    print(org_uzel)
    #check if uzel  changed
    if len(net_found) > 0:
        for net in net_found:
            #print(net)
            if  net[1]!=org_uzel:
                if net[2]=='Juniper':
                    jun_main(net[1], remove=nets)
                elif net[2]=="telnet":
                    cisco_main(net[1], remove=nets)
                #uzel_apply_conf[net]
                pass
            ############
    org_protocol=sql_get_data(arp_db, f"select protocol from  uzel where ip_route='{org_uzel}'")[0][0]
    if org_protocol =='telnet':
        cisco_main(org_uzel, link=link_net, client=client_net, vlan=org_vlan)
    elif org_protocol=='Juniper':
        jun_main(org_uzel, link=link_net, client=client_net, vlan=org_vlan)
main()
