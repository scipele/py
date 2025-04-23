import os

def get_pipe_od(nom_dia):
    pipe_lookup = {
        0.125: 0.405, 
        0.25: 0.54,
        0.375: 0.675,
        0.5: 0.84,
        0.75: 1.05,
        1: 1.315,
        1.25: 1.66,
        1.5: 1.9,
        2: 2.375,
        2.5: 2.875,
        3: 3.5,
        3.5: 4,
        4: 4.5,
        4.5: 5,
        5: 5.563,
        6: 6.625,
        7: 7.625,
        8: 8.625,
        9: 9.625,
        10: 10.75,
        12: 12.75,
        14: 14,
        16: 16,
        18: 18,
        20: 20,
        22: 22,
        24: 24,
        26: 26,
        28: 28,
        30: 30,
        32: 32,
        34: 34,
        36: 36
    }
    return pipe_lookup.get(nom_dia)    

if __name__ == "__main__":
    
    os.system("cls")
    pipe_diameters = (0.75,1,1.5,2,3,4,6,8,10,12)
    print('Listing of Pipe Diameters:')
    print('+-------------+-------------+')
    print('|   nom_dia   |   pipe_od   |')
    print('+-------------+-------------+')
    for nom_dia in pipe_diameters:
        pipe_od = get_pipe_od(nom_dia)
        print(f"|    {nom_dia:<8} |    {pipe_od:<9.2f}|")
    print('+-------------+-------------+')
