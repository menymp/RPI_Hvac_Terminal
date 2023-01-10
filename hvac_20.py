#change example for hvac_20.py file
#menymp 10 jan 2023
from tkinter import *
from configparser import ConfigParser
import os
import threading
import time
import board
import busio
import digitalio
import adafruit_max31855
import adafruit_mcp4725

class GUI_hvac:
	def __init__(self,tempVal,state):
		self.tempVal = tempVal
		self.state = state
		self.GUI_Constructor()
		pass
		
	def GUI_Constructor(self):
		self.ObjWindow = Tk()
		self.ObjWindow.title("Temp control")
		self.ObjWindow.geometry("1080x720")
		
		var = IntVar()
		var.set(int(self.tempVal))
		self.NumericSetpoint = Spinbox(self.ObjWindow,from_ = 15 ,to = 32,width = 2, font = ("Arial Bold", 70),textvariable = var)
		self.NumericSetpoint.place(x = 160,y = 50)
		self.TaskUpdateTempConfig = threading.Thread(target = self.NumericSetpoint_click)
		self.OldTempVal = self.NumericSetpoint.get()
		self.TaskUpdateTempConfig.start()
		
		self.LblSetpoint = Label(self.ObjWindow, text="°C", font = ("Arial Bold", 70))
		self.LblSetpoint.grid(column = 0, row = 0)
		self.LblSetpoint.place(x = 30,y = 50)
		
		self.LblMsg = Label(self.ObjWindow, text="Off", font = ("Arial Bold", 60))
		self.LblMsg.grid(column = 0, row = 0)
		self.LblMsg.place(x = 30,y = 320)
		
		self.LblTemp = Label(self.ObjWindow, text="0°C",font = ("Arial Bold", 70))
		self.LblTemp.grid(column = 0, row = 0)
		self.LblTemp.place(x = 420,y = 50)
		self.LblTemp.config(background = "gray")
		
		self.BtnAuto = Button(self.ObjWindow, text = "Auto", font = ("Arial Bold", 70),bg = "gray",command = lambda:self.BtnAuto_click(self.ObjWindow))
		self.BtnAuto.place(x = 30, y = 200)
		
		
		self.BtnOff = Button(self.ObjWindow, text = "Off", font = ("Arial Bold", 70), bg = "gray",command = lambda:self.BtnOff_click(self.ObjWindow))
		self.BtnOff.place(x = 590, y = 200)
		
		
		
		if self.state == "off":
			self.BtnOff.config(background = "green")
			pass
		if self.state == "auto":
			self.BtnAuto.config(background = "green")
			pass
		return self.ObjWindow
	
	def NumericSetpoint_click(self):
		while 1:
			if self.OldTempVal != self.NumericSetpoint.get():
				self.OldTempVal = self.NumericSetpoint.get()
				self.SaveConfig()
			time.sleep(0.3)
		pass
	
	def BtnAuto_click(self,ObjWindowRef):
		self.BtnAuto.config(background = "green")
		self.BtnOff.config(background = "gray")
		self.state = "auto"
		self.SaveConfig()
		pass
	
	def BtnOff_click(self,ObjWindowRef):
		self.BtnAuto.config(background = "gray")
		self.BtnOff.config(background = "green")
		self.state = "off"
		self.SaveConfig()
		pass
	
	def mainloop(self):
		self.ObjWindow.mainloop()
		
	def Get_Setpoint(self):
		#print(self.NumericSetpoint.get())
		return int(self.NumericSetpoint.get())
		
	def Get_State(self):
		return self.state
	
	def Display_CurrentTemp(self, TempValue):
		self.LblTemp.config(text = str(TempValue)+"°C")
		pass
		
	def Display_Msg(self, Msg):
		self.LblMsg.config(text = Msg)
		pass
	
	def SaveConfig(self):
		configf = ConfigParser()
		configf.read('config.ini')
		configf.set('HVAC_Configs','temp',self.NumericSetpoint.get())
		configf.set('HVAC_Configs','state',self.state)
		with open('config.ini','w') as f:
			configf.write(f)
		pass

class TempController_hvac:
	def __init__(self,GUI_hvac_Ref):
		#init de sensores y dac
		self.GUI_hvac_Ref = GUI_hvac_Ref
		self.TaskControlTemp = threading.Thread(target = self.ControlTemp_Routine)
		
		self.spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
		self.cs = digitalio.DigitalInOut(board.D10)
		self.max31855 = adafruit_max31855.MAX31855(self.spi, self.cs)
		
		self.Relay = digitalio.DigitalInOut(board.D13)
		self.Relay.direction = digitalio.Direction.OUTPUT
		
		self.i2c = busio.I2C(board.SCL, board.SDA)
		self.dac = adafruit_mcp4725.MCP4725(self.i2c, address = 0x60)
		
		self.TaskControlTemp.start()
		pass
	
	def ControlTemp_Routine(self):
		while 1:
			TempC = int(self.ReadTemp()/2)
			self.GUI_hvac_Ref.Display_CurrentTemp(TempC)
			
			if self.GUI_hvac_Ref.state == "auto":
				Err = TempC - self.GUI_hvac_Ref.Get_Setpoint()
				#print(str(Err) + ' '+ str(TempC)+ ' ' +str(self.GUI_hvac_Ref.Get_Setpoint()))
				if(abs(Err) <= 1):
					self.SetResistor(True)
					self.SetValve(0)
					self.GUI_hvac_Ref.Display_Msg('Estable')
					pass
				elif((abs(Err) > 1) and (Err < 0)):
					while (TempC < (self.GUI_hvac_Ref.Get_Setpoint()+1)) and self.GUI_hvac_Ref.state == "auto":
						self.SetResistor(False)
						self.SetValve(0)
						TempC = int(self.ReadTemp()/2)
						self.GUI_hvac_Ref.Display_CurrentTemp(TempC)
						self.GUI_hvac_Ref.Display_Msg('Resistor On')
						time.sleep(4)
					pass
				elif((abs(Err) > 1) and (Err > 0)):
					while (TempC > (self.GUI_hvac_Ref.Get_Setpoint()-1)) and self.GUI_hvac_Ref.state == "auto":
						self.SetResistor(True)
						
						ValveVal = int(320 * Err + 800)
						
						if(ValveVal > 4090):
							ValveVal = 4090
						
						self.SetValve(ValveVal)
						Err = TempC - self.GUI_hvac_Ref.Get_Setpoint()
						TempC = int(self.ReadTemp()/2)
						self.GUI_hvac_Ref.Display_CurrentTemp(TempC)
						self.GUI_hvac_Ref.Display_Msg('Valvula '+ str(int(100*self.dac.normalized_value))+'%')
						time.sleep(4)
					pass
				pass
			elif self.GUI_hvac_Ref.state == "off":
				self.SetResistor(True)
				self.SetValve(0)
				self.GUI_hvac_Ref.Display_Msg('Off')
				pass
			time.sleep(4)
		pass
	
	def ReadTemp(self):
		return self.max31855.temperature
		pass
	
	def SetResistor(self,value):
		self.Relay.value = value
		#print(value)
		pass
	
	def SetValve(self,value):
		self.dac.raw_value = value
		pass
	
	pass

if __name__ == "__main__":
	if os.path.exists('config.ini'):
		config = ConfigParser()
		config.read('config.ini')
		
		ObjWindow = GUI_hvac(config.get('HVAC_Configs','temp'),config.get('HVAC_Configs','state'))
	else:
		config = ConfigParser()
		config.read('config.ini')
		config.add_section('HVAC_Configs')
		config.set('HVAC_Configs','temp','23')
		config.set('HVAC_Configs','state','off')
		with open('config.ini','w') as f:
			config.write(f)
		ObjWindow = GUI_hvac("23","off")
		
	ControllerTmp = TempController_hvac(ObjWindow)
	#print("GUI Init ok... "+str(ObjWindow.Get_Setpoint()))
	while 1:
		ObjWindow.mainloop()
		
	
