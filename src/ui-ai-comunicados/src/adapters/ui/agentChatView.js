import { executeSubmitQuery } from '../../usecases/SubmitQuery.js';

/**
 * Generate a new RFC-4122 v4 UUID for each chat session.
 * Using crypto.randomUUID() when available (all modern browsers),
 * with a manual fallback for older environments.
 * @returns {string}
 */
function generateSessionId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback: manual UUID v4
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Convert a subset of markdown to HTML for chat bubble rendering.
 * Handles: **bold**, *italic*, `code`, bullet lists, numbered lists,
 * ### headings, and line breaks — without pulling in an external library.
 * @param {string} text
 * @returns {string} Safe HTML string
 */
function renderMarkdown(text) {
  // Escape HTML entities first to prevent XSS
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  return escaped
    // Code blocks (``` fenced)
    .replace(/```[\s\S]*?```/g, (match) => {
      const code = match.replace(/^```\w*\n?/, '').replace(/\n?```$/, '');
      return `<pre class="chat-code-block"><code>${code}</code></pre>`;
    })
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="chat-inline-code">$1</code>')
    // ### Headings
    .replace(/^### (.+)$/gm, '<h4 class="chat-heading">$1</h4>')
    // ## Headings
    .replace(/^## (.+)$/gm, '<h3 class="chat-heading">$1</h3>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Bullet lists — group consecutive lines starting with * or -
    .replace(/^[*\-] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]+?<\/li>)(?!\s*<li>)/g, '<ul class="chat-list">$1</ul>')
    // Numbered lists
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // Line breaks (double newline → paragraph break)
    .replace(/\n\n/g, '</p><p class="chat-para">')
    // Single newlines
    .replace(/\n/g, '<br>');
}

export function agentChatView() {
  // Generate a fresh session ID every time this view is mounted.
  // This guarantees a clean conversation history with the ADK agent.
  const sessionId = generateSessionId();

  const container = document.createElement('div');
  container.className = 'max-w-5xl mx-auto h-[calc(100vh-6rem)] flex flex-col animate-in';

  container.innerHTML = `
    <!-- Header row -->
    <div class="mb-5 flex justify-between items-center">
      <div>
        <h2 class="text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-3">
          <span class="relative flex h-3 w-3">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
          </span>
          Communications Agent
        </h2>
        <p class="text-slate-500 font-medium mt-1.5 text-sm">
          Intelligent retrieval &amp; context-aware assistance for project documents.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <!-- Session badge -->
        <span id="session-badge" class="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 text-slate-500 text-[10px] font-bold border border-slate-200 tracking-wide font-mono" title="Session ID">
          <svg class="w-3 h-3 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>
          <span id="session-id-short"></span>
        </span>

        <!-- New conversation button -->
        <button id="new-chat-btn"
          class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-bold border border-indigo-200 transition-all hover:shadow-sm active:scale-95"
          title="Start a new conversation (clears history)">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/>
          </svg>
          Nueva conversación
        </button>
      </div>
    </div>

    <!-- Chat panel -->
    <div class="glass-panel shadow-2xl shadow-slate-200/60 border border-slate-200 rounded-2xl flex-1 flex flex-col overflow-hidden relative">

      <!-- Messages area -->
      <div id="chat-messages" class="flex-1 overflow-y-auto p-6 md:p-10 space-y-6 bg-slate-50/20 scroll-smooth">
        <!-- Initial AI greeting (static, not counted as a real turn) -->
        <div class="flex items-start gap-4 group">
          <div class="agent-avatar flex-shrink-0">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
          </div>
          <div class="chat-bubble-ai">
            <p class="text-sm leading-relaxed">
              ¡Hola! Soy tu <strong>Asistente de Comunicaciones</strong>. ¿En qué te puedo ayudar hoy?
            </p>
          </div>
        </div>
      </div>

      <!-- Divider with session info -->
      <div class="px-8 py-1.5 bg-slate-50/80 border-t border-slate-100 flex items-center gap-2">
        <span class="text-[10px] text-slate-400 font-mono tracking-wide">sesión:</span>
        <span id="session-id-footer" class="text-[10px] text-slate-400 font-mono tracking-wider"></span>
      </div>

      <!-- Input area -->
      <div class="p-5 md:p-7 bg-white/80 border-t border-slate-100 backdrop-blur-sm">
        <form id="chat-form" class="relative max-w-4xl mx-auto flex items-center group">
          <div class="absolute left-4 text-slate-400 group-focus-within:text-indigo-500 transition-colors">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
            </svg>
          </div>
          <input
            type="text"
            id="chat-input"
            class="w-full pl-12 pr-16 py-4 bg-slate-100 border-2 border-transparent rounded-2xl focus:bg-white focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100 transition-all text-sm font-medium placeholder:text-slate-400"
            placeholder="Pregunta sobre documentos, contratos, planos..."
            autocomplete="off"
          >
          <button
            type="submit"
            id="send-btn"
            class="absolute right-3 p-2.5 text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 focus:outline-none transition-all active:scale-90 disabled:opacity-40 shadow-md shadow-indigo-100"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
            </svg>
          </button>
        </form>
        <p class="text-center text-[10px] text-slate-400 mt-3 font-bold uppercase tracking-widest">
          Powered by Agentic RAG · Google ADK
        </p>
      </div>
    </div>
  `;

  // ─── Bind Logic ────────────────────────────────────────────────────────────
  setTimeout(() => {
    const chatForm      = document.getElementById('chat-form');
    const chatInput     = document.getElementById('chat-input');
    const chatMessages  = document.getElementById('chat-messages');
    const sendBtn       = document.getElementById('send-btn');
    const newChatBtn    = document.getElementById('new-chat-btn');

    // Display short session ID in UI for debugging / traceability
    const shortId = sessionId.split('-')[0];
    const sessionBadgeEl = document.getElementById('session-id-short');
    const sessionFooterEl = document.getElementById('session-id-footer');
    if (sessionBadgeEl) sessionBadgeEl.textContent = shortId;
    if (sessionFooterEl) sessionFooterEl.textContent = sessionId;

    // Keep a mutable reference so "Nueva conversación" can replace it
    let activeSessionId = sessionId;

    /** Render a message bubble into the chat */
    function addMessage(htmlContent, isUser = false) {
      const msgDiv = document.createElement('div');
      msgDiv.className = `flex items-start gap-4 chat-message-enter ${isUser ? 'flex-row-reverse' : ''}`;

      const avatar = isUser
        ? `<div class="user-avatar flex-shrink-0">US</div>`
        : `<div class="agent-avatar flex-shrink-0">
             <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
               <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"/>
             </svg>
           </div>`;

      const bubbleClass = isUser ? 'chat-bubble-user' : 'chat-bubble-ai';

      msgDiv.innerHTML = `
        ${avatar}
        <div class="${bubbleClass} chat-bubble-content">
          <p class="text-sm leading-relaxed">${htmlContent}</p>
        </div>
      `;

      chatMessages.appendChild(msgDiv);
      // Smooth scroll to bottom
      chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: 'smooth' });
    }

    /** Show animated typing indicator while waiting for response */
    function showTypingIndicator() {
      const id = 'typing-' + Date.now();
      const el = document.createElement('div');
      el.id = id;
      el.className = 'flex items-start gap-4 chat-message-enter';
      el.innerHTML = `
        <div class="agent-avatar flex-shrink-0">
          <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"/>
          </svg>
        </div>
        <div class="chat-bubble-ai typing-bubble">
          <div class="typing-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
      `;
      chatMessages.appendChild(el);
      chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: 'smooth' });
      return id;
    }

    function removeTypingIndicator(id) {
      document.getElementById(id)?.remove();
    }

    /** Reset chat to a fresh state with a new session ID */
    function startNewConversation() {
      // Generate a fresh session ID
      activeSessionId = generateSessionId();
      const newShortId = activeSessionId.split('-')[0];
      if (sessionBadgeEl) sessionBadgeEl.textContent = newShortId;
      if (sessionFooterEl) sessionFooterEl.textContent = activeSessionId;

      // Clear messages and show greeting again
      chatMessages.innerHTML = '';
      addMessage('¡Conversación reiniciada! 🔄 Estoy listo para una nueva consulta.', false);
      chatInput.focus();
    }

    // ── Event Listeners ──────────────────────────────────────────────────────

    newChatBtn.addEventListener('click', startNewConversation);

    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = chatInput.value.trim();
      if (!text) return;

      chatInput.value = '';
      chatInput.disabled = true;
      sendBtn.disabled = true;

      // Render user message as plain text (escaped by renderMarkdown)
      addMessage(renderMarkdown(text), true);
      const typingId = showTypingIndicator();

      try {
        const rawResponse = await executeSubmitQuery(text, activeSessionId);
        removeTypingIndicator(typingId);
        // Render agent response with markdown support
        addMessage(renderMarkdown(rawResponse), false);
      } catch (error) {
        removeTypingIndicator(typingId);
        addMessage(
          'Lo siento, ocurrió un error de conexión con el agente. Verifique que los servicios backend estén en ejecución.',
          false
        );
      } finally {
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
      }
    });
  }, 0);

  return container;
}
