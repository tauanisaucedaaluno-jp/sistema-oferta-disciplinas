---
name: mcp-builder
description: >-
  Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools.
---

# MCP Server Builder

Use this skill when the user wants to integrate external APIs or services by building an MCP server.

## Guidelines

1. **Identify the Need**: Determine what external resources or tools the agent needs access to.
2. **Choose the Stack**: Decide between Python (using FastMCP) or Node/TypeScript (using the official MCP SDK).
3. **Define Resources and Tools**: 
   - Define *Resources* for static or read-only data.
   - Define *Tools* for actionable operations with clear JSON schemas for arguments.
4. **Error Handling**: Ensure the MCP server gracefully handles API limits, timeouts, and invalid inputs.
5. **Configuration**: Instruct the user on how to add the newly created MCP server to suas configurações.
