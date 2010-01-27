#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import serial

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qwt5 import *

from pybrewMainWindow import MainWindow

from brewcontroller import BrewController, BrewControllerException

class Pybrew(MainWindow):
    def __init__(self):
        MainWindow.__init__(self)

        self.tempUpdateInterval = 1000 # update interval in milliseconds
        
        self.target_temp = 0

        try:
            self.bc = BrewController()
            self.bc.open_port('/dev/ttyUSB0')
        except BrewControllerException as e:
            QMessageBox.critical(None, "Fatal error", str(e))
            sys.exit(1)
        
        self.bc.serialErrorSignal.connect(self.serialErrorEvent, Qt.QueuedConnection)
        
        self.bc.getTempSignal.connect(self.serialGetTempEvent, Qt.QueuedConnection)
        self.bc.getTargetTempSignal.connect(self.serialGetTargetTempEvent, Qt.QueuedConnection)
        self.bc.getValveStateSignal.connect(self.serialGetValveStateEvent, Qt.QueuedConnection)

        buttons = self.bc.VALVES.keys()
        buttons.sort()
        self.valve_buttons = {}
        def get_callback(id, button):
            def cb():
                self.valve_button_clicked(id, button)
            return cb

        for k in buttons:
            v = QPushButton(self.bc.VALVES[k], self)
            v.connect(v, SIGNAL('clicked()'), get_callback(k, v))
            v.setObjectName(k)
            v.setCheckable(True)
            self.valveButtonLayout.addWidget(v)
            self.valve_buttons[k] = v
            
        self.tempCurve = QwtPlotCurve("Temperature")
        self.tempCurve.attach(self.tempQwtPlot)
        
        self.tempXData = []
        self.tempYData = []
        
        self.Thermo.setAlarmLevel(25)
        self.Thermo.setAlarmColor(Qt.green)

        self.tempUpdateTimer = QTimer(self)
        self.connect(self.tempUpdateTimer, SIGNAL('timeout()'), self.tempUpdateEvent)
        self.tempUpdateTimer.start(self.tempUpdateInterval)
        
        self.read_serial_state()

    def read_serial_state(self):
        for b in self.valve_buttons:
            self.bc.get_valve_state(b)
        self.bc.get_target_temp()
        print "read serial state done"
    
    def serialErrorEvent(self, msg):
        print "Serial error:", msg

    def serialGetTempEvent(self, sensor, temp):
        print "got temp", sensor, temp
        
        self.Thermo.setValue(temp)
        if not self.tempXData:
            self.tempXData = [0]
        else:
            self.tempXData.append(self.tempXData[-1] + self.tempUpdateInterval/1000.0)
        self.tempYData.append(int(temp))
        self.tempCurve.setData(self.tempXData, self.tempYData)
        self.tempQwtPlot.replot()
    
    def serialGetTargetTempEvent(self, temp):
        print "got target temp", temp
        self.targetTempLineEdit.setText(str(temp))
    
    def serialGetValveStateEvent(self, valve_id, state):
        print "got valve state:", valve_id, state
        valve_id = str(valve_id)
        state = str(state)
        if state == "open":
            is_open = True
        elif state == "closed":
            is_open = False
        else:
            print "Bad valve state", valve, state
            return
        button = self.valve_buttons[valve_id]
        button.setChecked(is_open)
        pal = button.palette()
        if is_open:
            color = Qt.green
        else:
            color = Qt.yellow
        pal.setColor(button.backgroundRole(), color)
        button.setPalette(pal)

    def setTargetTempEvent(self):
        temp = self.targetTempLineEdit.text()
        self.set_target_temp(temp)
        self.bc.get_target_temp() # read back the setting to verify
    
    def tempUpdateEvent(self):
        self.bc.get_temp("0")

    def set_target_temp(self, temp):
        try:
            temp = int(temp)
        except ValueError:
            print temp, "is not a valid temperature."
            return
        if temp == self.target_temp:
            return
        temp = self.bc.set_temp(temp)
        self.target_temp = temp

    def valve_button_clicked(self, valve_id, button):
        self.bc.set_valve_open(valve_id, button.isChecked())
        self.bc.get_valve_state(valve_id)

    def closeEvent(self, ev):
        sys.exit(0)

def main():
    qApp = QApplication(sys.argv)
    pybrew = Pybrew()
    pybrew.show()
    sys.exit(qApp.exec_())

if __name__ == "__main__":
    main()

app = App(0)
app.MainLoop()
