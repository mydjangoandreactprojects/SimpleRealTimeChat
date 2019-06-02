from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
import json
from core.models import User
from core.models import Message


class ChatConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super(ChatConsumer, self).__init__(*args, **kwargs)
        self.commands = {
            'init_chat': self.init_chat,
            'fetch_messages': self.fetch_messages,
            'new_message': self.new_message
        }
        self.room_name = None
        self.room_group_name = None

    def init_chat(self, data):
        username = data['username']
        user, created = User.objects.get_or_create(username=username)
        content = {
            'command': 'init_chat'
        }
        if not user:
            content['error'] = 'Unable to get or create User with username:' \
                f' {username}'
            self.send_message(content)
        content['success'] = 'Chatting in with success with username:' \
            f' {username}'
        self.send_message(content)

    def fetch_messages(self, data):
        messages = Message.last_50_messages()
        content = {
            'command': 'messages',
            'messages': self.messages_to_json(messages)
        }
        self.send_message(content)

    def new_message(self, data):
        author = data['from']
        text = data['text']
        author_user, created = User.objects.get_or_create(username=author)
        message = Message.objects.create(author=author_user, content=text)
        content = {
            'command': 'new_message',
            'message': self.message_to_json(message)
        }
        self.send_chat_message(content)

    def messages_to_json(self, messages):
        result = []
        for message in messages:
            result.append(self.message_to_json(message))

    @staticmethod
    def message_to_json(message):
        return {
            'id': message.id and str(message.id) or None,
            'author': message.author.username,
            'content': message.content,
            'created_at': str(message.created_at)
        }

    commands = {
        'init_chat': init_chat,
        'fetch_messages': fetch_messages,
        'new_message': new_message
    }

    def connect(self):
        self.room_name = 'room'
        self.room_group_name = f'chat_{self.room_name}'

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, code):
        # Leave group room
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        self.commands[data['command']](data)

    def send_message(self, message):
        self.send(text_data=json.dumps(message))

    def send_chat_message(self, message):
        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    # Receive message from room group
    def chat_message(self, event):
        message = event['message']
        # Send message to WebSocket
        self.send(text_data=json.dumps(message))
