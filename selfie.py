# Image resolution 640 x 480
# Manual overlay can accomidate 35 characters
# A 'pre built' overlay must be 640 x 50
#
# Decided not to store photos to the SD card as it slows up the process
# Saving 1000 photos to the SD card increased memory usage by only 3%

from time import sleep
import picamera
import time, numpy
import tweepy
import os, sys
import os.path
import subprocess # Used to ping googles 8.8.8.8 static corporate IP address
from datetime import datetime # date and time format used for tweeting pic
import RPi.GPIO as GPIO  
from SimpleCV import Image, Display, DrawingLayer, Color
import ConfigParser  # Reading in the settings in the confihg.txt file

#### Predefined status put on tweets
tweet = 'Photo auto-tweet from Tatyms 21st: ' 

#### Defining the google static IP for ping testing
host = '8.8.8.8'

#### Defining the GPIO pins
CAPTURE = 10 ###17  # Had to switch these around because of wiring problem
LED_CAPTURE = 9 ###11
TWEET_IT = 17 ###10
LED_TWEET_IT = 11 ###9
LED5 = 23 ###7
LED4 = 24 ###8
LED3 = 25
LED2 = 8 ###24
LEDSMILE = 7 ###23
LEDTWEETING = 18

#### Reversing the GPIO on/off so it reads logically
ON = False
OFF = True

#### GPIO setup
GPIO.setmode(GPIO.BCM)  # BCM GPIO format
GPIO.setwarnings(False)
GPIO.setup(CAPTURE, GPIO.IN, GPIO.PUD_UP)  # This is for the capture button
GPIO.setup(TWEET_IT, GPIO.IN, GPIO.PUD_UP)  # This is for the send photo to twitter button
GPIO.setup(LED_CAPTURE, GPIO.OUT, GPIO.PUD_UP)  # For the in button LED
GPIO.setup(LED_TWEET_IT, GPIO.OUT, GPIO.PUD_UP)  # For the in button LED
GPIO.setup(LED5, GPIO.OUT, GPIO.PUD_UP)  # LED 5
GPIO.setup(LED4, GPIO.OUT, GPIO.PUD_UP)  # LED 4
GPIO.setup(LED3, GPIO.OUT, GPIO.PUD_UP)  # LED 3
GPIO.setup(LED2, GPIO.OUT, GPIO.PUD_UP)  # LED 2
GPIO.setup(LEDSMILE, GPIO.OUT, GPIO.PUD_UP)  # LED SMILE!
GPIO.setup(LEDTWEETING, GPIO.OUT, GPIO.PUD_UP)  # LED tweeting pic

#### global variables
global counter
global imageName
global myDisplay
global fullName
global modifiedName
global path
global pathORIGINAL
global pathMODIFIED
global CK
global CS
global AT
global ATS
global overlayText

#### defining variables
myDisplay = Display()
config = ConfigParser.RawConfigParser()
picPath = '/home/pi/photobooth/'
overlayPath = '/home/pi/photobooth/overlay.png'
original = '/original'
modified = '/modified'
configFile = '/home/pi/photobooth/config.txt'

#### display a 'live feed' from the camera
def idleCam():
    try:
        camera.start_preview()
        camera.hflip = True # correcting the camera display
        camera.vflip = True # correcting the camera display
    except:
        print "Error - Unable to start the idle camera."
        print "Please reboot the system."
	
def shutDown():
    GPIO.cleanup()
    os.system("sudo reboot")  # Will reboot the Pi. Taken out while testing
    sys.exit(0) # Just exits the program
	
def twitterOAuth():
    global api
    # OAuth process, using the keys and tokens
    auth = tweepy.OAuthHandler(CK, CS)
    auth.set_access_token(AT, ATS)
    auth.secure = True
    # Creation of the actual interface, using authentication
    api = tweepy.API(auth)
	
def overlayTweet(text):
    myText = text
    myDisplay = Display()
    myImage = Image(fullName)  # Need to load the original photo
    myDrawingLayer = DrawingLayer((myImage.width, myImage.height))
    myDrawingLayer.rectangle((70, 20), (500, 70), filled=True)
    myDrawingLayer.setFontSize(90)
    myDrawingLayer.text(myText, (80, 20), color = Color.WHITE) # ("Send to Twitter?", (80, 20), color = Color.WHITE)
    myImage.addDrawingLayer(myDrawingLayer)
    myImage.applyLayers()
    myImage.save(myDisplay)
	
def tweetPic():
    # Check if users want to Tweet photo. If they do then send the tweet with photo
    i = datetime.now()  # take time and date for filename
    overlayTweet("Send to Twitter?") # Calls the overlayTweet function which displays the photo just take with the relevant text
    GPIO.output(LED_TWEET_IT, ON) # Turns on the in button LED to repersent a ready state
    for x in xrange(1, 22): # This give a 10 second gap to Tweet photo. The end range was change from 11 to 22 to coniside with the delay change to half a second.
        if (GPIO.input(TWEET_IT) == 0): # Checks to see if the TWEET_IT button has been pressed
            try:
                print "Tweet button pressed"
                overlayTweet("Busy sending...")
                GPIO.output(LEDTWEETING, ON) # Sets tweeting LED pic on
                GPIO.output(LED_TWEET_IT, OFF) # Turns on the in button LED off once button pressed
                print "Sending photo to Twitter..."
                status = tweet  + i.strftime('%Y/%m/%d %H:%M:%S') # Tweets the photo with a 'status' and the currrent date and time
#                os.environ['http_proxy']='' ####not sure why
                api.update_with_media(modifiedName, status=status) # fullName is the path of the modified photo with a banner on the bottom
                overlayTweet("Sent to Twitter!")
                GPIO.output(LEDTWEETING, OFF) # Sets tweeting pic off
                print "Photo sent to Twitter!"
                sleep(3)
                break
            except tweepy.TweepError as e:
                ledOFF()
                print e.response.status
                print e.message[0]['code']  # prints 34
                print e.args[0][0]['code']  # prints 34
                print 'Unable to send to twitter'
                overlayTweet("Error. Not sent!")
                sleep(3)
                break
        else:
            print "Send to Twitter? - " + str(x)
            sleep(0.5) # This was originally a 1 second delay, but the 1 second delay would allow a 'missed button press' if the user pressed the button at the incorrect time.
                       # Changing the delay time to half a second would decrease the possibility of the code missing the button press.
            x = x + 1
	
def createPath():
    global path
    global pathORIGINAL
    global pathMODIFIED
    today = time.strftime("%Y-%m-%d")
    path = picPath + today
    pathORIGINAL = picPath + today + original
    pathMODIFIED = picPath + today + modified
    if not (os.path.isdir(path)):
        print "Creating the path - " + path
        os.mkdir(path)
        os.chmod(path, 0777)
    if not (os.path.isdir(pathORIGINAL)):
        print "Creating the path - " + pathORIGINAL 
        os.mkdir(pathORIGINAL)
        os.chmod(pathORIGINAL, 0777)
    if not (os.path.isdir(pathMODIFIED)):
        print "Creating the path - " + pathMODIFIED 
        os.mkdir(pathMODIFIED)
        os.chmod(pathMODIFIED, 0777)
    else:
        print "Path already made - " + path

def writeConfig(): 
    global counter
    global configFile
    config.read(configFile)
    config.set('counter', 'count', counter) # Keeps a count of photos taken in the config file
    with open(configFile, 'wb') as configfile: # Writing the configuration file to configFile
        config.write(configfile)


def readConfig(): 
    global configFile
    global counter
    global CK
    global CS
    global AT
    global ATS
    global overlayText
    config.read(configFile)
    counter = config.get('counter', 'count')
    CK = config.get('twitter', 'consumer_key')
    CS = config.get('twitter', 'consumer_secret')
    AT = config.get('twitter', 'access_token')
    ATS = config.get('twitter', 'access_token_secret')
    overlayText = config.get('overlay', 'text')
	
def picName():
    today = time.strftime("%Y-%m-%d")
    now = time.strftime("%H-%M-%S")
    imageName = today + "_" + now
    return imageName
	
def captureImage():
    global fullName
    global counter
    global name # so that the same name can be used on the modified pic
    name = picName() # The name of the image is only defined when the capture button is pressed
    fullName = pathORIGINAL + "/" + name + ".jpg"
    ledOFF()
    camera.capture(fullName)
    camera.stop_preview()
    ledON()
    counter = int(counter) + 1
    print "Image taken - " + name
	
def overlayAuto():
    global modifiedName
#    myDisplay = Display()
    modifiedName = pathMODIFIED + "/" + name + ".jpg"
    myImage = Image(fullName)  # Need to load the original photo
    size = int(len(overlayText))
    if size >= 41:
        myText = "Overlay text must not be > than 40"
    else:
        myText = overlayText
    myDrawingLayer = DrawingLayer((myImage.width, myImage.height))
    myDrawingLayer.rectangle((0,430), (640,50), filled = True)
    myDrawingLayer.setFontSize(45)
    myDrawingLayer.text(myText, (20, 440), color = Color.WHITE)
    myImage.addDrawingLayer(myDrawingLayer)
    myImage.applyLayers()
    myImage.save(modifiedName)
# No need to show the below as they will be uploaded to twitter
#    myImage.show()
#    sleep(10)
	
def overlayManual():
    global modifiedName
    modifiedName = pathMODIFIED + "/" + name + ".jpg"
    img1 = Image(fullName)
    img2 = Image('/home/pi/photobooth/overlay.png')
    img1.dl().blit(img2, (0, 430))
    img1.save(modifiedName)
# No need to show the below as they will be uploaded to twitter
#    img1.show()
#    print "showing" + modifiedName
#    time.sleep(10)
    
	
def ledOFF():
    GPIO.output(LED5, OFF) # Sets LED 5 off
    GPIO.output(LED4, OFF) # Sets LED 4 off
    GPIO.output(LED3, OFF) # Sets LED 3 off
    GPIO.output(LED2, OFF) # Sets LED 2 off
    GPIO.output(LEDSMILE, OFF) # Sets LED SMILE! off
    GPIO.output(LEDTWEETING, OFF) # Sets tweeting pic off
    GPIO.output(LED_TWEET_IT, OFF) # Sets TWEET_IT in button LED off

def ledON():
    GPIO.output(LED5, ON) # Sets LED 5 on
    GPIO.output(LED4, ON) # Sets LED 4 on
    GPIO.output(LED3, ON) # Sets LED 3 on
    GPIO.output(LED2, ON) # Sets LED 2 on
    GPIO.output(LEDSMILE, ON) # Sets LED SMILE! on
	
def countDown():
    GPIO.output(LED5, ON) # Sets LED 5 on
    sleep(1)
    GPIO.output(LED4, ON) # Sets LED 4 on
    sleep(1)
    GPIO.output(LED3, ON) # Sets LED 3 on
    sleep(1)
    GPIO.output(LED2, ON) # Sets LED 2 on
    sleep(1)
    GPIO.output(LEDSMILE, ON) # Sets LED SMILE! on
    sleep(1)
	
#### Setup everything
createPath()
ledOFF()
readConfig()
print "Overlay text - " + overlayText
#twitterOAuth() # cant really do this here......................

while 1:
    try:
        with picamera.PiCamera() as camera:
            ping = subprocess.Popen(['ping', '-c 2', host], stdout=subprocess.PIPE) # Setting up the ping sub process command
            ledOFF()
            idleCam()
            print "Ready to capture photo"
            GPIO.output(LED_CAPTURE, ON) # Turns on the in button LED to repersent a ready state
            GPIO.wait_for_edge(CAPTURE, GPIO.FALLING) # code will wait here until the capture button is pressed
            if (GPIO.input(TWEET_IT) == 0): # Checks to see if the TWEET_IT button has been pressed right after CAPTURE pressed. This is for shutdown.
                shutDown()
            GPIO.output(LED_CAPTURE, OFF) # Turns off the in button LED once the button is pressed
            countDown()
            captureImage()

            myDisplay = Display()
            myImage = Image(fullName)
            myImage.save(myDisplay)
            sleep(5) # 5 second preview of the photo
		
            ledOFF()

            if os.path.isfile(overlayPath):
                print "PNG exsists"
                overlayManual()
            else:
                print "No PNG"
                overlayAuto()

            writeConfig() # Only writing the photo count number back to the file. Should happen last.
            if (ping.communicate()[0]):
                print "Connected to internet."
                twitterOAuth()
                tweetPic() # calling the function to tweet the pic
            else:
                print "No internet connection. Cannot Tweet photo."
    except:
        print "Error - Unable to start the camera."
        print "Please reboot the system."
        sleep(10)
        os.system("sudo reboot")  # Will reboot the Pi. Taken out while testing
        exit()

