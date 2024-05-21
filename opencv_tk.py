#!/usr/bin/python3
import numpy as np
import cv2
import math
import ht301_hacklib
import utils
import time
from skimage.exposure import rescale_intensity, equalize_hist
import pickle
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

def increase_luminance_contrast(frame):
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)

    # Applying CLAHE to L-channel
    # feel free to try different values for the limit and grid size:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)

    # merge the CLAHE enhanced L-channel with the a and b channel
    limg = cv2.merge((cl, a, b))
    frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    return frame

def rotate_frame(frame, orientation):
    if orientation == 0:
        return frame
    elif orientation == 90:
        return np.rot90(frame).copy()
    elif orientation == 180:
        return np.rot90(frame, 2).copy()
    elif orientation == 270:
        return np.rot90(frame, 3).copy()
    else:
        return frame

class App(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.root = master

        self.cap = ht301_hacklib.Camera()

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
        self.delay_to_calibrate = -1
        self.orientation = 0  # 0, 90, 180, 270
        self.draw_temp = False
        self.upscale_factor = 2
        self.verbose_info = True

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
        if False:
            # Sketchy auto-exposure
            frame -= frame.min()
            frame /= max(1, frame.max())
            frame = (np.clip(frame, 0, 1)*255).astype(np.uint8)
            frame = cv2.applyColorMap(frame, cv2.COLORMAP_JET)
        elif True:
            frame = rescale_intensity(
                equalize_hist(frame), in_range="image", out_range=(0, 255)
            ).astype(np.uint8)

            frame = cv2.applyColorMap(frame, cv2.COLORMAP_INFERNO)

        increase_luminance_contrast(frame)

        frame = rotate_frame(frame, self.orientation)

        frame = np.kron(frame, np.ones((self.upscale_factor, self.upscale_factor, 1))).astype(
            np.uint8
        )

        if self.draw_temp:
            utils.drawTemperature(frame, info['Tmin_point'], info['Tmin_C'], (55,0,0))
            utils.drawTemperature(frame, info['Tmax_point'], info['Tmax_C'], (0,0,85))
            utils.drawTemperature(frame, info['Tcenter_point'], info['Tcenter_C'], (0,255,255))

        # https://pyimagesearch.com/2016/05/23/opencv-with-tkinter/
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.cv_frame = frame
        frame = Image.fromarray(frame)
        #frame = frame.resize((frame.width*2, frame.height*2))
        frame = ImageTk.PhotoImage(frame)
        self.imgLabel.image = frame
        self.imgLabel.configure(image=frame)

        if 0 <= self.calibrate <= 30:
            cv2.imwrite(time.strftime("%Y-%m-%d_%H:%M:%S") + ("_calib%02d" % self.calibrate) + '.png', self.cv_frame)
        if self.calibrate >= 0:
            self.calibrate += 1

        if self.delay_to_calibrate >= 0:
            self.delay_to_calibrate -= 1
            if self.delay_to_calibrate == 0:
                self.cap.calibrate()
                self.calibrate = 0

        s = ""
        if self.verbose_info:
            i = 0
            per_line = 24
            s += "     "
            for j in range(0, per_line):
                s += " %4d" % j
            s += "\n"
            meta = self.cap.frame_raw_u16[self.cap.fourLinePara:]
            for j in range(0, len(meta), per_line):
                s += "%04x:" % (2*i)
                for k in range(j, min(j+per_line, len(meta))):
                    s += " %04x" % meta[k]
                    i += 1
                if len(meta) < j+per_line:
                    for k in range(len(meta), j+per_line):
                        s += "     "
                s += " | "
                for k in range(j, min(j+per_line, len(meta))):
                    a = meta[k] & 0xff
                    if chr(a) >= ' ':
                        s += chr(a)
                    else:
                        s += "."
                    a = (meta[k] >> 8) & 0xff
                    if chr(a) >= ' ':
                        s += chr(a)
                    else:
                        s += "."
                s += "\n"
            s += "min: %f\nmax: %f\n" % (frame_min, frame_max)
            s += "min: %f\nmax: %f\n" % (frame_min2, frame_max2)
            s += "meta[0] = 0:%d, 1:%d, 16:%d\n" % (meta[0], meta[1], meta[16])
            s += "meta[1] = 0:%d, 1:%d\n" % (meta[256], meta[257])
        if self.delay_to_calibrate >= 0:
            s += "waiting to calibrate... %d...\n" % self.delay_to_calibrate
        if 0 <= self.calibrate <= 30:
            s += "calibrating...\n"
        if self.verbose_info:
            s += "\n".join(self.history[-3:]) + "\n"
        for k in info:
            v = info[k]
            if isinstance(v, float) or isinstance(v, np.floating):
                v = "%7.2f" % v
            else:
                v = repr(v)
            s += "%-18s %s\n" % (k+":", v)
        self.metaLabel.text = s
        self.metaLabel.configure(text=s)

        if self.verbose_info and self.prev_meta is not None:
            for x in range(len(meta)):
                if self.prev_meta[x] != meta[x] and x not in (0, 1):
                    msg = "meta[%d] changed from 0x%04x=%d to 0x%04x=%d" % (x, self.prev_meta[x], self.prev_meta[x], meta[x], meta[x])
                    print(msg)
                    self.history.append(msg)
        if self.verbose_info:
            self.prev_meta = meta

        root.after(10, self.show_frame)

    def keydown(self, e):
        if e.char == 'q':
            self.root.destroy()
        elif e.char == 'u':
            self.cap.calibrate()
            self.calibrate = 0
        elif e.char == 's' or e.char == 'w':
            cv2.imwrite(time.strftime("%Y-%m-%d_%H:%M:%S") + '.png', self.cv_frame)
        elif e.char == 'k':
            self.cap.temperature_range_normal()
            # some delay is needed before calibration
            self.delay_to_calibrate = 100 # 50
            self.calibration_image = None
        elif e.char == 'l':
            self.cap.temperature_range_high()
            # some delay is needed before calibration
            self.delay_to_calibrate = 150 # 50
            self.calibration_image = None
        elif e.char == 'o':
            self.orientation = (self.orientation - 90) % 360
        elif e.char == 'a':
            # save to disk
            ret, frame = self.cap.read()
            data = (frame)
            name = time.strftime("%Y-%m-%d_%H-%M-%S") + ".pkl"
            with open(name, "wb") as f:
                pickle.dump(data, f)
        elif e.char == 't':
            self.draw_temp = not self.draw_temp
        elif e.char == 'v':
            self.verbose_info = not self.verbose_info
            if self.verbose_info:
                self.upscale_factor = 2
            else:
                self.upscale_factor = 4
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
