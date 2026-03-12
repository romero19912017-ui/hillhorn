import * as vscode from "vscode";
import * as https from "https";
import * as http from "http";

async function callGateway(
  gatewayUrl: string,
  body: {
    agent_type: string;
    prompt: string;
    max_tokens: number;
    auto_agent: boolean;
    workspace_id?: string;
    workspace_path?: string;
  }
): Promise<{ ok: boolean; content?: string; error?: string }> {
  const url = new URL(gatewayUrl.replace(/\/$/, "") + "/v1/agent/query");
  const data = JSON.stringify(body);
  const opts: http.RequestOptions = {
    hostname: url.hostname,
    port: url.port || (url.protocol === "https:" ? 443 : 80),
    path: url.pathname,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Content-Length": Buffer.byteLength(data, "utf8"),
    },
  };

  return new Promise((resolve) => {
    const lib = url.protocol === "https:" ? https : http;
    const req = lib.request(opts, (res) => {
      let chunks = "";
      res.on("data", (c) => (chunks += c));
      res.on("end", () => {
        try {
          const parsed = JSON.parse(chunks || "{}");
          if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
            resolve({ ok: true, content: parsed.content || "" });
          } else {
            resolve({
              ok: false,
              error: parsed.detail || String(res.statusCode),
            });
          }
        } catch {
          resolve({ ok: false, error: chunks || String(res.statusCode) });
        }
      });
    });
    req.on("error", (e) => resolve({ ok: false, error: e.message }));
    req.write(data);
    req.end();
  });
}

function callGatewayStream(
  gatewayUrl: string,
  body: {
    agent_type: string;
    prompt: string;
    max_tokens: number;
    context?: Array<{ role: string; content: string }>;
  },
  onChunk: (chunk: string) => void,
  onDone: () => void,
  onError: (err: string) => void
): void {
  const url = new URL(gatewayUrl.replace(/\/$/, "") + "/v1/agent/query/stream");
  const data = JSON.stringify(body);
  const opts: http.RequestOptions = {
    hostname: url.hostname,
    port: url.port || (url.protocol === "https:" ? 443 : 80),
    path: url.pathname,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Content-Length": Buffer.byteLength(data, "utf8"),
    },
  };

  const lib = url.protocol === "https:" ? https : http;
  const req = lib.request(opts, (res) => {
    if (res.statusCode && (res.statusCode < 200 || res.statusCode >= 300)) {
      let buf = "";
      res.on("data", (c) => (buf += c.toString()));
      res.on("end", () => onError(buf || String(res.statusCode)));
      return;
    }
    let buffer = "";
    res.on("data", (chunk: Buffer) => {
      buffer += chunk.toString("utf8");
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const jsonStr = line.slice(6).trim();
          if (jsonStr === "[DONE]" || !jsonStr) continue;
          try {
            const obj = JSON.parse(jsonStr);
            if (obj.error) onError(obj.error);
            else if (obj.content) onChunk(obj.content);
            else if (obj.done) onDone();
          } catch {
            /* skip malformed */
          }
        }
      }
    });
    res.on("end", () => onDone());
  });
  req.on("error", (e) => onError(e.message));
  req.write(data);
  req.end();
}

interface CodeBlock {
  path?: string;
  lang: string;
  code: string;
}

function parseCodeBlocks(text: string): CodeBlock[] {
  const blocks: CodeBlock[] = [];
  const re = /```(\w*)(?::([^\n]+))?\n([\s\S]*?)```/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    const lang = m[1] || "";
    const pathLine = m[2]?.trim();
    let code = m[3].replace(/\n$/, "");
    let path: string | undefined;
    if (pathLine && !pathLine.includes(" ")) {
      path = pathLine;
    }
    blocks.push({ path, lang, code });
  }
  return blocks;
}

async function applyEdit(
  workspaceFolder: vscode.WorkspaceFolder | undefined,
  block: CodeBlock,
  currentUri: vscode.Uri | undefined,
  currentSelection: vscode.Selection | undefined
): Promise<boolean> {
  const edit = new vscode.WorkspaceEdit();
  let targetUri: vscode.Uri;
  let range: vscode.Range;

  if (block.path && workspaceFolder) {
    targetUri = vscode.Uri.joinPath(workspaceFolder.uri, block.path);
    let doc: vscode.TextDocument | null = null;
    try {
      doc = await vscode.workspace.openTextDocument(targetUri);
    } catch {
      // File may not exist yet
    }
    if (doc) {
      range = new vscode.Range(0, 0, doc.lineCount, 0);
      edit.replace(targetUri, range, block.code);
    } else {
      edit.createFile(targetUri, { overwrite: true });
      edit.insert(targetUri, new vscode.Position(0, 0), block.code);
    }
  } else if (currentUri) {
    targetUri = currentUri;
    const doc = await vscode.workspace.openTextDocument(currentUri);
    if (currentSelection && !currentSelection.isEmpty) {
      range = new vscode.Range(currentSelection.start, currentSelection.end);
    } else {
      const pos = currentSelection?.start ?? new vscode.Position(0, 0);
      range = new vscode.Range(pos, pos);
    }
    edit.replace(targetUri, range, block.code);
  } else {
    const picked = await vscode.window.showSaveDialog({
      defaultUri: workspaceFolder?.uri,
      filters: { "All files": ["*"] },
    });
    if (!picked) return false;
    edit.createFile(picked, { overwrite: true });
    edit.insert(picked, new vscode.Position(0, 0), block.code);
  }

  return vscode.workspace.applyEdit(edit);
}

function getWebviewContent(): string {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: var(--vscode-font-family); padding: 12px; margin: 0; font-size: 13px; }
    #messages { height: 320px; overflow-y: auto; margin-bottom: 12px;
      border: 1px solid var(--vscode-panel-border); padding: 8px; }
    .msg { margin: 8px 0; padding: 8px; border-radius: 4px; }
    .user { background: var(--vscode-input-background); }
    .assistant { background: var(--vscode-editor-inactiveSelectionBackground); }
    .error { color: var(--vscode-errorForeground); }
    .code-block { margin: 8px 0; border: 1px solid var(--vscode-panel-border); border-radius: 4px; overflow: hidden; }
    .code-header { display: flex; justify-content: space-between; align-items: center; padding: 4px 8px; background: var(--vscode-editor-background); font-size: 11px; }
    .code-body { padding: 8px; overflow-x: auto; white-space: pre-wrap; font-family: var(--vscode-editor-font-family); font-size: 12px; }
    .apply-btn { padding: 2px 8px; font-size: 11px; cursor: pointer; background: var(--vscode-button-background); color: var(--vscode-button-foreground); border: none; border-radius: 3px; }
    .apply-btn:hover { opacity: 0.9; }
    #input { width: 100%; margin-bottom: 8px; resize: vertical; min-height: 60px; }
    button#send { padding: 6px 12px; }
    pre { white-space: pre-wrap; font-size: 12px; margin: 0; }
  </style>
</head>
<body>
  <div id="messages"></div>
  <textarea id="input" rows="3" placeholder="Ask Hillhorn... (select code to edit)"></textarea>
  <button id="send">Send</button>
  <script>
    const vscode = acquireVsCodeApi();
    const messages = document.getElementById('messages');
    const input = document.getElementById('input');
    const sendBtn = document.getElementById('send');

    function escapeHtml(s) {
      const d = document.createElement('div');
      d.textContent = s;
      return d.innerHTML;
    }

    function renderContent(text, codeBlocks) {
      if (!codeBlocks || codeBlocks.length === 0) {
        return '<pre>' + escapeHtml(text) + '</pre>';
      }
      let idx = 0;
      return text.replace(/\`\`\`(\w*)(?::([^\n]+))?\n([\s\S]*?)\`\`\`/g, (_, lang, path, code) => {
        const block = codeBlocks[idx++];
        if (!block) return _;
        const pathLabel = (block.path || path || 'current file').trim();
        return '<div class="code-block"><div class="code-header"><span>' + escapeHtml(pathLabel) + '</span><button class="apply-btn" data-idx="' + (idx-1) + '">Apply</button></div><div class="code-body">' + escapeHtml(block.code) + '</div></div>';
      });
    }

    function addMsg(role, text, isError, codeBlocks) {
      const div = document.createElement('div');
      div.className = 'msg ' + role + (isError ? ' error' : '');
      div.innerHTML = isError ? '<pre>' + escapeHtml(text) + '</pre>' : renderContent(text, codeBlocks || []);
      div.querySelectorAll('.apply-btn').forEach(btn => {
        btn.onclick = () => vscode.postMessage({ type: 'apply', idx: parseInt(btn.dataset.idx) });
      });
      messages.appendChild(div);
      messages.scrollTop = messages.scrollHeight;
    }

    function appendStreamChunk(div, chunk) {
      const pre = div.querySelector('pre') || (() => {
        const p = document.createElement('pre');
        div.appendChild(p);
        return p;
      })();
      pre.textContent += chunk;
      messages.scrollTop = messages.scrollHeight;
    }

    function finalizeStream(div, content, codeBlocks) {
      div.innerHTML = renderContent(content, codeBlocks || []);
      div.querySelectorAll('.apply-btn').forEach(btn => {
        btn.onclick = () => vscode.postMessage({ type: 'apply', idx: parseInt(btn.dataset.idx) });
      });
      messages.scrollTop = messages.scrollHeight;
    }

    sendBtn.onclick = () => {
      const text = input.value.trim();
      if (!text) return;
      addMsg('user', text, false, null);
      input.value = '';
      sendBtn.disabled = true;
      vscode.postMessage({ type: 'send', text: text });
    };

    let lastCodeBlocks = [];
    let streamingDiv = null;
    window.addEventListener('message', e => {
      const msg = e.data;
      if (msg.type === 'streamStart') {
        streamingDiv = document.createElement('div');
        streamingDiv.className = 'msg assistant';
        streamingDiv.innerHTML = '<pre></pre>';
        messages.appendChild(streamingDiv);
        messages.scrollTop = messages.scrollHeight;
      } else if (msg.type === 'streamChunk' && streamingDiv) {
        appendStreamChunk(streamingDiv, msg.chunk || '');
      } else if (msg.type === 'streamEnd' && streamingDiv) {
        lastCodeBlocks = msg.codeBlocks || [];
        finalizeStream(streamingDiv, msg.content || '', lastCodeBlocks);
        streamingDiv = null;
        sendBtn.disabled = false;
      } else if (msg.type === 'response') {
        if (msg.error) {
          if (streamingDiv) {
            streamingDiv.className = 'msg assistant error';
            streamingDiv.innerHTML = '<pre>' + escapeHtml('Error: ' + msg.error) + '</pre>';
            streamingDiv = null;
          } else {
            addMsg('assistant', 'Error: ' + msg.error, true, null);
          }
        } else {
          if (streamingDiv) streamingDiv = null;
          lastCodeBlocks = msg.codeBlocks || [];
          addMsg('assistant', msg.content || '', false, lastCodeBlocks);
        }
        sendBtn.disabled = false;
      } else if (msg.type === 'applyResult') {
        if (msg.success) addMsg('assistant', 'Applied.', false, null);
        else addMsg('assistant', 'Apply failed: ' + (msg.error || 'unknown'), true, null);
      }
    });
  </script>
</body>
</html>`;
}

class HillhornChatViewProvider implements vscode.WebviewViewProvider {
  private _view?: vscode.WebviewView;
  private _gatewayUrl = "http://localhost:8001";
  private _workspaceId = "default";
  private _agentType = "chat";
  private _autoAgent = false;
  private _lastCodeBlocks: CodeBlock[] = [];
  private _lastEditorUri?: vscode.Uri;
  private _lastSelection?: vscode.Selection;

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this._view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    this._loadConfig();
    this.updateHtml();
    webviewView.webview.onDidReceiveMessage((msg) => this._onMessage(msg));
  }

  private _loadConfig(): void {
    const config = vscode.workspace.getConfiguration("hillhorn");
    this._gatewayUrl = config.get<string>("gatewayUrl", "http://localhost:8001");
    this._workspaceId = config.get<string>("workspaceId", "default");
    this._agentType = config.get<string>("agentType", "chat");
    this._autoAgent = config.get<boolean>("autoAgent", false);
  }

  private async _onMessage(msg: { type: string; text?: string; idx?: number }): Promise<void> {
    if (msg.type === "send" && msg.text) {
      await this._handleSend(msg.text);
    } else if (msg.type === "apply" && typeof msg.idx === "number") {
      await this._handleApply(msg.idx);
    }
  }

  private _captureEditorState(): void {
    const editor = vscode.window.activeTextEditor;
    this._lastEditorUri = editor?.document.uri;
    this._lastSelection = editor?.selection;
  }

  private async _handleSend(text: string): Promise<void> {
    if (!this._view) return;
    this._loadConfig();
    this._captureEditorState();

    const folders = vscode.workspace.workspaceFolders;
    const workspacePath = folders?.[0]?.uri.fsPath;
    const editor = vscode.window.activeTextEditor;
    const selected = editor?.document.getText(editor.selection)?.trim();
    let prompt = text;
    if (selected) {
      const rel = workspacePath && editor
        ? vscode.workspace.asRelativePath(editor.document.uri)
        : editor?.document.fileName;
      prompt = `[Context: file ${rel || ""}, selection]\n\`\`\`\n${selected}\n\`\`\`\n\n[Task]\n${prompt}`;
    } else if (workspacePath) {
      prompt = `[Workspace: ${workspacePath}]\n\n${prompt}`;
    }

    const agentType = this._autoAgent ? "chat" : this._agentType;
    const useStreaming = ["chat", "documenter"].includes(agentType);

    if (useStreaming) {
      this._view.webview.postMessage({ type: "streamStart" });
      let fullContent = "";
      callGatewayStream(
        this._gatewayUrl,
        { agent_type: agentType, prompt, max_tokens: 4096 },
        (chunk) => {
          fullContent += chunk;
          this._view?.webview.postMessage({ type: "streamChunk", chunk });
        },
        () => {
          this._lastCodeBlocks = parseCodeBlocks(fullContent);
          this._view?.webview.postMessage({
            type: "streamEnd",
            content: fullContent,
            codeBlocks: this._lastCodeBlocks,
          });
        },
        (err) => {
          this._view?.webview.postMessage({ type: "response", error: err });
        }
      );
      return;
    }

    const result = await callGateway(this._gatewayUrl, {
      agent_type: agentType,
      prompt,
      max_tokens: 4096,
      auto_agent: this._autoAgent,
      workspace_id: this._workspaceId || undefined,
      workspace_path: workspacePath,
    });

    this._lastCodeBlocks = result.content ? parseCodeBlocks(result.content) : [];
    this._view.webview.postMessage({
      type: "response",
      content: result.content,
      error: result.error,
      codeBlocks: this._lastCodeBlocks,
    });
  }

  private async _handleApply(idx: number): Promise<void> {
    const block = this._lastCodeBlocks[idx];
    if (!block || !this._view) return;

    const folders = vscode.workspace.workspaceFolders;
    const applied = await applyEdit(
      folders?.[0],
      block,
      this._lastEditorUri,
      this._lastSelection
    );
    this._view.webview.postMessage({
      type: "applyResult",
      success: applied,
      error: applied ? undefined : "Could not apply edit",
    });
  }

  private updateHtml(): void {
    if (!this._view) return;
    this._view.webview.html = getWebviewContent();
  }
}

export function activate(context: vscode.ExtensionContext): void {
  const provider = new HillhornChatViewProvider();
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("hillhornChat", provider)
  );
  context.subscriptions.push(
    vscode.commands.registerCommand("hillhorn.openChat", () => {
      vscode.commands.executeCommand("workbench.view.extension.hillhorn");
    })
  );
  context.subscriptions.push(
    vscode.commands.registerCommand("hillhorn.applyCodeBlock", async (block: CodeBlock) => {
      const folders = vscode.workspace.workspaceFolders;
      const editor = vscode.window.activeTextEditor;
      await applyEdit(folders?.[0], block, editor?.document.uri, editor?.selection);
    })
  );
}

export function deactivate(): void {}
