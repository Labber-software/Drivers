import InstrumentDriver
import Tkinter
import numpy as np

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements a user input driver"""
    

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        pass


    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        if quant.name == 'waitForUser':
            tk = Tkinter.Tk()
            label = Tkinter.Label(tk, text="Paused...")
            label.pack(expand=1)
            button = Tkinter.Button(tk, text="Continue", command=tk.destroy)
            button.pack(side=Tkinter.BOTTOM)
            tk.bind('<Return>', (lambda e, button=button: button.invoke()))
            tk.focus_force()
            tk.mainloop()
        return value


    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # proceed depending on quantity
        if quant.name == 'floatValue':
            tk = Tkinter.Tk()
            label = Tkinter.Label(tk, text="Please enter a float.")
            label.pack(expand=1)
            entry = Tkinter.Entry(tk)
            entry.pack(expand=1)
            entry.focus_set()
            global result
            def getResult():
                global result
                result = entry.get()
                try:
                    float(result)
                    tk.destroy()
                except ValueError:
                    label.config(text="That is not a float...")
            button = Tkinter.Button(tk, text="OK", command=getResult)
            button.pack(side=Tkinter.BOTTOM)
            tk.bind('<Return>', (lambda e, button=button: button.invoke()))
            tk.focus_force()
            tk.mainloop()
            return result
        return quant.getValue()


