

import matplotlib.pyplot as plt

def form_table( bpL ):
    outL = []
    x0,y0 = bpL[0]
    for i in range(1,len(bpL)):
        x1,y1 = bpL[i]

        for x in range(x0,x1):
            frac = (x-x0)/(x1-x0)
            y = y0 + frac * (y1-y0)
            outL.append((x,y))
        x0=x1
        y0=y1

    return [ int(round(y)) for _,y in outL ] 
    

# Your list of 10 numbers (y-axis values)
numbers = [3, 7, 2, 8, 5, 12, 9, 4, 11, 6]

ivory = [ 1,5,10,16,21,26,32,37,42,48,53,58,64,69,74,80,85,90,96,101,106,112,117,122,127]
calced = [1, 1, 1, 4, 4, 4, 4, 6, 6, 6, 6, 9, 9, 9,  9, 10, 10, 11, 12, 13, 14, 14, 15, 15, 17, 19, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 32, 33, 33, 34, 35, 36, 37, 38, 39, 40, 42, 43, 43, 43, 46, 48, 49, 52, 54, 56, 59, 59, 62, 63, 65, 68, 69, 68, 70, 75, 77, 81, 82, 82, 83, 83, 83, 87, 85, 87, 87, 89, 92, 92, 99, 105, 101, 102, 104, 102, 103, 103, 105, 100, 102, 103, 101, 106, 106, 106, 106, 106, 107, 107, 107, 107, 110, 110, 110, 110, 110, 110, 111, 112, 113, 115, 116, 117, 118, 120, 120, 121, 121, 122, 122, 122, 124, 124, 124, 125, 125, 125]
spirio = [1, 1, 2, 2, 3, 5, 8,10,13,16,20,24,28,33,38,43,49,55,62,68,72,85,94,103,112]
spirio_1 = [ 1, 3, 5, 7, 8, 9,12,15,19,21,25,29,31,35,39,43,47,51,55,59,61,67,73,77,80 ]

for mid_point in [65,70,75,80,85]:
    new_vt = form_table([(0,0),(mid_point,100),(127,127)])
    print(f'vt_{mid_point}',new_vt)

line_vt = form_table([(0,0),(127,127)])

if True:
    fig, axs = plt.subplots(2, 2, figsize=(8, 6))

    # Create the line plot
    axs[0,0].plot(ivory, marker='o')
    axs[0,0].set_title('ivory')

    axs[0,1].plot(new_vt)
    axs[0,1].plot(line_vt)
    axs[0,1].set_title('new')

    axs[1,0].plot(spirio, marker='o')
    axs[1,0].set_title('spirio')

    axs[1,1].plot(spirio_1, marker='o')
    axs[1,1].set_title('spirio_1')



# Display the graph
plt.show()
