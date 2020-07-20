from PyQt5.QtWidgets import *
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5 import uic
import nidaqmx
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from nidaqmx.constants import LineGrouping
import time
from nidaqmx.types import CtrTime
import sys, os
import xlsxwriter    

pathname = os.path.dirname(sys.argv[0])         
path=os.path.abspath(pathname)
form_class = uic.loadUiType(path+'\\PID.ui')[0] 

workbook = xlsxwriter.Workbook('Dane.xlsx')
worksheet = workbook.add_worksheet()
bold = workbook.add_format({'bold' : True})
worksheet.write(0,0, 'Set_Point', bold)
worksheet.write(0,1, 'Curr_Temp', bold)
worksheet.write(0,2, 'Y', bold)
worksheet.write(0,3, 'Kp', bold)
worksheet.write(0,4, 'Ti', bold)
worksheet.write(0,5, 'Td', bold)
worksheet.write(0,6, '', bold)
worksheet.write(0,7, 'fun_duty', bold)
worksheet.write(0,8, 'fun_freq', bold)
worksheet.write(0,9, 'probkowanie', bold)
chart=workbook.add_chart({'type':'line'})
# 116 strona


class MyWindow(QMainWindow, form_class):
    def __init__(self,P = 2.0, I = 0.0, D = 1.0, Derivator = 0, Integrator = 0, Integrator_max = 100, Integrator_min = 0):
        super().__init__()
        self.setupUi(self)
        self.isRun = True
        self.fig = plt.Figure()
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Time [s]")
        self.ax.set_ylabel("Temperature [\u2103]")
        self.y = np.zeros(600)
        self.x = np.zeros(600)
        self.iterator=0
        self.lineSP, = self.ax.plot([0,60], [0,100], "r")
        self.line, = self.ax.plot([0,60], [20,30], "g")

        self.canvas = FigureCanvas(self.fig)
        self.Figure.addWidget(self.canvas)
        self.starten=time.time()
        self.freqSlider.valueChanged.connect(self.updateFreq)
        self.dutySlider.valueChanged.connect(self.updateDuty)
        self.freqSlider2.valueChanged.connect(self.updateFreq2)
        self.dutySlider2.valueChanged.connect(self.updateDuty2)
        self.freq1=self.freqSlider.value()
        self.duty1=self.dutySlider.value()
        self.freq2=self.freqSlider2.value()
        self.duty2=self.dutySlider2.value()
        self.DAQ()
        self.row = 1
        self.col = 1
# Inicjalizacja parametrów dla Heat-PID
        self.KpSlider.valueChanged.connect(self.updateKp)
        self.Kp = self.KpSlider.value()/100
        self.TiSlider.valueChanged.connect(self.updateTi)
        self.Ki = self.TiSlider.value()/100
        self.TDSlider.valueChanged.connect(self.updateTD)
        self.Kd = self.TDSlider.value()/100
        self.Derivator = Derivator
        self.Integrator = Integrator
        self.Integrator_max = Integrator_max
        self.Integrator_min = Integrator_min
        self.SetPoint = self.wartZadPokretlo.value()
        self.wartZadPokretlo.valueChanged.connect(self.updateSetPoint)
        self.error = 0.0

# Inicjalizacja przycisku Zapisu
        self.Zapis.toggled.connect(self.Write_Data)
        self.samps_channel_slider.valueChanged.connect(self.updateSamps)
        self.probka = self.samps_channel_slider.value()

    def updatePID(self, current_value):
        self.SetPoint = self.wartZadanaValue.value()
        self.error = self.SetPoint - current_value
        self.P_value = self.Kp * self.error
        self.D_value = self.Kd * (self.error - self.Derivator)
        self.Derivator = self.Derivator
        self.Integrator = self.Integrator + self.error
     
        if self.Integrator > self.Integrator_max:
            self.Integrator = self.Integrator_max
        elif self.Integrator < self.Integrator_min:
           self.Integrator = self.Integrator_min

        self.I_value = self.Integrator * self.Ki
        PID = self.P_value + self.I_value + self.D_value
        if(PID <= 0):
            PID = 1
        return PID

    def updateKp(self, event):
        self.KpLCD.display(event/100)
    
    def updateTi(self, event):
        self.TiLCD.display(event/1000)

    def updateTD(self, event):
        self.TDLCD.display(event/1000)

    def updateSetPoint(self, event):
        self.wartZadanaValue.display(event)

    def updateSamps(self, event):
        self.probLCD.display(event)
    def updateFreq(self, event):
        self.freqLCD.display(event)
    
    def updateDuty(self, event):
        self.dutyLCD.display(event)
    
    def updateFreq2(self, event):
        self.freqLCD2.display(event)
    
    def updateDuty2(self, event):
        self.dutyLCD2.display(event)

    def drawPlot(self):    
        self.line.set_xdata(self.x)
        self.line.set_ydata(self.y)
        self.canvas.draw()

    def drawSetPoint(self):
        self.lineSP.set_xdata(self.x)
        self.lineSP.set_ydata(self.SetPoint)
        self.canvas.draw()

    def Write_Data(self, curr_temp):
        worksheet.write(self.col,self.row-1, self.SetPoint)
        worksheet.write(self.col,self.row, curr_temp)
        worksheet.write(self.col,self.row+1, self.Y.value())
        worksheet.write(self.col,self.row+2, self.Kp)
        worksheet.write(self.col,self.row+3, self.Ki)
        worksheet.write(self.col,self.row+4, self.Kd)
        worksheet.write(self.col,self.row+6, self.duty1)
        worksheet.write(self.col,self.row+7, self.freq1)
        worksheet.write(self.col,self.row+8, self.probka)
        
    
    def DAQ(self):
        global read_task
        global fan_task
        global heat_task

        read_task = nidaqmx.Task()
        fan_task=nidaqmx.Task()
        heat_task=nidaqmx.Task()
        read_task.ai_channels.add_ai_voltage_chan("Dev1/ai1")
        read_task.timing.cfg_samp_clk_timing(rate=10,
                                       sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
                                      samps_per_chan=1)

        fan_task.co_channels.add_co_pulse_chan_freq(counter="Dev1/ctr0",freq=self.freq1, duty_cycle=self.duty1/100)
        fan_task.timing.cfg_implicit_timing(sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
        samps_per_chan=1)

        heat_task.co_channels.add_co_pulse_chan_freq(counter="Dev1/ctr1",freq=self.freq2, duty_cycle=self.duty2/100)
        heat_task.timing.cfg_implicit_timing(sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
        samps_per_chan=1)

        fan_task.start()
        fan_task.is_task_done()

        heat_task.start()
        heat_task.is_task_done()

        
        def callback(task_handle, every_n_samples_event_type,
                     number_of_samples, callback_data):
            global fan_task
            global heat_task
            miejsce_zapisu=1

            if(self.probka != self.samps_channel_slider.value()):
                self.probka = self.samps_channel_slider.value()

            if(self.Kp != self.KpLCD.value()):
               self.Kp = self.KpLCD.value()
            
            if(self.Ki != self.TiLCD.value()):
              self.Ki = self.TiLCD.value()

            if(self.Kd != self.TDLCD.value()):
               self.Kd = self.TDLCD.value()

            if(self.freq1!=self.freqSlider.value() or self.duty1!=self.dutySlider.value()):
                self.freq1=self.freqSlider.value()
                self.duty1=self.dutySlider.value()
                fan_task.is_task_done()
                fan_task.stop()
                fan_task.close()
                fan_task=nidaqmx.Task()
                fan_task.co_channels.add_co_pulse_chan_freq(counter="Dev1/ctr0",freq=self.freq1, duty_cycle=self.duty1/100)
                fan_task.timing.cfg_implicit_timing(sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,samps_per_chan=1000)
                fan_task.start()

            if(self.freq2!=self.freqSlider2.value() or self.duty2!=self.dutySlider2.value()):
                self.freq2=self.freqSlider2.value()
                self.duty2=self.dutySlider2.value()
                heat_task.is_task_done()
                heat_task.stop()
                heat_task.close()
                heat_task=nidaqmx.Task()
                heat_task.co_channels.add_co_pulse_chan_freq(counter="Dev1/ctr1",freq=self.freq2, duty_cycle=self.duty2/100)
                heat_task.timing.cfg_implicit_timing(sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,samps_per_chan=self.probka)
                heat_task.start()
                   
            if(self.SetPoint != self.wartZadPokretlo.value()):
               self.SetPoint = self.wartZadPokretlo.value()
               self.wartZadanaValue_PID.display("{:.1f}".format(float(SetPoint)))
                        
            

            t = time.time() - self.starten
            #old_list=read_task.read(number_of_samples_per_channel=1)
            old_list=read_task.read(number_of_samples_per_channel = nidaqmx.constants.READ_ALL_AVAILABLE)
            my_new_list = [i * 100 for i in old_list ]
            self.tempValue.display("{:.1f}".format(float(np.array(my_new_list))))

            currTemp = self.tempValue.value()
            self.curr.display(currTemp)
            
            if(currTemp != self.SetPoint):
                Y = self.updatePID(currTemp)

                self.curr.display(currTemp)
                heat_task.is_task_done()
                heat_task.stop()
                heat_task.close()
                heat_task=nidaqmx.Task()
                heat_task.co_channels.add_co_pulse_chan_freq(counter="Dev1/ctr1",freq=self.freq2, duty_cycle=Y/100)
                heat_task.timing.cfg_implicit_timing(sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,samps_per_chan=self.probka)
                heat_task.start()
                                
                self.Y.display(Y)
                
            
            self.y = np.append(self.y[1:599],np.array(my_new_list)) 
            self.x=np.linspace(t-60,t,599)
            if t>60: self.ax.set_xlim(t-60, t)
            else: self.ax.set_xlim(0, 60)
            self.ax.set_ylim(0, np.max(self.y)+10)
            self.drawPlot()
            self.drawSetPoint()  
            
            if (self.Zapis.isChecked() == True):  
                self.Write_Data(currTemp)
                self.col = self.col+1

            return 0
        
        read_task.register_every_n_samples_acquired_into_buffer_event(1, callback)      
        read_task.start()
        

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    myWindow = MyWindow()
    myWindow.show()
    app.exec_()
    read_task.close()
    fan_task.close()
    workbook.close()
    sys.exit()
