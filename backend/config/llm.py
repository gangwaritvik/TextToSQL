import os
from dotenv import load_dotenv
load_dotenv(".env.local")  # Load environment variables from .env.local

azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION")

from langchain_openai import AzureChatOpenAI

model = AzureChatOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=azure_api_key,
        api_version=azure_api_version,
        model="gpt-4.1")
