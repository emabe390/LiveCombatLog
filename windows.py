import tkinter as tk
from threading import Thread
from time import sleep

from PIL import Image, ImageTk

import character_fetcher
from parser import follow, Line, DamageCombatLine


class Window():
    def __init__(self):

        window = tk.Tk()
        window.title("EVE Online Live Combat Log")
        window.wm_attributes("-topmost", 1)

        f1 = tk.Frame(window, width=64*5, height=64, bg="red")
        self.f1 = f1
        self.row = []
        f2 = tk.Frame(window, width=300, height=64, bg="blue")
        f3 = tk.Frame(window, width=300, height=64, bg="green")
        f4 = tk.Frame(window, width=300, height=64, bg="yellow")

       # self.sf1 = tk.Label(f1, width=64, height=64, bg="pink")
      #  self.sf1.pack(side=tk.LEFT)
        #image = tk.Image.open('cache/images/90014930.png')
        #image = PhotoImage(image)

        self.set_image("cache/images/90014930.png")

        f1.pack(fill=tk.X)
        f2.pack(fill=tk.X)
        f3.pack(fill=tk.X)
        f4.pack(fill=tk.X)

        thread = Thread(target=self.background_thread)
        thread.daemon = True
        thread.start()

        window.mainloop()

    def set_image(self, path):
        img = Image.open(path)
        img = ImageTk.PhotoImage(img)
        sf1 = tk.Label(self.f1, width=64, height=64, bg="pink")
        if self.row:
            sf1.pack(side=tk.LEFT, before=self.row[-1])
        else:
            sf1.pack(side=tk.LEFT)
        self.row.append(sf1)
        while len(self.row) > 5:
            self.row.pop(0).destroy()
        sf1.config(image=img)
        sf1.image = img

    def background_thread(self):
        cache = character_fetcher.Cache.get_instance()
        self.set_image(cache.get_image_path("Freany"))
        sleep(1)
        self.set_image(cache.get_image_path("Garrus Ongrard"))
        sleep(1)
        self.set_image(cache.get_image_path("Clay Snow"))
        sleep(1)
        self.set_image(cache.get_image_path("Clay Snow"))
        sleep(1)
        self.set_image(cache.get_image_path("Clay Snow"))
        sleep(1)
        self.set_image(cache.get_image_path("Clay Snow"))
        filename = "20240206_152435_788408631.txt"
        path = f"C:/Users/Aitesh/Documents/EVE/logs/Gamelogs/{filename}"
        with open(path) as logfile:
            for line in follow(logfile):
                data = Line.parse(line)
                if data.parsed and isinstance(data, DamageCombatLine):
                    print(data.pilot)
                    self.set_image(cache.get_image_path(data.pilot))

if __name__ == '__main__':
    Window().__init__()
