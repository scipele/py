#| Item	        | Documentation Notes                                         |
#|--------------|-------------------------------------------------------------|
#| Filename     | flashCard.py                                                |
#| EntryPoint   | __main__                                                    |
#| Purpose      | compute estimate work hours for various                     |                   
#| Inputs       | varies                                                      |                                                                         
#| Outputs      | number of work hours                                        |                                                           
#| Dependencies | random, csv, tkinter                                        |                                     
#| By Name,Date | T.Sciple, 11/28/2024                                        |                                                           


import random
import csv
import tkinter as tk


def read_flashcards(filename):
    flashcards = []
    with open(filename, "r") as f:
        reader = csv.reader(f, delimiter='|')
        for row in reader:
            flashcards.append(tuple(row))
    return flashcards


def display_flashcard(flashcard, window, flashcards):
    label = tk.Label(window, text=flashcard[0], font=("TkDefaultFont", 16))
    label.pack()
    if len(flashcard) > 2:
        additional_label = tk.Label(window, text=flashcard[2:], font=("TkDefaultFont", 16))
        additional_label.pack(pady=5)
    answer_label = tk.Label(window, text=flashcard[1], font=("TkDefaultFont", 16), relief="sunken", width=600, height=5, wraplength=60*10)
    answer_button = tk.Button(window, text="Show Answer", command=lambda: reveal_answer(answer_label), width=20)
    answer_button.pack(pady=5)
    answer_label.pack_forget()
    if flashcards:
        next_button = tk.Button(window, text="Next Clue", command=lambda: clear_and_display(flashcards, window))
        next_button.pack(pady=5)


def reveal_answer(answer_label):
    answer_label.pack(pady=5)


def clear_and_display(flashcards, window):
    for widget in window.winfo_children():
        widget.destroy()
    if flashcards:
        flashcard = random.choice(flashcards)
        flashcards.remove(flashcard)
        display_flashcard(flashcard, window, flashcards)


def display_flashcards(flashcards):
    window = tk.Tk()
    window.title("Clue")
    window.geometry("800x400")
    window.minsize(800, 400)

    if flashcards:
        flashcard = random.choice(flashcards)
        flashcards.remove(flashcard)
        display_flashcard(flashcard, window, flashcards)
    window.mainloop()


if __name__ == "__main__":
    flashcards = read_flashcards("c:/temp/flashcards.txt")
    display_flashcards(flashcards)