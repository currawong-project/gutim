import json


if __name__ == "__main__":

    char_codeL = [ 'a','b','c']

    tocL = []
    for char_code in char_codeL:
        fn = f"gutim_2/{char_code}/output/caw_toc.json"

        with open(fn) as f:
            tocL += json.load(f)

            
    tocL = sorted(tocL,key=lambda x:(x['beg_meas_num'],x['piano']))

    with open("cheat_sheet.txt","w") as f:
        for x in tocL:
        
            # print(f"m{x['beg_meas_num']} to {x['end_meas_num']} : piano:{x['piano']} {x['player']}",end=" ")
            # for sect in x['sectL']:
            #    print(sect,end=" ")
            # print("")

            name = {"AK":"Asi","HC":"Han","AG":"Ars","NN":"Nic","EP":"Eli","SP":"Spi"}[x['player']]
            meas = x['beg_meas_num']

            
            f.write(f"{name} {x['piano']} {meas}\n")
