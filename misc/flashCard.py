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
    answer_label = tk.Label(window, text=flashcard[1], font=("TkDefaultFont", 16), relief="sunken", width=600, height=5, wraplength=70*10)
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
    window.title("Bible Verses")

    # Set the minimum size (width, height)
    window.wm_minsize(800, 600)  

    # Optionally, set the initial size of the window
    window.geometry("800x600") 

    if flashcards:
        flashcard = random.choice(flashcards)
        flashcards.remove(flashcard)
        display_flashcard(flashcard, window, flashcards)
    window.mainloop()

flashcards = read_flashcards("c:/temp/flashcards.txt")
display_flashcards(flashcards)
