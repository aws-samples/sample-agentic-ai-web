import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { randomUUID } from 'crypto';
import {
    chromium
} from 'playwright';
import * as fs from 'fs';

const sessionId = randomUUID();

fs.mkdirSync(`screenshots/${sessionId}/`, { recursive: true });
fs.mkdirSync(`artefacts/${sessionId}/`, { recursive: true });

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Create an MCP server
const server = new McpServer({
    name: "Web Automation Server",
    version: "1.0.0"
});

server.tool("getPageInfo",
    async () => {
        const title = await page.title();
        const url = page.url();

        return { content: [{ type: "text", text: `Current page: ${title}, URL: ${url}` }] }
    }
);

server.tool("navigate",
    {
        url: z.string(),
    },
    async ({ url }) => {
        console.log("Navigating to", url);
        await page.goto(url, { timeout: 80000, waitUntil: 'domcontentloaded' });

        const title = await page.title();

        return { content: [{ type: "text", text: title }] }
    }
);

server.tool("screenshot",
    async () => {
        const filename = `screenshots/${sessionId}/screenshot_${randomUUID()}.png`;
        console.log("Taking screenshot", filename);
        await page.screenshot({ path: filename, quality: 80, type: "jpeg" });

        return { content: [{ type: "text", text: filename }] }
    }
);

server.tool("type",
    {
        text: z.string(),
        submit: z.boolean().optional().default(false),
    },
    async ({ text, submit }) => {
        try {
            await page.keyboard.type(text);

            if (submit) {
                printSystem(`Pressing Enter to submit`);
                await page.keyboard.press('Enter');
                return { content: [{ type: "text", text: "submited" }] }
            }
            return { content: [{ type: "text", text: "not submited" }] }
        } catch (error) {
            printSystem(`Error typing text: ${error}`);
            return { content: [{ type: "text", text: error.message }] }
        }
    }
);

server.tool("click",
    {
        x: z.number(),
        y: z.number()
    },
    async ({ x, y }) => {
        await page.mouse.click(x, y);
        sleep(1000);

        return {
            clicked_at: { x, y }
        };
    }
);

server.tool("scroll",
    {
        direction: z.string(),
        amount: z.number().optional().default(500)
    },
    async ({ direction, amount }) => {
        if (direction.toLowerCase() === "down") {
            await page.evaluate(`window.scrollBy(0, ${amount})`);
            await page.waitForTimeout(2000);
        } else if (direction.toLowerCase() === "up") {
            await page.evaluate(`window.scrollBy(0, ${amount})`);
            await page.waitForTimeout(2000);
        } else {

            return { content: [{ type: "text", text: "not scrolled" }] }
        }
        sleep(1000);

        return { content: [{ type: "text", text: "scrolled" }] }
    }
);

server.tool("writeFile",
    {
        filename: z.string(),
        content: z.string()
    },
    async ({ filename, content }) => {
        try {
            fs.writeFileSync(`artefacts/${sessionId}/${filename}`, content, 'utf8');
            return { content: [{ type: "text", text: filename }] }
        } catch (error) {
            printSystem(`Error writing file: ${error}`);
            return { content: [{ type: "text", text: error.message }] }
        }
    }
);

const browser = await chromium.launch({ headless: false });
const page = await browser.newPage();
await page.goto('https://example.com', { waitUntil: 'networkidle' });
console.log("Browser resources initialized");



const transport = new StdioServerTransport();
await server.connect(transport);