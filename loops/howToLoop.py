# sample loops

def ex_for_each(fruits):
    print('This is an example for each loop:')
    for fruit in fruits:
        print('    ', fruit)
    print('\n')

def ex_loop_with_index(fruits):
    print('This is an example for each loop with an enumerated index:')
    for indx, fruit in enumerate(fruits):
        print('Index:', indx, 'fruit type:', fruit)

def ex_while():
    print('This is an example for each loop:')
    count = 0
    while count < 5:
        print(count)
        count += 1

if __name__ == "__main__":
    fruits = ['apple', 'orange', 'pear', 'bananna']
    ex_for_each(fruits)
    ex_loop_with_index(fruits)
    ex_while()    