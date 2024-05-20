#!/usr/bin/python3
import numpy as np
import cv2
import math
import ht301_hacklib
import utils
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

draw_temp = False

class App(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.root = master

        self.cap = ht301_hacklib.HT301()

        self.grid()
        self.imgLabel = ttk.Label(self, image=None)
        self.imgLabel.grid(column=0, row=1)
        self.metaLabel = ttk.Label(self, text="meta", font=("Courier", 10))
        self.metaLabel.grid(column=1, row=1)
        ttk.Button(self, text="Quit", command=root.destroy).grid(column=0, row=3)
        root.after(10, self.show_frame)
        self.bind("<KeyPress>", self.keydown)
        self.bind("<KeyRelease>", self.keyup)
        # https://forums.raspberrypi.com/viewtopic.php?t=149791#p985220
        self.focus_set()

        self.prev_meta = None
        self.history = []
        #self.calibrate = -1
        self.calibrate = 0  # We start with calibration anyway.
        self.calibration_image = None

    def show_frame(self):
        ret, frame = self.cap.read()
        info, lut = self.cap.info()
        frame = frame.astype(np.float32)

        frame_min = frame.min()
        frame_max = frame.max()
        if self.calibrate == 15:
            # frames 1..24 were with shutter closed in my test
            self.calibration_image = frame.copy()
            #print("saving calibration image, %s" % (frame[0][0]))
        if True and self.calibration_image is not None:
            a = frame[0][0]
            frame -= self.calibration_image
            #print("%s - %s = %s" % (a, self.calibration_image[0][0], frame[0][0]))
        frame_min2 = frame.min()
        frame_max2 = frame.max()
        if True:
            # Sketchy auto-exposure
            frame -= frame.min()
            frame /= max(1, frame.max())
        frame = (np.clip(frame, 0, 1)*255).astype(np.uint8)
        frame = cv2.applyColorMap(frame, cv2.COLORMAP_JET)

        if draw_temp:
            utils.drawTemperature(frame, info['Tmin_point'], info['Tmin_C'], (55,0,0))
            utils.drawTemperature(frame, info['Tmax_point'], info['Tmax_C'], (0,0,85))
            utils.drawTemperature(frame, info['Tcenter_point'], info['Tcenter_C'], (0,255,255))

        # https://pyimagesearch.com/2016/05/23/opencv-with-tkinter/
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.cv_frame = frame
        frame = Image.fromarray(frame)
        frame = frame.resize((frame.width*2, frame.height*2))
        frame = ImageTk.PhotoImage(frame)
        self.imgLabel.image = frame
        self.imgLabel.configure(image=frame)

        if 0 <= self.calibrate <= 30:
            cv2.imwrite(time.strftime("%Y-%m-%d_%H:%M:%S") + ("_calib%02d" % self.calibrate) + '.png', self.cv_frame)
        if self.calibrate >= 0:
            self.calibrate += 1

        s = ""
        i = 0
        per_line = 24
        s += "     "
        for j in range(0, per_line):
            s += " %4d" % j
        s += "\n"
        for x in self.cap.meta:
            for j in range(0, len(x), per_line):
                s += "%04x:" % (2*i)
                for k in range(j, min(j+per_line, len(x))):
                    s += " %04x" % x[k]
                    i += 1
                if len(x) < j+per_line:
                    for k in range(len(x), j+per_line):
                        s += "     "
                s += " | "
                for k in range(j, min(j+per_line, len(x))):
                    a = x[k] & 0xff
                    if chr(a) >= ' ':
                        s += chr(a)
                    else:
                        s += "."
                    a = (x[k] >> 8) & 0xff
                    if chr(a) >= ' ':
                        s += chr(a)
                    else:
                        s += "."
                s += "\n"
        s += "min: %f\nmax: %f\n" % (frame_min, frame_max)
        s += "min: %f\nmax: %f\n" % (frame_min2, frame_max2)
        s += "meta[0] = 0:%d, 1:%d, 16:%d\n" % (self.cap.meta[0][0], self.cap.meta[0][1], self.cap.meta[0][16])
        s += "meta[1] = 0:%d, 1:%d\n" % (self.cap.meta[1][0], self.cap.meta[1][1])
        s += "\n".join(self.history[-3:])
        self.metaLabel.text = s
        self.metaLabel.configure(text=s)

        if self.prev_meta is not None:
            for y in range(len(self.cap.meta)):
                prev = self.prev_meta[y]
                curr = self.cap.meta[y]
                for x in range(len(curr)):
                    if prev[x] != curr[x] and (y,x) not in ((0,0), (0,1)):
                        msg = "meta[%d][%d] changed from 0x%04x=%d to 0x%04x=%d" % (y, x, prev[x], prev[x], curr[x], curr[x])
                        print(msg)
                        self.history.append(msg)
        self.prev_meta = self.cap.meta

        root.after(10, self.show_frame)

    def keydown(self, e):
        if e.char == 'q':
            self.root.destroy()
        elif e.char == 'u':
            self.cap.calibrate()
            self.calibrate = 0
        elif e.char == 's' or e.char == 'w':
            cv2.imwrite(time.strftime("%Y-%m-%d_%H:%M:%S") + '.png', self.cv_frame)
    def keyup(self, e):
        pass

try:
    root = tk.Tk()
    myapp = App(root)
    myapp.mainloop()
finally:
    try:
        myapp.cap.release()
    except:
        pass
    root.destroy()
