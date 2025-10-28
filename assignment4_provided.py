import os
from socket import *
import sys
import threading
import pickle

GOODBYEMSGFILE = "./goodbye.txt"
BEFORELOGINMSGFILE = "./prelogin.txt"
HELPMESSAGEFILE = "./help.txt"
WELCOMEFILE = "./welcome.txt"
beforeLoginMsg = ""
goodbyeMsg = ""
helpMessage = ""
welcomeMsg = ""
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
            pass
    with open("users.pickle", "rb") as f:
        if os.path.getsize("users.pickle") == 0:
            users = dict()
        else:
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
    global helpMessage
    global welcomeMsg
    with open(BEFORELOGINMSGFILE, "r") as f:
        beforeLoginMsg = f.read()
    with open(GOODBYEMSGFILE, "r") as f:
        goodbyeMsg = f.read()
    with open(HELPMESSAGEFILE, "r") as f:
        helpMessage = f.read()
    with open(WELCOMEFILE, "r") as f:
        welcomeMsg = f.read()


n = len(sys.argv)
if n != 2:
    print("Usage: server_port")
    exit()
loadMsgs()


# Send all data to sock, return 1 if successful
# 1 if failed (socket error)
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


def sendToSockets(to_lst, message, sender_sock):
    for s in to_lst:
        print(
            "block list:",
            users[socks[s][0]][2],
            "sendername",
            socks[sender_sock],
            "condition:",
            socks[sender_sock] in users[socks[s][0]][2],
        )
        if socks[sender_sock][0] in users[socks[s][0]][2]:
            continue
        mySendAll(s, message.encode())


def sendMessageToRoom(room_number, message, sock):
    sock_list = rooms[room_number][1]
    sendToSockets(sock_list, message, sock)


def handleShout(sock, split_message):
    if len(split_message) < 2:
        return "Usage: shout <Msg>\n"
    username = socks[sock][0]
    message = " ".join(split_message[1:])
    sendToSockets(socks, f"!!{username}!!: { message }\n", sock)
    return f""


def handleRegister(split_message, sock):
    if len(split_message) != 3:
        return "Usage: register <user> <passwd>\n"
    if split_message[1] in users.keys():
        return f"Username {split_message[1]} is already taken. Please choose another username.\n"
    users[split_message[1]] = [split_message[2], "", []]
    saveUsers()
    return f"User {split_message[1]} registered\n"


guest_prompt = "You login as a guest. The only commands that you can use are \n'register username password', 'exit', and 'quit'.\n"


def handleChangeInfo(sock, split_message):
    username = socks[sock][0]
    if len(split_message) < 2:
        info = users[username][1]
        if info == "":
            info = "-"
        return f"Info: {info}\n"
    info = " ".join(split_message[1:])
    users[username][1] = info
    saveUsers()
    return "Your information has been updated\n"


def handleStatus(sock, split_message):
    username = ""
    if len(split_message) != 2:
        username = socks[sock][0]
    else:
        username = split_message[1]
    if username not in users.keys():
        return f"User {username} does not exist.\n"
    print("handleStatus for", username)
    info = users[username][1]
    if info == "":
        info = "-"
    onlineStatus = (
        "online" if username in [socks[s][0] for s in socks.keys()] else "offline"
    )
    blocked_users = ", ".join(users[username][2])
    print("finished handleStatus for", username)
    return f"User: {username} \nInfo: {info} \nBlocked user(s): {blocked_users} \n{onlineStatus}\n"


def handleWho(sock, split_message):
    if split_message != ["who"]:
        return "Usage: who\n"
    online_users = [socks[s][0] for s in socks.keys()]
    return f"{len(online_users)} users online: \n\n{' '.join(online_users)}\n"


def handleStart(sock, split_message):
    if len(split_message) < 2:
        return "Usage: start <topic>\n"
    room_topic = split_message[1]
    # get next availble room number
    room_number = 0
    while str(room_number) in rooms.keys():
        room_number += 1
    rooms[str(room_number)] = [room_topic, [sock]]
    sendToSockets(
        socks,
        f"\n!!system!!: {socks[sock][0]} created room {room_number}, topic: {room_topic}\n",
        None,
    )
    return f""


def handleRooms(sock, split_message):
    # return list of rooms
    # num_rooms room:
    # Room room_num, topic: room_topic
    # num_participants Participant(s): [list of usernames]
    response = ""
    if len(rooms) <= 1:
        response += f"{len(rooms)} room:\n\n"
    else:
        response += f"{len(rooms)} rooms:\n"
    for room_num in rooms.keys():
        room_topic = rooms[room_num][0]
        participants = [socks[s][0] for s in rooms[room_num][1]]
        response += f"Room {room_num}, topic: {room_topic}\n"
        response += f"{len(participants)} Participant(s): {', '.join(participants)}\n\n"
    return response


def handleJoin(sock, split_message):
    if len(split_message) != 2:
        return "Usage: join <room_number>\n"
    room_number = split_message[1]
    if room_number not in rooms:
        return f"Room {room_number} does not exist.\n"
    rooms[room_number][1].append(sock)
    return f"You have joined room {room_number}.\n"


def clearRoom(room_number, room_topic, sock):
    if room_number in rooms:
        sendToSockets(
            rooms[room_number][1],
            f"\n!!system!!: Room {room_number}(topic: {room_topic}) closed\n",
            None,
        )
        rooms.pop(room_number)


def handleLeave(sock, split_message):
    if len(split_message) != 2:
        return "Usage: leave <room_number>\n"
    room_number = split_message[1]
    if room_number not in rooms:
        return f"Room {room_number} does not exist.\n"
    if sock not in rooms[room_number][1]:
        return f"You are not in room {room_number}.\n"
    room_topic = rooms[room_number][0]
    if rooms[room_number][1][0] == sock:
        # room creator is leaving, close the room
        clearRoom(room_number, room_topic, sock)
        return f""
    else:
        rooms[room_number][1].remove(sock)
        return f"You Have left room {room_number}\n\n"


# tell the sender if they are blocked
def handleTell(sock, split_message):
    if len(split_message) < 3:
        return "Usage: tell <user> <Msg>\n"
    to_name = split_message[1]
    if to_name not in users.keys():
        return f"User {to_name} does not exist.\n"
    if to_name not in [socks[s][0] for s in socks.keys()]:
        return f"User {to_name} is not online.\n"
    from_name = socks[sock][0]
    message = " ".join(split_message[2:])
    for s in socks.keys():
        if socks[s][0] == to_name:
            sendToSockets([s], f"{from_name}: {message}\n", sock)
            break
    return f""


def handleBlock(sock, split_message):
    if len(split_message) != 2:
        return "Usage: block <user>\n"
    username = socks[sock][0]
    user_to_block = split_message[1]
    if user_to_block == username:
        return "Sorry, you cannot block yourself.\n"
    if user_to_block not in users.keys():
        return f"User {user_to_block} does not exist.\n"
    if user_to_block in users[username][2]:
        return f"User {user_to_block} is already blocked.\n"
    users[username][2].append(user_to_block)
    saveUsers()
    return f"User {user_to_block} has been blocked.\n"


def handleUnblock(sock, split_message):
    if len(split_message) != 2:
        return "Usage: unblock <user>\n"
    username = socks[sock][0]
    user_to_unblock = split_message[1]
    if user_to_unblock not in users.keys():
        return f"User {user_to_unblock} does not exist.\n"
    if user_to_unblock not in users[username][2]:
        return f"User {user_to_unblock} is not blocked.\n"
    users[username][2].remove(user_to_unblock)
    saveUsers()
    return f"User {user_to_unblock} has been unblocked.\n"


def handleSay(sock, split_message):
    if len(split_message) < 3:
        return "Usage: say <room_number> <Msg>\n"
    room_number = split_message[1]
    message = " ".join(split_message[2:])
    username = socks[sock][0]
    if room_number not in rooms:
        return f"Room {room_number} does not exist.\n"
    if sock not in rooms[room_number][1]:
        return f"You are not in room {room_number}.\n"
    # send message to all users in room
    sendMessageToRoom(
        room_number, f"[Room {room_number}] *{username}*: {message}\n", sock
    )
    return f""


def selectCommand(message, sock, isGuest):
    # split message and get command from first word
    split_message = message.split()
    cmd = split_message[0].lower()
    sender_name = socks[sock][0]
    if cmd == "register":
        return handleRegister(split_message, sock)
    if isGuest:
        return guest_prompt
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
            return handleShout(sock, split_message)
        case "tell":
            return handleTell(sock, split_message)
        case "info":
            return handleChangeInfo(sock, split_message)
        case "block":
            return handleBlock(sock, split_message)
        case "unblock":
            return handleUnblock(sock, split_message)
        case "say":
            return handleSay(sock, split_message)
        case "help":
            return helpMessage
        case _:
            return f"Unknown command: {cmd}.\n"


def processCmd(sock, cmd):
    userName = socks[sock][0]
    print(f"process '{cmd}' from {userName}'")
    isGuest = False
    if userName == "guest":
        isGuest = True
    cmd_response = selectCommand(cmd, sock, isGuest)
    print(f"Response: {cmd_response}")
    mySendAll(sock, f"{cmd_response}".encode())


def disconnectUser(sock):
    socks.pop(sock)
    mySendAll(sock, goodbyeMsg.encode())
    sock.close()


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
                if username == "guest":
                    mySendAll(sock, guest_prompt.encode())
                mySendAll(sock, prompt(username, cmdCount + 1).encode())
                continue
            command = cmd.split()[0].lower()
            if command == "quit" or command == "exit":
                disconnectUser(sock)
                break
            else:
                processCmd(sock, cmd)
            # send prompt
            print(f"{username} processed command '{cmd}'")
            mySendAll(sock, prompt(username, cmdCount + 1).encode())
    except Exception as e:
        print("Exception in handleUser:", e)
        disconnectUser(sock)


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


def authenticateUser(sock):
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
            socks.pop(s)
            mySendAll(s, goodbyeMsg.encode())
            s.close()
            break
    # create entry in socks
    socks[sock] = [username, 0]
    return username


def handleOneClient(sock):
    username = authenticateUser(sock)
    mySendAll(sock, welcomeMsg.encode())
    if username == "guest":
        mySendAll(sock, guest_prompt.encode())
    else:
        mySendAll(sock, helpMessage.encode())
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
