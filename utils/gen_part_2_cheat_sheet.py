import json

top_string = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>CAW</title>
    <script type="text/javascript" src="js/ui.js"></script>
    <link href="css/ui.css" rel="stylesheet">
    <link href="css/caw.css" rel="stylesheet">
    <link href="cheat.css" rel="stylesheet">
     

    <script text="text/javascript">
      window.addEventListener("load",main, false )
    </script>
    
  </head>
  <body>    
"""

bot_string = """

    <div id="appTitleDiv" class="uiRow">
      <p id="appTitleId">CAW:</p>
      <p id="connectTitleId">Disconnected</p>
    </div>

      
  </body>
</html>

"""

def cheat_sheet( tocL ):

    pianoTocD = dict(A=[],B=[],C=[])
    
    for toc in tocL:
        pianoTocD[toc['piano']].append(toc)

    mult = 15
    for piano,tocL in pianoTocD.items():
        tocL = sorted(tocL,key=lambda x:x['beg_meas_num'])
        for x in tocL:
            x['width_pix'] = (x['end_meas_num'] - x['beg_meas_num']) * mult
            x['beg_pix']   = x['beg_meas_num'] * mult
            x['end_pix']   = x['end_meas_num'] * mult


    with open("cheat_sheet.html","w") as f:
        f.write(f"{top_string}\n")
        f.write("<div class=\"cheat_panel\">\n")
        for piano,tocL in pianoTocD.items():
            f.write("  <div class=\"cheat_row\">\n")
            for toc in tocL:
                color = dict(purple='purple',yellow='lightyellow',rose='pink',white='white',blue='lightblue',green='lightgreen')[toc['color']]
                
                f.write(f"""    <div class="cheat_ele" style="left:{toc['beg_pix']}px; width:{toc['width_pix']}px; background-color:{color};">{toc['beg_meas_num']} {toc['player']}</div>\n""")
            f.write("  </div>\n")
        f.write("</div>\n")
        f.write(f"{bot_string}\n")
        



if __name__ == "__main__":

    char_codeL = [ 'a','b','c']

    tocL = []
    for char_code in char_codeL:
        fn = f"gutim_2/{char_code}/output/caw_toc.json"

        with open(fn) as f:
            tocL += json.load(f)

    
    tocL = sorted(tocL,key=lambda x:(x['beg_meas_num'],x['piano']))

    cheat_sheet(tocL)
    
    if False:
        with open("cheat_sheet.txt","w") as f:
            for x in tocL:

                # print(f"m{x['beg_meas_num']} to {x['end_meas_num']} : piano:{x['piano']} {x['player']}",end=" ")
                # for sect in x['sectL']:
                #    print(sect,end=" ")
                # print("")

                name = {"AK":"Asi","HC":"Han","AG":"Ars","NN":"Nic","EP":"Eli","SP":"Spi"}[x['player']]
                meas = x['beg_meas_num']


                f.write(f"{name} {x['piano']} {meas}\n")
