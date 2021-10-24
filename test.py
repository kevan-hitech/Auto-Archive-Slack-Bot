import slack
from pathlib import Path

# You probably want to use a database to store any conversations information ;)
conversations_store = {}

def get_token():
    """Get token from text file"""
    path = str(Path(__file__).parent.resolve()) + '/'
    fullpath = path + "token.txt"
    file = open(fullpath,"r")
    
    return (file.read())

SLACK_TOKEN = get_token()
client = slack.WebClient(token=SLACK_TOKEN)

def fetch_conversations():
    try:
        # Call the conversations.list method using the WebClient
        result = client.conversations_list()
        save_conversations(result["channels"])

    except Exception as e:
        print(e)


# Put conversations into the JavaScript object
def save_conversations(conversations):
    conversation_id = ""
    for conversation in conversations:
        # Key conversation info on its unique ID
        conversation_id = conversation["id"], conversation["name"]
        print(conversation_id)

        # Store the entire conversation object
        # (you may not need all of the info)
        conversations_store[conversation_id] = conversation
        

fetch_conversations()