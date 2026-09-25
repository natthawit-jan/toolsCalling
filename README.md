# File creation MCP server

A small JavaScript MCP server using the official SDK and stdio transport.
Requires Node.js 20 or newer.

```sh
npm install
npm start
```

The server waits for an MCP client on stdin; it is not an HTTP server.

Add this entry to your MCP client's server configuration (adjust the absolute path):

```json
{
  "mcpServers": {
    "file-creation": {
      "command": "node",
      "args": ["/Users/natthawit/Desktop/toolsCalling/server.js"]
    }
  }
}
```

The `create_file` tool accepts:

```json
{
  "filename": "hello.txt",
  "content": "Hello, world!\n"
}
```

Files go into `files/` beside `server.js`. Set the `FILES_DIR` environment variable
to an absolute directory path to change this location, including through an `env`
object in the client configuration. The directory is created automatically.
Only plain filenames are accepted, and existing files (including symlinks) are
never overwritten. Use a trusted output directory.

SDK reference: https://ts.sdk.modelcontextprotocol.io/server

## Python chatbot

The repository also includes a terminal chatbot using the OpenAI Python SDK against
Apfel's OpenAI-compatible endpoint. It starts the local MCP server, discovers its
tools, and lets Apfel call them during a conversation.

```sh
uv sync
uv run python chatbot.py
```

The defaults are:

- `APFEL_BASE_URL=http://localhost:11434/v1`
- `APFEL_API_KEY=unused`
- `APFEL_MODEL=apple-foundationmodel`

Override them with environment variables when needed. Copy `.env.example` as a
reference; the chatbot reads configuration from the environment and does not load
or print secrets from a file.
