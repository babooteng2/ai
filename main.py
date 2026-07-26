# qustion with file upload : Find out how many Apples shares I have and how up or down my portfolio is based on the current market price. thx

import dotenv

import os

dotenv.load_dotenv()
from openai import OpenAI
import asyncio
import streamlit as st
from agents import Agent, Runner, SQLiteSession, WebSearchTool, FileSearchTool

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
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    st.write(message["content"])
                else:
                    if message["type"] == "message":
                        st.write(message["content"][0]["text"])
        if "type" in message and message["type"] == "web_search_call":
            with st.chat_message("ai"):
                st.write("📰 Web Search completed.")
        if "type" in message and message["type"] == "file_search_call":
            with st.chat_message("ai"):
                st.write("🗂️ File Search completed.")


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
    }

    if event in status_messages:
        label, state = status_messages[event]
        status_container.update(label=label, state=state)


async def run_agent(message):
    with st.chat_message("ai"):
        status_container = st.status("⏳", expanded=False)
        text_placeholder = st.empty()
        response = ""

        stream = Runner.run_streamed(agent, message, session=session)

        async for event in stream.stream_events():
            if event.type == "raw_response_event":

                update_status(status_container, event.data.type)

                if event.data.type == "response.output_text.delta":
                    response += event.data.delta
                    text_placeholder.write(response)


prompt = st.chat_input(
    "Write a message for your assistant", accept_file=True, file_type=["txt"]
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
    if prompt.text:
        with st.chat_message("human"):
            st.write(prompt.text)
        asyncio.run(run_agent(prompt.text))


with st.sidebar:
    reset = st.button("Reset memory")
    if reset:
        asyncio.run(session.clear_session())
    st.write(asyncio.run(session.get_items()))
