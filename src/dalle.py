import base64
import json
import math
import os
import requests
import asyncio

class Dalle():
    def __init__(self, path:str, delay = 3, batch = 4, max_requests = 10):
        self.tokens = {}
        if os.path.exists(path):
            with open(path) as fr:
                self.tokens = json.load(fr)
                print(self.tokens)
        else:
            print("warning: dalle token file not found.")
        self.task_sleep_seconds = delay
        self.batch_size = batch
        self.max_requests = max_requests
    
    def addToken(self, user_id:str, token:str):
        self.tokens[user_id] = token
    
    def saveTokens(self, path:str):
        with open(path, 'w') as fr:
            json.dump(self.tokens, fr)

    async def generate(self, user_id, prompt):
        print(user_id, 'asked to generate an image.')
        if not str(user_id) in self.tokens.keys():
            raise Exception('''Error: token not provided by user.\n
            - Go to https://labs.openai.com/
            - Open the Network Tab in Developer Tools\n
            - Type a prompt and press \"Generate\"
            - Look for fetch to https://labs.openai.com/api/labs/tasks
            - In the request header look for authorization then get the Bearer Token
            - Use `/dalle-token [token]` to add your token
            ''')

        body = {
            "task_type": "text2im",
            "prompt": {
                "caption": prompt,
                "batch_size": self.batch_size,
            }
        }

        url = "https://labs.openai.com/api/labs/tasks"
        headers = {
            'Authorization': "Bearer " + self.tokens[str(user_id)],
            'Content-Type': "application/json",
        }

        response = requests.post(url, headers=headers, data=json.dumps(body))
        if response.status_code != 200:
            print(response.text)
            return None
        data = response.json()
        print(f"✔️ Task created with ID: {data['id']}")
        print("⌛ Waiting for task to finish...")

        for _ in range(self.max_requests):
            url = f"https://labs.openai.com/api/labs/tasks/{data['id']}"
            response = requests.get(url, headers=headers)
            data = response.json()

            if not response.ok:
                raise Exception("Request failed with status: {response.status_code}, data: {response.json()}")
            if data["status"] == "failed":
                raise Exception(f"Task failed: {data['status_information']}")
            if data["status"] == "rejected":
                raise Exception(f"Task rejected: {data['status_information']}")
            if data["status"] == "succeeded":
                print("Generation succeeded")
                return data["generations"]["data"]

            await asyncio.sleep(self.task_sleep_seconds)
        
        raise Exception("Request time out.")