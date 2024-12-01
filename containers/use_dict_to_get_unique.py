import os

def get_unique_list(orig_list):

    # Create an empty dictionary to track unique items
    dict = {}
    
    # read the names into the dict if they are not
    for item in orig_list:
        if item not in dict:
            dict[item] = ''
    return sorted(dict.keys())

if __name__ == "__main__":
    
    os.system("cls")
    names_with_dups = ('bob','larry','sam','tim','tony','sally','bob')
    unique_names = get_unique_list(names_with_dups)
    print(unique_names)


    