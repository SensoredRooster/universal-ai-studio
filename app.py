"""
Universal AI Studio - local AI chat using Ollama
"""
import re

import requests
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)
OLLAMA_URL = "http://localhost:11434"

HTML = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Universal AI Studio</title>
    <style>
        * { box-sizing: border-box; }
        body {
            margin: 0;
            font-family: system-ui, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        header { text-align: center; color: white; margin-bottom: 24px; }
        h1 { margin-bottom: 8px; }
        .chat-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        @media (max-width: 768px) {
            .chat-grid { grid-template-columns: 1fr; }
        }
        .chat-box {
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
            min-height: 500px;
            overflow: hidden;
        }
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px 20px;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            background: #f7f7f7;
            padding: 15px;
        }
        .message {
            margin-bottom: 12px;
            display: flex;
        }
        .message.user { justify-content: flex-end; }
        .message-content {
            max-width: 86%;
            padding: 10px 14px;
            border-radius: 10px;
            line-height: 1.6;
            word-break: break-word;
            white-space: normal;
        }
        .message.user .message-content {
            background: #667eea;
            color: white;
        }
        .message.ai .message-content {
            background: #e7e7e7;
            color: #222;
        }
        .list-item {
            display: block;
            margin: 5px 0;
        }
        .chat-input {
            display: flex;
            gap: 8px;
            padding: 12px;
            border-top: 1px solid #ddd;
        }
        input {
            flex: 1;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            cursor: pointer;
        }
        strong { font-weight: 700; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Universal AI Studio</h1>
            <p>Local AI • Side-by-side chat</p>
        </header>

        <div class="chat-grid">
            <div class="chat-box">
                <div class="chat-header">
                    <h2>The Architect</h2>
                </div>
                <div id="qwen-box" class="chat-messages"></div>
                <form id="qwen-form" class="chat-input">
                    <input id="qwen-input" type="text" placeholder="Ask anything...">
                    <button type="submit">Send</button>
                </form>
            </div>

            <div class="chat-box">
                <div class="chat-header">
                    <h2>The Inspector</h2>
                </div>
                <div id="deepseek-box" class="chat-messages"></div>
                <form id="deepseek-form" class="chat-input">
                    <input id="deepseek-input" type="text" placeholder="Ask anything...">
                    <button type="submit">Send</button>
                </form>
            </div>
        </div>
    </div>

    <script>
        function escapeHtml(text) {
            return String(text)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/\"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        function formatResponse(text) {
            if (!text) return '';

            let formatted = escapeHtml(text)
                .replace(/\r\n/g, '\n')
                .replace(/(^|\n)(\d+\.\s+.+?)(?=\n\d+\.\s+|\n|$)/g, '$1<div class="list-item">$2</div>')
                .replace(/(^|\n)([-*•]\s+.+?)(?=\n[-*•]\s+|\n|$)/g, '$1<div class="list-item">$2</div>')
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/__(.+?)__/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');

            return formatted;
        }

        function sendMessage(boxId, modelId, formEvent) {
            formEvent.preventDefault();
            const input = document.getElementById(boxId + '-input');
            const box = document.getElementById(boxId + '-box');
            if (!input || !box) return;

            const message = input.value.trim();
            if (!message) return;

            const userMsg = document.createElement('div');
            userMsg.className = 'message user';
            userMsg.innerHTML = '<div class="message-content">' + escapeHtml(message) + '</div>';
            box.appendChild(userMsg);

            input.value = '';
            input.disabled = true;

            fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model: modelId, prompt: message })
            })
            .then(async response => {
                const data = await response.json();
                if (!response.ok) throw new Error(data.response || 'Request failed');
                return data;
            })
            .then(data => {
                const aiMsg = document.createElement('div');
                aiMsg.className = 'message ai';
                aiMsg.innerHTML = '<div class="message-content">' + formatResponse(data.response) + '</div>';
                box.appendChild(aiMsg);
                box.scrollTop = box.scrollHeight;
                input.disabled = false;
                input.focus();
            })
            .catch(err => {
                const aiMsg = document.createElement('div');
                aiMsg.className = 'message ai';
                aiMsg.innerHTML = '<div class="message-content">Error: ' + escapeHtml(err.message) + '</div>';
                box.appendChild(aiMsg);
                input.disabled = false;
            });
        }

        document.getElementById('qwen-form').addEventListener('submit', function(e) {
            sendMessage('qwen', 'qwen2.5-coder:7b-instruct', e);
        });
        document.getElementById('deepseek-form').addEventListener('submit', function(e) {
            sendMessage('deepseek', 'deepseek-coder:6.7b-instruct', e);
        });

    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/chat', methods=['POST'])
def chat():
    payload = request.get_json(silent=True) or {}
    model = payload.get('model')
    prompt = payload.get('prompt')

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "system": "You are a helpful assistant. Use clear formatting with each numbered point on a new line.",
                "stream": False,
            },
            timeout=120,
        )
        if response.status_code == 200:
            text = response.json().get('response', 'No response')
            text = text.replace('\r\n', '\n')
            text = re.sub(r'(?<!\n)(\d{1,2}\.\s+)', r'\n\n\1', text)
            text = re.sub(r'(?<!\n)([-*•]\s+)', r'\n\n\1', text)
            return jsonify({"response": text})
        return jsonify({"response": f"Error: {response.status_code}"})
    except requests.exceptions.ConnectionError:
        return jsonify({"response": "Error: Ollama not running. Run 'ollama serve' in another terminal."})
    except Exception as exc:
        return jsonify({"response": f"Error: {exc}"})


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
