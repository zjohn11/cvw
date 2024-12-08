#########################################################################################
# openocdGUIsimple.py
#
# Written: Zach Johnson zjohn11@okstate.edu
# Created: 15 November 2024
#
# Purpose: Python GUI for openocd
#
# A component of the CORE-V-WALLY configurable RISC-V project.
# https://github.com/openhwgroup/cvw
#
# Copyright (C) 2021-24 Harvey Mudd College & Oklahoma State University
#
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Licensed under the Solderpad Hardware License v 2.1 (the “License”); you may not use this file 
# except in compliance with the License, or, at your option, the Apache License version 2.0. You 
# may obtain a copy of the License at
#
# https://solderpad.org/licenses/SHL-2.1/
#
# Unless required by applicable law or agreed to in writing, any work distributed under the 
# License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, 
# either express or implied. See the License for the specific language governing permissions 
# and limitations under the License.
#########################################################################################

# Hacky way to add $wally/bin to path so we can import openocd_tcl_wrapper from $wally/tests
import sys
import os
import tkinter as tk
from tkinter import font,ttk
from tkinter import *
sys.path.insert(0, os.path.abspath("bin"))
sys.path.insert(0, os.path.abspath("../../../bin"))
from openocd_tcl_wrapper import OpenOCD

gui_order = [
    "PCM",
    "INSTRM",
    "INSTRVALIDM",
    "MEMRWM",
    "WRITEDATAM",
    "READDATAM (Read-Only)",
    "TRAPM (Read-Only)",
    "IEUADRM",
    "DCSR",
    "DPC",
    "General Purpose Registers:",
    "X0 - X31",
    "F0 - F31"
]

dropdown_options = ['Read', 'Write']

def main():
    global root
    global app

    root = tk.Tk()
    ocd = OpenOCD()

    ocd.__enter__()

    app = WallyDebugApp(root, ocd)
    root.configure(bg='DarkOrange1')
    app.initialize_buttons(ocd)
    reset(ocd)
    root.mainloop()



class WallyDebugApp:
    def __init__(self, root, ocd):
        self.root = root
        self.root.title("WALLY Architecture Debug")

        self.frame = Frame(root)
        self.frame.pack()

        self.state = 0
        self.vals_frame = None
        self.rw_frame = None
        self.next = None
        self.write_label = None
        self.progbuf_frame = None
        self.regs_frame = None

        # Title label
        self.title_label = tk.Label(root, text="WALLY Architecture Debug GUI",font=font.Font(weight='bold', size='18'),
                                    pady=8, bg='DarkOrange1')
        
        self.title_label.pack(side='top', anchor='w')  # Align to the left

        self.scrollable_frame = ttk.Frame(root)
        self.scrollable_frame.pack(fill="both", expand=True)

        # Set the window size based on the screen size
        screenwidth = root.winfo_screenwidth()
        screenheight = root.winfo_screenheight()
        self.width = screenwidth * 0.378  # Adjust the factor as needed
        height = screenheight * 0.42

        alignstr = '%dx%d+%d+%d' % (self.width, height, (screenwidth - self.width) / 2, (screenheight - height) / 2)
        root.geometry(alignstr)
        root.resizable(width=True, height=True)  # Allow resizing

        # Add a horizontal scrollbar at the bottom
        self.x_scrollbar = ttk.Scrollbar(self.scrollable_frame, orient=tk.HORIZONTAL)
        self.x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Add a canvas for displaying the cycles
        self.canvas = tk.Canvas(self.scrollable_frame, xscrollcommand=self.x_scrollbar.set)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Configure the scrollbar to work with the canvas
        self.x_scrollbar.config(command=self.canvas.xview)

        # Create a frame inside the canvas to hold the cycles
        self.frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.frame, anchor=tk.NW)

        # Track the data width and total cycles
        self.data_width = 100  # Adjust as needed
        self.total_cycles = 24  # Adjust as needed
        
        # Bind the event to update the canvas scroll region when resized
        self.canvas.bind("<Configure>", self.on_canvas_configure)

    def initialize_buttons(self,ocd):
        frame = tk.Frame(self.frame, height=2000, width=self.data_width, bg='white',padx=5,pady=30)
        frame.pack(side='left')

        # Buttons
        self.button_resume = tk.Button(root, text='Resume', width=20,height=1, command=lambda:resume(ocd), font=("Helvetica", 12, "bold"))
        self.button_resume.pack(in_=frame, side='top', anchor ='w',padx=25, pady=43)  # Align to the left

        self.button_halt = tk.Button(root, text='Halt', width=20,height=1, command=lambda:halt(ocd), font=("Helvetica", 12, "bold"))
        self.button_halt.pack(in_=frame, side='top', anchor ='w',padx=25, pady=43)  # Align to the left

        button_step = tk.Button(root, text='Step Instruction', width=20,height=1, bg='lightblue', command=lambda:step(ocd), font=("Helvetica", 12, "bold"))
        button_step.pack(in_=frame, side='top', anchor ='w',padx=25, pady=43)  # Align to the left

        button_reset = tk.Button(root, text='Reset Core', width=20,height=1, bg='lightblue', command=lambda:reset(ocd), font=("Helvetica", 12, "bold"))
        button_reset.pack(in_=frame, side='top', anchor ='w',padx=25, pady=43)  # Align to the left
        
    def update_buttons(self):
        if self.state == 0:
            self.button_resume.config(bg='lightgreen')
            self.button_halt.config(bg='gray')
        elif self.state == 1:
            self.button_resume.config(bg='gray')
            self.button_halt.config(bg='lightgreen')

    def dropdown_check(self):
        selected_val = self.dropdown.get()

        if selected_val == 'Read':
            self.next.delete(0,"end")
            self.next.config(state="readonly")
        elif selected_val == 'Write':
            self.next.config(state="normal",bg='white')
            self.next.delete(0,"end")

    def submit_check(self,ocd):
        selected_val = self.dropdown.get()
        
        if selected_val == 'Read':
            try:
                self.next.config(state="normal")
                self.next.delete(0,"end")
                self.next.insert("end", ocd.read_data(self.reg_entry.get()))
                self.next.config(state='readonly')
            except:
                self.next.config(state="normal")
                self.next.delete(0,"end")
                self.next.insert("end", f"Failed to Read {self.reg_entry.get()}")
                self.next.config(state='readonly')
        elif selected_val == 'Write':
            try:
                ocd.write_data(self.reg_entry.get(), self.next.get())
                self.next.config(bg='lightgreen')
            except:
                self.next.config(bg='light coral')

    def initialize_rw(self,ocd):
        if self.rw_frame != None:
            self.rw_frame.destroy()

        if self.next != None:
            self.next.destroy()

        if self.write_label != None:
            self.write_label.destroy()
        self.rw_frame = tk.Frame(self.frame, height=950, width=1000, borderwidth=3, relief='solid',bg='white', padx=5,pady=35)
        self.rw_frame.pack(side='top', anchor='nw')

        self.dropdown = tk.StringVar()
        self.dropdown.set(dropdown_options[0])

        self.dropdown_spot = tk.OptionMenu(self.rw_frame, self.dropdown, *dropdown_options, command=lambda _:self.dropdown_check())
        self.dropdown_spot.grid(row=2, column=1, padx=10, pady=5)

        self.entry_label = tk.Label(self.rw_frame, text="Register to R/W", fg='black', bg='white', font=font.Font(weight='bold', size=10), padx=20,pady=1)
        self.entry_label.grid(row=1, column=2, padx=40)

        self.reg_entry = tk.Entry(self.rw_frame,width=20,font=font.Font(weight='bold', size=12),bd=2, relief="solid")
        self.reg_entry.grid(row=2, column=2, padx=5, pady=5)

        self.submit_button = tk.Button(self.rw_frame, text='Submit', command=lambda:self.submit_check(ocd),width=7,height=1, bg='lightblue', font=("Helvetica", 10, "bold"))
        self.submit_button.grid(row=4, column=1, padx=10, pady=5)

        self.write_label = tk.Label(self.rw_frame, text='Read Data/Data to Write', fg='black', bg='white', font=font.Font(weight='bold', size=10), padx=20,pady=1)
        self.write_label.grid(row=3,column=2, padx=5, pady=5)
        
        self.next = tk.Entry(self.rw_frame,width=20,font=font.Font(weight='bold', size=12),bd=2, relief="solid")
        self.next.grid(row=4, column=2, padx=5, pady=5)

        self.next.config(state="readonly")

    def initialize_progbuf(self,ocd):
        if self.progbuf_frame != None:
            self.progbuf_frame.destroy()

        self.progbuf_frame = tk.Frame(self.frame, height=950, width=2500, bg='white', borderwidth=3, relief='solid',padx=5,pady=35)
        self.progbuf_frame.pack(side='bottom', anchor='sw', expand=True)

        self.instruction1 = tk.Label(self.progbuf_frame, text='Instruction 1', fg='black', bg='white', font=font.Font(weight='bold', size=10), padx=20,pady=1)
        self.instruction1.grid(row=0, column=2)

        self.progbuf_entry1 = tk.Entry(self.progbuf_frame, width=20, font=font.Font(weight='bold', size=12),bd=2, relief="solid")
        self.progbuf_entry1.grid(row=1, column=2, padx=63.5, pady=10)

        self.instruction2 = tk.Label(self.progbuf_frame, text='Instruction 2', fg='black', bg='white', font=font.Font(weight='bold', size=10), padx=20,pady=1)
        self.instruction2.grid(row=2, column=2)

        self.progbuf_entry2 = tk.Entry(self.progbuf_frame, width=20, font=font.Font(weight='bold', size=12),bd=2, relief="solid")
        self.progbuf_entry2.grid(row=3, column=2, padx=33.45, pady=10)

        self.instruction3 = tk.Label(self.progbuf_frame, text='Instruction 3', fg='black', bg='white', font=font.Font(weight='bold', size=10), padx=20,pady=1)
        self.instruction3.grid(row=4, column=2)

        self.progbuf_entry3 = tk.Entry(self.progbuf_frame, width=20, font=font.Font(weight='bold', size=12),bd=2, relief="solid")
        self.progbuf_entry3.grid(row=5, column=2, padx=33.45, pady=10)

        self.progbuf_button = tk.Button(self.progbuf_frame, text='Execute Program Buffer', command=lambda:exec_progbuf(ocd,[self.progbuf_entry1.get(), self.progbuf_entry2.get(), self.progbuf_entry3.get()]),width=20,height=1, bg='lightblue', font=("Helvetica", 12, "bold"))
        self.progbuf_button.grid(row=6, column=2, padx=33.45, pady=10)

    def initialize_regs(self):
        if self.regs_frame != None:
            self.regs_frame.destroy()
        self.regs_frame = tk.Frame(self.frame, height=1000, width=self.data_width, bg='white', padx=5,pady=35)
        self.regs_frame.pack(side='right', anchor='e')

        self.reg_title = tk.Label(self.regs_frame, text="Available Registers for Read/Write",fg='black',bg='white',font=font.Font(weight='bold', size=15, underline=True), padx=13,pady=6)
        self.reg_title.grid(row=0, column=1)

        for num,reg in enumerate(gui_order):
            self.reg = tk.Label(self.regs_frame, text=reg, fg='black',bg='white', font=font.Font(weight='bold', size=12), padx=10,pady=5.4)
            self.reg.grid(row=num+1, column=1)

    def on_canvas_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if event.width != self.canvas.winfo_reqwidth():
            # Update the canvas width to match the frame width
            self.canvas.config(width=event.width)

def resume(ocd):
    #resume action
    # will call update_regs after resuming
    ocd.resume()
    app.state = 0
    app.update_buttons()
    app.initialize_regs()
    app.initialize_rw(ocd)
    app.initialize_progbuf(ocd)

def halt(ocd):
    #halt action
    # will call update_regs after halting
    ocd.halt()
    app.state = 1
    app.update_buttons()
    app.initialize_regs()
    app.initialize_rw(ocd)
    app.initialize_progbuf(ocd)

def step(ocd):
    #step one instruction
    ocd.step()
    app.initialize_regs()
    app.initialize_rw(ocd)
    app.initialize_progbuf(ocd)

def reset(ocd):
    ocd.reset_hart()
    ocd.clear_abstrcmd_err()
    app.state = 0
    app.update_buttons()
    app.initialize_regs()
    app.initialize_rw(ocd)
    app.initialize_progbuf(ocd)

def exec_progbuf(ocd, instructions):
    #execute program buffer
    ocd.write_progbuf(instructions)
    ocd.exec_progbuf()
    app.initialize_progbuf(ocd)
          
if __name__ == "__main__":
    main()
