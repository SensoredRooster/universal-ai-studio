"""
Universal AI Studio - local AI chat and image generation using Ollama and ComfyUI
"""
import json
import os
import random
import re
import time
import uuid

import requests
from flask import Flask, jsonify, render_template_string, request, send_file

from agents.social.api import social_bp

app = Flask(__name__)
app.register_blueprint(social_bp)
OLLAMA_URL = "http://localhost:11434"
COMFYUI_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "workspace", "images")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Default ComfyUI workflow for SDXL text-to-image.
# The checkpoint filename is replaced at runtime with whatever the user has.
# ---------------------------------------------------------------------------
BASE_WORKFLOW = {
    "3": {
        "inputs": {
            "seed": 0,
            "steps": 25,
            "cfg": 7.0,
            "sampler_name": "euler_ancestral",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0],
        },
        "class_type": "KSampler",
    },
    "4": {
        "inputs": {"ckpt_name": "{{CHECKPOINT}}"},
        "class_type": "CheckpointLoaderSimple",
    },
    "5": {
        "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        "class_type": "EmptyLatentImage",
    },
    "6": {
        "inputs": {"text": "{{POSITIVE}}", "clip": ["4", 1]},
        "class_type": "CLIPTextEncode",
    },
    "7": {
        "inputs": {"text": "{{NEGATIVE}}", "clip": ["4", 1]},
        "class_type": "CLIPTextEncode",
    },
    "8": {
        "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        "class_type": "VAEDecode",
    },
    "9": {
        "inputs": {"filename_prefix": "uas", "images": ["8", 0]},
        "class_type": "SaveImage",
    },
}

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
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        header { text-align: center; color: white; margin-bottom: 18px; }
        h1 { margin-bottom: 6px; }
        .tabs {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            background: rgba(255,255,255,0.2);
            color: white;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 999px;
            padding: 8px 22px;
            cursor: pointer;
            font-weight: 600;
        }
        .tab.active {
            background: white;
            color: #764ba2;
        }
        .view { display: none; }
        .view.active { display: block; }

        /* Chat styles */
        .chat-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        @media (max-width: 900px) {
            .chat-grid { grid-template-columns: 1fr; }
        }
        .chat-box {
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
            min-height: 520px;
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
        .message { margin-bottom: 12px; display: flex; }
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
        .list-item { display: block; margin: 5px 0; }
        .chat-input {
            display: flex;
            gap: 8px;
            padding: 12px;
            border-top: 1px solid #ddd;
        }
        input, textarea, select {
            flex: 1;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-family: inherit;
            font-size: 14px;
        }
        textarea { resize: vertical; min-height: 80px; }
        button {
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            cursor: pointer;
            font-weight: 600;
        }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        strong { font-weight: 700; }

        /* Image Studio styles */
        .image-studio {
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            padding: 20px;
            max-width: 900px;
            margin: 0 auto;
        }
        .image-controls { display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px; }
        .control-row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
        .control-row label { font-weight: 600; min-width: 90px; }
        .control-row input[type="number"] { flex: 0 0 90px; }
        .generated-image {
            width: 100%;
            max-width: 1024px;
            border-radius: 10px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
            margin-top: 12px;
        }
        .status { color: #555; font-style: italic; margin-top: 10px; }
        .error { color: #c00; }
        .download-link {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-top: 14px;
            padding: 10px 16px;
            border-radius: 8px;
            background: #667eea;
            color: white;
            font-weight: 700;
            text-decoration: none;
        }
        .social-result-card {
            margin-top: 18px;
            padding: 16px;
            background: #f8f9ff;
            border: 1px solid #e1e5ff;
            border-radius: 12px;
        }
        .social-result-card h3 { margin: 0 0 6px; }
        .social-result-card p { margin: 0 0 12px; color: #555; }
        .social-preview {
            display: block;
            width: min(100%, 320px);
            max-height: 560px;
            margin: 0 auto;
            background: #111;
            border-radius: 10px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.18);
        }
        .social-result-actions { display: flex; justify-content: center; }
        .file-picker {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }
        .file-picker input[type="file"] {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            border: 0;
        }
        .file-picker-label {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            white-space: nowrap;
        }
        .file-picker-label:hover { background: #5a6fd6; }
        .file-picker-summary {
            color: #555;
            font-size: 14px;
            font-style: italic;
        }
        .file-picker-summary.has-files { color: #333; font-style: normal; font-weight: 600; }
        .social-progress {
            display: none;
            margin-top: 16px;
            padding: 12px 14px;
            background: #f5f6ff;
            border: 1px solid #dfe3ff;
            border-radius: 10px;
        }
        .social-progress-track {
            height: 12px;
            overflow: hidden;
            background: #e2e5ef;
            border-radius: 999px;
        }
        .social-progress-fill {
            width: 0%;
            height: 100%;
            background: linear-gradient(90deg, #667eea, #49b6ff);
            border-radius: inherit;
            transition: width 0.35s ease;
        }
        .social-progress-meta {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            margin-top: 7px;
            color: #555;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Universal AI Studio</h1>
            <p>Local AI • Chat + Image Generation</p>
        </header>

        <div class="tabs">
            <button id="tab-chat" class="tab active" onclick="switchTab('chat')">💬 Chat</button>
            <button id="tab-image" class="tab" onclick="switchTab('image')">🎨 Image Studio</button>
            <button id="tab-social" class="tab" onclick="switchTab('social')">🚀 Social Agent</button>
        </div>

        <div id="view-chat" class="view active">
            <div class="chat-grid">
                <div class="chat-box">
                    <div class="chat-header"><h2>The Architect</h2></div>
                    <div id="qwen-box" class="chat-messages"></div>
                    <form id="qwen-form" class="chat-input">
                        <input id="qwen-input" type="text" placeholder="Ask anything...">
                        <button type="submit">Send</button>
                    </form>
                </div>

                <div class="chat-box">
                    <div class="chat-header"><h2>The Inspector</h2></div>
                    <div id="deepseek-box" class="chat-messages"></div>
                    <form id="deepseek-form" class="chat-input">
                        <input id="deepseek-input" type="text" placeholder="Ask anything...">
                        <button type="submit">Send</button>
                    </form>
                </div>
            </div>
        </div>

        <div id="view-image" class="view">
            <div class="image-studio">
                <h2>🎨 Image Studio</h2>
                <p>Generate images locally with ComfyUI + SDXL.</p>

                <div class="image-controls">
                    <div class="control-row" style="flex-direction: column; align-items: stretch;">
                        <label for="image-prompt">Prompt</label>
                        <textarea id="image-prompt" placeholder="A futuristic city at sunset, digital art..."></textarea>
                    </div>
                    <div class="control-row">
                        <label for="image-negative">Negative</label>
                        <input id="image-negative" type="text" placeholder="blurry, low quality, watermark" value="blurry, low quality, watermark, text">
                    </div>
                    <div class="control-row">
                        <label for="image-width">Width</label>
                        <input id="image-width" type="number" value="1024" min="512" max="2048" step="64">
                        <label for="image-height">Height</label>
                        <input id="image-height" type="number" value="1024" min="512" max="2048" step="64">
                        <label for="image-steps">Steps</label>
                        <input id="image-steps" type="number" value="25" min="10" max="100">
                    </div>
                    <button id="image-generate" onclick="generateImage()">Generate Image</button>
                </div>

                <div id="image-status" class="status"></div>
                <div id="image-result"></div>
            </div>
        </div>

        <div id="view-social" class="view">
            <div class="image-studio">
                <h2>🚀 Social Agent</h2>
                <p>Auto-generate YouTube Shorts from trending topics using local AI.</p>

                <div class="image-controls">
                    <div class="control-row" style="flex-direction: column; align-items: stretch;">
                        <label for="social-topics">Trend Topics (comma separated)</label>
                        <input id="social-topics" type="text" value="AI, technology, gaming" placeholder="AI, science, motivation...">
                    </div>
                    <div class="control-row">
                        <button onclick="fetchSocialTrends()">🔍 Find Trends</button>
                        <button onclick="generateSocialVideo(false)">🎬 Generate Draft</button>
                        <button onclick="generateSocialVideo(true)">📤 Generate & Post</button>
                    </div>
                    <div class="control-row" style="flex-direction: column; align-items: stretch; border-top: 1px solid #e4e4ee; padding-top: 14px; margin-top: 4px;">
                        <label for="social-clips">Import Your Own Clips</label>
                        <div class="file-picker">
                            <label for="social-clips" class="file-picker-label">📂 Choose Clips</label>
                            <input id="social-clips" type="file" accept=".mp4,.mov,.webm,.mkv,.avi,.m4v" multiple onchange="updateClipSummary()">
                            <span id="social-clips-summary" class="file-picker-summary">No clips selected</span>
                        </div>
                        <input id="social-clip-title" type="text" placeholder="Caption text (optional)">
                        <button onclick="composeSocialClips()">🎬 Render My Clips</button>
                    </div>
                </div>

                <div id="social-status" class="status"></div>
                <div id="social-progress" class="social-progress" aria-live="polite">
                    <div class="social-progress-track"><div id="social-progress-fill" class="social-progress-fill"></div></div>
                    <div class="social-progress-meta"><span id="social-progress-message">Queued</span><strong id="social-progress-percent">0%</strong></div>
                </div>
                <div id="social-result"></div>
            </div>
        </div>
    </div>

    <script>
        function switchTab(name) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.getElementById('tab-' + name).classList.add('active');
            document.getElementById('view-' + name).classList.add('active');
        }

        function escapeHtml(text) {
            return String(text)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
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

        async function generateImage() {
            const prompt = document.getElementById('image-prompt').value.trim();
            const negative = document.getElementById('image-negative').value.trim();
            const width = parseInt(document.getElementById('image-width').value, 10);
            const height = parseInt(document.getElementById('image-height').value, 10);
            const steps = parseInt(document.getElementById('image-steps').value, 10);
            const btn = document.getElementById('image-generate');
            const status = document.getElementById('image-status');
            const result = document.getElementById('image-result');

            if (!prompt) {
                status.textContent = 'Please enter a prompt.';
                status.className = 'status error';
                return;
            }

            btn.disabled = true;
            status.className = 'status';
            status.textContent = 'Submitting job to ComfyUI...';
            result.innerHTML = '';

            try {
                const res = await fetch('/generate-image', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt, negative, width, height, steps })
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Image generation failed');

                status.textContent = 'Generating image... this may take 30s to several minutes.';

                let done = false;
                let attempts = 0;
                const maxAttempts = 300;
                while (!done && attempts < maxAttempts) {
                    await new Promise(r => setTimeout(r, 2000));
                    const poll = await fetch('/image-status/' + data.job_id);
                    const pollData = await poll.json();
                    if (pollData.status === 'ready') {
                        done = true;
                        status.textContent = 'Done!';
                        result.innerHTML = '<img class="generated-image" src="/images/' + data.job_id + '.png" alt="Generated image">' +
                            '<br><a class="download-link" href="/images/' + data.job_id + '.png" download>Download PNG</a>';
                    } else if (pollData.status === 'error') {
                        throw new Error(pollData.error || 'Generation error');
                    } else {
                        status.textContent = 'Generating image... (' + pollData.status + ')';
                    }
                    attempts++;
                }
                if (!done) throw new Error('Timed out waiting for image.');
            } catch (err) {
                status.textContent = 'Error: ' + err.message;
                status.className = 'status error';
            } finally {
                btn.disabled = false;
            }
        }

        async function fetchSocialTrends() {
            const topics = document.getElementById('social-topics').value.split(',').map(t => t.trim()).filter(Boolean);
            const status = document.getElementById('social-status');
            const result = document.getElementById('social-result');
            status.className = 'status';
            status.textContent = 'Fetching trends...';
            result.innerHTML = '';
            try {
                const qs = topics.map(t => 'topic=' + encodeURIComponent(t)).join('&');
                const res = await fetch('/social/trends?' + qs);
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Trend fetch failed');
                status.textContent = 'Found ' + data.trends.length + ' trends.';
                result.innerHTML = '<ul>' + data.trends.map(t => '<li>' + escapeHtml(t.title) + '</li>').join('') + '</ul>';
            } catch (err) {
                status.textContent = 'Error: ' + err.message;
                status.className = 'status error';
            }
        }

        function updateClipSummary() {
            const fileInput = document.getElementById('social-clips');
            const summary = document.getElementById('social-clips-summary');
            const count = fileInput.files.length;
            if (!count) {
                summary.textContent = 'No clips selected';
                summary.classList.remove('has-files');
                return;
            }
            const names = Array.from(fileInput.files).map(f => f.name).join(', ');
            summary.textContent = count === 1 ? names : count + ' clips selected: ' + names;
            summary.classList.add('has-files');
        }

        async function composeSocialClips() {
            const fileInput = document.getElementById('social-clips');
            const status = document.getElementById('social-status');
            const result = document.getElementById('social-result');
            const progressBox = document.getElementById('social-progress');
            const progressFill = document.getElementById('social-progress-fill');
            const progressMessage = document.getElementById('social-progress-message');
            const progressPercent = document.getElementById('social-progress-percent');
            const buttons = document.querySelectorAll('#view-social button');
            const updateProgress = (value, message) => {
                const percent = Math.max(0, Math.min(100, Number(value) || 0));
                progressBox.style.display = 'block';
                progressFill.style.width = percent + '%';
                progressPercent.textContent = percent + '%';
                progressMessage.textContent = message || 'Working...';
            };
            if (!fileInput.files.length) {
                status.textContent = 'Pick at least one video clip first.';
                status.className = 'status error';
                return;
            }
            buttons.forEach(button => button.disabled = true);
            status.className = 'status';
            status.textContent = 'Uploading ' + fileInput.files.length + ' clip(s)...';
            result.innerHTML = '';
            updateProgress(0, 'Uploading');
            try {
                const form = new FormData();
                for (const file of fileInput.files) form.append('clips', file);
                form.append('title', document.getElementById('social-clip-title').value.trim());
                const res = await fetch('/social/compose', { method: 'POST', body: form });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Upload failed');

                const jobId = data.job_id;
                status.textContent = 'Rendering your clips...';
                let done = false;
                let attempts = 0;
                while (!done && attempts < 300) {
                    await new Promise(r => setTimeout(r, 2000));
                    const poll = await fetch('/social/job-status/' + jobId);
                    const pollData = await poll.json();
                    updateProgress(pollData.progress, pollData.message || pollData.status);
                    if (pollData.status === 'ready') {
                        done = true;
                        updateProgress(100, 'Complete');
                        status.textContent = 'Rendered successfully.';
                        const videoName = pollData.result.video_path.split('\\').pop().split('/').pop();
                        const videoUrl = '/social/videos/' + encodeURIComponent(videoName);
                        result.innerHTML = `
                            <div class="social-result-card">
                                <h3>Clips rendered</h3>
                                <p>Your clips were captioned and stitched into a Short.</p>
                                <video class="social-preview" controls playsinline preload="metadata" src="${videoUrl}"></video>
                                <div class="social-result-actions">
                                    <a class="download-link" href="${videoUrl}" download>Download MP4</a>
                                </div>
                            </div>`;
                    } else if (pollData.status === 'error') {
                        throw new Error(pollData.error || 'Render error');
                    }
                    attempts++;
                }
                if (!done) throw new Error('Timed out waiting for render.');
            } catch (err) {
                status.textContent = 'Error: ' + err.message;
                status.className = 'status error';
                progressMessage.textContent = 'Failed';
            } finally {
                buttons.forEach(button => button.disabled = false);
            }
        }

        async function generateSocialVideo(postNow) {
            const topics = document.getElementById('social-topics').value.split(',').map(t => t.trim()).filter(Boolean);
            const status = document.getElementById('social-status');
            const result = document.getElementById('social-result');
            const progressBox = document.getElementById('social-progress');
            const progressFill = document.getElementById('social-progress-fill');
            const progressMessage = document.getElementById('social-progress-message');
            const progressPercent = document.getElementById('social-progress-percent');
            const buttons = document.querySelectorAll('#view-social button');
            const updateProgress = (value, message) => {
                const percent = Math.max(0, Math.min(100, Number(value) || 0));
                progressBox.style.display = 'block';
                progressFill.style.width = percent + '%';
                progressPercent.textContent = percent + '%';
                progressMessage.textContent = message || 'Working...';
            };
            buttons.forEach(button => button.disabled = true);
            status.className = 'status';
            status.textContent = postNow ? 'Queueing generation and YouTube Shorts post...' : 'Queueing video draft generation...';
            result.innerHTML = '';
            updateProgress(0, 'Queued');
            try {
                const endpoint = postNow ? '/social/post' : '/social/generate';
                const res = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topics })
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Video generation failed');

                const jobId = data.job_id;
                status.textContent = 'Job ' + jobId.slice(0, 8) + ' running...';

                let done = false;
                let attempts = 0;
                const maxAttempts = 180; // up to ~6 minutes
                while (!done && attempts < maxAttempts) {
                    await new Promise(r => setTimeout(r, 2000));
                    const poll = await fetch('/social/job-status/' + jobId);
                    const pollData = await poll.json();
                    updateProgress(pollData.progress, pollData.message || pollData.status);
                    if (pollData.status === 'ready') {
                        done = true;
                        updateProgress(100, 'Complete');
                        const generated = !postNow;
                        status.textContent = generated ? 'Generated successfully.' : 'Posted successfully.';
                        const videoName = pollData.result.video_path ? pollData.result.video_path.split('\\').pop().split('/').pop() : '';
                        const videoUrl = videoName ? '/social/videos/' + encodeURIComponent(videoName) : '';
                        result.innerHTML = videoUrl ? `
                            <div class="social-result-card">
                                <h3>${generated ? 'Draft generated' : 'Short posted'}</h3>
                                <p>${generated ? 'Preview your Short before sharing it.' : 'Your Short was uploaded successfully.'}</p>
                                <video class="social-preview" controls playsinline preload="metadata" src="${videoUrl}"></video>
                                <div class="social-result-actions">
                                    <a class="download-link" href="${videoUrl}" download>Download MP4</a>
                                </div>
                            </div>` : '<div class="social-result-card"><h3>Generation complete</h3></div>';
                    } else if (pollData.status === 'error') {
                        throw new Error(pollData.error || 'Generation error');
                    } else {
                        status.textContent = 'Job ' + jobId.slice(0, 8) + ': ' + pollData.status;
                    }
                    attempts++;
                }
                if (!done) throw new Error('Timed out waiting for social agent job.');
            } catch (err) {
                status.textContent = 'Error: ' + err.message;
                status.className = 'status error';
                progressMessage.textContent = 'Failed';
            } finally {
                buttons.forEach(button => button.disabled = false);
            }
        }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    model = payload.get("model")
    prompt = payload.get("prompt")

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
            text = response.json().get("response", "No response")
            text = text.replace("\r\n", "\n")
            text = re.sub(r"(?<!\n)(\d{1,2}\.\s+)", r"\n\n\1", text)
            text = re.sub(r"(?<!\n)([-*•]\s+)", r"\n\n\1", text)
            return jsonify({"response": text})
        return jsonify({"response": f"Error: {response.status_code}"})
    except requests.exceptions.ConnectionError:
        return jsonify({"response": "Error: Ollama not running. Run 'ollama serve' in another terminal."})
    except Exception as exc:
        return jsonify({"response": f"Error: {exc}"})


def _find_checkpoint():
    """Return the first available .safetensors/.ckpt checkpoint in ComfyUI."""
    comfy_ckpt = os.path.join(os.path.dirname(__file__), "ComfyUI", "models", "checkpoints")
    if not os.path.isdir(comfy_ckpt):
        return None
    for name in os.listdir(comfy_ckpt):
        lower = name.lower()
        if lower.endswith(".safetensors") or lower.endswith(".ckpt") or lower.endswith(".pt"):
            return name
    return None


def _queue_prompt(workflow):
    """Submit a prompt to ComfyUI and return the prompt_id."""
    data = {"prompt": workflow, "client_id": str(uuid.uuid4())}
    resp = requests.post(f"{COMFYUI_URL}/prompt", json=data, timeout=30)
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def _get_history(prompt_id, timeout=600):
    """Poll ComfyUI history until the job completes or times out."""
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=30)
        resp.raise_for_status()
        history = resp.json()
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(1)
    raise TimeoutError("ComfyUI did not finish the image in time.")


def _fetch_image(filename, subfolder, folder_type):
    """Download a generated image from ComfyUI's view endpoint."""
    params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    resp = requests.get(f"{COMFYUI_URL}/view", params=params, timeout=60)
    resp.raise_for_status()
    return resp.content


@app.route("/generate-image", methods=["POST"])
def generate_image():
    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt", "").strip()
    negative = payload.get("negative", "").strip()
    width = int(payload.get("width", 1024))
    height = int(payload.get("height", 1024))
    steps = int(payload.get("steps", 25))

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    checkpoint = _find_checkpoint()
    if not checkpoint:
        return jsonify({
            "error": "No checkpoint found in ComfyUI/models/checkpoints. "
                     "The installer is downloading SDXL in the background. "
                     "Wait for the install window to finish, then try again."
        }), 503

    job_id = str(uuid.uuid4())
    workflow = json.loads(json.dumps(BASE_WORKFLOW))

    # Inject prompt values
    wf_str = json.dumps(workflow)
    wf_str = wf_str.replace("{{CHECKPOINT}}", checkpoint)
    wf_str = wf_str.replace("{{POSITIVE}}", prompt)
    wf_str = wf_str.replace("{{NEGATIVE}}", negative)
    workflow = json.loads(wf_str)

    # Apply user settings
    workflow["3"]["inputs"]["seed"] = random.randint(1, 1_000_000_000)
    workflow["3"]["inputs"]["steps"] = steps
    workflow["5"]["inputs"]["width"] = width
    workflow["5"]["inputs"]["height"] = height

    try:
        prompt_id = _queue_prompt(workflow)
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Cannot connect to ComfyUI. Make sure it is running (run.bat starts it)."}), 503
    except Exception as exc:
        return jsonify({"error": f"Failed to queue prompt: {exc}"}), 500

    # Start a background thread to wait for completion and save the file
    def _process():
        try:
            history = _get_history(prompt_id)
            outputs = history.get("outputs", {})
            for node_id, node_output in outputs.items():
                images = node_output.get("images", [])
                if images:
                    img_info = images[0]
                    image_data = _fetch_image(img_info["filename"], img_info.get("subfolder", ""), img_info.get("type", "output"))
                    out_path = os.path.join(OUTPUT_DIR, f"{job_id}.png")
                    with open(out_path, "wb") as f:
                        f.write(image_data)
                    _set_job_status(job_id, "ready")
                    return
            _set_job_status(job_id, "error", "No image output found.")
        except Exception as exc:
            _set_job_status(job_id, "error", str(exc))

    _set_job_status(job_id, "pending")
    import threading
    threading.Thread(target=_process, daemon=True).start()

    return jsonify({"job_id": job_id})


_jobs = {}


def _set_job_status(job_id, status, error=None):
    _jobs[job_id] = {"status": status, "error": error}


@app.route("/image-status/<job_id>")
def image_status(job_id):
    return jsonify(_jobs.get(job_id, {"status": "unknown"}))


@app.route("/images/<filename>")
def serve_image(filename):
    safe = os.path.basename(filename)
    return send_file(os.path.join(OUTPUT_DIR, safe))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
