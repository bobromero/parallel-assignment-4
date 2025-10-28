import os
from socket import *
import sys
import threading
import pickle
GOODBYEMSGFILE = "./goodbye.txt"
BEFORELOGINMSGFILE = "./prelogin.txt"
beforeLoginMsg = ""
goodbyeMsg = ""
rooms = dict()
# <room_num,[topic,[list of sockets inside]]
# persistent information
# <username,[password,info,[blocked_users]]>
users = dict()
# <socket,[username,cmdCount]>
socks = dict()
prompt = lambda user, x: f"<{user}:{x}> "
def loadUsers():
    # save the users dictionary to a pickle object
    # create the file if it does not exist
    global users
    if not os.path.exists("users.pickle"):
        with open("users.pickle", "wb") as f:
            pickle.dump({}, f)
    with open("users.pickle", "rb") as f:
        users = pickle.load(f)
    print("Loaded users:", users)
def saveUsers():
    print("Saving users to file...")
    with open("users.pickle", "wb") as f:
        pickle.dump(users, f)
     print("Users saved.", users)
def loadMsgs():
    global beforeLoginMsg
    global goodbyeMsg
    with open(BEFORELOGINMSGFILE, "r") as f:
        beforeLoginMsg = f.read()
    with open(GOODBYEMSGFILE, "r") as f:
        goodbyeMsg = f.read()
n = len(sys.argv)
if n != 2:
    print("Usage: server_port")
    exit()
loadMsgs()
    #Send all data to sock, return 1 if successful 1 if failed (socket error)
def mySendAll(sock, data):
    total_sent = 0
    data_length = len(data)
    try:
        while total_sent < data_length:
            sent = sock.send(data[total_sent:])
            if sent == 0:
                # Socket connection broken
                return -1
            total_sent += sent
    except Exception:
        print("Socket send error in mySendAll.\n")
        return -1
    return 1
def sendToSockets(to_lst, message):
    for s in to_lst:
        mySendAll(s, message.encode())
def sendMessageToRoom(room_name, message):
     sock_list = rooms[room_name]
    sendToSockets(sock_list, message)
def handleShout(message, sock):
    username = socks[sock][0]
    sendToSockets(socks, "\n" + f"<{username}> " + message + "\n")
    print("socks", socks)
    return f"Shout sent to all connected users. {message}"
def handleRegister(split_message, sock):
    if len(split_message) != 3:
        mySendAll(
            socks[sock],
            "Usage: register username password\n".encode(),
        )
        return "ran register command with wrong number of args"
    mySendAll(
        socks[sock],
        f"register: {split_message[1]} {split_message[2]}".encode(),
    )
    if split_message[1] in users.keys():
        mySendAll(
            socks[sock],
            f"Username {split_message[1]} is already taken. Please choose another username.\n".encode(),
        )
        return "ran register command with existing username"
    users[split_message[1]] = [split_message[2], ""]
    saveUsers()
    return f"User {split_message[1]} registered"
guest_prompt = "You login as a guest. The only commands that you can use are 'register username password', 'exit', and 'quit'."
def handleChangeInfo(sock, split_message):
    username = socks[sock][0]
    info = " ".join(split_message[1:])
    users[username][1] = info
    saveUsers()
    return (f"Your info: {info}\n".encode(),)
def handleStatus(sock, split_message):
    username = split_message[1]
    print("handleStatus for", username)
    if username not in users.keys():
        return f"User {username} does not exist.\n"
    info = users[username][1]
    if info == "":
        info = "-"
    onlineStatus = (
        "online" if username in [socks[s][0] for s in socks.keys()] else "offline"
    )
    return f"User: {username} \nInfo: {info} \nBlocked users: (not implemented) \n{onlineStatus}\n"
def handleWho(sock, split_message):
    online_users = [socks[s][0] for s in socks.keys()]
    return "Online users: " + ", ".join(online_users) + "\n"
def handleStart(sock, split_message):
    room_topic = split_message[1]
    # get next availble room number
    room_number = 0
    while str(room_number) in rooms.keys():
        room_number += 1
    rooms[str(room_number)] = [room_topic, [sock]]
    return f"Room {room_number} started with topic: {room_topic}\n"
def handleRooms(sock, split_message):
    # return list of rooms
    # num_rooms room:
    # Room room_num, topic: room_topic
    # num_participants Participant(s): [list of usernames]
    response = ""
    response += f"{len(rooms)} room(s):\n"
    for room_num in rooms.keys():
        room_topic = rooms[room_num][0]
        participants = [socks[s][0] for s in rooms[room_num][1]]
        response += f" Room {room_num}, topic: {room_topic}\n"
        response += f"  {len(participants)} Participant(s): {', '.join(participants)}\n"
    return response
def handleJoin(sock, split_message):
    room_number = split_message[1]
    if room_number not in rooms:
        return f"Room {room_number} does not exist.\n"
    rooms[room_number][1].append(sock)
    return f"You have joined room {room_number}.\n"
def handleLeave(sock, split_message):
    room_number = split_message[1]
    if room_number not in rooms:
        return f"Room {room_number} does not exist.\n"
    if sock not in rooms[room_number][1]:
        return f"You are not in room {room_number}.\n"
    rooms[room_number][1].remove(sock)
    return f"You have left room {room_number}.\n"
# tell the sender if they are blocked
def handleTell(sock, split_message):
    user = split_message[1]
    message = split_message[2:]
    mySendAll(socks[user], message.encode())
    return f""
def handleBlock(sock, split_message):
    user = split_message[1]
def selectCommand(message, sock, isGuest):
    # split message and get command from first word
    split_message = message.split()
    cmd = split_message[0].lower()
    sender_name = socks[sock][0]
    if cmd == "register":
        return handleRegister(split_message, sock)
    if isGuest:
        return guest_prompt.encode()
    match (cmd):
        case "who":
            return handleWho(sock, split_message)
        case "status":
            return handleStatus(sock, split_message)
        case "start":
            return handleStart(sock, split_message)
        case "rooms":
            return handleRooms(sock, split_message)
        case "join":
            return handleJoin(sock, split_message)
        case "leave":
            return handleLeave(sock, split_message)
        case "shout":
            return handleShout(message, sock)
        case "tell":
            handleTell(sock, split_message)
        case "info":
            return handleChangeInfo(sock, split_message)
        case "block":
            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "unblock":
            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "say":
            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case "help":
            mySendAll(socks[sender_name], f"command not implemented: {cmd}.\n".encode())
        case _:
            mySendAll(socks[sender_name], f"Unknown command: {cmd}.\n".encode())
def processCmd(sock, cmd):
    userName = socks[sock][0]
    print(f"process '{cmd}' from {userName}'")
    isGuest = False
    if userName == "guest":
        isGuest = True
    cmd_response = selectCommand(cmd, sock, isGuest)
    print(f"Response: {cmd_response}")
    mySendAll(sock, f"{cmd_response}\n".encode())
def handleUser(sock):
    try:
        while True:
            data = sock.recv(1000)
            if len(data) == 0:
                print("Client closed connection")
                sock.close()
                break
            cmd = data.decode().replace("\t", "").replace("\n", "").replace("\r", "")
            tmp = cmd.split()
            username = socks[sock][0]
            cmdCount = socks[sock][1]
            socks[sock][1] += 1
            if cmd == "" or len(tmp) == 0:
                mySendAll(sock, prompt(username, cmdCount).encode())
                continue
            command = cmd.split()[0].lower()
            if command == "quit" or command == "exit":
                socks.pop(sock)
                mySendAll(sock, goodbyeMsg.encode())
                sock.close()
                break
            else:
                processCmd(sock, cmd)
            # send prompt
            print(f"{username} processed command '{cmd}'")
            mySendAll(sock, prompt(username, cmdCount).encode())
    except Exception as e:
        print("Exception in handleUser:", e)
        socks.pop(sock)
        sock.close()
def askForUsername(sock):
    mySendAll(sock, beforeLoginMsg.encode())
    mySendAll(sock, "Enter your username: ".encode())
    data1 = sock.recv(1000)
    if len(data1) == 0:
        sock.close()
        return
    data2 = data1.decode().split(" ")[0]
    return data2.replace("\t", " ").replace("\n", "").replace("\r", "")
def askForPassword(sock):
    mySendAll(sock, "Enter your password: ".encode())
    data1 = sock.recv(1000)
    if len(data1) == 0:
        sock.close()
        return
    data2 = data1.decode().split(" ")[0]
    return data2.replace("\t", " ").replace("\n", "").replace("\r", "")
def authenticateUser():
    username = ""
    while username == "":
        givenUsername = askForUsername(sock)
        if givenUsername in users.keys():
            password = askForPassword(sock)
            if password == users[givenUsername][0]:
                username = givenUsername
        else:
            username = "guest"
    # check if username already logged in
    for s in socks.keys():
        if socks[s][0] == username:
            mySendAll(
                s,
                goodbyeMsg.encode()
            )
            socks.pop(s)
            s.close()
    # create entry in socks
    socks[sock] = [username, 0]
    return username
def handleOneClient(sock):
    print("Users", users)
    username = authenticateUser()
    str = f"Welcome to the Internet Chat Room, {username}!\n\n"
    mySendAll(sock, str.encode())
    mySendAll(sock, prompt(socks[sock][0], socks[sock][1]).encode())
    handleUser(sock)
s = socket()
h = gethostname()
print(sys.argv[0], sys.argv[1])
loadUsers()
s.bind((h, int(sys.argv[1])))
s.listen(5)
while True:
    sock, addr = s.accept()
    p = threading.Thread(target=handleOneClient, args=(sock,), daemon=True)
    p.start()
