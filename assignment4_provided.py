from socket import *
import sys
import threading
 GOODBYEMSGFILE = "./goodbye.txt"
%BEFORELOGINMSGFILE = "./prelogin.txt"
beforeLoginMsg = ""
goodbyeMsg = ""
rooms = dict()
,# <room_num,[topic,[list of sockets inside]]
# <username,[password,info]>
users = dict()
# <socket,[username,cmdCount]>
socks = dict()
)prompt = lambda user, x: f"<{user}:{x}> "
def loadUsers():
%    # create file if it doesn't exist
    try:
&        open("users.txt", "x").close()
    except FileExistsError:
        pass
%    with open("users.txt", "r") as f:
        lines = f.readlines()
        for line in lines:
-            split_line = line.strip().split()
$            if len(split_line) >= 2:
(                username = split_line[0]
(                password = split_line[1]
N                info = " ".join(split_line[2:]) if len(split_line) > 2 else ""
2                users[username] = [password, info]
def saveUser():
$    print("Saving users to file...")
%    with open("users.txt", "w") as f:
8        for username, (password, info) in users.items():
6            f.write(f"{username} {password} {info}\n")
     print("Users saved.", users)
def loadMsgs():
    global beforeLoginMsg
    global goodbyeMsg
,    with open(BEFORELOGINMSGFILE, "r") as f:
!        beforeLoginMsg = f.read()
(    with open(GOODBYEMSGFILE, "r") as f:
        goodbyeMsg = f.read()
n = len(sys.argv)
if n != 2:
    print("Usage: server_port")
    exit()
loadMsgs()
-Send all data to sock, return 1 if successful
-1 if failed (socket error)
def mySendAll(sock, data):
    total_sent = 0
    data_length = len(data)
    try:
'        while total_sent < data_length:
/            sent = sock.send(data[total_sent:])
            if sent == 0:
*                # Socket connection broken
                return -1
            total_sent += sent
    except Exception:
2        print("Socket send error in mySendAll.\n")
        return -1
    return 1
#def sendToSockets(to_lst, message):
    for s in to_lst:
&        mySendAll(s, message.encode())
*def sendMessageToRoom(room_name, message):
     sock_list = rooms[room_name]
%    sendToSockets(sock_list, message)
def handleShout(message, sock):
    username = socks[sock][0]
B    sendToSockets(socks, "\n" + f"<{username}> " + message + "\n")
    print("socks", socks)
:    return f"Shout sent to all connected users. {message}"
(def handleRegister(split_message, sock):
    if len(split_message) != 3:
        mySendAll(
            socks[sock],
;            "Usage: register username password\n".encode(),
                )
?        return "ran register command with wrong number of args"
    mySendAll(
        socks[sock],
D        f"register: {split_message[1]} {split_message[2]}".encode(),
    )
(    if split_message[1] in users.keys():
        mySendAll(
            socks[sock],
h            f"Username {split_message[1]} is already taken. Please choose another username.\n".encode(),
                )
<        return "ran register command with existing username"
4    users[split_message[1]] = [split_message[2], ""]
    saveUser()
0    return f"User {split_message[1]} registered"
guest_prompt = "You login as a guest. The only commands that you can use are 'register username password', 'exit', and 'quit'."
*def handleChangeInfo(sock, split_message):
    username = socks[sock][0]
&    info = " ".join(split_message[1:])
    users[username][1] = info
    saveUser()
-    return (f"Your info: {info}\n".encode(),)
&def handleStatus(sock, split_message):
    username = split_message[1]
'    print("handleStatus for", username)
$    if username not in users.keys():
3        return f"User {username} does not exist.\n"
    info = users[username][1]
    if info == "":
        info = "-"
    onlineStatus = (
R        "online" if username in [socks[s][0] for s in socks.keys()] else "offline"
    )
c    return f"User: {username} \nInfo: {info} \nBlocked users: (not implemented) \n{onlineStatus}\n"
*def selectCommand(message, sock, isGuest):
3    # split message and get command from first word
#    split_message = message.split()
"    cmd = split_message[0].lower()
     sender_name = socks[sock][0]
    if cmd == "register":
2        return handleRegister(split_message, sock)
    if isGuest:
$        return guest_prompt.encode()
    match (cmd):
        case "who":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "status":
4            return handleStatus(sock, split_message)
        case "start":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "rooms":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "join":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "leave":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "shout":
-            return handleShout(message, sock)
        case "tell":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "info":
8            return handleChangeInfo(sock, split_message)
        case "block":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "unblock":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "say":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "help":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case _:
P            mySendAll(socks[sender_name], f"Unknown command: {cmd}.\n".encode())
def processCmd(sock, cmd):
    userName = socks[sock][0]
.    print(f"process '{cmd}' from {userName}'")
    isGuest = False
    if userName == "guest":
        isGuest = True
4    cmd_response = selectCommand(cmd, sock, isGuest)
&    print(f"Response: {cmd_response}")
1    mySendAll(sock, f"{cmd_response}\n".encode())
def handleUser(sock):
    try:
        while True:
"            data = sock.recv(1000)
            if len(data) == 0:
1                print("Client closed connection")
                sock.close()
                break
U            cmd = data.decode().replace("\t", "").replace("\n", "").replace("\r", "")
            tmp = cmd.split()
%            username = socks[sock][0]
%            cmdCount = socks[sock][1]
            socks[sock][1] += 1
*            if cmd == "" or len(tmp) == 0:
D                mySendAll(sock, prompt(username, cmdCount).encode())
                continue
,            command = cmd.split()[0].lower()
6            if command == "quit" or command == "exit":
4                mySendAll(sock, goodbyeMsg.encode())
                sock.close()
                break
            else:
%                processCmd(sock, cmd)
            # send prompt
:            print(f"{username} processed command '{cmd}'")
@            mySendAll(sock, prompt(username, cmdCount).encode())
    except Exception as e:
,        print("Exception in handleUser:", e)
        sock.close()
def askForUsername(sock):
,    mySendAll(sock, beforeLoginMsg.encode())
5    mySendAll(sock, "Enter your username: ".encode())
    data1 = sock.recv(1000)
    if len(data1) == 0:
        sock.close()
        return
(    data2 = data1.decode().split(" ")[0]
G    return data2.replace("\t", " ").replace("\n", "").replace("\r", "")
def askForPassword(sock):
5    mySendAll(sock, "Enter your password: ".encode())
    data1 = sock.recv(1000)
    if len(data1) == 0:
        sock.close()
        return
(    data2 = data1.decode().split(" ")[0]
G    return data2.replace("\t", " ").replace("\n", "").replace("\r", "")
def authenticateUser():
    username = ""
    while username == "":
,        givenUsername = askForUsername(sock)
)        if givenUsername in users.keys():
+            password = askForPassword(sock)
3            if password == users[givenUsername][0]:
(                username = givenUsername
        else:
            username = "guest"
    # create entry in socks
    socks[sock] = [username, 0]
    return username
def handleOneClient(sock):
!    username = authenticateUser()
?    str = f"Welcome to the Internet Chat Room, {username}!\n\n"
!    mySendAll(sock, str.encode())
D    mySendAll(sock, prompt(socks[sock][0], socks[sock][1]).encode())
    handleUser(sock)
s = socket()
h = gethostname()
print(sys.argv[0], sys.argv[1])
loadUsers()
s.bind((h, int(sys.argv[1])))
s.listen(5)
while True:
    sock, addr = s.accept()
K    p = threading.Thread(target=handleOneClient, args=(sock,), daemon=True)
    p.start()5
7    saveUser(split_message[1], split_message[2], split)5
4            f.write(f"{username} {password} {info}\n5
from socket import *
import sys
import threading
import uuid
 GOODBYEMSGFILE = "./goodbye.txt"
%BEFORELOGINMSGFILE = "./prelogin.txt"
beforeLoginMsg = ""
goodbyeMsg = ""
rooms = dict()
,# <room_num,[topic,[list of sockets inside]]
# <username,[password,info]>
users = dict()
# <socket,[username,cmdCount]>
socks = dict()
)prompt = lambda user, x: f"<{user}:{x}> "
def loadUsers():
    global users
%    with open("users.txt", "r") as f:
        lines = f.readlines()
        for line in lines:
-            split_line = line.strip().split()
$            if len(split_line) >= 2:
(                username = split_line[0]
(                password = split_line[1]
N                info = " ".join(split_line[2:]) if len(split_line) > 2 else ""
2                users[username] = [password, info]
def saveUser():
%    with open("users.txt", "w") as f:
8        for username, (password, info) in users.items():
4            f.write(f"{username} {password} {info}\n
def updateUserInfo():
    pass
def loadMsgs():
    global beforeLoginMsg
    global goodbyeMsg
,    with open(BEFORELOGINMSGFILE, "r") as f:
!        beforeLoginMsg = f.read()
(    with open(GOODBYEMSGFILE, "r") as f:
        goodbyeMsg = f.read()
n = len(sys.argv)
if n != 2:
    print("Usage: server_port")
    exit()
loadMsgs()
-Send all data to sock, return 1 if successful
-1 if failed (socket error)
def mySendAll(sock, data):
    total_sent = 0
    data_length = len(data)
    try:
'        while total_sent < data_length:
/            sent = sock.send(data[total_sent:])
            if sent == 0:
*                # Socket connection broken
                return -1
            total_sent += sent
    except Exception:
2        print("Socket send error in mySendAll.\n")
        return -1
    return 1
#def sendToSockets(to_lst, message):
    for s in to_lst:
&        mySendAll(s, message.encode())
*def sendMessageToRoom(room_name, message):
     sock_list = rooms[room_name]
%    sendToSockets(sock_list, message)
def handleShout(message, sock):
    username = socks[sock][0]
B    sendToSockets(socks, "\n" + f"<{username}> " + message + "\n")
    print("socks", socks)
:    return f"Shout sent to all connected users. {message}"
(def handleRegister(split_message, sock):
    if len(split_message) != 3:
        mySendAll(
            socks[sock],
;            "Usage: register username password\n".encode(),
                )
?        return "ran register command with wrong number of args"
    mySendAll(
        socks[sock],
D        f"register: {split_message[1]} {split_message[2]}".encode(),
    )
(    if split_message[1] in users.keys():
        mySendAll(
            socks[sock],
h            f"Username {split_message[1]} is already taken. Please choose another username.\n".encode(),
                )
<        return "ran register command with existing username"
4    users[split_message[1]] = [split_message[2], ""]
0    return f"User {split_message[1]} registered"
guest_prompt = "You login as a guest. The only commands that you can use are 'register username password', 'exit', and 'quit'."
*def selectCommand(message, sock, isGuest):
3    # split message and get command from first word
#    split_message = message.split()
"    cmd = split_message[0].lower()
     sender_name = socks[sock][0]
    if cmd == "register":
2        return handleRegister(split_message, sock)
    if isGuest:
        mySendAll(
            socks[sender_name],
\            f"Guests can only use the following commands: register, exit, quit.\n".encode(),
                )
        return
    match (cmd):
        case "who":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "status":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "start":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "rooms":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "join":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "leave":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "shout":
-            return handleShout(message, sock)
        case "tell":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "info":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "block":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "unblock":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "say":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "help":
X            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case _:
P            mySendAll(socks[sender_name], f"Unknown command: {cmd}.\n".encode())
def processCmd(sock, cmd):
    userName = socks[sock][0]
.    print(f"process '{cmd}' from {userName}'")
    isGuest = False
    if userName == "guest":
        isGuest = True
4    cmd_response = selectCommand(cmd, sock, isGuest)
&    print(f"Response: {cmd_response}")
def handleUser(sock):
    try:
        while True:
"            data = sock.recv(1000)
            if len(data) == 0:
1                print("Client closed connection")
                sock.close()
                break
U            cmd = data.decode().replace("\t", "").replace("\n", "").replace("\r", "")
            tmp = cmd.split()
%            username = socks[sock][0]
%            cmdCount = socks[sock][1]
            socks[sock][1] += 1
*            if cmd == "" or len(tmp) == 0:
D                mySendAll(sock, prompt(username, cmdCount).encode())
                continue
,            command = cmd.split()[0].lower()
6            if command == "quit" or command == "exit":
4                mySendAll(sock, goodbyeMsg.encode())
                sock.close()
                break
            else:
%                processCmd(sock, cmd)
            # send prompt
:            print(f"{username} processed command '{cmd}'")
@            mySendAll(sock, prompt(username, cmdCount).encode())
    except Exception as e:
,        print("Exception in handleUser:", e)
        sock.close()
def askForUsername(sock):
,    mySendAll(sock, beforeLoginMsg.encode())
5    mySendAll(sock, "Enter your username: ".encode())
    data1 = sock.recv(1000)
    if len(data1) == 0:
        sock.close()
        return
(    data2 = data1.decode().split(" ")[0]
G    return data2.replace("\t", " ").replace("\n", "").replace("\r", "")
def askForPassword(sock):
5    mySendAll(sock, "Enter your password: ".encode())
    data1 = sock.recv(1000)
    if len(data1) == 0:
        sock.close()
        return
(    data2 = data1.decode().split(" ")[0]
G    return data2.replace("\t", " ").replace("\n", "").replace("\r", "")
def authenticateUser():
    username = ""
    while username == "":
,        givenUsername = askForUsername(sock)
)        if givenUsername in users.keys():
+            password = askForPassword(sock)
3            if password == users[givenUsername][0]:
(                username = givenUsername
        else:
            username = "guest"
    # create entry in socks
    socks[sock] = [username, 0]
    return username
def handleOneClient(sock):
!    username = authenticateUser()
?    str = f"Welcome to the Internet Chat Room, {username}!\n\n"
!    mySendAll(sock, str.encode())
D    mySendAll(sock, prompt(socks[sock][0], socks[sock][1]).encode())
    handleUser(sock)
s = socket()
h = gethostname()
print(sys.argv[0], sys.argv[1])
s.bind((h, int(sys.argv[1])))
s.listen(5)
while True:
    sock, addr = s.accept()
K    p = threading.Thread(target=handleOneClient, args=(sock,), daemon=True)
    p.start()5
def update():5
