import slack
from pathlib import Path
import datetime, re, time
import botsettings


def message_format(title,message,message2=None):
    """Slack Message Format"""
    if not message2:
        message2 = " "
    msg = [
        {
			"type": "header",
			"text": {
				"type": "plain_text",
				"text": title,
				"emoji": True}
	    },
        {
			"type": "section",
			"fields": [{
					"type": "mrkdwn",
					"text": message},]
        },
         {
			"type": "section",
			"fields": [{
					"type": "mrkdwn",
					"text": message2}]
        }
        ]
    return msg


def message_format2(archived_channels):
    archive_message = "The following channels have archived:\n\n"
    for achannel in archived_channels:
        archive_message += "•<#"+achannel+">\n"

    msg = [{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": str(archive_message)
			}
		},
		{
			"type": "divider"
		}]        

    return msg

def get_token():
    """Get token from text file"""

    path = str(Path(__file__).parent.resolve()) + '/'
    fullpath = path + "token.txt"
    file = open(fullpath,"r")
    
    return (file.read().split('\n'))

def get_protectedchannels():
    """Get protected channels from text file"""

    pchan = []
    path = str(Path(__file__).parent.resolve()) + '/'
    fullpath = path + "protectedchannels.txt"
    file = open(fullpath,"r")

    for item in file.readlines():
        pchan.append(item.rstrip().replace('\n',"").replace("#",""))
    
    return pchan

def fetch_conversations():
    """Call the conversations.list method using the WebClient"""
    client = slack.WebClient(token=USER_TOKEN)
    result = client.conversations_list()
    all_channels = save_conversations(result["channels"])

    return all_channels


def save_conversations(conversations):
    """Put conversations into the dictionary object"""
    time_now = datetime.datetime.now()
    conversation_id = ""
    for conversation in conversations:
        # Key conversation info on its unique ID
        conversation_id = conversation["id"]

        # Store the entire conversation object
        # (you may not need all of the info)
        conversations_store[conversation_id] = conversation
        channel = (conversations_store[conversation_id])
        print(channel["name"])
        #print(channel)
        if not channel["is_archived"]:
            try:
                client = slack.WebClient(token=USER_TOKEN)
                result = client.conversations_history(channel=channel["id"], limit=1)
                conversation_history = result["messages"]
                #Grab first message
                channel_info = (conversation_history[0]) #print(channel_info)
                epoch = (float(channel_info["ts"]))
                # Print datetime of last activity
                delta = (datetime.datetime.fromtimestamp(epoch) - time_now).days
                print(" - Inactive for:",delta,"DAYS")
                # If channel inactive for longer than EXPIRY_LIMIT mark as archivabl
                # Unless listed in protected channels
                if channel["name"] not in PROTECTED_CHANNELS:
                    if ((int(delta)*-1) >= EXPIRY_LIMIT):
                        toarchive.append((channel["id"],channel["name"]))
            except Exception as e:
                if "'error': 'not_in_channel'" in str(e):
                    print(" - Bot isn't in this channel")
                    if (channel["name"]) not in PROTECTED_CHANNELS:
                        nopermissions.append((channel["id"],channel["name"]))
                else:
                    print("ERROR:",e)
            
    return(toarchive,nopermissions)

def list_archivables(toarchive_list, private_channel,token_type):
    """Create list of channels which the bot will mark for archiving."""

    client = slack.WebClient(token=token_type)
    archivable_channels = toarchive_list[0]
    if archivable_channels:
        archive_date = ((datetime.datetime.now()) + datetime.timedelta(days=GRACE_PERIOD))
        message = "These channels have been inactive for over *%s* day(s) and are going to be archived by: *[%s]*\n" % (str(EXPIRY_LIMIT),archive_date.strftime("%m/%d/%y"))
        client.chat_postMessage(channel=private_channel,text=message, 
            blocks=message_format(":broom: Archive Request :broom:",message)
            )
        
        for archive in archivable_channels:
            message = ("• *ARCHIVING: *<#" + archive[0]) + ">"
            client.chat_postMessage(channel=private_channel,text=message)  

        message = "You can stop a channel from being archived by adding the :X: reaction to a listed channel.\n<https://slack.com/help/articles/213185307-Archive-or-delete-a-channel#h_01FFR2DKWZQZ9BHDMEHBXTFQAW| ~ Recover archived channels by following this guide.>\n"
        client.chat_postMessage(channel=private_channel,text=message, 
            blocks=[{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": message
			}
		},
		{
			"type": "divider"
		}]
            )
    
        return (archive_date.strftime("%m/%d/%y"))
    
    else:
        return ("")
    
def check_message(private_channel,token_type):
    """Check the status of messages"""
    client = slack.WebClient(token=token_type)
    message_history = client.conversations_history(channel=private_channel,limit=5)
    conversation = message_history["messages"]
    for convo in (conversation):
        xcheck = 0
        try:
            #print("---------botid ",convo["bot_id"])
            #print("---------text ",convo["text"])
            #print("---------reaction",convo["reactions"])
            for react in convo["reactions"]:
                if react["name"] == "x":
                    xcheck = 1
            if xcheck == 0:
                raise Exception("")
            #print("---------time",datetime.datetime.fromtimestamp(float(convo["ts"])))
            channelid = re.findall(r"[<#](\S+)[>]",(convo["text"]))
            channelid = (channelid[0])[1::]
            for channel in toarchive:
                if channelid == channel[0]:
                    toarchive.pop(toarchive.index(channel))
            client.chat_delete(channel=private_channel,ts=convo["ts"])

            pass
        except KeyError:
            pass
        except Exception as e:
            print("General Error:",e)

def archive_channel(private_channel,token_type):
    """Archive channel if requirements are meant"""
    archived = []
    client = slack.WebClient(token=token_type)

    for achannel in toarchive:
        #client.conversations_archive(channel=c[0])
        archived.append(achannel[0])

    # Format message indicating channels that have been archived
    message = message_format2(archived)
    client.chat_postMessage(channel=private_channel,text=message, 
            blocks=message
            )

# -----------------------------------------------------------------------------------------------

check_date = (datetime.datetime.now()).strftime("%m/%d/%y")
toarchive, nopermissions = [], []
today,current_time = check_date,"12:00"

while True:
    SETTINGS = (botsettings.config())
    # Channels that will be added to either list
    # How long a channel must be inactive to be marked for archiving
    EXPIRY_LIMIT = SETTINGS["EXPIRY_LIMIT"]
    # How long before a marked channel is archived
    GRACE_PERIOD = SETTINGS["GRACE_PERIOD"]
    CHECK_INTERVAL = SETTINGS["CHECK_INTERVAL"]
    # Channel the bot communicates.
    PRIVATE_CHANNEL_ID = SETTINGS["PRIVATE_CHANNEL_ID"]
    PROTECTED_CHANNELS = get_protectedchannels()
    BOT_TOKEN = get_token()[0]
    USER_TOKEN = get_token()[1]
    client = slack.WebClient(token=USER_TOKEN)

    # Check channel for reactions
    check_message(PRIVATE_CHANNEL_ID, BOT_TOKEN)

    # Check every X days for channels to mark
    if today == check_date and current_time == "12:00":
        conversations_store = {}
        channels = fetch_conversations()
        archive_date =  list_archivables(channels, PRIVATE_CHANNEL_ID, BOT_TOKEN)
        check_date = ((datetime.datetime.now())+datetime.timedelta(
            days=CHECK_INTERVAL)).strftime("%m/%d/%y")

    # Archive if marked
    if today == archive_date and current_time == "18:10":
        archive_channel(PRIVATE_CHANNEL_ID, BOT_TOKEN)
        toarchive = []

    print("time",today,current_time)
    print("Checking again:",check_date, "Archiving by:",archive_date)
    print("Marked for archiving:",toarchive)
    time.sleep(59)

    #Get today's date
    today = (datetime.datetime.now()).strftime("%m/%d/%y")
    # Get current time
    current_time = (datetime.datetime.now()).strftime("%H:%M")
  