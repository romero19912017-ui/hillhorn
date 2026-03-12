"use strict";
const vscode = require("vscode");
const path = require("path");
const fs = require("fs");

let statusBarItem;
let intervalId;

function getDataDir() {
    const folders = vscode.workspace.workspaceFolders || [];
    for (const f of folders) {
        const d = path.join(f.uri.fsPath, "data");
        if (fs.existsSync(path.join(d, "hillhorn_activity.json"))) return d;
    }
    const def = path.join("c:", "Hillhorn", "data");
    return fs.existsSync(def) ? def : (folders[0] ? path.join(folders[0].uri.fsPath, "data") : null);
}

function getActivityPath() {
    const d = getDataDir();
    return d ? path.join(d, "hillhorn_activity.json") : null;
}

function getCallsPath() {
    const d = getDataDir();
    return d ? path.join(d, "hillhorn_calls.jsonl") : null;
}

function formatAgo(ts) {
    const sec = (Date.now() / 1000) - ts;
    if (sec < 60) return "just now";
    if (sec < 3600) return Math.floor(sec / 60) + "m ago";
    return Math.floor(sec / 3600) + "h ago";
}

function countCallsToday() {
    const cp = getCallsPath();
    if (!cp || !fs.existsSync(cp)) return 0;
    try {
        const today = new Date().toISOString().slice(0, 10);
        const lines = fs.readFileSync(cp, "utf8").trim().split("\n").filter(Boolean);
        let n = 0;
        for (const line of lines.slice(-500)) {
            const o = JSON.parse(line);
            const d = new Date(o.ts * 1000).toISOString().slice(0, 10);
            if (d === today) n++;
        }
        return n;
    } catch { return 0; }
}

function updateStatus() {
    if (!statusBarItem) return;
    const p = getActivityPath();
    const callsToday = countCallsToday();
    if (!p || !fs.existsSync(p)) {
        statusBarItem.text = "$(database) Hillhorn";
        statusBarItem.tooltip = "Hillhorn MCP - no activity yet" + (callsToday ? ` | Calls today: ${callsToday}` : "");
        return;
    }
    try {
        const data = JSON.parse(fs.readFileSync(p, "utf8"));
        const ago = formatAgo(data.last_use || 0);
        statusBarItem.text = `$(database) Hillhorn: ${data.last_tool || "?"} ${ago}`;
        statusBarItem.tooltip = `Last: ${data.last_tool || "?"} (${ago})` + (callsToday ? ` | Calls today: ${callsToday}` : "");
    } catch {
        statusBarItem.text = "$(database) Hillhorn";
        statusBarItem.tooltip = "Hillhorn MCP" + (callsToday ? ` | Calls today: ${callsToday}` : "");
    }
}

function activate(context) {
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = "hillhorn.status";
    context.subscriptions.push(statusBarItem);
    statusBarItem.text = "$(database) Hillhorn";
    statusBarItem.show();
    updateStatus();
    intervalId = setInterval(updateStatus, 5000);
    context.subscriptions.push({ dispose: () => intervalId && clearInterval(intervalId) });
    const p = getActivityPath();
    if (p && fs.existsSync(p)) {
        const watcher = vscode.workspace.createFileSystemWatcher("**/hillhorn_activity.json");
        watcher.onDidChange(updateStatus);
        context.subscriptions.push(watcher);
    }
    const callsWatcher = vscode.workspace.createFileSystemWatcher("**/hillhorn_calls.jsonl");
    if (callsWatcher) {
        callsWatcher.onDidChange(updateStatus);
        context.subscriptions.push(callsWatcher);
    }
    context.subscriptions.push(vscode.commands.registerCommand("hillhorn.status", () => {
        vscode.commands.executeCommand("workbench.action.tasks.runTask", "Hillhorn: Status");
    }));
    context.subscriptions.push(vscode.commands.registerCommand("hillhorn.showHistory", async () => {
        const cp = getCallsPath();
        const ch = vscode.window.createOutputChannel("Hillhorn History");
        ch.show();
        if (!cp || !fs.existsSync(cp)) {
            ch.appendLine("No call history yet.");
            return;
        }
        const lines = fs.readFileSync(cp, "utf8").trim().split("\n").filter(Boolean);
        const last = lines.slice(-20).reverse();
        ch.appendLine(`Last 20 calls (total: ${lines.length}):\n`);
        for (const line of last) {
            try {
                const o = JSON.parse(line);
                const dt = new Date(o.ts * 1000).toLocaleString();
                ch.appendLine(`  ${dt} | ${o.tool} | ${o.duration_ms || "?"} ms`);
            } catch { ch.appendLine("  (parse error)"); }
        }
    }));
}

function deactivate() {
    if (intervalId) clearInterval(intervalId);
    if (statusBarItem) statusBarItem.dispose();
}

module.exports = { activate, deactivate };
