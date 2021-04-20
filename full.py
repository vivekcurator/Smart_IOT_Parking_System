import RPi.GPIO as GPIO
import time
import cv2
import imutils
import numpy as np
import pytesseract
import urllib2, urllib, httplib
import json
import os
import mysql.connector
from mysql.connector import Error
from time import sleep
from functools import partial
from PIL import Image
from picamera.array import PiRGBArray
from picamera import PiCamera
from datetime import datetime

GPIO.setmode(GPIO.BOARD)

TRIG1 = 7
ECHO1 = 12
SERVO = 11
IR1 = 13
IR2 = 15
IR3 = 16
IR4 = 18
TRIG2 = 31
ECHO2 = 29

GPIO.setup(TRIG1,GPIO.OUT)
GPIO.setup(ECHO1,GPIO.IN)
GPIO.setup(SERVO,GPIO.OUT)
GPIO.setup(IR1,GPIO.IN)
GPIO.setup(IR2,GPIO.IN)
GPIO.setup(IR3,GPIO.IN)
GPIO.setup(IR4,GPIO.IN)
GPIO.setup(TRIG2,GPIO.OUT)
GPIO.setup(ECHO2,GPIO.IN)

def ct1():
	global sec1,dt1
        now = datetime.now()
        dt1 = now.strftime ("%d/%m/%Y %H:%M:%S")
        print (dt1)
	sec1 = int(round(time.time()))
	print (sec1)

def ct2():
	global sec2,dt2
        now = datetime.now()
        dt2 = now.strftime ("%d/%m/%Y %H:%M:%S")
        print (dt2)
	sec2 = int(round(time.time()))
	print (sec2)

def ir():
	global a,b,c,d
	global sl
	print "  Looking for empty slots....."
	print " "

	try:
		if GPIO.input(IR1):
			a = 'slo'
			sl = 'S1'
        		print "  Slot 1 is empty"
        		while GPIO.input(IR1):
                		time.sleep(0.2)
				break
		else:
			a = 'slc'
      			print "  Object is present in Slot 1 "

		if GPIO.input(IR2):
			b = 'slo'
			sl = 'S2'
        		print "  Slot 2 is empty"
        		while GPIO.input(IR1):
                		time.sleep(0.2)
		else:
			b = 'slc'
        		print "  Object is present in Slot 2"

		if GPIO.input(IR3):
			c = 'slo'
			sl = 'S3'
        		print "  Slot 3 is empty"
        		while GPIO.input(IR1):
                		time.sleep(0.2)
		else:
			c = 'slc'
        		print "  Object is present in Slot 3"

		if GPIO.input(IR4):
			d = 'slo'
			sl = 'S4'
        		print "  Slot 4 is empty"
        		while GPIO.input(IR1):
                		time.sleep(0.2)
		else:
			d = 'slc'
        		print "  Object is present in Slot 4"

	except (KeyboardInterrupt, SystemExit):
        	raise


def ult1():
	global d1
	GPIO.output(TRIG1, True)
	time.sleep(0.00001)
	GPIO.output(TRIG1, False)

	while GPIO.input(ECHO1) == False:
        	start = time.time()

	while GPIO.input(ECHO1) == True:
        	end = time.time()

	sig_time = end - start

#CM:
	d1 = sig_time / 0.000058
	#print "Distance : {}cm".format(distance)
	return d1

def ult2():
        global d2
        GPIO.output(TRIG2, True)
        time.sleep(0.00001)
        GPIO.output(TRIG2, False)

        while GPIO.input(ECHO2) == False:
                start = time.time()

        while GPIO.input(ECHO2) == True:
                end = time.time()

        sig_time = end - start

#CM:
        d2 = sig_time / 0.000058
        #print "Distance : {}cm".format(distance)
        return d2



def Entry():
	dist = ult1()
	pwm=GPIO.PWM(SERVO, 50)
	pwm.start(0)
	sleep(1)
	if(dist <= 10):
		pwm.ChangeDutyCycle(5) # neutral position
		sleep(2)
		pwm.ChangeDutyCycle(10) # right +90 deg position
		sleep(2)
		pwm.stop()
	return 0


def Exit():
        dist = ult2()
        pwm=GPIO.PWM(SERVO, 50)
        pwm.start(0)
        sleep(1)
        if(dist <= 10):
                pwm.ChangeDutyCycle(5) # neutral position
                sleep(2)
                pwm.ChangeDutyCycle(10) # right +90 deg position
                sleep(2)
                pwm.stop()
        return 0


def ocr():
	camera = PiCamera()
	camera.resolution = (640, 480)
	camera.framerate = 30
	rawCapture = PiRGBArray(camera, size=(640, 480))
	for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
        	image = frame.array
        	cv2.imshow("Frame", image)
        	key = cv2.waitKey(1) & 0xFF
        	rawCapture.truncate(0)
        	if key == ord("s"):
             		gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) #convert to grey scale
             		gray = cv2.bilateralFilter(gray, 11, 17, 17) #Blur to reduce noise
             		edged = cv2.Canny(gray, 30, 200) #Perform Edge detection
             		cnts = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
             		cnts = imutils.grab_contours(cnts)
             		cnts = sorted(cnts, key = cv2.contourArea, reverse = True)[:10]
             		screenCnt = None
             		for c in cnts:
                		peri = cv2.arcLength(c, True)
                		approx = cv2.approxPolyDP(c, 0.018 * peri, True)
                		if len(approx) == 4:
                  			screenCnt = approx
                  			break
             		if screenCnt is None:
               			detected = 0
               			print "No contour detected"
             		else:
               			detected = 1
             		if detected == 1:
               			cv2.drawContours(image, [screenCnt], -1, (0, 255, 0), 3)
             			mask = np.zeros(gray.shape,np.uint8)
             			new_image = cv2.drawContours(mask,[screenCnt],0,255,-1,)
             			new_image = cv2.bitwise_and(image,image,mask=mask)
             			(x, y) = np.where(mask == 255)
             			(topx, topy) = (np.min(x), np.min(y))
             			(bottomx, bottomy) = (np.max(x), np.max(y))
             			Cropped = gray[topx:bottomx+1, topy:bottomy+1]
          			text = pytesseract.image_to_string(Cropped, config='--psm 11')
             			text = pytesseract.image_to_string(Cropped)
             			print "Detected Number is: ",text
             			cv2.imshow("Frame", image)
             			cv2.imshow('Cropped',Cropped)
             			cv2.waitKey(0)
             			break
	cv2.destroyAllWindows()


def insert_db_Entry(Sno, Nu_Plate, Entry_Time, Slot_No, A_Sec):
	try:
		connection = mysql.connector.connect(host='localhost',
                                         database='Final Year Project',
                                         user='Project',
                                         password='database')

		cursor = connection.cursor()
		mySql_insert_query = "INSERT INTO System_Info (Sno, Nu_Plate, Entry_Time, Slot_No, A_Sec) VALUES (%s, %s, %s, %s, %s);"

		recordTuple = (Sno, Nu_Plate, Entry_Time, Slot_No, A_Sec)
		cursor.execute(mySql_insert_query, recordTuple)
		connection.commit()
		print ("Record inserted successfully into System_Info table")

	except mysql.connector.Error as error:
		print ("Failed to insert into MySQL table {}".format(error))

	finally:
		if (connection.is_connected()):
			cursor.close()
			connection.close()
			print ("MySQL connection is closed")



def insert_db_Exit(Nu_Plate, Exit_Time, B_Sec):
	try:
		connection = mysql.connector.connect(host='localhost',
                                         database='Final Year Project',
                                         user='Project',
                                         password='database')

		cursor = connection.cursor()
		mySql_insert_query = "INSERT INTO System_Info (Nu_Plate, Exit_Time, B_Sec) VALUES (%s, %s, %s);"

		recordTuple = (Nu_Plate, Exit_Time, B_Sec)
		cursor.execute(mySql_insert_query, recordTuple)
		connection.commit()
		print ("Record inserted successfully into System_Info table")

	except mysql.connector.Error as error:
		print ("Failed to insert into MySQL table {}".format(error))

	finally:
		if (connection.is_connected()):
			cursor.close()
			connection.close()
			print ("MySQL connection is closed")




def main():
	ult1()
	ult2()
	if (d1 <= 10):
		print "   Welcome to Parking lot of G10 "
		print "  "
        	ir()
		Sno = 0
        	if(a == 'slo' or b == 'slo' or c == 'slo' or d == 'slo' ):
                	print "   Opening the Gate  "
			Sno += 1
                	sleep(2)
			if(sl == 'S1'):
				print "  Assigned slot is S1"
			elif(sl == 'S2'):
				print "  Assigned slot is S2"
			elif(sl == 'S3'):
				print "  Assigned slot is S3"
			elif(sl == 'S4'):
				print "  Assigned slot is S4"
                	Entry()
                	print "   Wait for image capture  "
			ocr()
			ct1()
			print "Slot ",sl
			#insert_db_Entry(Sno, text, dt1, sl, sec1)


		else:
			print "Parking space is not available"


	if (d2 <= 10):
		print "  Thanks for visiting "
		print " "
		print "  Please wait for bill to be generated"
		ocr()
		ct2()
		insert_db_Exit(text, dt2, sec2)
		#get_Detail()
		#sending vehicle no.to database and getting back the detail of entry"
		#qr() {generate qr code by subtracting ct2-ct1 and assigning value of rs 10 for 1min
		#print " Please pay the bill"
		#if bill paid open gate
		Exit()

if __name__ == "__main__":
        main()
	GPIO.cleanup()
	exit()

