import copy
import ctypes
import datetime
from importlib.abc import Traversable
import json
import os
import random
import re
import socket
import sys
import threading
import tkinter
from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
from math import ceil
from time import sleep, time
from tkinter import filedialog, messagebox

import numpy
import pyqtgraph
from pyModbusTCP.client import ModbusClient
#import ui.Ico.ico_rc
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRegExp, QThread, Qt
from PyQt5.QtGui import QBrush, QColor, QRegExpValidator
from PyQt5.QtWidgets import QLineEdit, QStyledItemDelegate
from pyqtgraph import mkPen
from pyqtgraph.dockarea import *

from UI.ProjectVUZV4 import Ui_mw_ProjectVUZ


class ToMainThread(QThread): # class Has to be defined. Cannot be empty '()'
    '''Passes a function into the mainThread'''
    # Signals and slots:
    # A way to pass variables between Classes and into the main thread
    tabState = QtCore.pyqtSignal(str) # this is Signal
    printS = QtCore.pyqtSignal(tuple)
    showBox = QtCore.pyqtSignal(tuple)
    setItemColor = QtCore.pyqtSignal(str)
    setLabelValues = QtCore.pyqtSignal(tuple)
    setPlots = QtCore.pyqtSignal(tuple)

    def __init__(self, parent=None, function='', item=0):
        super(ToMainThread, self).__init__(parent)
        self.function = function
        self.item = item
        self.is_running = True
    def run(self):
        if self.function == 'tabState':
            self.tabState.emit(self.item)
            #print("1t")
        elif self.function == 'printS':
            self.printS.emit(self.item)
            #print("2t")
        elif self.function == 'showBox':
            self.showBox.emit(self.item)
            #print(self.item)
        elif self.function == 'setItemColor':
            self.setItemColor.emit(self.item)
            #print(self.item)
        elif self.function == 'setLabelValues':
            self.setLabelValues.emit(self.item)
            #print(self.item)
        elif self.function == 'setPlots':
            self.setPlots.emit(self.item)
    def stop(self):
        print("ToMainThread - Exited")
        self.is_running = False
        self.terminate()

class MainWindow(Ui_mw_ProjectVUZ):
    def __init__(self, window) -> None:
        self.setupUi(window)

        self.tab_PLCTab.tabBarClicked.connect(self.SwitchTP1)
        self.tab_MAINtab.currentChanged.connect(self.Parametrization)
        self.tab_MAINtab.currentChanged.connect(self.Measurement)
        self.pb_LoadPar.clicked.connect(self.LoadParameters)
        self.pb_SavePar.clicked.connect(self.SaveParameters)

        self.cb_MoveDir
        self.pb_MoveStart.clicked.connect(self.StartMovement)
        #self.comboBox.currentIndexChanged.connect(self.newSamplePeriod)

        self.mainThread = ToMainThread()
        self.mainThread.tabState.connect(self.tabState)
        self.mainThread.printS.connect(self.printS)
        self.mainThread.showBox.connect(self.showBox)
        self.mainThread.setItemColor.connect(self.setItemColor)
        self.mainThread.setLabelValues.connect(self.setLabelValues)
        self.mainThread.setPlots.connect(self.setPlots)
        self.sb_sampleLenght.valueChanged.connect(self.newSampleLenght)
        self.cb_sampleTime.currentIndexChanged.connect(self.newSampleTime)

        self.pb_engineStart.clicked.connect(lambda: self.StartEngine(0))
        self.pb_engineLeft.clicked.connect(lambda: self.StartEngine(1))
        self.pb_engineLeft_2.clicked.connect(lambda: self.StartEngine(2))
        self.pb_engineRight.clicked.connect(lambda: self.StartEngine(3))
        self.pb_engineRight_2.clicked.connect(lambda: self.StartEngine(4))
        self.pb_engineList=[
            self.pb_engineLeft,
            self.pb_engineLeft_2,
            self.pb_engineRight,
            self.pb_engineRight_2
        ]

        self.twButton = {
            "L1": [self.pb_L1Add_0],
            "L2": [self.pb_L2Add_0],
            "R1": [self.pb_R1Add_0],
            "R2": [self.pb_R2Add_0],
        }

    # in MainThread
    def toMainThread(self, function: str, item):
        self.mainThread.function = function #set mainThread to SetSuffix
        self.mainThread.item = item #spinBox index and value
        self.mainThread.start() #Trigger MainThread
        sleep(0.01)

    # Save Settings
    config = ConfigParser()
    def loadSettings(self):
        # load default settings

        overWriteConfig = False
        try:
            self.config.read('config.ini')
        except 2:
            sleep(1)
            self.config.read('config.ini')
        except:
            overWriteConfig = True
        else:
            if (not self.config.has_section("position") or
                not self.config.has_section("force") or
                not self.config.has_section("temperature") or
                not self.config.has_section("controlwords") or
                not self.config.has_section("connect") or
                not self.config.has_section("testVar") or
                not self.config.has_section("sample")):
                overWriteConfig = True

        if overWriteConfig:
            self.printS("An error occurred while loading settings.")
            root = tkinter.Tk()
            root.withdraw()
            fail = True
            test = True

            tries = 0
            while fail and test:
                sleep(1)
                #test = messagebox.askretrycancel(title="Error with Config File", message="MasterAPP encountered an error while loading Config file. (" + str(tries) + " tries out of 5)" + " \nDo you wish to try again? \n\nCancel: Rewrite Config file. Settings will be lost.", master=root)
                #Doesn't work
                try:
                    self.config.read('config.ini')
                except:
                    tries += 1
                else:
                    if (not self.config.has_section("position") or
                        not self.config.has_section("force") or
                        not self.config.has_section("temperature") or
                        not self.config.has_section("controlwords") or
                        not self.config.has_section("connect") or
                        not self.config.has_section("testVar") or
                        not self.config.has_section("sample")):
                        tries += 1
                    else:
                        fail = False
                if tries == 6: break
            if fail:
                self.createConfigFile()

        # Load Config File
        '''com.address = self.config.get("connect", "address")
        com.comForm = self.config.get("connect", "form")
        com.register_0 = self.config.getint("controlwords", "refWord")
        com.register_1 = self.config.getint("controlwords", "conWord")
        com.register_2 = self.config.getint("controlwords", "temWord")
        com.register_18 = self.config.getint("controlwords", "pacWord")
        com.register_3 = self.config.getint("position", "set")
        com.register_11 = self.config.getint("position", "act1")
        com.register_4 = self.config.getint("position", "act2")
        com.register_5 = self.config.getint("force", "set")
        com.register_6 = self.config.getint("force", "act")
        com.register_7 = self.config.getint("temperature", "set")
        com.register_8 = self.config.getint("temperature", "act")
        com.register_9 = self.config.getint("testVar", "frek")
        com.register_10 = self.config.getint("testVar", "amp")
        com.register_pos = self.config.getint("position", "arr")
        com.register_for = self.config.getint("force", "arr")
        com.register_tem = self.config.getint("temperature", "arr")
        mes.samplelenght = self.config.getint("sample", "length")
        mes.sampletime = self.config.getfloat("sample", "time")
        mes.updateRate = self.config.getfloat("sample", "rate")
        mes.showedRange = self.config.getfloat("sample", "range")
        mes.TimeInterFileWrite = self.config.getint("sample", "saveInterval")'''

        # Express settings
        #checkSettings = False
        '''self.le_adress.setText(com.address)
        self.sb_register_0.setValue(com.register_0)
        self.sb_register_1.setValue(com.register_1)
        self.sb_register_2.setValue(com.register_2)
        self.sb_register_3.setValue(com.register_3)
        self.sb_register_4.setValue(com.register_4)
        self.sb_register_5.setValue(com.register_5)
        self.sb_register_6.setValue(com.register_6)
        self.sb_register_7.setValue(com.register_7)
        self.sb_register_8.setValue(com.register_8)
        self.sb_register_9.setValue(com.register_9)
        self.sb_register_10.setValue(com.register_10)
        self.sb_register_11.setValue(com.register_11)
        self.sb_register_18.setValue(com.register_18)
        self.sb_register_pos.setValue(com.register_pos)
        self.sb_register_for.setValue(com.register_for)
        self.sb_register_tem.setValue(com.register_tem)
        self.sb_sampleLenght.setValue(mes.samplelenght)
        self.sb_sampleLenght_2.setValue(mes.sampletime)
        self.sb_updateRate.setValue(mes.updateRate)
        self.sb_showedRange.setValue(mes.showedRange)
        self.sb_fileInterval.setValue(mes.TimeInterFileWrite)'''


        pass
    def updateSettings(self):

        #Synchronization

        '''com.address = self.le_adress.text()
        com.register_0 = self.sb_register_0.value()
        com.register_1 = self.sb_register_1.value()
        com.register_2 = self.sb_register_2.value()
        com.register_18 = self.sb_register_18.value()
        com.register_3 = self.sb_register_3.value()
        com.register_11 = self.sb_register_11.value()
        com.register_4 = self.sb_register_4.value()
        com.register_5 = self.sb_register_5.value()
        com.register_6 = self.sb_register_6.value()
        com.register_7 = self.sb_register_7.value()
        com.register_8 = self.sb_register_8.value()
        com.register_9 = self.sb_register_9.value()
        com.register_10 = self.sb_register_10.value()
        com.register_pos = self.sb_register_pos.value()
        com.register_for = self.sb_register_for.value()
        com.register_tem = self.sb_register_tem.value()
        mes.samplelenght = self.sb_sampleLenght.value()
        mes.sampletime = self.sb_sampleLenght_2.value()
        mes.updateRate = self.sb_updateRate.value()
        mes.showedRange = self.sb_showedRange.value()
        mes.TimeInterFileWrite = self.sb_fileInterval.value()

        #Special behavior
        if self.rb_Communication.isChecked():
            com.comForm == "Modbus"
        if self.rb_Communication_2.isChecked():
            com.comForm == "Library"'''


        #Config backup
        '''self.config.set('connect', 'address', str(com.address))
        self.config.set('connect', 'form', str(com.comForm))
        self.config.set("controlwords", "refWord", str(com.register_0))
        self.config.set("controlwords", "conWord", str(com.register_1))
        self.config.set("controlwords", "temWord", str(com.register_2))
        self.config.set("controlwords", "pacWord", str(com.register_18))
        self.config.set("position", "set", str(com.register_3))
        self.config.set("position", "act1", str(com.register_11))
        self.config.set("position", "act2", str(com.register_4))
        self.config.set("force", "set", str(com.register_5))
        self.config.set("force", "act", str(com.register_6))
        self.config.set("temperature", "set", str(com.register_7))
        self.config.set("temperature", "act", str(com.register_8))
        self.config.set("testVar", "frek", str(com.register_9))
        self.config.set("testVar", "amp", str(com.register_10))
        self.config.set("position", "arr", str(com.register_pos))
        self.config.set("force", "arr", str(com.register_for))
        self.config.set("temperature", "arr", str(com.register_tem))
        self.config.set("sample", "length", str(mes.samplelenght))
        self.config.set("sample", "time", str(mes.sampletime))
        self.config.set("sample", "rate", str(mes.updateRate))
        self.config.set("sample", "range", str(mes.showedRange))
        self.config.set("sample", "saveInterval", str(mes.TimeInterFileWrite))

        with open('config.ini', 'w') as f:
            self.config.write(f)
            f.close()'''
    def createConfigFile(self):
        '''if not self.config.has_section("connect"):
            self.config.add_section('connect')
            self.config.set('connect', 'address', str(com.address))
            self.config.set('connect', 'form', str(com.comForm))
        if not self.config.has_section("controlwords"):
            self.config.add_section('controlwords')
            self.config.set("controlwords", "conWord", str(com.register_0))
            self.config.set("controlwords", "refWord", str(com.register_1))
            self.config.set("controlwords", "temWord", str(com.register_2))
            self.config.set("controlwords", "pacWord", str(com.register_18))
            pass
        if not self.config.has_section("position"):
            self.config.add_section('position')
            self.config.set("position", "set", str(com.register_3))
            self.config.set("position", "act1", str(com.register_11))
            self.config.set("position", "act2", str(com.register_4))
            self.config.set("position", "arr", str(com.register_pos))
            pass
        if not self.config.has_section("force"):
            self.config.add_section('force')
            self.config.set("force", "set", str(com.register_5))
            self.config.set("force", "act", str(com.register_6))
            self.config.set("force", "arr", str(com.register_for))
            pass
        if not self.config.has_section("temperature"):
            self.config.add_section('temperature')
            self.config.set("temperature", "set", str(com.register_7))
            self.config.set("temperature", "act", str(com.register_8))
            self.config.set("temperature", "arr", str(com.register_tem))
            pass
        if not self.config.has_section("testVar"):
            self.config.add_section('testVar')
            self.config.set("testVar", "frek", str(com.register_9))
            self.config.set("testVar", "amp", str(com.register_10))
            pass
        if not self.config.has_section("sample"):
            self.config.add_section('sample')
            self.config.set("sample", "length", str(mes.samplelenght))
            self.config.set("sample", "time", str(mes.sampletime))
            self.config.set("sample", "rate", str(mes.updateRate))
            self.config.set("sample", "range", str(mes.showedRange))
            self.config.set("sample", "saveInterval", str(mes.TimeInterFileWrite))
            pass'''
        with open('config.ini', 'w') as f:
            self.config.write(f)
            f.close()
        pass

    #APP handlers
    def Start(self):
        #self.loadSettings()

        self.printS("V.U.Z Start")
        #self.rb_Communication.setChecked(True)
        #self.swapComunication()
        self.setLock("m", True)
        self.tab_MAINtab.widget(1).setEnabled(False)
        self.tab_MAINtab.widget(0).setEnabled(True)

        self.SetupWindowUI()
        data.Build()
        self.SwitchTP1(0)
        pass
    def Exit(self):
        global stopUpdate
        stopUpdate = True
        sleep(0.1)
        com.disconnect()
        #self.updateSettings()
        self.printS("V.U.Z Exit")
        pass

    #UI shenanigans
    def SetupWindowUI(self):
        #Set up docks for PLCtabs
        self.printS("UI Setup", "Start")
        #spacer = QtWidgets.QSpacerItem(72, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        #self.hl_PageHolder_0.addItem(spacer)
        #self.hl_PageHolder.addWidget(area)

        twHolder = {
            "L1": [self.vl_L1Holder_0],
            "L2": [self.vl_L2Holder_0],
            "R1": [self.vl_R1Holder_0],
            "R2": [self.vl_R2Holder_0],
        }
        '''twDock = {
            "L1": [Dock("Left 1", size=(0,0))],
            "L2": [Dock("Left 2", size=(0,0))],
            "R1": [Dock("Right 1", size=(0,0))],
            "R2": [Dock("Right 2", size=(0,0))],
        }'''
        twLabel = {
            "L1": [self.l_Left1_0],
            "L2": [self.l_Left2_0],
            "R1": [self.l_Right1_0],
            "R2": [self.l_Right2_0],
        }
        twTable = {
            "L1": [self.tw_Left1_0],
            "L2": [self.tw_Left2_0],
            "R1": [self.tw_Right1_0],
            "R2": [self.tw_Right2_0],
        }


        for tw in ("L1", "L2", "R1", "R2"):
            twHolder[tw][0].addWidget(twLabel[tw][0])
            twHolder[tw][0].addWidget(twTable[tw][0])
            twHolder[tw][0].addWidget(self.twButton[tw][0])
            spacerItem = QtWidgets.QSpacerItem(72, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
            twHolder[tw][0].addItem(spacerItem)
            twTable[tw][0].setEnabled(False)
            self.twButton[tw][0].setEnabled(False)

        '''self.twButton["L1"][0].clicked.connect(lambda: self.addRow("L1"))
        self.twButton["L2"][0].clicked.connect(lambda: self.addRow("L2"))
        self.twButton["R1"][0].clicked.connect(lambda: self.addRow("R1"))
        self.twButton["R2"][0].clicked.connect(lambda: self.addRow("R2"))'''


        self.printS("UI Setup", "TableWidget")
        for r in range(self.tw_Left1_0.rowCount()):
            for c in range(self.tw_Left1_0.columnCount()):
                item = QtWidgets.QTableWidgetItem(self.tw_Left1_0.item(r, c))
                item.setTextAlignment(self.tw_Left1_0.item(0,0).textAlignment())
                self.tw_Left1_0.setItem(r, c, item)
                item = QtWidgets.QTableWidgetItem(self.tw_Left1_0.item(r, c))
                item.setTextAlignment(self.tw_Left1_0.item(0,0).textAlignment())
                self.tw_Left2_0.setItem(r, c, item)
                item = QtWidgets.QTableWidgetItem(self.tw_Left1_0.item(r, c))
                item.setTextAlignment(self.tw_Left1_0.item(0,0).textAlignment())
                self.tw_Right1_0.setItem(r, c, item)
                item = QtWidgets.QTableWidgetItem(self.tw_Left1_0.item(r, c))
                item.setTextAlignment(self.tw_Left1_0.item(0,0).textAlignment())
                self.tw_Right2_0.setItem(r, c, item)

        for i in range(1, 9):
            # Add PLCtab
            newPLCtab = QtWidgets.QTabWidget()
            newPLCtab.setStyleSheet(self.tp_PLCpage_0.styleSheet())
            newPLCtab.setMaximumSize(self.tp_PLCpage_0.maximumSize())
            newPLCtab.setObjectName("tp_PLCtab_" + str(i))
            newPLCtab.setTabText(i, str(i))
            self.tab_PLCTab.addTab(newPLCtab, str(i))

            #Copy Page
            newPLCpage = QtWidgets.QVBoxLayout(newPLCtab)
            newPLCpage.setContentsMargins(self.verticalLayout.contentsMargins())
            newPLCpage.setSpacing(self.verticalLayout.spacing())
            newPLCpage.setObjectName("tp_PLCpage_" + str(i))

            #Copy holder
            newPageHolder = QtWidgets.QHBoxLayout()
            newPageHolder.setContentsMargins(self.hl_PageHolder_0.contentsMargins())
            newPageHolder.setSpacing(self.hl_PageHolder_0.spacing())
            newPageHolder.setObjectName("hl_PageHolder_" + str(i))
            newPLCpage.addLayout(newPageHolder)

            spacerItem = QtWidgets.QSpacerItem(72, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            newPageHolder.addItem(spacerItem) #Left Spacer

            '''#Prepare Dock
            dock = {
                "L1": Dock("Left 1"),
                "L2": Dock("Left 2"),
                "R1": Dock("Right 1"),
                "R2": Dock("Right 2"),
            }'''
            # Copy Widget
            for tw in ("L1", "L2", "R1", "R2"):
                if tw[0] == "L":
                    name = "Left" + tw[1]
                else:# tw[0] == "R":
                    name = "Right" + tw[1]
                #Copy twHolder
                twHolder[tw].append(QtWidgets.QVBoxLayout(newPLCtab))
                twHolder[tw][i].setContentsMargins(twHolder[tw][0].contentsMargins())
                twHolder[tw][i].setSpacing(twHolder[tw][0].spacing())
                twHolder[tw][i].setObjectName("vl_"+ tw +"Holder_" + str(i))

                '''#Add dock
                twDock[tw].append(dock[tw])'''
                twLabel[tw].append(QtWidgets.QLabel())
                twLabel[tw][i].setFont(twLabel[tw][0].font())
                twLabel[tw][i].setStyleSheet(twLabel[tw][0].styleSheet())
                twLabel[tw][i].setAlignment(twLabel[tw][0].alignment())
                twLabel[tw][i].setObjectName("l_" + name + "_" + str(i))
                twLabel[tw][i].setText(twLabel[tw][0].text())

                #Copy tableWidget
                twTable[tw].append(QtWidgets.QTableWidget())
                twTable[tw][i].setStyleSheet(twTable[tw][0].styleSheet())
                twTable[tw][i].setSizePolicy(twTable[tw][0].sizePolicy())
                twTable[tw][i].setMinimumSize(twTable[tw][0].minimumSize())
                twTable[tw][i].setMaximumSize(twTable[tw][0].maximumSize())
                twTable[tw][i].setFont(twTable[tw][0].font())
                twTable[tw][i].setObjectName("tw_" + name + "_" + str(i))
                twTable[tw][i].setColumnCount(twTable[tw][0].columnCount())
                twTable[tw][i].setRowCount(twTable[tw][0].rowCount())
                twTable[tw][i].setSelectionMode(twTable[tw][0].selectionMode())
                twTable[tw][i].setEditTriggers(twTable[tw][0].editTriggers())
                twTable[tw][i].setFocusPolicy(twTable[tw][0].focusPolicy())

                #Copy putton
                self.twButton[tw].append(QtWidgets.QPushButton())
                self.twButton[tw][i].setAutoDefault(self.twButton[tw][0].autoDefault())
                self.twButton[tw][i].setDefault(self.twButton[tw][0].isDefault())
                self.twButton[tw][i].setText(self.twButton[tw][0].text())
                self.twButton[tw][i].setFlat(self.twButton[tw][0].isFlat())
                self.twButton[tw][i].setObjectName("pb_" + tw + "Add_" + str(i))

                #Set order
                twHolder[tw][i].addWidget(twLabel[tw][i])
                twHolder[tw][i].addWidget(twTable[tw][i])
                twHolder[tw][i].addWidget(self.twButton[tw][i])
                spacerItem = QtWidgets.QSpacerItem(72, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
                twHolder[tw][i].addItem(spacerItem)

                newPageHolder.addLayout(twHolder[tw][i])

            spacerItem2 = QtWidgets.QSpacerItem(72, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            newPageHolder.addItem(spacerItem2) # RightSpacer

            for tw in ("L1", "L2", "R1", "R2"):
                for r in range(twTable[tw][0].rowCount()):
                    twTable[tw][i].setVerticalHeaderItem(r, twTable[tw][0].verticalHeaderItem(r))
                    twTable["L1"][i].verticalHeader().setSectionResizeMode(r, QtWidgets.QHeaderView.Fixed)
                for c in range(twTable[tw][0].columnCount()):
                    twTable[tw][i].setHorizontalHeaderItem(c, twTable[tw][0].horizontalHeaderItem(c))
                    twTable["L1"][i].horizontalHeader().setSectionResizeMode(c, QtWidgets.QHeaderView.Fixed)

                for r in range(twTable[tw][0].rowCount()):
                    for c in range(twTable[tw][0].columnCount()):
                        item = QtWidgets.QTableWidgetItem(twTable[tw][0].item(r, c))
                        item.setTextAlignment(twTable[tw][0].item(0,0).textAlignment())
                        item.setText("0")
                        twTable[tw][i].setItem(r, c, item)

                twTable[tw][i].horizontalHeader().setDefaultSectionSize(twTable[tw][0].horizontalHeader().defaultSectionSize())
                twTable[tw][i].horizontalHeader().setMinimumSectionSize(twTable[tw][0].horizontalHeader().minimumSectionSize())
                twTable[tw][i].horizontalHeader().setVisible(True)
                twTable[tw][i].verticalHeader().setVisible(False)
                twTable["L1"][i].verticalHeader().setVisible(True)
                twTable[tw][i].verticalHeader().setDefaultSectionSize(twTable[tw][0].verticalHeader().defaultSectionSize())
                twTable[tw][i].verticalHeader().setMinimumSectionSize(twTable[tw][0].verticalHeader().minimumSectionSize())
                twTable[tw][i].setVerticalScrollBarPolicy(twTable[tw][0].verticalScrollBarPolicy())
                twTable[tw][i].setHorizontalScrollBarPolicy(twTable[tw][0].horizontalScrollBarPolicy())


                delegate = NumericDelegate(twTable[tw][i])
                twTable[tw][i].setItemDelegate(delegate)
                twTable[tw][i].itemEntered.connect(self.fixColor)
                twTable[tw][i].itemChanged.connect(self.dataChanged)

            self.twButton["L1"][i].clicked.connect(lambda: self.addRow("L1"))
            self.twButton["L2"][i].clicked.connect(lambda: self.addRow("L2"))
            self.twButton["R1"][i].clicked.connect(lambda: self.addRow("R1"))
            self.twButton["R2"][i].clicked.connect(lambda: self.addRow("R2"))

            tabPageList.append((
                    newPLCtab,
                    {
                    "L1":twTable["L1"][i],
                    "L2":twTable["L2"][i],
                    "R1":twTable["R1"][i],
                    "R2":twTable["R2"][i],
                    }
                )
            )

        self.setItemColor("yellow")

        #Setup Graphs
        self.printS("UI Setup", "Graphs")

        for tw in ("L1", "L2", "R1", "R2"):
            for type in ("Pos", "For"):
                graphList[tw][type].plotItem.clear()
                graphList[tw][type].setBackground(None) # nastavi bile pozadi
                graphList[tw][type].plotItem.showGrid(True,True)
                graphList[tw][type].plotItem.setMenuEnabled(False)
                graphList[tw][type].plotItem.getViewBox().setLimits(xMin=0 - 0.5, xMax=None, minXRange=0.1, maxXRange=None, yMin=-3, yMax=23, minYRange=-3, maxYRange=23)
                graphList[tw][type].plotItem.getViewBox().setRange(xRange=(0 - 0.5, 20), yRange=(-3, 23))
                graphList[tw][type].plotItem.hideButtons()
            #graphList[tw][type].plotItem.getViewBox().setRange(xRange=(0 - 0.5, 60), yRange=(-3, 3), padding=2)

        self.printS("UI Setup", "FIN")
    def addRow(self, tw):
        '''Adds a row to a 'tw' depending on which page is currently selected, also adjusts its size'''
        self.blockChange = True
        tableWidget = tabPageList[currentTP[0]][1][tw]
        r = tableWidget.rowCount()
        tableWidget.insertRow(r)
        for c in range(tableWidget.columnCount()):
            item = QtWidgets.QTableWidgetItem(tableWidget.item(r, c))
            item.setTextAlignment(tableWidget.item(0,0).textAlignment())
            item.setText("0")
            tableWidget.setItem(r, c, item)
        tableWidget.setVerticalHeaderItem(r, QtWidgets.QTableWidgetItem())
        tableWidget.verticalHeader().setSectionResizeMode(r, QtWidgets.QHeaderView.Fixed)
        tableWidget.verticalHeaderItem(r).setText("Pos. " + str(r + 1).zfill(2))
        rowHeight = tableWidget.verticalHeader().defaultSectionSize() + 0
        r += 1
        while tableWidget.maximumHeight() < (rowHeight + (rowHeight * r)):
            tableWidget.setMaximumHeight(tableWidget.maximumHeight() + rowHeight)
            tableWidget.setMinimumHeight(tableWidget.minimumHeight() + rowHeight)
        #tableWidget.resizeRowsToContents()
        if r >= 20:
            self.twButton[tw][currentTP[0]].hide()

        self.blockChange = False
        for c in range(tableWidget.columnCount()):
            self.setItemColor("yellow", tableWidget.item(r, c))
    def removeRow(self, tableWidget:QtWidgets.QTableWidget, tw):
        tableWidget.removeRow(tableWidget.rowCount())
        tableWidget.adjustSize()
        pass
    switching = False
    def SwitchTP1(self, pageIndex=None):
        '''Detects page change and passes on its index'''
        global currentTP

        if self.switching:
            return
        self.switching = True

        oldIndex = self.tab_PLCTab.currentIndex()

        self.printS("SwitchTP", "Start")
        #self.SwitchTP2(pageIndex, oldIndex)
        threadpool.submit(self.SwitchTP2, pageIndex, oldIndex)
    def SwitchTP2(self, pageIndex, oldIndex):
        '''Works with page index and calls 'Connect/Disconnect' and handles its result'''
        global currentTP
        global valThread
        #Disconnect from previous PLC
        self.tabState("yellow")
        self.pb_WritePar.setEnabled(False)
        self.pb_WriteTara.setEnabled(False)
        self.setLock("m", True)

        self.printS("PLC" + str(oldIndex), "Odpojování...")
        if com.disconnect():
            self.tabState("white")
            self.printS("Odpojení uspělo")
        else:
            self.tabState("red")
            self.printS("Odpojení selhalo")

            '''for p in range(len(tabPageList)):
                for tw in list(tabPageList[p][1].values()):
                    tw.setEnabled(True)'''
            self.switching = False
            return

        if pageIndex == 0:
            self.tabState("green")
            self.printS("SwitchTP", "FIN")
            self.switching = False

            '''for p in range(len(tabPageList)):
                for tw in list(tabPageList[p][1].values()):
                    tw.setEnabled(True)'''
            self.switching = False
            return

        currentTP = (pageIndex, self.tab_PLCTab.widget(pageIndex)) #Assign a new tab
        self.tabState("yellow")

        #connect to new PLC
        self.printS("PLC" + str(pageIndex), "Připojování...")
        if com.connect(pageIndex): #Success
            self.tabState("green")
            self.pb_WritePar.setEnabled(True)
            self.pb_WriteTara.setEnabled(True)
            self.printS("Spojení uspělo")
            '''for p in range(len(tabPageList)):
                for tw in list(tabPageList[p][1].values()):
                    tw.setEnabled(True)'''

            com.ReadParameters()
            if not valThread.running():
                valThread = threadpool.submit(updateValues)
        else: #Fail
            #currentTP = (oldIndex, self.tab_PLCTab.widget(oldIndex)) #If failed, assign old tab. #unecessary - plc already disconected, only paint red
            self.tabState("red")
            self.printS("Spojení selhalo")
            self.showBox("showerror","CHYBA PŘIPOJENÍ", "Nepodařilo se připojit ke stroji '"+str(pageIndex)+"' na adrese: " + com.IPList[pageIndex])

        self.l_PLCIndex.setText(str(currentTP[0]))
        self.printS("SwitchTP", "FIN")
        self.switching = False

    '''def newSamplePeriod(self):
        if self.comboBox.currentIndex() == 0: # 0.030s
            mes.sampletime = 30
            pass
        elif self.comboBox.currentIndex() == 1: # 0.1s
            mes.samplePeriod = 100
            mes.samplePeriodReal = 0.1
            pass
        if self.comboBox.currentIndex() == 0: # 0.30s
            mes.samplePeriod = 300
            mes.samplePeriodReal = 0.30
            pass
        elif self.comboBox.currentIndex() == 2: # 0.5s
            mes.samplePeriod = 500
            mes.samplePeriodReal = 0.5
            pass
        elif self.comboBox.currentIndex() == 3: # 1s
            mes.samplePeriod = 1000
            mes.samplePeriodReal = 1
            pass
        mes.resetPlot()
        pass'''
    def newSampleLenght(self):
        mes.samplelenght = self.sb_sampleLenght.value()
        com.setRegister(com.register_21, mes.samplelenght)
    def newSampleTime(self):
        if self.cb_sampleTime.currentIndex() == 0: # 0.030s = sampleLenght[0]
            mes.sampletime = .3
        elif self.cb_sampleTime.currentIndex() == 1: # 0.1s = sampleLenght[0]
            mes.sampletime = 1
        if self.cb_sampleTime.currentIndex() == 2: # 0.30s = sampleLenght[0]
            mes.sampletime = 3
        elif self.cb_sampleTime.currentIndex() == 3: # 0.5s = sampleLenght[0]
            mes.sampletime = 5
        elif self.cb_sampleTime.currentIndex() == 4: # 10s = len(sampleLenght)/ 1s = sampleLenght[0]
            mes.sampletime = 10
        com.setRegister(com.register_21, mes.samplelenght)
    #UI TW checks and corrections
    blockChange = False
    def dataChanged(self, itemWidget:QtWidgets.QTableWidgetItem):
        '''handles any changed data'''

        if self.blockChange:
            return
        self.blockChange = True

        name = itemWidget.tableWidget().objectName()
        pageIndex = int(name[-1]) #Get page number
        tw = name[3] + name[-3]
        if self.checkInput(itemWidget, tw):
            self.setItemColor("yellow", itemWidget)
            data.Refresh(pageIndex, tw)
            self.setLock("m", False)
        else:
            #! If triggered will let pass on different change
            self.setItemColor("red", itemWidget)
            itemWidget.setText("0")
            self.setLock("m", True)
        self.fixColor(itemWidget)
        self.blockChange = False
        pass
    def checkInput(self, itemWidget:QtWidgets.QTableWidgetItem, tw: str):
        '''Checks the input and corrects what delegate 'NumericDelegate' didn't handle'''
        try:
            float(itemWidget.text())
        except:
            pass
        else:
            curABS = float(itemWidget.tableWidget().item(itemWidget.row(), 0).text())
            curREL = float(itemWidget.tableWidget().item(itemWidget.row(), 1).text())
            oldABS = data.mainDatabase[currentTP[0]][tw][0][itemWidget.row()]
            oldREL = data.mainDatabase[currentTP[0]][tw][1][itemWidget.row()]

            newAbs, newRel = data.convertValue(curABS, curREL, oldABS, oldREL)
            if data.dataLimit[tw] != (None, None):
                if itemWidget.column() == 1 or itemWidget.column() == 0: # Relative is changed
                    if newAbs < data.dataLimit[tw][0]:
                        newAbs, newRel = data.convertValue(data.dataLimit[tw][0], oldREL, oldABS, oldREL)
                        itemWidget.tableWidget().item(itemWidget.row(), 1).setText(str('{0:g}'.format(newRel)))
                        itemWidget.tableWidget().item(itemWidget.row(), 0).setText(str('{0:g}'.format(newAbs)))
                    elif newAbs > data.dataLimit[tw][1]:
                        newAbs, newRel = data.convertValue(data.dataLimit[tw][1], oldREL, oldABS, oldREL)
                        itemWidget.tableWidget().item(itemWidget.row(), 1).setText(str('{0:g}'.format(newRel)))
                        itemWidget.tableWidget().item(itemWidget.row(), 0).setText(str('{0:g}'.format(newAbs)))
                '''if itemWidget.column() == 0: # Absolute is changed
                    if float(itemWidget.text()) < data.dataLimit[tw][0]:
                        itemWidget.setText(str(float(data.dataLimit[tw][0])))
                    elif float(itemWidget.text()) > data.dataLimit[tw][1]:
                        itemWidget.setText(str(float(data.dataLimit[tw][1])))'''
            if itemWidget.column() == 0:
                itemWidget.tableWidget().item(itemWidget.row(), 1).setText(str('{0:g}'.format(newRel)))
            elif itemWidget.column() == 1:
                itemWidget.tableWidget().item(itemWidget.row(), 0).setText(str('{0:g}'.format(newAbs)))
            elif itemWidget.column() == 2:
                if float(itemWidget.text()) < float(0):
                    itemWidget.setText(str(float(0)))
                elif float(itemWidget.text()) > (1):
                    itemWidget.setText(str(float(1)))
            elif itemWidget.column() == 3:
                if float(itemWidget.text()) < float(0):
                    itemWidget.setText(str(float(0)))
                elif float(itemWidget.text()) > float(60):
                    itemWidget.setText(str(float(60)))
            return True
        dash = False
        if itemWidget.text()[0] == '-':
            dash = True
        newText = ""
        for x in itemWidget.text():
            if x.isnumeric() or dash or x =='.':
                dash = False
            else:
                x = '.'
            newText += x
        itemWidget.setText(newText)
        try:
            float(itemWidget.text())
        except:
            return False
        else:
            curABS = float(itemWidget.tableWidget().item(itemWidget.row(), 0).text())
            curREL = float(itemWidget.tableWidget().item(itemWidget.row(), 1).text())
            oldABS = data.mainDatabase[currentTP[0]][tw][0][itemWidget.row()]
            oldREL = data.mainDatabase[currentTP[0]][tw][1][itemWidget.row()]

            newAbs, newRel = data.convertValue(curABS, curREL, oldABS, oldREL)
            if data.dataLimit[tw] != (None, None):
                if itemWidget.column() == 1:
                    if newAbs < data.dataLimit[tw][0]:
                        newAbs, newRel = data.convertValue(data.dataLimit[tw][0], curREL, oldABS, oldREL)
                        itemWidget.setText(str(float(data.dataLimit[tw][0])))
                    elif newAbs > data.dataLimit[tw][1]:
                        newAbs, newRel = data.convertValue(data.dataLimit[tw][1], curREL, oldABS, oldREL)
                if itemWidget.column() == 0:
                    if float(itemWidget.text()) < data.dataLimit[tw][0]:
                        itemWidget.setText(str(float(data.dataLimit[tw][0])))
                    elif float(itemWidget.text()) > data.dataLimit[tw][1]:
                        itemWidget.setText(str(float(data.dataLimit[tw][1])))
            if itemWidget.column() == 0:
                itemWidget.tableWidget().item(itemWidget.row(), 1).setText(str('{0:g}'.format(newRel)))
            elif itemWidget.column() == 1:
                itemWidget.tableWidget().item(itemWidget.row(), 0).setText(str('{0:g}'.format(newAbs)))
            elif itemWidget.column() == 2:
                if float(itemWidget.text()) < float(0):
                    itemWidget.setText(str(float(0)))
                elif float(itemWidget.text()) > (1):
                    itemWidget.setText(str(float(1)))
            elif itemWidget.column() == 3:
                if float(itemWidget.text()) < float(0):
                    itemWidget.setText(str(float(0)))
                elif float(itemWidget.text()) > float(60):
                    itemWidget.setText(str(float(60)))
            return True
    def fixColor(self, itemWidget:QtWidgets.QTableWidgetItem):
        '''workaround for a focused cell color'''
        itemWidget.tableWidget().clearSelection()
        '''newSS = (window.tw_Left1_0.styleSheet() +
            "QTableWidget::item:selected{"+
                "background-color: rgb" + str((itemWidget.background().color().red(),itemWidget.background().color().green(),itemWidget.background().color().blue())) +
            "}")'''
        '''self.blockChange = True
        if itemWidget.tableWidget().styleSheet() != newSS:
            itemWidget.tableWidget().setStyleSheet(newSS)
        self.blockChange = False'''
        pass

    #Buttons
    fileH = ""
    def LoadParameters(self):
        '''Loads Pars from a file'''
        root = tkinter.Tk()
        root.withdraw()
        with open(filedialog.askopenfile(initialdir=self.fileH, defaultextension=".json", initialfile="database.json", filetypes=[("Text files", ".json")]).name, "r") as file_path:
            root.destroy()
            # Reading from json file
            self.printS("Načítání dat z: ", file_path.name)
            data.mainDatabase = json.load(file_path)
            self.fileH = file_path.name
        data.Express()
        self.setItemColor("yellow")
        pass
    def SaveParameters(self):
        '''Saves Pars into a file'''
        root = tkinter.Tk()
        root.withdraw()
        with open(filedialog.asksaveasfile(initialdir=self.fileH, defaultextension=".json", initialfile="database.json", filetypes=[("Text files", ".json")]).name, "w") as file_path:
            root.destroy()
            # Serializing json
            '''json_object = json.dumps(data.mainDatabase, indent=2)
            json_object = re.sub('\s*{\s*"(.)": (\d+),\s*"(.)": (\d+)\s*}(,?)\s*', r'{"\1":\2,"\3":\4}\5', json_object)
            file_path.write(json_object)'''

            self.printS("Ukládání dat do: ", file_path.name)
            json.dump(data.mainDatabase, file_path, indent=None, sort_keys=True,separators=(",",":"))
            self.fileH = file_path.name
        pass
    def MovementDirection(self):
        pass
    def StartMovement(self, cancel=False):
        if cancel:
            self.pb_MoveStart.setText("START")
            return

        root = tkinter.Tk()
        root.withdraw()
        self.pb_MoveStart.setEnabled(False)
        if self.pb_MoveStart.text() == "STOP":
            if messagebox.askokcancel("POZOR!", "POHON SE ZASTAVÍ, SOUHLASÍTE?"):
                self.printS("Pohyb", self.pb_MoveStart.text())
                self.pb_MoveStart.setText("START")
        elif self.pb_MoveStart.text() == "START":
            if messagebox.askokcancel("POZOR!", "POHON SE ZAČNE POHYBOVAT, SOUHLASÍTE?"):
                self.printS("Pohyb", self.pb_MoveStart.text())
                self.pb_MoveStart.setText("STOP")

        self.pb_MoveStart.setEnabled(True)
        root.destroy()
        pass

    engineList=[False, False, False, False, False]
    def StartEngine(self, index):
        '''Handles engine buttons'''
        running = "QPushButton:checked{	background-color: green;}QPushButton{	background-color: red;}"
        #running2 = "background-color: green"
        idle = "QPushButton:checked{	background-color: yellow;}QPushButton{	background-color: white;}"

        if index != 0: # Switch button state UNLESS it is START
            self.engineList[index] = not self.engineList[index]
        if index == 0:
            x = "Všechny"
            if any(self.engineList[1:]):
                x = ""
                for i in range(len(self.engineList)):
                    if self.engineList[i]:
                        x = x + ("", "L1, ", "L2, ", "R1, ", "R2")[i]
            self.pb_engineStart.setEnabled(False)
            if not self.engineList[0] and self.showBox("askokcancel","MĚŘENÍ", "Měření nyní započne s motory: " + x +"\nSouhlasíte?"): # If Start is pressed AND confirmed: Start
                if not any(self.engineList[1:]): #If only START is pressed: Start Everything
                    self.pb_engineStart.setText("STOP")
                    self.pb_engineStart.setStyleSheet("background-color: green;")
                    for i, pb in enumerate(self.pb_engineList):
                        pb.setChecked(True)
                        self.engineList[i + 1] = True #[0] Will not inverse
                else: #if engines are selected: Start individually
                    '''for i, pb in enumerate(self.pb_engineList):
                        pb.setEnabled(self.engineList[i + 1])'''

                    self.pb_engineStart.setText("STOP ALL")
                    self.pb_engineStart.setStyleSheet("background-color: green;")
                for i, pb in enumerate(self.pb_engineList):
                    pb.setEnabled(False)

                self.engineList[0] = True
                window.printS("Měření", "ZAHÁJENO")
                self.setLock("p", True)
                mes.startMeasurement()
            else: #If start isn't pressed OR isn't confirmed: Stop
                if not self.engineList[0]: #If only START isn't pressed: Cancel Everything
                    self.pb_engineStart.setText("START")
                    self.pb_engineStart.setStyleSheet("")

                    '''for i, pb in enumerate(self.pb_engineList):
                        pb.setEnabled(True)
                        pb.setStyleSheet(idle)
                        self.engineList[i + 1] = False'''
                else: #If START is pressed AND engines are selected (Measurement was truly in progress): Stop Selected engines
                    self.pb_engineStart.setText("START ALL")
                    self.pb_engineStart.setStyleSheet("")
                    for i, pb in enumerate(self.pb_engineList):
                        pb.setEnabled(True)
                        pb.setChecked(False)
                        self.engineList[i + 1] = False #[0] Will not inverse
                    self.engineList[0] = False
                    self.setLock("p", False)
                    mes.stopMeasurement()
                    self.reDrawPlots()
            self.pb_engineStart.setEnabled(True)

            if self.engineList[0] and self.engineList[1]:
                self.pb_engineLeft.setStyleSheet(running)
            else:
                self.pb_engineLeft.setStyleSheet(idle)
            if self.engineList[0] and self.engineList[2]:
                self.pb_engineLeft_2.setStyleSheet(running)
            else:
                self.pb_engineLeft_2.setStyleSheet(idle)
            if self.engineList[0] and self.engineList[3]:
                self.pb_engineRight.setStyleSheet(running)
            else:
                self.pb_engineRight.setStyleSheet(idle)
            if self.engineList[0] and self.engineList[4]:
                self.pb_engineRight_2.setStyleSheet(running)
            else:
                self.pb_engineRight_2.setStyleSheet(idle)
        '''elif index == 1:
            pass
        elif index == 2:
            pass
        elif index == 3:
            pass
        elif index == 4:
            pass'''

        if index != 0: #If it is not the START that was pressed: adjust button look and Start look
            if not self.engineList[0] and not any(self.engineList[1:]): # if START isn't pressed: adjust look
                self.pb_engineStart.setText("START")
                self.pb_engineStart.setStyleSheet("background-color: white;")
            elif not self.engineList[0]: # if START isn't pressed: adjust look
                self.pb_engineStart.setText("START")
                self.pb_engineStart.setStyleSheet("background-color: yellow;")
            else: # If START is pressed ...
                self.pb_engineStart.setText("STOP")
                self.pb_engineStart.setStyleSheet("background-color: green;")
            self.setLock("p", False)
        pass
    #MainTab
    pm_block = False
    p_Locked = False
    m_Locked = True
    def setLock(self, tab:str, lock:bool):
        if tab == "p":
            self.p_Locked = lock
            #self.m_Locked = not lock
            #self.tab_MAINtab.widget(1).setEnabled(lock)
            self.tab_MAINtab.widget(0).setEnabled(not lock)
        if tab == "m":
            self.m_Locked = lock
            #self.p_Locked = not lock
            #self.tab_MAINtab.widget(0).setEnabled(lock)
            self.tab_MAINtab.widget(1).setEnabled(not lock)
        if lock:
            self.tab_MAINtab.setStyleSheet("QTabBar::tab:selected{background-color:white; color: black;}")
        else:
            self.tab_MAINtab.setStyleSheet("QTabBar::tab:selected{background-color:black; color: white;}")
        self.sb_sampleLenght.setEnabled(not lock)
        self.cb_sampleTime.setEnabled(not lock)
    def Parametrization(self, index):
        if index == 1 or self.pm_block:
            return
        if self.p_Locked:
            self.pm_block = True
            self.tab_MAINtab.setCurrentWidget(self.tab_MAINtab.widget(1))
            sleep(0.01)
            self.pm_block = False
            return

        '''if com.readyToSend:
            self.setLock("m", False)'''

        pass
    def Measurement(self, index):
        global valThread
        if index == 0 or self.pm_block:
            return
        if self.m_Locked:
            self.pm_block = True
            self.tab_MAINtab.setCurrentWidget(self.tab_MAINtab.widget(0))
            sleep(0.01)
            self.pm_block = False
            return
        pass

    #toMainThread
    def printS(self, string: str, description=""):
            '''Prints the state of the application on the bottom of the gui.\n
            !Processed in the MainThread!'''

            if not isinstance(threading.current_thread(), threading._MainThread):
                window.toMainThread('printS', (string, description))
                sleep(0.001) #Delay from the previous printS
                return
            if isinstance(string, tuple):
                description = string[1]
                string = string[0]
            elif isinstance(string, str):
                pass
            else:
                return

            if description != "":
                description = " ("+ description +")"

            window.statusbar.showMessage(string + description)
            print(string, description)
            '''    try:
                with open(logFilePath, 'a') as logfile:
                    logfile.write(string + " / " + description + "\n")
                    logfile.close()
            except:
                pass'''
    def showBox(self, box:str, title:str="", message:str=""):
        '''Workaround to show a message box. Can only be used in mainthread. !Processed in the MainThread!'''

        if not isinstance(threading.current_thread(), threading._MainThread):
            window.toMainThread('showBox', (box, title, message))
            sleep(0.001) #Delay from the previous printS
            return
        if isinstance(box, tuple):
            message = box[2]
            title = box[1]
            box = box[0]

        root = tkinter.Tk()
        root.withdraw()
        #root.grab_set_global()
        if box == "showerror":
            box = messagebox.showerror(title, message)
        if box == "askokcancel":
            box = messagebox.askokcancel(title, message)
        if box == "askyesno":
            box = messagebox.askyesno(title, message)

        #root.grab_release()
        return box
    def tabState(self, state: str):
        '''Changes color of currently selected page. !Processed in the MainThread!'''

        if not isinstance(threading.current_thread(), threading._MainThread):
            window.toMainThread('tabState', state)
            sleep(0.001)
            return
        if state == "red" or state == "yellow":
            for p in range(len(tabPageList)):
                for tw in list(tabPageList[p][1].values()):
                    tw.setEnabled(False)
            self.l_PLCIndex.setStyleSheet(
                "QTabBar::tab:selected{background-color: " + state + ";}"
                )
        if state == "green":
            if currentTP[0] != 0:
                for tw in list(tabPageList[currentTP[0]][1].values()):
                    tw.setEnabled(True)
            self.l_PLCIndex.setStyleSheet(
                "QTabBar::tab:selected{background-color: " + state + ";}"
                )

        self.tab_PLCTab.setStyleSheet(
            "QTabBar::tab:selected{background-color: " + state + ";}"
            )
    def setItemColor(self, color:str, itemWidget:QtWidgets.QTableWidgetItem=None):
        '''sets collor of itemWidget. If none, sets color of all itemWidgets of current tableWidget. !Processed in the MainThread!'''

        if not isinstance(threading.current_thread(), threading._MainThread):
            window.toMainThread('setItemColor', color)
            sleep(0.001)
            return

        self.blockChange = True
        if itemWidget is not None:
            itemWidget.setBackground(QColor(color))
        else:
            for tableWidget in list(tabPageList[currentTP[0]][1].values()):
                for r in range(tableWidget.rowCount()):
                    for c in range(tableWidget.columnCount()):
                        tableWidget.item(r, c).setBackground(QColor(color))
        self.blockChange = False
    def setLabelValues(self, PL1:float, PL2:float=0, PR1:float=0, PR2:float=0, FL1:float=0, FL2:float=0, FR1:float=0, FR2:float=0):
        '''Updates the value of Position and Force values.\n
        !Processed in the MainThread!'''

        if not isinstance(threading.current_thread(), threading._MainThread):
            window.toMainThread('setLabelValues', (PL1, PL2, PR1, PR2, FL1, FL2, FR1, FR2))
            sleep(0.001) #Delay from the previous printS
            return
        if isinstance(PL1, tuple):
            PL1, PL2, PR1, PR2, FL1, FL2, FR1, FR2 = PL1
        elif isinstance(PL1, float):
            pass
        else:
            return

        self.l_PosValueL_1.setText(str(PL1))
        self.l_PosValueL_2.setText(str(PL2))
        self.l_PosValueR_1.setText(str(PR1))
        self.l_PosValueR_2.setText(str(PR2))
        self.l_ForValueL_1.setText(str(FL1))
        self.l_ForValueL_2.setText(str(FL2))
        self.l_ForValueR_1.setText(str(FR1))
        self.l_ForValueR_2.setText(str(FR2))
        pass
    def setPlots(self, tuple):
        dataX, dataY = tuple
        check = True
        for tw in ("L1", "L2", "R1", "R2"):
            for dataType in ("Pos", "For"):
                if dataY[tw][0]:
                    if len(dataX) != len(dataY[tw][1][dataType]):
                        continue
                    if check:
                        check = False
                        if int(dataX[-1]*100) > int(graphList[tw][dataType].plotItem.getViewBox().state["viewRange"][0][1]*100):
                            graphList[tw][dataType].plotItem.getViewBox().setRange(xRange=(dataX[-1], dataX[-1] + (mes.sampletime * (mes.samplelenght * 10))))
                            for tw2 in ("L1", "L2", "R1", "R2"):
                                for dataType2 in ("Pos", "For"):
                                    if dataY[tw2][0]:
                                        graphList[tw2][dataType2].plotItem.getViewBox().clear()
                    #graphList[tw][dataType].plotItem.getViewBox().disableAutoRange()
                    graphList[tw][dataType].plotItem.plot(dataX, dataY[tw][1][dataType], pen=mkPen(color='black',width=2))
    def reDrawPlots(self):
        for tw in ("L1", "L2", "R1", "R2"):
            for dataType in ("Pos", "For"):
                graphList[tw][dataType].plotItem.getViewBox().clear()
                graphList[tw][dataType].plotItem.plot(mes.dataTime, mes.measuredData[tw][dataType], pen=mkPen(color='black',width=2))
app = QtWidgets.QApplication(sys.argv)
mainWindow = QtWidgets.QMainWindow()
window = MainWindow(mainWindow)

threadpool = ThreadPoolExecutor(5)

### Classes
class Database():
    '''Handles the internal database'''
    def __init__(self) -> None:
        self.mainDatabase = [
            {
                "L1":None,
                "L2":None,
                "R1":None,
                "R2":None,
            }
        ]
        '''[PageIndex]["tw"] -> Value'''
        self.dataLimit = {
            "L1": (None,None),
            "L2": (None,None),
            "R1": (None,None),
            "R2": (None,None)
        }
        '''["tw"](Min,Max) -> Value'''
        self.blockRefresh = False
    def Build(self, refresh=True):
        '''Builds an empty database'''
        self.mainDatabase = []
        for _ in range(window.tab_PLCTab.count()):
            self.mainDatabase.append(
                {
                "L1":[[0 for _ in range(20)] for _ in range(window.tw_Left1_0.columnCount())],
                "L2":[[0 for _ in range(20)] for _ in range(window.tw_Left1_0.columnCount())],
                "R1":[[0 for _ in range(20)] for _ in range(window.tw_Left1_0.columnCount())],
                "R2":[[0 for _ in range(20)] for _ in range(window.tw_Left1_0.columnCount())],
                }
            )
        if refresh:
            self.Refresh()
        pass
    def Refresh(self, pageIndex: int = None, tw: str = None):
        '''Loads QTable data into the database'''
        if self.blockRefresh:
            return
        if pageIndex is None and tw is None:
            for i in range(1, window.tab_PLCTab.count() - 1):
                for tw in ("L1", "L2", "R1", "R2"):
                    for c in range(4):
                        for r in range(20):
                            if r < tabPageList[i][1][tw].rowCount():
                                self.mainDatabase[i][tw][c][r] = float(tabPageList[i][1][tw].item(r,c).text())
                            else: self.mainDatabase[i][tw][c][r] = float(0)


        elif pageIndex is not None and tw is not None:
            for c in range(4):
                for r in range(20):
                    if r < tabPageList[pageIndex][1][tw].rowCount():
                        self.mainDatabase[pageIndex][tw][c][r] = float(tabPageList[pageIndex][1][tw].item(r,c).text())
                    else: self.mainDatabase[pageIndex][tw][c][r] = float(0)

        '''elif pageIndex is not None and tw is None:
            for r in range(20):
                for c in range(4):
                    self.mainDatabase[pageIndex]["L1"][c][r] = float(tabPageList[pageIndex][1]["L1"].item(r,c).text())
                    self.mainDatabase[pageIndex]["L2"][c][r] = float(tabPageList[pageIndex][1]["L2"].item(r,c).text())
                    self.mainDatabase[pageIndex]["R1"][c][r] = float(tabPageList[pageIndex][1]["R1"].item(r,c).text())
                    self.mainDatabase[pageIndex]["R2"][c][r] = float(tabPageList[pageIndex][1]["R2"].item(r,c).text())

        elif pageIndex is None and tw is not None:
            for i in range(1, window.tab_PLCTab.count()):
                for r in range(20):
                    for c in range(4):
                        self.mainDatabase[i][tw][c][r] = float(tabPageList[i][1][tw].item(r,c).text())
                        '''
        if tw is None: tw = "Všechny"
        if pageIndex is None: pageIndex = "Všechny"

        window.printS("Aktualizace dat", "strana: " + str(pageIndex) + ", list: " + tw)
        pass
    def Express(self):
        '''Expresses Database data into QTable'''
        self.blockRefresh = True
        window.blockChange = True

        for i in range(1, window.tab_PLCTab.count()):
            for tw in ("L1", "L2", "R1", "R2"):
                for c in range(4):
                    for r in range(tabPageList[i][1][tw].rowCount()):
                        if c == 1: #Relative Row
                            pass
                            #self.mainDatabase[i][tw][1][r] = self.convertValue(self.mainDatabase[i][tw][0][r], "REL")[1]
                        tabPageList[i][1][tw].item(r,c).setText(str('{0:g}'.format(self.mainDatabase[i][tw][c][r])))

        '''elif pageIndex is not None and tw is not None:
            for c in range(4):
                for r in range(tabPageList[pageIndex][1][tw].rowCount()):
                    if c == 1:
                        self.mainDatabase[pageIndex][tw][1][r] = self.convertValue(self.mainDatabase[pageIndex][tw][0][r], "REL")
                    tabPageList[pageIndex][1][tw].item(r,c).setText(str('{0:g}'.format(self.mainDatabase[pageIndex][tw][c][r])))
        elif pageIndex is None and tw is not None:
            for i in range(1, window.tab_PLCTab.count()):
                for c in range(4):
                    for r in range(tabPageList[i][1][tw].rowCount()):
                        if c == 1:
                            self.mainDatabase[i][tw][1][r] = self.convertValue(self.mainDatabase[i][tw][0][r], "REL")
                        tabPageList[i][1][tw].item(r,c).setText(str('{0:g}'.format(self.mainDatabase[i][tw][c][r])))

        elif pageIndex is not None and tw is None:
            for c in range(4):
                for r in range(tabPageList[pageIndex][1][tw].rowCount()):
                    for tw in ("L1", "L2", "R1", "R2"):
                        if c == 1:
                            self.mainDatabase[pageIndex][tw][1][r] = self.convertValue(self.mainDatabase[pageIndex][tw][0][r], "REL")
                        tabPageList[pageIndex][1][tw].item(r,c).setText(str('{0:g}'.format(self.mainDatabase[pageIndex][tw][c][r])))'''

        window.printS("Aktualizace panelů")
        self.blockRefresh = False
        window.blockChange = False
        pass
    def convertValue(self, ABS: float, REL:float, oldAbs:float, oldRel:float):
        '''Takes current and old value of ABS/REL and calculates what the oposite should be'''
        if REL > oldRel:
            newABS = oldAbs + (REL - oldRel)
        elif REL < oldRel:
            newABS = oldAbs - (oldRel - REL)
        else:
            newABS = ABS

        if ABS > oldAbs:
            newREL = oldRel + (ABS - oldAbs)
        elif ABS < oldAbs:
            newREL = oldRel - (oldAbs - ABS)
        else:
            newREL = REL
        return newABS, newREL

data = Database()
class LRLibrary():
    discreetInputs = []
    coils = []
    inputRegisters = []
    holdingRegisters = []
    repeat = False
    delay = 1
    busy = False
    loadTime = 0
    def UpdateLibrary(force=False, blank=False):
        if blank: return

        highestAddress = max(
            com.register_0,
            com.register_1,
            com.register_2,
            com.register_3,
            com.register_4,
            com.register_5,
            com.register_6,
            com.register_7,
            com.register_8,
            com.register_9,
            com.register_10,
            com.register_11,
            com.register_12,
            com.register_13,
            com.register_14,
            com.register_15,
            com.register_16,
            com.register_17,
            com.register_18,
            com.register_19,
            com.register_20,
            com.registerL1,
            com.registerL2,
            com.registerR1,
            com.registerR2,
            com.registerL1For,
            com.registerL2For,
            com.registerR1For,
            com.registerR2For,
            com.registerL1Pos,
            com.registerL2Pos,
            com.registerR1Pos,
            com.registerR2Pos,
        ) + mes.samplelenght

        i = 1
        transferSize = highestAddress
        while transferSize > 100:
            transferSize = ceil(highestAddress / i)
            i += 1
        while True: # Do While
            LRLibrary.holdingRegisters = [0]*highestAddress
            start_time = time()

            registers = []
            while LRLibrary.busy and not force:
                pass
            LRLibrary.busy = True
            timeout = 0
            i = 0
            while i < highestAddress:
                try:
                    if not com.plc_server.is_open():
                        com.plc_server.open()
                    registers.extend(com.plc_server.read_holding_registers(i, transferSize))
                    i += transferSize
                except:
                    timeout += 1
                    if timeout > 5:
                        break
                    continue
            LRLibrary.busy = False
            LRLibrary.holdingRegisters = registers
            LRLibrary.loadTime = time() - start_time
            if not LRLibrary.repeat:
                break
            sleep(LRLibrary.delay)
        com.plc_server.close()
        if timeout > 5:
            return False
        else:
            return True
    LRLThread = threadpool.submit(UpdateLibrary, blank=True)
class NumericDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = super(NumericDelegate, self).createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            reg_ex = QRegExp("^(?:-(?:[1-9](?:\\d{0,2}(?:,\\d{3})+|\\d*))|(?:0|(?:[1-9](?:\\d{0,2}(?:,\\d{3})+|\\d*))))(?:.\\d+|)$")
            validator = QRegExpValidator(reg_ex, editor)
            editor.setValidator(validator)
        return editor

class Communication():
    def __init__(self) -> None:
        window.pb_WritePar.clicked.connect(self.WriteParameters)
        window.pb_WriteTara.clicked.connect(self.WriteTara)
        self.IPList = [
            "0.0.0.0",
            "0.0.0.0",
            "0.0.0.0",
            "0.0.0.0",
            "0.0.0.0",
            "0.0.0.0",
            "0.0.0.0",
            "0.0.0.0",
            socket.gethostbyname(socket.gethostname())
        ]
        self.plc_server = ModbusClient(timeout=5, auto_close=False, auto_open=True)
        self.readyToSend = False
        self.cancelConn = False
        self.referenceWord = [False]*3
        self.comForm = "Modbus"
        '''
        register0\n
        0(1) = ref_START\n
        1(2) = ref_OK\n
        2(4) = ref_FAULT\n
        '''
        self.packetWord = [False]*3
        '''
        register1\n
        0(1) = Stav_pos_P1_AKT\n
        1(2) = Stav_for_AKT\n
        2(4) = Stav_temp_AKT\n
        '''
        self.controlWord = [False]*12

        self.register_0 = 0
        '''
        mereni_done,\n
        ref_OK,\n
        ref_err,\n'''
        self.register_1 = 1
        '''
        stav_sila_M1,\n
        stav_sila_M2,\n
        stav_sila_M3,\n
        stav_sila_M4,\n
        stav_power_M1,\n
        stav_power_M2,\n
        stav_power_M3,\n
        stav_power_M4'''
        self.register_2 = 2
        '''
        start mereni, \n
        tara
        '''
        self.register_3 = 3
        '''akt_pozice_m_1'''
        self.register_4 = 4
        '''akt_pozice_m_2'''
        self.register_5 = 5
        '''akt_pozice_m_3'''
        self.register_6 = 6
        '''akt_pozice_m_4'''
        self.register_7 = 7
        '''akt_sila_m_1'''
        self.register_8 = 8
        '''akt_sila_m_2'''
        self.register_9 = 9
        '''akt_sila_m_3'''
        self.register_10 = 10
        '''akt_sila_m_4'''
        self.register_11 = 11
        '''max_vyska_M_1'''
        self.register_12 = 12
        '''min_vyska_M_1'''
        self.register_13 = 13
        '''max_vyska_M_2'''
        self.register_14 = 14
        '''min_vyska_M_2'''
        self.register_15 = 15
        '''max_vyska_M_3'''
        self.register_16 = 16
        '''min_vyska_M_3'''
        self.register_17 = 17
        '''max_vyska_M_4'''
        self.register_18 = 18
        '''min_vyska_M_4'''
        self.register_19 = 19
        '''poz_pohyb_motor'''
        self.register_20 = 20
        '''poz_vyska_man'''
        self.register_21 = 21
        '''sampleLenght'''
        self.register_22 = 22
        '''sampleTime'''
        self.registerL1 = 30
        '''set_MTX_motor_1'''
        self.registerL2 = 91
        '''set_MTX_motor_2'''
        self.registerR1 = 152
        '''set_MTX_motor_3'''
        self.registerR2 = 213
        '''set_MTX_motor_4'''
        self.registerL1For = 320
        '''MTX_akt_sila_1'''
        self.registerL2For = 331
        '''MTX_akt_sila_2'''
        self.registerR1For = 342
        '''MTX_akt_sila_3'''
        self.registerR2For = 353
        '''MTX_akt_sila_4'''
        self.registerL1Pos = 364
        '''MTX_akt_poloha_1'''
        self.registerL2Pos = 375
        '''MTX_akt_poloha_2'''
        self.registerR1Pos = 386
        '''MTX_akt_poloha_3'''
        self.registerR2Pos = 397
        '''MTX_akt_poloha_4'''
        pass
    def connect(self, index, blank=False):
        '''Connects either using Modbus or a Library'''
        global stopUpdate
        global valThread
        if blank: return #blank is just a set up. If thread is already running, return

        #self.cancelConn = False
        '''if index < 5:
            return True #Debug'''

        #window.updateSettings()
        if self.readyToSend:
            self.readyToSend = False
        try:
            self.plc_server.host(self.IPList[index])
        except:
            return False

        window.printS("Připojování k " + str(self.IPList[index]) +":"+ str(self.plc_server.port()))

        if not self.plc_server.open():  # Connection Fail
            #self.plc_server.host(self.IPList[index])
            if self.cancelConn:
                self.cancelConn = False
                #self.plc_server.close()
                return False
            return False
        else:                           # Connection Success
            self.plc_server.host(self.IPList[index])
            if self.cancelConn:
                self.cancelConn = False
                return False
            self.readyToSend = True
            return True
    conThread = threadpool.submit(connect, blank=True)
    def connectionLost(self):
        global stopUpdate
        self.readyToSend = False
        self.cancelConn = True
        stopUpdate = True
        window.setLock("m", True)
        window.tabState("red")

        window.printS("Spojení ztraceno.")
        pass
    def testConnection(self):
        '''Tries to connect ten times. If fails, connection is lost'''
        #if com.comForm == "Modbus":
        i = 0

        while not self.plc_server.open() and i < 10:
            sleep(0.1)
            i += 1
        if i >= 10:
            return False

        '''elif com.comForm == "Library":

            while not bool(LibraryHandler.InitAD()) and i < 10:
                sleep(0.1)
                i += 1
            if i >= 10:
                return False'''
        return True
    def disconnect(self):
        self.readyToSend = False
        while LRLibrary.busy:
            pass
        LRLibrary.busy = True
        if self.plc_server.is_open():
            self.plc_server.close()
        LRLibrary.busy = False
        return True

    def WriteParameters(self):
        '''Sets value of registers 'set_MTX_motor_1' to 'set_MTX_motor_4' '''
        prepData = copy.deepcopy(data.mainDatabase[int(currentTP[0])])
        debug = False

        for tw in ("L1", "L2", "R1", "R2"):
            if len(prepData[tw]) != 3:
                del prepData[tw][1]
            if debug:
                prepData[tw][0] = [random.randint(0, 200) for i in range(len(prepData[tw][0]))]
                prepData[tw][1] = [random.randint(0, 200) for i in range(len(prepData[tw][1]))]
                prepData[tw][2] = [random.randint(0, 200) for i in range(len(prepData[tw][2]))]

        registers = [[], [], [], []]
        for c in range(len(prepData["L1"])):
            for r in range(len(prepData["L1"][c])):
                prepData["L1"][c][r] = int(prepData["L1"][c][r]*100)
            registers[0].extend(prepData["L1"][c])
        for c in range(len(prepData["L2"])):
            for r in range(len(prepData["L2"][c])):
                prepData["L2"][c][r] = int(prepData["L2"][c][r]*100)
            registers[1].extend(prepData["L2"][c])
        for c in range(len(prepData["R1"])):
            for r in range(len(prepData["R1"][c])):
                prepData["R1"][c][r] = int(prepData["R1"][c][r]*100)
            registers[2].extend(prepData["R1"][c])
        for c in range(len(prepData["R2"])):
            for r in range(len(prepData["R2"][c])):
                prepData["R2"][c][r] = int(prepData["R2"][c][r]*100)
            registers[3].extend(prepData["R2"][c])

        i = 0
        while True:
            self.setRegisters(com.registerL1, registers[0])
            self.setRegisters(com.registerL2, registers[1])
            self.setRegisters(com.registerR1, registers[2])
            self.setRegisters(com.registerR2, registers[3])
            sleep(0.5)
            if (
                {
                    "L1": [self.getRegisters(com.registerL1, 20), self.getRegisters(com.registerL1 + 20, 20), self.getRegisters(com.registerL1 + 40, 20)],
                    "L2": [self.getRegisters(com.registerL2, 20), self.getRegisters(com.registerL2 + 20, 20), self.getRegisters(com.registerL2 + 40, 20)],
                    "R1": [self.getRegisters(com.registerR1, 20), self.getRegisters(com.registerR1 + 20, 20), self.getRegisters(com.registerR1 + 40, 20)],
                    "R2": [self.getRegisters(com.registerR2, 20), self.getRegisters(com.registerR2 + 20, 20), self.getRegisters(com.registerR2 + 40, 20)]
                }   == prepData
                or i > 5
                ):
                break
            i += 1
        if i >= 5:
            window.setItemColor("red")
            window.printS("WriteParameters", "Chyby při zapsávání dat do PLC" + str(currentTP[0]) + "!")
            return False
        window.setItemColor("green")
        window.printS("WriteParameters", "Data zapsána do PLC" + str(currentTP[0]))
        window.setLock("m", False)
        return True
    def ReadParameters(self):
        '''Reads value of registers 'set_MTX_motor_1' to 'set_MTX_motor_4' '''
        data.Build(False)
        LRLibrary.UpdateLibrary()
        rawL1 = (
            self.getRegisters(self.registerL1, 20),
            self.getRegisters(self.registerL1 + 20, 20),
            self.getRegisters(self.registerL1 + 40, 20)
        )
        rawL2 = (
            self.getRegisters(self.registerL2, 20),
            self.getRegisters(self.registerL2 + 20, 20),
            self.getRegisters(self.registerL2 + 40, 20)
        )
        rawR1 = (
            self.getRegisters(self.registerR1, 20),
            self.getRegisters(self.registerR1 + 20, 20),
            self.getRegisters(self.registerR1 + 40, 20)
        )
        rawR2 = (
            self.getRegisters(self.registerR2, 20),
            self.getRegisters(self.registerR2 + 20, 20),
            self.getRegisters(self.registerR2 + 40, 20)
        )
        for c in range(len(rawL1)):
            for r in range(len(rawL1[c])):
                rawL1[c][r] = float(rawL1[c][r]/100)
        for c in range(len(rawL2)):
            for r in range(len(rawL2[c])):
                rawL2[c][r] = float(rawL2[c][r]/100)
        for c in range(len(rawR1)):
            for r in range(len(rawR1[c])):
                rawR1[c][r] = float(rawR1[c][r]/100)
        for c in range(len(rawR2)):
            for r in range(len(rawR2[c])):
                rawR2[c][r] = float(rawR2[c][r]/100)
        data.mainDatabase[int(currentTP[0])]["L1"][0] = rawL1[0]
        data.mainDatabase[int(currentTP[0])]["L1"][2] = rawL1[1]
        data.mainDatabase[int(currentTP[0])]["L1"][3] = rawL1[2]
        data.mainDatabase[int(currentTP[0])]["L2"][0] = rawL2[0]
        data.mainDatabase[int(currentTP[0])]["L2"][2] = rawL2[1]
        data.mainDatabase[int(currentTP[0])]["L2"][3] = rawL2[2]
        data.mainDatabase[int(currentTP[0])]["R1"][0] = rawR1[0]
        data.mainDatabase[int(currentTP[0])]["R1"][2] = rawR1[1]
        data.mainDatabase[int(currentTP[0])]["R1"][3] = rawR1[2]
        data.mainDatabase[int(currentTP[0])]["R2"][0] = rawR2[0]
        data.mainDatabase[int(currentTP[0])]["R2"][2] = rawR2[1]
        data.mainDatabase[int(currentTP[0])]["R2"][3] = rawR2[2]

        data.dataLimit["L1"] = (self.getRegisters(self.register_12), self.getRegisters(self.register_11))
        data.dataLimit["L2"] = (self.getRegisters(self.register_14), self.getRegisters(self.register_13))
        data.dataLimit["R1"] = (self.getRegisters(self.register_16), self.getRegisters(self.register_15))
        data.dataLimit["R2"] = (self.getRegisters(self.register_18), self.getRegisters(self.register_17))

        data.Express()
        window.setItemColor("green")
        window.printS("ReadParameters", "Data přečtena z PLC" + str(currentTP[0]))
    def WriteTara(self):
        self.setRegister(self.register_2, 1, 1)

    busy = False
    def getRegisters(self, address:int, amount:int=None, debug=False):
        '''Gets a register from the LocalRegisterLibrary\n
        If 'amount' has value, returns list of registers'''
        if amount is None:
            if debug:
                return random.randrange(0, 255)
            registers = LRLibrary.holdingRegisters[address]
            #registers = self.plc_server.read_holding_registers(address, 1)[0]
            registers = numpy.int16(registers)

        else:
            if debug:
                return [random.randrange(0, 255) for _ in range(amount)]
            registers = LRLibrary.holdingRegisters[address:address+amount]
            #registers = self.plc_server.read_holding_registers(address, amount)
            registers = [numpy.int16(value) for value in registers]
        return registers
    def setRegister(self, address:int, value:int, wordIndex:int=None):
        '''Sets value of the target register to 'value' if 'wordIndex' is None\n
        Otherwise it will treat register as word and sets target index of the word to 'value' '''
        if wordIndex is None:
            register = numpy.uint16(value)
        else:
            register = self.getRegisters(address)
            if register is False:
                return False

            oldWord = self.registerToWord(register)
            word = oldWord[:wordIndex] + str(value) + oldWord[wordIndex + 1:]
            register = int(word[::-1], 2)

        while LRLibrary.busy:
            pass
        LRLibrary.busy = True
        try:
            while True:
                '''if not self.plc_server.is_open():
                    if not self.plc_server.open():
                        return False'''

                self.plc_server.write_single_register(address, register)

                LRLibrary.UpdateLibrary(force=True)
                if self.getRegisters(address) == register:
                    break
        except:
            LRLibrary.busy = False
            return False
        else:
            LRLibrary.busy = False
            return True
    def setRegisters(self, address:int, registers:list):
        while LRLibrary.busy:
            pass
        LRLibrary.busy = True
        try:
            while True:
                '''if not self.plc_server.is_open():
                    if not self.plc_server.open():
                        return False'''

                self.plc_server.write_multiple_registers(address, registers)

                LRLibrary.UpdateLibrary(force=True)
                if self.getRegisters(address, len(registers)) == registers:
                    break
        except:
            LRLibrary.busy = False
            return False
        else:
            LRLibrary.busy = False
            return True
        pass

    def registerToWord(self, register, wordIndex=None, length=12):
        '''Returns register as word
        if 'wordIndex' has value, will return only value'''
        if wordIndex is None:
            word = bin(register)[2:].rjust(length, '0')[::-1]
        else:
            word = bin(register)[2:].rjust(length, '0')[::-1][wordIndex]
        return word
    def wordToList(self, word:str):
        '''returns a word as an array of bool'''
        word = list(word)
        for i in range(len(word)):
            word[i] = bool(int(word[i]))
        return word
com = Communication()

#Handles measurement
class MeasurementHandler():
    def __init__(self) -> None:
        self.currentValues = [0, 0, 0]
        self.measurementEnabled = False
        self.measuredData = {
            "L1": {"Pos": [0], "For":[0]},
            "L2": {"Pos": [0], "For":[0]},
            "R1": {"Pos": [0], "For":[0]},
            "R2": {"Pos": [0], "For":[0]},
        }
        self.dataTime = [0]
        #self.amplitude = 0
        #self.frequency = 0

        self.samplelenght = 10
        ''' pocet vzorku v baliku dat - podle toho, jak nastaveno v PLC!!!'''
        self.sampletime = 0.3

        self.updateRate = 0.1
        self.showedRange = 10.0
        self.samplePeriod = 1
        self.samplePeriodReal = 0.1 # [s]
        '''nastaveni casoveho kroku merenych dat - musi byt stejne jako v PLC!!!!'''

        self.TimeInterFileWrite = 60 # [s]
        '''interval zápisu dat do souboru'''
        self.FileName = None
        # inicializace identifikace souboru
        pass

    def startMeasurement(self):
        '''Starts or resumes the measurement '''
        while True:
            if window.showBox("askyesno", "DATA BUDOU UKLÁDÁNA", "Naměřená data budou ukládána do složky Data, souhlasíte?"):
                self.gener_soubor()
                break
            else:
                if window.showBox("askokcancel", "DATA BUDOU ZTRACENA", "Přejete si zahodit naměřená data?"):
                    break
        for tw in ("L1", "L2", "R1", "R2"):
            for type in ("Pos", "For"):
                graphList[tw][type].plotItem.clear()
                graphList[tw][type].plotItem.getViewBox().setRange(xRange=(0, (mes.sampletime * (mes.samplelenght * 10))))

        self.measuredData = {
            "L1": {"Pos": [0], "For":[0]},
            "L2": {"Pos": [0], "For":[0]},
            "R1": {"Pos": [0], "For":[0]},
            "R2": {"Pos": [0], "For":[0]},
        }
        self.dataTime = [0]
        self.timeIndex = 0

        for tw in ("L1", "L2", "R1", "R2"):
            for type in ("Pos", "For"):
                graphList[tw][type].getPlotItem().getViewBox().setMouseEnabled(x=False)
            graphList[tw]["Pos"].setXLink(graphList["L1"]["Pos"])
            graphList[tw]["Pos"].setXLink(graphList["L2"]["Pos"])
            graphList[tw]["Pos"].setXLink(graphList["R1"]["Pos"])
            graphList[tw]["Pos"].setXLink(graphList["R2"]["Pos"])
            graphList[tw]["Pos"].setXLink(graphList[tw]["For"])

            graphList[tw]["For"].setXLink(graphList["L1"]["For"])
            graphList[tw]["For"].setXLink(graphList["L2"]["For"])
            graphList[tw]["For"].setXLink(graphList["R1"]["For"])
            graphList[tw]["For"].setXLink(graphList["R2"]["For"])


        com.setRegister(com.register_2, 1, 0) #Sends a signal that measurement started
        self.measurementEnabled = True
    def stopMeasurement(self):
        '''Stops and clears the graphs or pauses measurement'''
        global stopUpdate
        global valThread
        self.measurementEnabled = False
        com.setRegister(com.register_2, 0, 0) #Sends a signal that measurement stopped
        com.setRegister(com.register_0, 0, 0) #Sends a signal that measurement stopped

        data = [mes.dataTime, self.measuredData["L1"], mes.measuredData["L2"], mes.measuredData["R1"], mes.measuredData["R2"]]
        self.saveDataToFile(data, True)

        for tw in ("L1", "L2", "R1", "R2"):
            for type in ("Pos", "For"):
                graphList[tw][type].getPlotItem().getViewBox().setMouseEnabled(x=True)
                graphList[tw][type].setXLink(graphList[tw][type])

        stopUpdate = True
        sleep(0.5)
        if not valThread.running():
            valThread = threadpool.submit(updateValues)

    def gener_soubor(self):
        # založení souboru dat
        if not os.path.exists('Data'): # vytvori adresar pro data pokud neexistuje
            os.makedirs('Data')
        FileName = str(datetime.datetime.now())
        FileName = FileName.replace(':','_')
        FileName = FileName.replace('.','_')
        #window.l_file.setText(FileName + '.txt')
        FileName = os.path.join(os.getcwd(), 'Data', FileName + '.txt')
        self.FileName = FileName
        with open(self.FileName,'at') as f: # otevření souboru, zapsani a zavreni
            f.write(
                't[s]' +
                '\t' + 'L1[mm]'+ '\t' + 'L2[mm]'+ '\t' + 'R1[mm]'+ '\t' + 'R2[mm]' +
                '\t' + 'L1[N]' + '\t' + 'L2[N]' + '\t' + 'R1[N]' + '\t' + 'R2[N]' + '\n') # tisk hlavicek sloupcu do souboru¨
        self.readLines = -1
    readLines = -1
    def saveDataToFile(self, data, final=False):
        '''if not (len(data[0]) == len(data[1]) == len(data[2]) == len(data[3]) == len(data[4])):
            return'''
        try:
            if self.FileName != None:
                # zapis zbylych raw dat
                if not os.path.exists(self.FileName): # pokud doslo ke smazani souboru, vytvori se novy s hlavickou
                    self.gener_soubor()
                with open(self.FileName, "a") as f:
                    ###
                    for i in range(1, 5):
                        for type in ("Pos", "For"):
                            while len(data[i][type]) < len(data[0]):
                                data[i][type].append(0)
                                pass
                    steps = self.samplePeriod # pocet kroku odpovidajici jedne periode vybraneho mereni
                    stepsLimit = len(self.dataTime) # maximalni pocet kroku zaznamu nez dojde k file write
                    if (steps <= stepsLimit): # odpovida vyberu periody 0.1;0.2;0.5;1;2;5;10;60s ne vice
                        for i in range(self.readLines + 1, len(self.dataTime), steps):
                            if i == self.readLines:
                                i += 1
                            line = (
                                format(data[0][i],'.3f')+'\t'+
                                format(data[1]["Pos"][i],'.0f')+'\t'+
                                format(data[1]["For"][i],'.0f')+'\t'+
                                format(data[2]["Pos"][i],'.0f')+'\t'+
                                format(data[2]["For"][i],'.0f')+'\t'+
                                format(data[3]["Pos"][i],'.0f')+'\t'+
                                format(data[3]["For"][i],'.0f')+'\t'+
                                format(data[4]["Pos"][i],'.0f')+'\t'+
                                format(data[4]["For"][i],'.0f')+'\n'
                                )
                            f.write(line) # zapis lajny do souboru
                            self.readLines = i
                    else:
                        if (data[0][self.readLines + 1] == 0.0): # 2min a delsi perioda - zapise jen jeden radek odpovidajici startu mereni
                            i = self.readLines + 1
                            line = (
                                format(data[0][i],'.3f')+'\t'+
                                format(data[1]["Pos"][i],'.0f')+'\t'+
                                format(data[1]["For"][i],'.0f')+'\t'+
                                format(data[2]["Pos"][i],'.0f')+'\t'+
                                format(data[2]["For"][i],'.0f')+'\t'+
                                format(data[3]["Pos"][i],'.0f')+'\t'+
                                format(data[3]["For"][i],'.0f')+'\t'+
                                format(data[4]["Pos"][i],'.0f')+'\t'+
                                format(data[4]["For"][i],'.0f')+'\n'
                                )
                            f.write(line) # zapis lajny do souboru
                            self.readLines = i
                    ###
                '''with open(self.FileName, 'at') as f: # otevreni, zapis, zavření souboru
                    while self.readLines < len(self.dataTime):
                        line = (
                            format(data[0][self.readLines],'.3f')+'\t'+
                            format(data[1][self.readLines],'.3f')+'\t'+
                            format(data[2][self.readLines],'.3f')+'\t'+
                            format(data[3][self.readLines],'.3f')+'\n'
                            )
                        self.readLines += 1'''
                window.printS("Saved to file", str(self.FileName))
                if final:
                    self.FileName = None # identifikace souboru - zruseni informace o predchozim souboru
                    #window.l_file.setText("N/A")
            else:
                window.printS("Failed to save to File!", str(self.FileName))
        except:
            messagebox.showinfo("Disabled", "Funkce je limitovaná, pro testování nechejte všechny motory zapnuté!")

    '''if False, pauses refreshPlot'''
    timeIndex = 0
    def refreshPlot(self, blank=False):
        '''adds value to all plots'''
        if blank: return
        if self.measurementEnabled:
            while self.resetting:
                sleep(.01)
                pass

            DataL1 = {"Pos": [], "For": []}
            DataL2 = {"Pos": [], "For": []}
            DataR1 = {"Pos": [], "For": []}
            DataR2 = {"Pos": [], "For": []}
            DataY = {
                "L1": (window.engineList[1], DataL1),
                "L2": (window.engineList[2], DataL2),
                "R1": (window.engineList[3], DataR1),
                "R2": (window.engineList[4], DataR2)
            }
            #plotting graphs 'plot' is always 'None'. All graphs update at once
            for tw in ("L1", "L2", "R1", "R2"):
                if DataY[tw][0]:
                    for dataType in ("Pos", "For"):
                        if self.timeIndex > self.samplePeriod - 1:
                            timePeriod = self.timeIndex - self.samplePeriod
                            DataX = [self.dataTime[timePeriod]]
                            DataY[tw][1][dataType] = [mes.measuredData[tw][dataType][timePeriod]]
                        else:
                            DataX = []
                            DataY[tw][1][dataType] = []
            while self.timeIndex < len(self.dataTime):
                DataX.append(self.dataTime[self.timeIndex])
                for tw in ("L1", "L2", "R1", "R2"):
                    if DataY[tw][0]:
                        for dataType in ("Pos", "For"):
                            if len(mes.measuredData[tw][dataType]) <= self.timeIndex:
                                continue
                            #if self.timeIndex == 0:
                            DataY[tw][1][dataType].append(mes.measuredData[tw][dataType][self.timeIndex])
                self.timeIndex += self.samplePeriod

            #window.setPlots((DataX, DataY1, DataY2, DataY3))
            window.toMainThread('setPlots', (DataX, DataY))
            pass

    plotThread = threadpool.submit(refreshPlot, blank=True)
    resetting = False
    def resetPlot(self):
        '''Resets the value of all graphs'''
        #plotting graphs
        DataX1 = {"Pos": [], "For": []}
        DataX2 = {"Pos": [], "For": []}
        DataX3 = {"Pos": [], "For": []}
        DataX4 = {"Pos": [], "For": []}
        DataL1 = {"Pos": [], "For": []}
        DataL2 = {"Pos": [], "For": []}
        DataR1 = {"Pos": [], "For": []}
        DataR2 = {"Pos": [], "For": []}
        self.resetting = True
        self.timeIndex = 0

        for i, twData in enumerate(list(self.measuredData.values())):
            dataX = (DataX1, DataX2, DataX3, DataX4)[i]
            dataY = (DataL1, DataL2, DataR1, DataR2)[i]
            for dataType in ("Pos", "For"):
                j = 0
                while j < len(twData[dataType]):
                    dataX[dataType].append(self.dataTime[j])
                    dataY[dataType].append(twData[dataType][j])
                    j += self.samplePeriod
                graphList[("L1", "L2", "R1", "R2")[i]][dataType].plotItem.clear()
                graphList[("L1", "L2", "R1", "R2")[i]][dataType].plotItem.plot(dataX[dataType], dataY[dataType], pen=mkPen(color='b',width=2))
        '''if plot is None or plot == 0:
            pass
        if plot is None or plot == 1:
            i = 0
            while i < len(self.left2):
                DataX2.append(self.dataTime[i])
                DataL2.append(self.left2[i])
                i += self.samplePeriod
            window.Plot2.plotItem.clear()
            window.Plot2.plotItem.plot(DataX2, DataL2, pen=mkPen(color='g',width=2))
            pass
        if plot is None or plot == 2:
            i = 0
            while i < len(self.right1):
                DataX3.append(self.dataTime[i])
                DataR1.append(self.right1[i])
                i += self.samplePeriod
            window.Plot3.plotItem.clear()
            window.Plot3.plotItem.plot(DataX3, DataR1, pen=mkPen(color='r',width=2))
            pass'''
        self.timeIndex = j - self.samplePeriod
        self.resetting = False
mes = MeasurementHandler()


###Global Vars
currentTP = (0, window.tp_PLCpage_0)
'''Contains index and pointer at currently selected PLCpage'''
tabPageList = [(
        window.tp_PLCpage_0,
        {
            "L1":window.tw_Left1_0,
            "L2":window.tw_Left2_0,
            "R1":window.tw_Right1_0,
            "R2":window.tw_Right2_0,
        }
    )
]
'''Contains pointers at every PLCPage and their tableWidgets'''
graphList = {
    "L1":{"Pos": window.pw_PlotPL_1, "For": window.pw_PlotFL_1},
    "L2":{"Pos": window.pw_PlotPL_2, "For": window.pw_PlotFL_2},
    "R1":{"Pos": window.pw_PlotPR_1, "For": window.pw_PlotFR_1},
    "R2":{"Pos": window.pw_PlotPR_2, "For": window.pw_PlotFR_2},
}
'''Contains pointers at every PlotWidget (graphList[tw][0/1 - Pos/For])'''
stopUpdate = False
def updateValues(blank=False):
    '''The update loop. Will repeat until stopUpdate is set to True\n
    Only in ThreadPool!'''
    global stopUpdate
    if blank: return #blank is just a set up. If thread is already running, return

    pass
    window.printS("Aktualizační smyčka zapnuta.")
    LRLibrary.UpdateLibrary()
    posReg = com.getRegisters(com.register_2)

    com.packetWord = com.wordToList(com.registerToWord(posReg, length=8))
    switch = [not i for i in com.packetWord]
    #switch = numpy.invert(com.packetWord).tolist()
    recvPacket = [True for _ in com.packetWord]
    #mes.measurementEnabled = False

    useDebugValues = False
    stopUpdate = False
    refWlast = None
    #conWlast = None
    pacWlast = None
    lastTime = 0
    writeFileIn = mes.TimeInterFileWrite

    #waitForNext = [[False, False] for _ in range(4)]

    atpw = [0]*20
    try:
        while (not stopUpdate and com.readyToSend):
            #test connection
            t = 0
            if not LRLibrary.UpdateLibrary() and t < 10:
                t +=1
                sleep(0.1)
            if t == 10:
                com.connectionLost()
                break
            com.plc_server.close()

            start_time = time()
            #Update controlwords
            refW = com.getRegisters(com.register_0)
            #conW = com.getRegisters(com.register_2) #unused
            pacW = com.getRegisters(com.register_1)
            if refW != refWlast:
                if refW is not False:
                    com.referenceWord = com.wordToList(com.registerToWord(refW, length=3))
                    '''if debug:
                        com.referenceWord[1] = True'''
                    #window.printS("Kontrolní slovo aktualizováno", "Reference Word")
                else:
                    window.printS("Failed to receive control words!", "Reference Word")
            '''if conW != conWlast:
                if conW is not False:
                    com.controlWord = com.wordToList(com.registerToWord(conW, length=12))
                    window.printS("Kontrolní slovo aktualizováno", "Control Word")
                else:
                    window.printS("Selhání aktualizace Kontrolního slova!", "Control Word")'''#unused
            if pacW != pacWlast:
                if pacW is not False:
                    com.packetWord = com.wordToList(com.registerToWord(pacW, length=8))
                    #window.printS("Kontrolní slovo aktualizováno", "Packet Word")
                    #window.printS("Now receiving data packets!")
                else:
                    window.printS("Selhání aktualizace Kontrolního slova!", "Packet Word")
            refWlast = refW
            #conWlast = conW
            pacWlast = pacW

            '''if debug:
                com.packetWord = numpy.invert(com.packetWord).tolist()'''
            '''if not com.referenceWord[0] and (not com.referenceWord[1] or com.referenceWord[2]): #Reference block
                com.sendRef(True)
                continue'''
            if not mes.measurementEnabled: #Update act values
                values = com.getRegisters(com.register_3, 8)
                if values is False or values is None:
                    continue
                window.setLabelValues(values[0], values[1], values[2], values[3], values[4], values[5], values[6], values[7])
            else: # Get packets
                if com.referenceWord[0]:
                    window.printS("Měření", "DOKONČENO")
                    window.setLock("p", False)
                    window.pb_engineStart.click()
                    continue
                for i in range(len(com.packetWord)):
                    if com.packetWord[i] == switch[i]:
                        recvPacket[i] = True
                        switch[i] = not switch[i]
                #debug
                '''for _ in range(4):
                    com.packetWord[random.randint(0, 7)] = True
                    com.packetWord[random.randint(0, 7)] = False'''
                '''left1 = None
                left2 = None
                right1 = None
                right2 = None'''
                updateLeft1 = False
                updateLeft2 = False
                updateRight1 = False
                updateRight2 = False
                if (window.engineList[1] and recvPacket[0] and recvPacket[4]):
                    updateLeft1 = True
                    left1 = {
                        "Pos": (recvPacket[0], com.getRegisters(com.registerL1Pos, mes.samplelenght, useDebugValues)),
                        "For": (recvPacket[4], com.getRegisters(com.registerL1For, mes.samplelenght, useDebugValues))
                    }
                    mes.measuredData["L1"]["Pos"].extend(left1["Pos"][1]) #mes.measuredData.extend(engineData)
                    mes.measuredData["L1"]["For"].extend(left1["For"][1]) #mes.measuredData.extend(engineData)
                    while len(mes.dataTime) < len(mes.measuredData["L1"]["Pos"]):
                        #mes.dataTime.append((mes.sampletime / mes.samplelenght) * len(mes.dataTime))
                        mes.dataTime.append(round(mes.dataTime[-1] + (mes.sampletime / mes.samplelenght), 3))


                if (window.engineList[2] and recvPacket[1] and recvPacket[5]):
                    updateLeft2 = True
                    left2 = {
                        "Pos": (recvPacket[1], com.getRegisters(com.registerL2Pos, mes.samplelenght, useDebugValues)),
                        "For": (recvPacket[5], com.getRegisters(com.registerL2For, mes.samplelenght, useDebugValues))
                    }
                    mes.measuredData["L2"]["Pos"].extend(left2["Pos"][1]) #mes.measuredData.extend(engineData)
                    mes.measuredData["L2"]["For"].extend(left2["For"][1]) #mes.measuredData.extend(engineData)
                    while len(mes.dataTime) < len(mes.measuredData["L2"]["Pos"]):
                        #mes.dataTime.append((mes.sampletime / mes.samplelenght) * len(mes.dataTime))
                        mes.dataTime.append(round(mes.dataTime[-1] + (mes.sampletime / mes.samplelenght), 3))

                if (window.engineList[3] and recvPacket[2] and recvPacket[6]):
                    updateRight1 = True
                    right1 = {
                        "Pos": (recvPacket[2], com.getRegisters(com.registerR1Pos, mes.samplelenght, useDebugValues)),
                        "For": (recvPacket[6], com.getRegisters(com.registerR1For, mes.samplelenght, useDebugValues))
                    }
                    mes.measuredData["R1"]["Pos"].extend(right1["Pos"][1]) #mes.measuredData.extend(engineData)
                    mes.measuredData["R1"]["For"].extend(right1["For"][1]) #mes.measuredData.extend(engineData)
                    while len(mes.dataTime) < len(mes.measuredData["R1"]["Pos"]):
                        #mes.dataTime.append((mes.sampletime / mes.samplelenght) * len(mes.dataTime))
                        mes.dataTime.append(round(mes.dataTime[-1] + (mes.sampletime / mes.samplelenght), 3))

                if (window.engineList[4] and recvPacket[3] and recvPacket[7]):
                    updateRight2 = True
                    right2 = {
                        "Pos": (recvPacket[3], com.getRegisters(com.registerR2Pos, mes.samplelenght, useDebugValues)),
                        "For": (recvPacket[7], com.getRegisters(com.registerR2For, mes.samplelenght, useDebugValues))
                    }
                    mes.measuredData["R2"]["Pos"].extend(right2["Pos"][1]) #mes.measuredData.extend(engineData)
                    mes.measuredData["R2"]["For"].extend(right2["For"][1]) #mes.measuredData.extend(engineData)
                    while len(mes.dataTime) < len(mes.measuredData["R2"]["Pos"]):
                        #mes.dataTime.append((mes.sampletime / mes.samplelenght) * len(mes.dataTime))
                        mes.dataTime.append(round(mes.dataTime[-1] + (mes.sampletime / mes.samplelenght), 3))

                if not mes.plotThread.running() and mes.dataTime[-1] > lastTime:
                    lastTime += .5
                    mes.plotThread = threadpool.submit(mes.refreshPlot)
                '''engineData = {
                    "L1": (updateLeft1, left1),
                    "L2": (updateLeft2, left2),
                    "R1": (updateRight1, right1),
                    "R2": (updateRight2, right2),
                }'''

                '''check = [False, False]
                update = False'''
                '''for i, tw in enumerate(("L1", "L2", "R1", "R2")):
                    check = [False, False]
                    if engineData[tw][0]: #if UpdateLeft1
                        for j, dataType in enumerate(("Pos", "For")):
                            if engineData[tw][1][dataType][0]: #if com.packetWord
                                mes.measuredData[tw][dataType].extend(engineData[tw][1][dataType][1]) #mes.measuredData.extend(engineData)

                                while len(mes.dataTime) < len(mes.measuredData[tw][dataType]):
                                    mes.dataTime.append((mes.sampletime / mes.samplelenght) * len(mes.dataTime))

                                #engineData[tw][1][dataType][0] = False #if com.packetWord
                                check[j] = True
                    if all(check):
                        update = True
                    if not all(check) and any(check):
                        update = False

                if (
                    (updateLeft1 and window.engineList[1]) or
                    (updateLeft2 and window.engineList[2]) or
                    (updateRight1 and window.engineList[3]) or
                    (updateRight2 and window.engineList[4]) or
                    not mes.plotThread.running()):
                    print("refreshPlot()")
                    mes.plotThread = threadpool.submit(mes.refreshPlot)'''


                if updateLeft1:
                    recvPacket[0] = False
                    recvPacket[4] = False
                if updateLeft2:
                    recvPacket[1] = False
                    recvPacket[5] = False
                if updateRight1:
                    recvPacket[2] = False
                    recvPacket[6] = False
                if updateRight2:
                    recvPacket[3] = False
                    recvPacket[7] = False

            #time handling
            '''window.l_NSTF_1.setText('{:.1f}'.format(mes.dataTime[-1]))
            window.l_NSTF_2.setText('{:.1f}'.format(writeFileIn))'''
            if mes.dataTime[-1] >= writeFileIn:
                data = [mes.dataTime, mes.measuredData["L1"], mes.measuredData["L2"], mes.measuredData["R1"], mes.measuredData["R2"]]
                threadpool.submit(mes.saveDataToFile, data)
                writeFileIn = mes.dataTime[-1] + mes.TimeInterFileWrite

                '''for tw in ("L1", "L2", "R1", "R2"):
                    for type in ("Pos", "For"):
                        mes.measuredData[tw][type] = [mes.measuredData[tw][type][-1]]
                mes.dataTime = [mes.dataTime[-1]]
                mes.timeIndex = 0'''

            atpw.append((time() - start_time) + LRLibrary.loadTime)
            atpw.pop(0)
            processingTime = numpy.average(atpw)
            delay = max(0, mes.updateRate - processingTime)
            '''window.l_ATPW.setText('{:.4f}'.format(processingTime) + " + " + '{:.4f}'.format(delay) + " = ")
            window.l_ATPW_2.setText('{:.4f}'.format(processingTime + delay))'''
            '''if processingTime + delay + 0.1 < mes.updateRate:
                window.l_ATPW_2.setStyleSheet("background-color: rgb(0, 170, 0);")
            elif processingTime + delay <= mes.updateRate + 0.1:
                window.l_ATPW_2.setStyleSheet("background-color: rgb(170, 170, 0);")
            else:
                window.l_ATPW_2.setStyleSheet("background-color: rgb(170, 0, 0);")'''
            #print(fin_time)
            #Wait
            sleep(delay)
    except:
        pass
    window.printS("Aktualizační smyčka ukončena.")
    stopUpdate = False
valThread = threadpool.submit(updateValues, blank=True)

if __name__ == "__main__":
    window.Start()
    mainWindow.show()
    app.aboutToQuit.connect(window.Exit)
    sys.exit(app.exec_())