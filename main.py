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
    WebSearchTool,
    FileSearchTool,
    ImageGenerationTool,
    CodeInterpreterTool,
    HostedMCPTool,
)
from FilteredSQLiteSession import FilteredSQLiteSession

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
            - Code Interpreter Tool: Use this tool when you need to write and code to answer the user's question.
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
                    "size": "1024x1024",
                }
            ),
            CodeInterpreterTool(
                tool_config={"type": "code_interpreter", "container": {"type": "auto"}}
            ),
            HostedMCPTool(
                tool_config={
                    "server_url": "https://mcp.context7.com/mcp",
                    "type": "mcp",
                    "server_label": "Context7",
                    "server_description": "Use this to get the docs from software projects.",
                    "require_approval": "always",
                }
            ),
        ],
    )
agent = st.session_state["agent"]

if "session" not in st.session_state:
    st.session_state["session"] = FilteredSQLiteSession(
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
            elif message_type == "file_search_call":
                with st.chat_message("ai"):
                    st.write("🗂️ File Search completed.")
            elif message_type == "image_generation_call":
                image = base64.b64decode(message["result"])
                with st.chat_message("ai"):
                    st.write("🖼️ Image generation completed.")
                    st.image(image)
            elif message_type == "code_interpreter_call":
                with st.chat_message("ai"):
                    st.write("🤖 Code interpreter completed.")
                    st.code(message["code"])
            elif message_type == "mcp_list_tools":
                with st.chat_message("ai"):
                    tools = message["tools"]
                    st.write(f"Listed {message["server_label"]}'s tools")
                    if isinstance(tools, str):
                        st.write(tools)
                    if isinstance(tools, list):
                        for index, (tool) in enumerate(tools):
                            if "name" in tool:
                                st.write(f"[ {index + 1} ] {tool["name"]}")
                            if "description" in tool:
                                st.write(f"- Description : {tool["description"]}")
                            if "input_schema" in tool:
                                st.json(tool["input_schema"])
                            st.write(
                                f"======================================================"
                            )
            elif message_type == "mcp_approval_request":
                with st.chat_message("ai"):
                    st.write(f"Server Label : {message["server_label"]}")
                    st.write(f"- Name : {message["name"]}")
                    st.json(message["arguments"])


asyncio.run(paint_history())


def update_status(status_container, event):
    status_messages = {
        'response.web_search_call.completed': ("✅ Web Search completed.", "complete"),
        'response.web_search_call.in_progress': (
            "📰 Starting Web Search...",
            "running",
        ),
        'response.web_search_call.searching': (
            "⏳ Web Search in progress...",
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
            "⏳ File Search in progress...",
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
        'response.code_interpreter_call_code.done': ("🤖 ran code done.", "complete"),
        'response.code_interpreter_call.completed': (
            "🤖 ran code complete.",
            "complete",
        ),
        'response.code_interpreter_call.in_progress': (
            "🤖 starting code.",
            "running",
        ),
        'response.code_interpreter_call.interpreting': (
            "🤖 running code...",
            "running",
        ),
        'response.mcp_call_arguments.delta': ("🛠️ MCP progress...", "running"),
        'response.mcp_call_arguments.done': ("🛠️ MCP arguments done...", "complete"),
        'response.mcp_call.completed': ("🛠️ MCP called...", "complete"),
        'response.mcp_call.failed': ("🛠️ MCP failed...", "fail"),
        'response.mcp_call.in_progress': ("🛠️ MCP calling...", "running"),
        'response.mcp_list_tools.completed': (
            "🛠️ Listed MCP tools...",
            "complete",
        ),
        'response.mcp_list_tools.failed': ("🛠️ MCP list tools failed...", "fail"),
        'response.mcp_list_tools.in_progress': (
            "🛠️ Listing MCP tools...",
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
        code_placeholder = st.empty()
        image_placeholder = st.empty()
        text_placeholder = st.empty()
        response = ""
        code_response = ""

        st.session_state["code_placeholder"] = code_placeholder
        st.session_state["image_placeholder"] = image_placeholder
        st.session_state["text_placeholder"] = text_placeholder

        stream = Runner.run_streamed(agent, message, session=session)

        async for event in stream.stream_events():
            if event.type == "raw_response_event":

                update_status(status_container, event.data.type)

                if event.data.type == "response.output_text.delta":
                    response += event.data.delta
                    text_placeholder.write(response)

                if event.data.type == "response.code_interpreter_call_code.delta":
                    code_response += event.data.delta
                    code_placeholder.code(code_response)

                elif event.data.type == "response.image_generation_call.partial_image":
                    image = base64.b64decode(event.data.partial_image_b64)
                    image_placeholder.image(image)


prompt = st.chat_input(
    "Write a message for your assistant",
    accept_file=True,
    file_type=["txt", "jpg", "jpeg", "png"],
)

if prompt:
    if "code_placeholder" in st.session_state:
        st.session_state["code_placeholder"].empty()
    if "image_placeholder" in st.session_state:
        st.session_state["image_placeholder"].empty()
    if "text_placeholder" in st.session_state:
        st.session_state["text_placeholder"].empty()

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

# code interpreter tool
# 1 : Calculate what happens if everything in my portfolio of stock goes up by 20% (run code to make the calculation)
# 2: Run some code to calculate what happens if everything in my portfolio goes up by 10%
# 3: Now calculate what happens if it goes down 40%

# MCP tools
# 1: what mcp tools do you have?
# 2: Use Context7 with HostedMCPTool to tell me about making SRT files with OpenAI
