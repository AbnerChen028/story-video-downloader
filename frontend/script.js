// 绘本视频搜索工具 - 前端脚本
var API_BASE = '';
var STATUS_POLL_INTERVAL = 2000;

// DOM
var authPage = document.getElementById('authPage');
var mainApp = document.getElementById('mainApp');
var authKeyInput = document.getElementById('authKeyInput');
var authBtn = document.getElementById('authBtn');
var authError = document.getElementById('authError');
var themeToggle = document.getElementById('themeToggle');
var linkInput = document.getElementById('linkInput');
var linkBtn = document.getElementById('linkBtn');
var detectBadge = document.getElementById('detectBadge');
var detectHint = document.getElementById('detectHint');
var loadingEl = document.getElementById('loading');
var resultsEl = document.getElementById('results');
var taskListEl = document.getElementById('taskList');
var downloadStatusEl = document.getElementById('downloadStatus');
var storyListEl = document.getElementById('storyList');
var pendingLinksEl = document.getElementById('pendingLinks');
var linkListEl = document.getElementById('linkList');
var historyPaginationEl = document.getElementById('historyPagination');
var activePolling = {};
var historyPage = 1;
var historyPageSize = 12;

async function loadServiceBrand() {
    try {
        var response = await fetch(API_BASE + '/api/health', { cache: 'no-store' });
        var info = await response.json();
        var isGeneral = info.app_mode === 'general';
        var title = info.app_title || (isGeneral ? '通用下载器' : '绘本视频下载');
        document.title = title;
        document.getElementById('authTitle').textContent = title;
        document.getElementById('appTitle').textContent = isGeneral ? '通用下载器' : '儿童绘本';
        document.getElementById('brandMark').textContent = isGeneral ? '通' : '绘';
        document.getElementById('appSubtitle').textContent = info.app_description || '';
        document.getElementById('panelCopy').textContent = isGeneral
            ? '支持小红书、抖音、快手、YouTube 等平台，整段分享文案也可以直接粘贴。'
            : '支持小红书、抖音、快手和 YouTube。整段分享文案也可以直接粘贴。';
    } catch (e) {}
}

var PLATFORM_META = {
    youtube: { icon: '▶️', label: 'YouTube', color: '#ff0000' },
    x: { icon: '𝕏', label: 'X', color: '#111111' },
    xiaohongshu: { icon: '📕', label: '小红书', color: '#ff2442' },
    douyin: { icon: '🎵', label: '抖音', color: '#000000' },
    kuaishou: { icon: '📹', label: '快手', color: '#ff6f00' },
};

function extractUrl(text) {
    var m = text.match(/https?:\/\/[^\s<>"'“”‘’（）【】《》]+/i);
    return m ? m[0].replace(/[，。！？；：、)）】》]+$/g, '').trim() : '';
}
var PLATFORM_DETECT = [
    { domains: ['xiaohongshu.com', 'xhslink.com', 'xhslink.cn'], platform: 'xiaohongshu' },
    { domains: ['douyin.com', 'iesdouyin.com'], platform: 'douyin' },
    { domains: ['kuaishou.com', 'gifshow.com'], platform: 'kuaishou' },
    { domains: ['youtube.com', 'youtu.be'], platform: 'youtube' },
    { domains: ['x.com', 'twitter.com'], platform: 'x' },
];
function detectPlatform(url) {
    var lower = url.toLowerCase();
    for (var i = 0; i < PLATFORM_DETECT.length; i++) {
        var rule = PLATFORM_DETECT[i];
        for (var j = 0; j < rule.domains.length; j++) {
            if (lower.indexOf(rule.domains[j]) !== -1) return rule.platform;
        }
    }
    return null;
}

// ===== 主题 =====
var currentTheme = localStorage.getItem('theme') || 'light';
function applyTheme(t) { currentTheme = t; document.documentElement.setAttribute('data-theme', t); localStorage.setItem('theme', t); themeToggle.textContent = t === 'dark' ? '☀️' : '🌙'; }
applyTheme(currentTheme);
themeToggle.addEventListener('click', function () { applyTheme(currentTheme === 'dark' ? 'light' : 'dark'); });

// ===== 密钥验证 =====
async function checkAuth() {
    try {
        var resp = await fetch(API_BASE + '/api/auth/check', { credentials: 'include' });
        if (resp.ok) { authPage.style.display = 'none'; mainApp.style.display = 'block'; initApp(); return; }
    } catch (e) {}
    authPage.style.display = 'flex';
    mainApp.style.display = 'none';
    authKeyInput.focus();
}

async function doAuth() {
    var key = authKeyInput.value.trim();
    if (!key) { authError.textContent = '请输入密钥'; return; }
    authError.textContent = '';
    authBtn.disabled = true;
    authBtn.textContent = '验证中...';
    try {
        var resp = await fetch(API_BASE + '/api/auth/verify', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: key }), credentials: 'include',
        });
        if (resp.ok) { authPage.style.display = 'none'; mainApp.style.display = 'block'; initApp(); }
        else { var d = await resp.json(); authError.textContent = d.detail || '密钥错误'; }
    } catch (e) { authError.textContent = '网络错误: ' + e.message; }
    finally { authBtn.disabled = false; authBtn.textContent = '确 认'; }
}

authBtn.addEventListener('click', doAuth);
authKeyInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') doAuth(); });

// ===== 初始化 =====
function initApp() {
    loadDownloadedList();
    updateBadge();
}

function updateBadge() {
    var url = extractUrl(linkInput.value);
    if (!url) { detectBadge.textContent = '🔍 自动识别'; detectBadge.style.background = '#7f8c8d'; detectHint.textContent = '粘贴链接后自动识别平台'; return; }
    var p = detectPlatform(url);
    if (p && PLATFORM_META[p]) { var m = PLATFORM_META[p]; detectBadge.textContent = m.icon + ' ' + m.label; detectBadge.style.background = m.color; detectHint.textContent = '已识别为 ' + m.label; }
    else { detectBadge.textContent = '❓ 未识别'; detectBadge.style.background = '#95a5a6'; detectHint.textContent = '未识别平台，仍可尝试下载'; }
}

// ===== 链接 =====
var pendingLinks = [];

function inferStoryName(title, rawText) {
    var known = ['好饿的毛毛虫', '爱吃水果的牛', '爱吃水果的鳄鱼', '鳄鱼怕怕 牙医怕怕', '鸭子骑车记', '乘着火车去旅行', '挖红薯巴士', '蜗牛出租车', '骑自行车的鳄鱼'];
    var source = (title || '') + ' ' + (rawText || '');
    var quoted = source.match(/《([^》]{1,40})》/);
    if (quoted) return quoted[1].trim();
    for (var i = 0; i < known.length; i++) if (source.indexOf(known[i]) !== -1) return known[i];
    var cleaned = (title || '').replace(/\.(mp4|mov|webm)$/i, '').replace(/[|｜].*$/, '').trim();
    cleaned = cleaned.replace(/^(儿童绘本|绘本故事|故事动画)[\s:：-]*/i, '').replace(/[【】\[\]]/g, '').trim();
    if (cleaned && cleaned.length <= 40 && !/^(分享|视频|作品|推荐|这本绘本)/.test(cleaned)) return cleaned;
    return '';
}

async function addLink() {
    var raw = linkInput.value;
    var url = extractUrl(raw);
    resultsEl.innerHTML = '';
    if (!url) { resultsEl.innerHTML = '<div class="inline-error">没有找到可识别的视频链接，请把完整分享文案粘贴进来。</div>'; return; }
    if (url.indexOf('http://') !== 0 && url.indexOf('https://') !== 0) { resultsEl.innerHTML = '<div class="inline-error">链接格式不正确。</div>'; return; }
    var detected = detectPlatform(url);
    var rt = '', rthumb = '', rweb = url, rp = detected || 'unknown';
    linkBtn.disabled = true;
    loadingEl.style.display = 'flex';
    detectHint.textContent = '正在解析分享链接，请稍候…';
    try {
        var r = await fetch(API_BASE + '/api/search/link', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: url, platform: detected || '', story_name: '', raw_text: raw }), credentials: 'include' });
        var d = await r.json();
        if (!r.ok || d.error) throw new Error(d.error || '链接解析失败');
        if (d.title) { rt = d.title; rthumb = d.thumbnail; rweb = d.webpage_url || url; rp = d.platform || rp; }
        var inferred = d.story_name || inferStoryName(rt, raw);
    } catch (e) {
        resultsEl.innerHTML = '<div class="inline-error">解析失败：' + esc(e.message || '网络错误') + '</div>';
        return;
    } finally {
        linkBtn.disabled = false;
        loadingEl.style.display = 'none';
    }

    var def = inferred || inferStoryName(rt, raw) || '';
    if (!def) def = rt || '请填写作品名';
    var name = prompt('绘本名称（可修改）：', def);
    if (!name || !name.trim()) { resultsEl.innerHTML = '<div class="inline-error">未填写作品名，已取消下载。</div>'; return; }

    var entry = { id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6), url: url, platform: rp, storyName: name, title: rt, thumbnail: rthumb, webpageUrl: rweb };
    pendingLinks.push(entry);
    renderLinks();
    linkInput.value = ''; updateBadge();
    renderLinks();
    dlExternal(entry);
}

linkBtn.addEventListener('click', addLink);
linkInput.addEventListener('keydown', function (e) { if ((e.metaKey || e.ctrlKey || e.shiftKey) && e.key === 'Enter') addLink(); });
linkInput.addEventListener('input', updateBadge);
function renderLinks() {
    if (!pendingLinks.length) { pendingLinksEl.style.display = 'none'; return; }
    pendingLinksEl.style.display = 'block';
    var html = '';
    pendingLinks.forEach(function (l) {
        var m = PLATFORM_META[l.platform] || { icon: '🔗', label: l.platform || '链接' };
        html += '<div class="pending-link-item"><span class="link-platform-tag" style="background:' + m.color + '">' + m.icon + ' ' + m.label + '</span><span class="link-url" title="' + esc(l.url) + '">' + esc(l.title || l.storyName) + '</span><span class="link-story">📁 ' + esc(l.storyName) + '</span><span class="link-status" id="ls-' + l.id + '">⏳ 提交下载...</span></div>';
    });
    linkListEl.innerHTML = html;
}
async function dlExternal(entry) {
    try {
        var r = await fetch(API_BASE + '/api/download', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ video_url: entry.webpageUrl || entry.url, story_name: entry.storyName, platform: entry.platform, title: entry.title || entry.storyName, thumbnail: entry.thumbnail || '' }), credentials: 'include' });
        var d = await r.json();
        if (d.task_id) { showTask(d.task_id, entry.storyName); poll(d.task_id); var el = document.getElementById('ls-' + entry.id); if (el) el.textContent = '✅ 已提交 (' + d.task_id.slice(0, 8) + ')'; }
    } catch (e) { var el = document.getElementById('ls-' + entry.id); if (el) el.textContent = '❌ ' + e.message; }
}

// ===== 下载 =====
async function dl(url, name, platform, title, thumb) {
    try {
        var r = await fetch(API_BASE + '/api/download', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ video_url: url, story_name: name, platform: platform, title: title, thumbnail: thumb }), credentials: 'include' });
        var d = await r.json();
        if (d.task_id) { showTask(d.task_id, title || name); poll(d.task_id); }
    } catch (e) { alert('下载失败: ' + e.message); }
}
function showTask(id, title) {
    downloadStatusEl.style.display = 'block';
    var item = document.createElement('div'); item.className = 'task-item'; item.id = 't-' + id;
    item.innerHTML = '<span class="task-title">' + esc(title) + '</span><div class="task-bar"><div class="progress" style="width:0%"></div></div><span class="task-status" id="s-' + id + '">排队中</span>';
    taskListEl.prepend(item);
}
function poll(id) {
    if (activePolling[id]) return;
    activePolling[id] = true;
    var fn = async function () {
        if (!activePolling[id]) return;
        try {
            var r = await fetch(API_BASE + '/api/tasks/' + id, { credentials: 'include' });
            var d = await r.json();
            var bar = document.querySelector('#t-' + id + ' .progress');
            var el = document.getElementById('s-' + id);
            if (bar) bar.style.width = (d.progress || 0) + '%';
            var m = { 'PENDING': '排队中', 'PROGRESS': '下载中 ' + (d.progress || 0) + '%', 'SUCCESS': '✅ 完成', 'FAILURE': '❌ 失败', 'RETRY': '🔄 重试中' };
            if (el) el.textContent = m[d.status] || d.status;
            if (d.status === 'PENDING' || d.status === 'PROGRESS') { setTimeout(fn, STATUS_POLL_INTERVAL); }
            else { delete activePolling[id]; if (d.status === 'SUCCESS') loadDownloadedList(); }
        } catch (e) { setTimeout(fn, STATUS_POLL_INTERVAL * 2); }
    };
    setTimeout(fn, 1000);
}
async function loadDownloadedList() {
    try {
        var r = await fetch(API_BASE + '/api/download/list?page=' + historyPage + '&page_size=' + historyPageSize, { credentials: 'include' });
        var d = await r.json();
        var stories = d.stories || [];
        if (!stories.length) { storyListEl.innerHTML = '<div class="no-results" style="grid-column:1/-1">暂无下载记录</div>'; historyPaginationEl.innerHTML = ''; return; }
        var html = '';
        stories.forEach(function (s) {
            html += '<div class="story-card"><img class="cover" src="' + (s.cover || '') + '" onerror="this.style.display=\'none\'"><div class="story-info"><div class="story-name">' + esc(s.name) + '</div><div class="story-meta">第 ' + (s.episode || '?') + ' 集' + (s.updated_at ? ' · ' + new Date(s.updated_at).toLocaleDateString() : '') + '</div><div class="history-actions"><button class="history-preview" data-file="' + esc(s.filename || '') + '" data-title="' + esc(s.name) + '">预览</button><button class="history-delete" data-file="' + esc(s.filename || '') + '" data-title="' + esc(s.name) + '">删除</button></div></div></div>';
        });
        storyListEl.innerHTML = html;
        storyListEl.querySelectorAll('.history-preview').forEach(function (button) {
            button.addEventListener('click', function () { previewHistory(button.dataset.file, button.dataset.title); });
        });
        storyListEl.querySelectorAll('.history-delete').forEach(function (button) {
            button.addEventListener('click', function () { deleteHistory(button.dataset.file, button.dataset.title); });
        });
        renderHistoryPagination(d.page || historyPage, d.total_pages || 1);
    } catch (e) {}
}
function renderHistoryPagination(page, totalPages) {
    if (totalPages <= 1) { historyPaginationEl.innerHTML = ''; return; }
    var html = '<button class="page-btn" data-page="' + (page - 1) + '"' + (page <= 1 ? ' disabled' : '') + '>上一页</button>';
    html += '<span class="page-info">第 ' + page + ' / ' + totalPages + ' 页</span>';
    html += '<button class="page-btn" data-page="' + (page + 1) + '"' + (page >= totalPages ? ' disabled' : '') + '>下一页</button>';
    historyPaginationEl.innerHTML = html;
    historyPaginationEl.querySelectorAll('.page-btn:not([disabled])').forEach(function (button) {
        button.addEventListener('click', function () {
            historyPage = Number(button.dataset.page);
            loadDownloadedList();
            document.getElementById('downloadedList').scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });
}
function previewHistory(filename, title) {
    var existing = document.querySelector('.preview-overlay');
    if (existing) existing.remove();
    var overlay = document.createElement('div');
    overlay.className = 'preview-overlay';
    overlay.innerHTML = '<div class="preview-modal"><div class="preview-header"><span class="preview-title">' + esc(title) + '</span><button class="preview-close" aria-label="关闭">×</button></div><video class="preview-video" controls autoplay playsinline src="/api/download/file?filename=' + encodeURIComponent(filename) + '"></video></div>';
    document.body.appendChild(overlay);
    overlay.querySelector('.preview-close').addEventListener('click', function () { overlay.remove(); });
    overlay.addEventListener('click', function (event) { if (event.target === overlay) overlay.remove(); });
}
async function deleteHistory(filename, title) {
    if (!filename || !confirm('确定删除“' + title + '”吗？视频文件也会被删除。')) return;
    try {
        var response = await fetch('/api/download/file?filename=' + encodeURIComponent(filename), { method: 'DELETE', credentials: 'include' });
        var data = await response.json();
        if (!response.ok) throw new Error(data.detail || '删除失败');
        if (historyPage > 1) historyPage -= 1;
        loadDownloadedList();
    } catch (error) {
        resultsEl.innerHTML = '<div class="inline-error">删除失败：' + esc(error.message) + '</div>';
    }
}
function esc(text) { if (!text) return ''; var d = document.createElement('div'); d.textContent = text; return d.innerHTML; }

// ===== 启动 =====
loadServiceBrand();
checkAuth();
