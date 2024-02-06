import tkinter as tk
from time import sleep

if __name__ == '__main__':
    window = tk.Tk()
    window.title("EVE Online Live Combat Log")
    window.wm_attributes("-topmost", 1)

    f1 = tk.Frame(window, width=300, height=64, bg="red")
    f2 = tk.Frame(window, width=300, height=64, bg="blue")
    f3 = tk.Frame(window, width=300, height=64, bg="green")
    f4 = tk.Frame(window, width=300, height=64, bg="yellow")

    f1.pack(fill=tk.X)
    f2.pack(fill=tk.X)
    f3.pack(fill=tk.X)
    f4.pack(fill=tk.X)

    window.mainloop()
