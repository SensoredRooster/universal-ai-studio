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
        .container { max-width: 1440px; margin: 0 auto; }
        header { text-align: center; color: white; margin-bottom: 14px; }
        h1 { margin-bottom: 4px; font-size: clamp(1.6rem, 2vw, 2.4rem); }
        .workspace-grid {
            display: grid;
            grid-template-columns: 1.2fr 1.2fr 1.05fr;
            gap: 16px;
            align-items: stretch;
            min-height: auto;
        }
        .panel {
            background: rgba(15, 18, 28, 0.9);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 16px;
            box-shadow: 0 14px 36px rgba(0,0,0,0.28);
            padding: 14px;
            color: #e5eefb;
            display: flex;
            flex-direction: column;
            min-height: 100%;
        }
        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.18);
        }
        .panel-header h2,
        .panel-header h3 {
            margin: 0;
            font-size: 1.12rem;
        }
        .ghost-chip {
            background: rgba(59, 130, 246, 0.16);
            border: 1px solid rgba(96, 165, 250, 0.35);
            color: #d7ebff;
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 11px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .view {
            display: block;
            width: 100%;
            flex: 1;
        }
        .chat-box {
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
            display: flex;
            flex-direction: column;
            min-height: 100%;
            overflow: hidden;
        }
        .chat-header {
            background: linear-gradient(135deg, #1f2937 0%, #3b82f6 100%);
            color: white;
            padding: 14px 18px;
        }
        .chat-header h2 {
            margin: 0;
            font-size: 1.05rem;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            background: #f3f5f9;
            padding: 15px;
            min-height: 320px;
            max-height: 420px;
        }
        .message { margin-bottom: 12px; display: flex; }
        .message.user { justify-content: flex-end; }
        .message-content {
            max-width: 86%;
            padding: 10px 14px;
            border-radius: 10px;
            line-height: 1.5;
            word-break: break-word;
            white-space: normal;
        }
        .message.user .message-content {
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            color: white;
        }
        .message.ai .message-content {
            background: #e7ebf5;
            color: #202533;
        }
        .list-item { display: block; margin: 5px 0; }
        .chat-input {
            display: flex;
            gap: 8px;
            padding: 12px;
            border-top: 1px solid #dfe5ef;
            background: #ffffff;
        }
        input, textarea, select {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #d2d9e5;
            border-radius: 10px;
            background: rgba(17, 24, 39, 0.03);
            color: #111827;
            font-family: inherit;
            font-size: 14px;
        }
        textarea { resize: vertical; min-height: 92px; }
        button {
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 16px;
            cursor: pointer;
            font-weight: 700;
            transition: filter 0.2s ease;
        }
        button:hover { filter: brightness(1.05); }
        button:disabled { opacity: 0.6; cursor: not-allowed; }
        strong { font-weight: 700; }

        .media-panel {
            display: flex;
            flex-direction: column;
            gap: 18px;
        }
        .media-stack {
            display: flex;
            flex-direction: column;
            gap: 18px;
            width: 100%;
        }
        .media-card {
            background: rgba(17, 24, 39, 0.42);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 16px;
            padding: 16px;
            width: 100%;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.15);
        }
        .image-studio {
            background: transparent;
            border: none;
            border-radius: 0;
            padding: 0;
            width: 100%;
        }
        .image-controls { display: flex; flex-direction: column; gap: 12px; }
        .control-row {
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }
        .control-row label {
            font-weight: 600;
            min-width: 90px;
            color: #dde8ff;
        }
        .inline-numeric {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
        }
        .num-field {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        .num-field label {
            min-width: 0;
        }
        .control-row input[type="number"] { flex: 1; }
        .generated-image {
            width: 100%;
            max-width: 1024px;
            border-radius: 10px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
            margin-top: 12px;
        }
        .status { color: #dbeafe; font-style: italic; margin-top: 10px; }
        .error { color: #fca5a5; }
        .download-link {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-top: 14px;
            padding: 10px 16px;
            border-radius: 8px;
            background: #3b82f6;
            color: white;
            font-weight: 700;
            text-decoration: none;
        }
        .social-result-card {
            margin-top: 18px;
            padding: 16px;
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 12px;
            color: #e2e8f0;
        }
        .social-result-card h3 { margin: 0 0 6px; }
        .social-result-card p { margin: 0 0 12px; color: #dfeafc; }
        .trend-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin: 10px 0 0;
            padding: 0;
            list-style: none;
        }
        .trend-item {
            border: 1px solid rgba(148, 163, 184, 0.2);
            background: rgba(15, 23, 42, 0.7);
            color: #edf6ff;
            border-radius: 12px;
            padding: 10px 12px;
            line-height: 1.35;
        }
        .trend-item strong {
            display: block;
            color: #ffffff;
            margin-bottom: 4px;
            font-size: 0.96rem;
        }
        .trend-item small {
            color: #bfd8ff;
            display: block;
            opacity: 0.9;
            font-size: 0.72rem;
        }
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
            width: 100%;
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
            justify-content: center;
            gap: 8px;
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 16px;
            cursor: pointer;
            font-weight: 700;
            font-size: 13px;
            white-space: nowrap;
        }
        .file-picker-summary {
            color: #dfeafc;
            font-size: 13px;
            font-style: italic;
            line-height: 1.3;
            overflow-wrap: anywhere;
        }
        .file-picker-summary.has-files { color: #ffffff; font-style: normal; font-weight: 600; }
        .social-progress {
            display: none;
            margin-top: 16px;
            padding: 12px 14px;
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 10px;
        }
        .social-progress-track {
            height: 12px;
            overflow: hidden;
            background: rgba(148, 163, 184, 0.18);
            border-radius: 999px;
        }
        .social-progress-fill {
            width: 0%;
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #22d3ee);
            border-radius: inherit;
            transition: width 0.35s ease;
        }
        .social-progress-meta {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            margin-top: 7px;
            color: #dfeafc;
            font-size: 13px;
        }
        @media (max-width: 1100px) {
            .workspace-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Universal AI Studio</h1>
            <p>Local AI • Chat + Image Generation</p>
        </header>

        <div class="workspace-grid">
            <section class="panel">
                <div class="panel-header">
                    <h2>The Architect</h2>
                    <span class="ghost-chip">Agent</span>
                </div>
                <div id="view-chat" class="view">
                    <div class="chat-box">
                        <div id="qwen-box" class="chat-messages"></div>
                        <form id="qwen-form" class="chat-input">
                            <input id="qwen-input" type="text" placeholder="Ask anything...">
                            <button type="submit">Send</button>
                        </form>
                    </div>
                </div>
            </section>

            <section class="panel">
                <div class="panel-header">
                    <h2>The Inspector</h2>
                    <span class="ghost-chip">Agent</span>
                </div>
                <div id="view-inspector" class="view">
                    <div class="chat-box">
                        <div id="deepseek-box" class="chat-messages"></div>
                        <form id="deepseek-form" class="chat-input">
                            <input id="deepseek-input" type="text" placeholder="Ask anything...">
                            <button type="submit">Send</button>
                        </form>
                    </div>
                </div>
            </section>

            <aside class="panel media-panel">
                <div class="panel-header">
                    <h2>Media Generation Suite</h2>
                    <span class="ghost-chip">Unified</span>
                </div>

                <div class="media-stack">
                    <div id="view-image" class="media-card">
                        <div class="image-studio">
                            <div class="image-controls">
                                <div class="control-row" style="flex-direction: column; align-items: stretch;">
                                    <label for="image-prompt">Prompt</label>
                                    <textarea id="image-prompt" placeholder="A futuristic city at sunset, digital art..."></textarea>
                                </div>
                                <div class="control-row" style="align-items: center;">
                                    <label for="image-input">Reference</label>
                                    <div class="file-picker" style="flex: 1;">
                                        <label for="image-input" class="file-picker-label">📷 Import Image</label>
                                        <input id="image-input" type="file" accept=".png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff" onchange="updateImageImportSummary()">
                                        <span id="image-input-summary" class="file-picker-summary">No reference image loaded</span>
                                    </div>
                                </div>
                                <div class="inline-numeric">
                                    <div class="num-field">
                                        <label for="image-width">Width</label>
                                        <input id="image-width" type="number" value="1024" min="512" max="2048" step="64">
                                    </div>
                                    <div class="num-field">
                                        <label for="image-height">Height</label>
                                        <input id="image-height" type="number" value="1024" min="512" max="2048" step="64">
                                    </div>
                                    <div class="num-field">
                                        <label for="image-steps">Steps</label>
                                        <input id="image-steps" type="number" value="25" min="10" max="100">
                                    </div>
                                </div>
                                <div class="control-row">
                                    <label for="image-negative">Negative</label>
                                    <input id="image-negative" type="text" placeholder="blurry, low quality, watermark" value="blurry, low quality, watermark, text">
                                </div>
                                <button id="image-generate" onclick="generateImage()">Generate Image</button>
                            </div>
                            <div id="image-status" class="status"></div>
                            <div id="image-result"></div>
                        </div>
                    </div>

                    <div id="view-social" class="media-card">
                        <div class="image-studio">
                            <h3>🚀 Social Agent</h3>
                            <div class="image-controls">
                                <div class="control-row" style="flex-direction: column; align-items: stretch;">
                                    <label for="social-topics">Trend Topics</label>
                                    <input id="social-topics" type="text" value="AI, technology, gaming" placeholder="AI, science, motivation...">
                                </div>
                                <div class="control-row" style="flex-wrap: nowrap;">
                                    <button type="button" onclick="fetchSocialTrends()" style="flex: 1;">🔍 Pull Top Gaming Trends</button>
                                    <button type="button" onclick="generateSocialVideo(false)" style="flex: 1;">🎬 Generate Draft</button>
                                    <button type="button" onclick="generateSocialVideo(true)" style="flex: 1;">📤 Generate & Post</button>
                                </div>
                                <div class="control-row" style="flex-direction: column; align-items: stretch; border-top: 1px solid rgba(148,163,184,0.18); padding-top: 12px; margin-top: 4px;">
                                    <label for="social-clips">Import Your Own Clips</label>
                                    <div class="file-picker">
                                        <label for="social-clips" class="file-picker-label">📂 Choose Clips</label>
                                        <input id="social-clips" type="file" accept=".mp4,.mov,.webm,.mkv,.avi,.m4v" multiple onchange="updateClipSummary()">
                                        <span id="social-clips-summary" class="file-picker-summary">No clips selected</span>
                                    </div>
                                    <input id="social-clip-title" type="text" placeholder="Caption text (optional)">
                                    <button type="button" onclick="composeSocialClips()">🎬 Render My Clips</button>
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
            </aside>
        </div>
    </div>

    <script>
        function escapeHtml(text) {
            return String(text)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        function cleanTrendText(value) {
            return String(value || '')
                .replace(/<[^>]+>/g, ' ')
                .replace(/https?:\/\/[^\s]+/gi, '')
                .replace(/\s+/g, ' ')
                .replace(/\s*[-|–]\s*[^-]+$/g, '')
                .trim();
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

        function updateImageImportSummary() {
            const fileInput = document.getElementById('image-input');
            const summary = document.getElementById('image-input-summary');
            if (!fileInput || !summary) return;
            const file = fileInput.files && fileInput.files[0];
            summary.textContent = file ? file.name : 'No reference image loaded';
            summary.classList.toggle('has-files', Boolean(file));
        }

        async function generateImage() {
            const prompt = document.getElementById('image-prompt').value.trim();
            const negative = document.getElementById('image-negative').value.trim();
            const width = parseInt(document.getElementById('image-width').value, 10);
            const height = parseInt(document.getElementById('image-height').value, 10);
            const steps = parseInt(document.getElementById('image-steps').value, 10);
            const btn = document.getElementById('image-generate');
            const status = document.getElementById('image-status');
            const result = document.getElementById('image-result');
            const imageInput = document.getElementById('image-input');

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
                const formData = new FormData();
                formData.append('prompt', prompt);
                formData.append('negative', negative);
                formData.append('width', String(width));
                formData.append('height', String(height));
                formData.append('steps', String(steps));
                if (imageInput && imageInput.files && imageInput.files[0]) {
                    formData.append('image', imageInput.files[0]);
                }

                const res = await fetch('/generate-image', { method: 'POST', body: formData });
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
            if (!topics.length) {
                status.textContent = 'Enter at least one topic to fetch trends.';
                status.className = 'status error';
                result.innerHTML = '';
                return;
            }
            status.className = 'status';
            status.textContent = 'Fetching trends...';
            result.innerHTML = '';
            try {
                const qs = topics.map(t => 'topic=' + encodeURIComponent(t)).join('&');
                const res = await fetch('/social/trends?' + qs);
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Trend fetch failed');
                const trends = Array.isArray(data.trends) ? data.trends : [];
                status.textContent = trends.length ? 'Found ' + trends.length + ' trends.' : 'No trends were returned.';
                if (!trends.length) {
                    result.innerHTML = '<div class="social-result-card"><h3>No trends found</h3><p>Try a different topic or refresh.</p></div>';
                    return;
                }
                result.innerHTML = `
                    <div class="trend-list">
                        ${trends.slice(0, 8).map(trend => {
                            const title = cleanTrendText(trend.title || 'Untitled trend');
                            const source = cleanTrendText(trend.source || trend.publisher || 'News');
                            const summary = cleanTrendText(trend.summary || '');
                            return `
                                <div class="trend-item">
                                    <strong>${escapeHtml(title || 'Untitled trend')}</strong>
                                    ${summary ? '<small>' + escapeHtml(summary) + '</small>' : ''}
                                    ${source ? '<small>' + escapeHtml(source) + '</small>' : ''}
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;
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
                const maxAttempts = 1800; // up to ~60 minutes for slower local WAN rendering
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


def _build_text_to_image_workflow(checkpoint, prompt, negative, width, height, steps):
    """Return the standard text-to-image workflow used by the app."""
    workflow = json.loads(json.dumps(BASE_WORKFLOW))
    wf_str = json.dumps(workflow)
    wf_str = wf_str.replace("{{CHECKPOINT}}", checkpoint)
    wf_str = wf_str.replace("{{POSITIVE}}", prompt)
    wf_str = wf_str.replace("{{NEGATIVE}}", negative)
    workflow = json.loads(wf_str)
    workflow["3"]["inputs"]["seed"] = random.randint(1, 1_000_000_000)
    workflow["3"]["inputs"]["steps"] = steps
    workflow["5"]["inputs"]["width"] = width
    workflow["5"]["inputs"]["height"] = height
    return workflow


def _build_image_to_image_workflow(checkpoint, prompt, negative, width, height, steps, image_name):
    """Return a simple image-guided workflow that uses a saved input image."""
    return {
        "1": {
            "inputs": {"image": image_name, "type": "input", "subfolder": ""},
            "class_type": "LoadImage",
        },
        "2": {
            "inputs": {"ckpt_name": checkpoint},
            "class_type": "CheckpointLoaderSimple",
        },
        "3": {
            "inputs": {"text": prompt, "clip": ["2", 1]},
            "class_type": "CLIPTextEncode",
        },
        "4": {
            "inputs": {"text": negative, "clip": ["2", 1]},
            "class_type": "CLIPTextEncode",
        },
        "5": {
            "inputs": {"pixels": ["1", 0], "vae": ["2", 2]},
            "class_type": "VAEEncode",
        },
        "6": {
            "inputs": {
                "seed": random.randint(1, 1_000_000_000),
                "steps": steps,
                "cfg": 7.0,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["2", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0],
            },
            "class_type": "KSampler",
        },
        "7": {
            "inputs": {"samples": ["6", 0], "vae": ["2", 2]},
            "class_type": "VAEDecode",
        },
        "8": {
            "inputs": {"filename_prefix": "uas", "images": ["7", 0]},
            "class_type": "SaveImage",
        },
    }


@app.route("/generate-image", methods=["POST"])
def generate_image():
    form_data = request.form.to_dict(flat=True)
    payload = request.get_json(silent=True) or {}

    if request.files and request.files.get("image"):
        uploaded = request.files["image"]
        if uploaded.filename:
            input_dir = os.path.join(os.path.dirname(__file__), "ComfyUI", "input")
            os.makedirs(input_dir, exist_ok=True)
            original_name = os.path.basename(uploaded.filename)
            image_name = f"uas_ref_{uuid.uuid4()}{os.path.splitext(original_name)[1].lower()}"
            image_path = os.path.join(input_dir, image_name)
            uploaded.save(image_path)
        else:
            image_name = None
    else:
        image_name = None

    prompt = (form_data.get("prompt") or payload.get("prompt") or "").strip()
    negative = (form_data.get("negative") or payload.get("negative") or "").strip()
    width = int(form_data.get("width") or payload.get("width") or 1024)
    height = int(form_data.get("height") or payload.get("height") or 1024)
    steps = int(form_data.get("steps") or payload.get("steps") or 25)

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
    if image_name:
        workflow = _build_image_to_image_workflow(checkpoint, prompt, negative, width, height, steps, image_name)
    else:
        workflow = _build_text_to_image_workflow(checkpoint, prompt, negative, width, height, steps)

    try:
        prompt_id = _queue_prompt(workflow)
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Cannot connect to ComfyUI. Make sure it is running (run.bat starts it)."}), 503
    except Exception as exc:
        return jsonify({"error": f"Failed to queue prompt: {exc}"}), 500

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
