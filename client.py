'''
flag notations:
non --> None
prn --> Simply print it, no special action required
bzz --> buzzer has been pressed. Take no action if not yourself
qsn --> Question has been posted
ans --> Send answer now
rst --> Reset responseState
rpo --> Receive and print options
kll --> Terminate
'''

import socket           #For the TCP socket
import select           #For selecting the input source
import sys              #For standerd system I/O

SERVER = socket.socket(socket.AF_INET,socket.SOCK_STREAM)       #Starting client socket
SERVER.connect(('',8000))                       #Connecting to the server socket
    
responseState = 'non'                           #Initializing response from the server to none

PLAYING = True                                  #While the server is still interacting
while PLAYING:

    listOfSockets = [sys.stdin, SERVER]         #The two input sources: the socket or the standerd input source
    inputs = select.select(listOfSockets,[],[])[0]      #Calling select for input only
        
    for src in inputs:                          #For the responses in the inputs received by select
        
        if src == SERVER:                       #If something came from the server

            message = SERVER.recv(1024).decode('ascii') #Receive it
            responseType = message[0:3]         #Extract the responseType flag from it
            message = message[3:]

            if responseType == "prn":           #Simply print the message; generic info
                print(message)

            elif responseType == "qsn":        #If a question has been sent
                print("\nQuestion: ",message)

            elif responseType == "rpo":         #If the buzzer can be pressed
                responseState = 1
                print(message) 
                
            elif responseType == "bzz":         #If the buzzer has been pressed by someone else
                responseState = 0    
                print("Buzzer pressed by " + message)
            
            elif responseType == "ans":         #If you have buzzed, send answer
                responseState = 2
                print("Enter your answer:")

            elif responseType == "rst":         #Reset everything, one question over
                responseState = 0
            
            elif responseType == 'kll':         #Terminate socket connection
                print(message)
                PLAYING = False

        else:                                   #If I/O is from the keyboard

            response = sys.stdin.readline()     #Take the input
            
            if responseState == 1:                  #If its the buzzer, simply send the flag
                SERVER.send("bzz".encode("ascii"))
            elif responseState == 2:                #Otherwise send the answer
                SERVER.send(("ans"+ response).encode("ascii"))                                   

