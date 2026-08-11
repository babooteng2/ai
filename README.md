# Openai-Chatgpt-Clone

- with streamlit

```cmd
streamlit run main.py
```

## Installation

```cmd
uv sync
```

### openai version

- openai==2.48.0
- openai-agents==0.18.3

### MCP Server

- context7 : "https://mcp.context7.com/mcp"
- https://www.pulsemcp.com/

### MCPServerStdio

1. remove caching
2. whenever send message, build agent (cache_tools_list=True)

## Examples of Questions

- File Search Tool

1. question with file upload : Find out how many Apples shares I have and how up or down my portfolio is based on the current market price. thx

- Image Generattion tool

1. question with image creation : Make image of a Cartoon tomato holding a potato.
2. : Now make it into Pixar style.
3. : Now in the style of medival painting.
4. Make an infographic of my portfolio, all the stocks i own, cash, assets, etc. in pixar style.

- Code Interpreter tool

1.  Calculate what happens if everything in my portfolio of stock goes up by 20% (run code to make the calculation)
2.  Run some code to calculate what happens if everything in my portfolio goes up by 10%
3.  Now calculate what happens if it goes down 40%

- Hosted MCP tools

1. what mcp tools do you have?
2. Use Context7 with HostedMCPTool to tell me about making SRT files with OpenAI

- Local MCPServerStdio

1. what tools do you have?
2. Tell me the stock price of AAPL
3. Tell me the PE ratio of Cloudflare NET
