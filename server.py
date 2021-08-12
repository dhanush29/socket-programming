from socket import *        #For TCP socket
from random import shuffle  #For shuffling the order of the questions
import sys
import time                 #For adding delays after each state 
import json                 #Load questions form the json file
from _thread import *       #The basic threading module in Python3
from threading import Lock  #For obtaining the Lock() function

'''
flag notations:
prn --> Simply print it, no special action required
bzz --> buzzer has been pressed. Take no action if not yourself
qsn --> Question has been posted
ans --> Send answer now
rst --> Reset responseState
rpo --> Receive and print options
kll --> Terminate
'''

LOCK = Lock()               #Initializing the global lock
                            #prevents multiple threads from changing a global variable at the same time

#Loading the questions and shuffling the order
with open("question.json") as load_data:
  questions = json.load(load_data)["qna"]

shuffle(questions) #An inbuilt function to shuffle the questions

#Setting the number of users
LIMIT = 3 if len(sys.argv) < 2 else int(sys.argv[1])   

#The minium number of questions to get correct to win
WIN_LEVEL = 5

if len(sys.argv) == 3:
    if int(sys.argv[2]) > len(list(questions[0].keys())):
        WIN_LEVEL = sys.argv[2]             

SERVER = socket()           #Starting the Server socket
SERVER.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)  #Setting reusability property to the socket

SERVER.bind(('', 8000))     #Binding the socket to localhost on port 8000
SERVER.listen(LIMIT)    #Setting the upper limit to the number of sources to listen to on the socket

users = []                  #List of socket info of all the users who have connected
scores = []                 #The scores in the quiz corresponding to the players in the users list
questionNumber = -1         #For the question which is to be displayed
start = 0                   #Permission to start the game; control variable
buzzer = "OFF"              #Global variable to store the status of the buzzer(pressed/not pressed)


#All the rules which are displayed when all the players are connected
rules = """\n\n1.You will be sent 10 questions(max).
2.The first person to press the buzzer gets the chance to answer.
3.If player wants to press the buzzer can press after question appears.
4.Who presses the buzzer should answer.
5.First person to reach """+str(WIN_LEVEL)+""" or more than 5 points wins the game!
6.Otherwise no one wins the quiz!
7.You are awarded a +1 for a correct answer.
8.0.5 points will be subtracted if you answer wrong.
9.Good Luck!!\n\n"""
          
#A function to broadcast a message to everyone
#Python3 makes it compulsory to encode any data into a binary stream before sending on a socket
def broadcast(data):
    for user in users:
        user.send(data.encode("ascii"))    

#A function to send the scorecard as per need
def sendScores():
    scorecard = "prn\n----Scorecard----\n  User\tScore:\n\n"
    
    for i in range(len(scores)):
        scorecard += "    "+str(i+1) + "\t  " + str(scores[i]) + "\n"
        
    time.sleep(0.001)
    broadcast(scorecard)
    print("Scores sent")
    time.sleep(5)

#A function to find the winner, while the game is running or when its over
def findWinner(gameOver = False):
    if gameOver:
    
        #If there is a winner or all the questions are over        
        broadcast("prn\nGame Over\n")
        time.sleep(0.001)
        c=0
        maxScore = 5
        winners = []
        message = "prn"
        Mscore=-1
        
        for i in range(len(scores)):
            if scores[i] >= 5:
                winners = ["User #"+str(i+1)]
                c+=1
        
            elif scores[i] >= maxScore:
                winners.append("User #"+str(i+1))
                c+=1
        
        if c==0:
            broadcast("prn\nNone of them won\n")
            broadcast("Better Luck Next Time")
  
        for i in range(len(scores)):
            if scores[i] > Mscore:
                Mscore =scores[i]

        message += "Winner is: " if len(winners) == 1 else "Winners are: "
        message += winners[0]

        if len(winners) > 1:

            for i in range(1,len(winners)):
                message += ", " + winners[i]

        broadcast(message)

        time.sleep(0.001)
        #Terminate the connection with all the clients
        broadcast("kllScore achieved by winner: " + str(Mscore) + " ")

    else:                   #If the server is not out of questions yet
        for score in scores:
            if score >= WIN_LEVEL:
                return True

        return False

# A function to just welcome the user
# Most important: Infinite loop transfers the control to the function above to handle all responses from the client
def handleUser(user):

    global scores, start, users
    
    #Append the score of the connected user
    userNo = len(scores)
    scores.append(0)

    #Send a message with the player number detail
    message = "prnWelcome to the game User #" + str(userNo+1)
    user.send(message.encode('ascii'))    

    while 1:
        quizHandle(user, userNo)
    

#Function to handle the buzzer presses; a separate instance for each player thread
def quizHandle(user, userNo):

    #Calling the global variables which are needed
    global buzzer, questionNumber, LOCK

    #If a buzzer press message is received from a client:
    if user.recv(1024).decode('ascii') == "bzz" and buzzer == "OFF":
        
        #Prevent all other threads from modifying the global buzzer variable
        LOCK.acquire()
        try:
            buzzer = userNo
        finally:
            LOCK.release()    

        #Log to the server
        print("Player #",userNo+1, " buzzed")

        #Small delay to prevent threads from overlapping
        time.sleep(0.001)

        #Send a buzzer already pressed flag to everyone, along with the player number
        #Prevents others from pressing the buzzer
        broadcast("bzz" + str(userNo+1) + " ")

        time.sleep(0.001)
        #Send the client, who pressed the buzzer, the flag to allow answering
        user.send("ans".encode("ascii"))

        #Receive the answer from the client socket
        choice = user.recv(1024).decode('ascii')[3:4]

        #Intermediate stage of the buzzer for processing in controlling
        LOCK.acquire()
        try:
            buzzer = "wait"
        finally:
            LOCK.release()    

        #Check for validity of the answer and accordingly take actions
        if questions[questionNumber]["answer"] == choice:

            time.sleep(0.5)
            broadcast("prnUser #" + str(userNo+1) + " has given the right answer!!")
            #Server console logging
            print("Correct answer")
            
            #Give a point to the player for answering correctly
            scores[userNo] += 1

        else:
            time.sleep(0.5)
            broadcast("prnUser #" + str(userNo+1) + " has given the wrong answer :-(")
            
            #Server console logging
            print("Incorrect answer")
            scores[userNo] -= 0.5
        
        correctAnswer = "prn\nThe correct answer is option: " + questions[questionNumber]["answer"]
        broadcast(correctAnswer)
            

#The main server thread function
def Controller():

    global LOCK, LIMIT, questionNumber, scores, buzzer, start, users
    
    #Wait until everyone has connected to the server
    while len(scores) < LIMIT:

        time.sleep(1)
    
    #Some necessary info sent to all the users
    broadcast("prn\nAll users are now connected and ready!\nLets start the game now!\n\nLets have the rules first:") 
    
    broadcast(rules)
    time.sleep(15)
    
    #Warn the users that the questions are going to start
    broadcast("prnStarting with the questions now!!")
    time.sleep(1)
    
    #Keep asking questions unless there is a winner or server is out of questions
    while questionNumber < len(questions) -1:
        
        #Go to next question; initial value is -1
        questionNumber += 1
        
        Question = questions[questionNumber]
        print(Question)

        #Send the question with a question flag
        broadcast("qsn" + Question["question"])        
        time.sleep(1)

        #After a brief pause sent the options and wait for 10s for a reply
        broadcast("rpo" + Question["options"])  
        broadcast("You can press the buzzer now!!")  
        time.sleep(10)

        #If no one presses the buzzer; received in the quizHandle function
        if buzzer == "OFF":
            if questionNumber < len(questions) -1:
              broadcast("prnOops! You're out of time!! Next Question....")

            time.sleep(1)
            
            #Reset all the clients, stop them from sending buzzer responses any more
            broadcast("rst")
            continue

        #While the buzzer is not in the intermediate, wait
        elif buzzer != "wait":
            while buzzer != "wait":
                time.sleep(1)    

        #After the buzzer is reset to an intermediate stage
        elif buzzer == "wait":
            time.sleep(0.001)

            LOCK.acquire()
            try:
                broadcast("prn ")
            finally:
                LOCK.release()
            
            #Reset all clients
            time.sleep(0.001)
            broadcast("rst")
        
        sendScores()
        
        #If we have a winning condition or WIN_LIMIT correct answer
        if findWinner(False):
            break

        #Set buzzer to initial state
        buzzer = "OFF"

        #Continue with the quiz
        time.sleep(0.001)
        if questionNumber < len(questions) -1:
          broadcast("prn\nNext question coming up!")
    

    #Finding the final winner
    findWinner(True)
    

# A loop to accept the requisite number of players
while len(users) != LIMIT:

    user, address = SERVER.accept()
    #Update the list of players
    users.append(user)

    #Log to the serve console
    print("New user#",len(users), "from socket ",address)

    #Start a new thread for the client who just joined the server socket
    start_new_thread(handleUser, (user, ))

#Start the server thread which handles the flow of control
Controller()

