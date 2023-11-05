import openai
from dotenv import load_dotenv
import os

load_dotenv()
openAI_key = os.getenv("OPENAI_KEY")
openAI_model = os.getenv("ENGINE", default='gpt-3.5-turbo')
# chatbot = AsyncChatbot(api_key=openAI_key, engine=openAI_model)

openai.api_key = openAI_key

contexts = {}

systemPrompt = []

TOKEN_LIMIT = 4096

async def handle_response(message, role = 'user', userid = None) -> str:
    global systemPrompt, contexts
    if role == "system":
        systemPrompt.append({"role": "system", "content": message})
        _massages = [systemPrompt[-1]]
    else:
        if userid and not userid in contexts.keys():
            contexts[userid] = systemPrompt
        if (len(contexts[userid]) == TOKEN_LIMIT):
            del contexts[userid][1]
        contexts[userid].append({"role": role, "content": message})
        _massages = contexts[userid]

    response = await openai.ChatCompletion.acreate(
        model=openAI_model,
        messages = _massages
    )
    responseMessage = response["choices"][0]["message"]["content"].lstrip('\n')

    return responseMessage