import dotenv

import os

dotenv.load_dotenv()
from openai import OpenAI
import asyncio
import base64
import streamlit as st
from agents import (
    Agent,
    Runner,
    SQLiteSession,
    WebSearchTool,
    FileSearchTool,
    ImageGenerationTool,
)

client = OpenAI()
vector_store_id = os.getenv("OPENAI_VECTOR_STORE_ID")

if "agent" not in st.session_state:
    st.session_state["agent"] = Agent(
        name="ChatGPT-Clone",
        instructions="""
        You are a helpful assistant.

        You have access to the followign tools:
            - Web Search Tool: Use this when the user asks a questions that isn't in your training data. Use this tool when the users asks about current or future events, when you think you don't know the answer, try searching for it in the web first.
            - File Search Tool: Use this tool when the user asks a question about facts related to themselves. Or when they ask questions about specific files.
        """,
        tools=[
            WebSearchTool(),
            FileSearchTool(vector_store_ids=[vector_store_id], max_num_results=3),
            ImageGenerationTool(
                tool_config={
                    "type": "image_generation",
                    "quality": "low",
                    "output_format": "jpeg",
                    "moderation": "low",
                    "partial_images": 1,
                }
            ),
        ],
    )
agent = st.session_state["agent"]

if "session" not in st.session_state:
    st.session_state["session"] = SQLiteSession(
        "chat-history", "chat-gpt-clone-memory.db"
    )
session = st.session_state["session"]


async def paint_history():
    messages = await session.get_items()

    for message in messages:
        if "role" in message:
            message_role = message["role"]
            if message_role == "user":
                with st.chat_message(message_role):
                    content = message["content"]
                    if isinstance(content, str):
                        st.write(content)
                    elif isinstance(content, list):
                        for part in content:
                            if part.get("type") == "text":
                                st.write(part.get("text"))
                            elif isinstance(content, list):
                                for part in content:
                                    if "image_url" in part:
                                        st.image(part["image_url"])
            else:
                if message["type"] == "message":
                    if message["content"][0]["text"] == "":
                        pass
                    else:
                        with st.chat_message(message_role):
                            st.write(message["content"][0]["text"].replace("$", "\\$"))

        if "type" in message:
            message_type = message["type"]
            if message_type == "web_search_call":
                with st.chat_message("ai"):
                    st.write("📰 Web Search completed.")
            if message_type == "file_search_call":
                with st.chat_message("ai"):
                    st.write("🗂️ File Search completed.")
            if message_type == "image_generation_call":
                image = base64.b64decode(message["result"])
                with st.chat_message("ai"):
                    st.write("🖼️ Image generation completed.")
                    st.image(image)


asyncio.run(paint_history())


def update_status(status_container, event):
    status_messages = {
        'response.web_search_call.completed': ("✅ Web Search completed.", "complete"),
        'response.web_search_call.in_progress': (
            "📰 Starting Web Search...",
            "running",
        ),
        'response.web_search_call.searching': (
            "⏳ Web Searh in progress...",
            "running",
        ),
        'response.file_search_call.completed': (
            "✅ File Search completed.",
            "complete",
        ),
        'response.file_search_call.in_progress': (
            "🗂️ Starting File Search...",
            "running",
        ),
        'response.file_search_call.searching': (
            "⏳ File Searh in progress...",
            "running",
        ),
        'response.image_generation_call.generating': (
            "🖌️ Drawing image...",
            "running",
        ),
        'response.image_generation_call.in_progress': (
            "🎨 Generating image...",
            "running",
        ),
        "response.completed": (" ", "complete"),
    }

    if event in status_messages:
        label, state = status_messages[event]
        status_container.update(label=label, state=state)


async def run_agent(message):
    with st.chat_message("ai"):
        status_container = st.status("⏳", expanded=False)
        text_placeholder = st.empty()
        image_placeholder = st.empty()
        response = ""

        stream = Runner.run_streamed(agent, message, session=session)

        async for event in stream.stream_events():
            if event.type == "raw_response_event":

                update_status(status_container, event.data.type)

                if event.data.type == "response.output_text.delta":
                    response += event.data.delta
                    text_placeholder.write(response)

                elif event.data.type == "response.image_generation_call.partial_image":
                    image = base64.b64decode(event.data.partial_image_b64)
                    image_placeholder.image(image)

                elif event.data.type == "response.completed":
                    image_placeholder.empty()
                    text_placeholder.empty()


prompt = st.chat_input(
    "Write a message for your assistant",
    accept_file=True,
    file_type=["txt", "jpg", "jpeg", "png"],
)

if prompt:

    for file in prompt.files:
        if file.type.startswith("text/"):
            with st.chat_message("ai"):
                with st.status("⏳ uploading files...") as status:
                    uploaded_file = client.files.create(
                        file=(file.name, file.getvalue()), purpose="user_data"
                    )
                    status.update(label="⏳ Attaching file...")
                    client.vector_stores.files.create(
                        vector_store_id=vector_store_id, file_id=uploaded_file.id
                    )
                    status.update(label="✅ File uploaded", state="complete")
        elif file.type.startswith("image/"):
            with st.status("⏳ uploading image...") as status:
                file_bytes = file.getvalue()
                base64_data = base64.b64encode(file_bytes).decode("utf-8")
                data_uri = f"data:{file.type};base64,{base64_data}"
                asyncio.run(
                    session.add_items(
                        [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_image",
                                        "detail": "auto",
                                        "image_url": data_uri,
                                    }
                                ],
                            }
                        ]
                    )
                )
                status.update(label="✅ Image uploaded", state="complete")
            with st.chat_message("human"):
                st.image(data_uri)

    if prompt.text:
        with st.chat_message("human"):
            st.write(prompt.text)
        asyncio.run(run_agent(prompt.text))


with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))

# question with file upload : Find out how many Apples shares I have and how up or down my portfolio is based on the current market price. thx

# 1 question with image creation : Make image of a Cartoon tomato holding a potato.
# 2 : Now make it into Pixar style.
# 3 : Now in the style of medival painting.
# 4 : Make an infographic of my portfolio, all the stocks i own, cash, assets, etc. in pixar style.
