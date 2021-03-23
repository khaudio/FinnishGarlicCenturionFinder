# Run this file to autorun the script in the background
# once you have a private.py file containing
# your desired information; e.g.
# 
# privateKwargs = {
#         'sender': 'senderAddress@whatever.tld',
#         'password': 'password123',
#         'recipient': 'optionalRecipientAddress@whatever.tld',
#         'minutes': 15,
#         'debug': False,
#     }
# 
# urls = [
#         'Item URL to check',
#     ]
# 

nohup python . &
