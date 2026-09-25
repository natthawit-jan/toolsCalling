import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const outputDirectory = path.resolve(
  process.env.FILES_DIR ?? fileURLToPath(new URL("./files/", import.meta.url)),
);
await mkdir(outputDirectory, { recursive: true });

const server = new McpServer({ name: "file-creation", version: "1.0.0" });

server.registerTool(
  "create_file",
  {
    description: "Create a UTF-8 text file in the configured output directory. Existing files are never overwritten. Subdirectories are not supported.",
    inputSchema: {
      filename: z.string().min(1).max(255)
        .refine((name) => !/[\\/\x00]/.test(name) && name !== "." && name !== "..",
          "Use a filename without directory separators."),
      content: z.string().describe("Text to write to the file."),
    },
  },
  async ({ filename, content }) => {
    const filePath = path.join(outputDirectory, filename);
    try {
      await writeFile(filePath, content, { encoding: "utf8", flag: "wx" });
      return { content: [{ type: "text", text: `Created ${filePath}` }] };
    } catch (error) {
      return {
        isError: true,
        content: [{ type: "text", text: error.code === "EEXIST"
          ? `File already exists: ${filename}`
          : `Could not create file: ${error.message}` }],
      };
    }
  },
);

// Stdout is reserved for MCP messages.
await server.connect(new StdioServerTransport());
