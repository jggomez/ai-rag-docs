import { searchAndRetrieveDocument, formatGcsUrl } from '../../infrastructure/api/ApiRepository.js';

export function retrieveView() {
  const container = document.createElement('div');
  container.className = 'max-w-4xl mx-auto animate-in';

  container.innerHTML = `
    <div class="mb-10">
      <h2 class="text-3xl font-extrabold text-slate-900 tracking-tight">Búsqueda y RAG</h2>
      <p class="text-slate-500 font-medium mt-2">Busca un documento recibido para recuperar su contexto RAG y generar un borrador de respuesta PDF.</p>
    </div>

    <div class="glass-panel rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200 overflow-hidden">
      <form id="retrieve-form" class="p-8 md:p-10 space-y-8">
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
          <div class="space-y-1.5">
            <label class="card-label">Código Comunicado Recibido (Heurístico)</label>
            <input type="text" id="received_communication_code" class="input-field" placeholder="e.g. REC-001 o nombre de archivo">
          </div>
          <div class="space-y-1.5">
            <label class="card-label">ID Documento Recibido (Firestore ID)</label>
            <input type="text" id="received_document_id" class="input-field" placeholder="e.g. 76857089_REC">
          </div>
          <div class="space-y-1.5">
            <label class="card-label">Frente de Trabajo (Pre-filtro RAG)</label>
            <input type="text" id="front" class="input-field" placeholder="e.g. Descarga intermedia">
          </div>
          <div class="space-y-1.5">
            <label class="card-label">Fecha Inicio (Pre-filtro RAG)</label>
            <input type="date" id="start_date" class="input-field">
          </div>
          <div class="space-y-1.5 md:col-span-2">
            <label class="card-label">Fecha Fin (Pre-filtro RAG)</label>
            <input type="date" id="end_date" class="input-field">
          </div>
        </div>

        <div class="pt-6 flex items-center justify-end">
          <button type="submit" id="submit-btn" class="btn-primary w-full md:w-auto min-w-[180px]">
            <span>Buscar y Generar RAG</span>
            <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
          </button>
        </div>
      </form>
    </div>
    
    <!-- Status Alert -->
    <div id="status-alert" class="mt-8 p-6 rounded-2xl hidden animate-in border shadow-lg transition-all duration-300">
      <div class="flex items-start gap-4">
        <div class="flex-shrink-0 w-10 h-10 rounded-xl bg-white flex items-center justify-center shadow-sm" id="status-icon"></div>
        <div class="flex-1">
          <h3 class="text-base font-bold" id="status-title"></h3>
          <div class="mt-2 text-sm leading-relaxed" id="status-message"></div>
        </div>
      </div>
    </div>
  `;

  // Bind UI logic
  setTimeout(() => {
    const form = document.getElementById('retrieve-form');
    const statusAlert = document.getElementById('status-alert');
    const submitBtn = document.getElementById('submit-btn');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const receivedCommunicationCode = document.getElementById('received_communication_code').value.trim();
      const receivedDocumentId = document.getElementById('received_document_id').value.trim();
      const front = document.getElementById('front').value.trim();
      const startDate = document.getElementById('start_date').value;
      const endDate = document.getElementById('end_date').value;

      if (!receivedCommunicationCode && !receivedDocumentId) {
        showStatus('error', 'Campos requeridos', 'Debes ingresar al menos uno de los identificadores del documento (Código Comunicado o ID Documento).');
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = `<svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Ejecutando RAG...`;
      
      try {
        const result = await searchAndRetrieveDocument({
          receivedCommunicationCode,
          receivedDocumentId,
          startDate: startDate || null,
          endDate: endDate || null,
          front: front || null,
        });

        const responseUrl = formatGcsUrl(result.gcs_url);

        const details = `
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
            <div class="p-3 bg-white/50 rounded-lg border border-indigo-100 sm:col-span-2">
              <span class="text-[10px] uppercase font-bold text-indigo-500 block mb-1">Asunto</span>
              <p class="font-bold text-slate-900">${result.subject || 'Sin asunto'}</p>
            </div>
            <div class="p-3 bg-white/50 rounded-lg border border-indigo-100">
              <span class="text-[10px] uppercase font-bold text-indigo-500 block mb-1">Chuncks Similares</span>
              <p class="font-bold text-slate-900">${result.similar_count || 0} Chunks</p>
            </div>
            <div class="p-3 bg-white/50 rounded-lg border border-indigo-100">
              <span class="text-[10px] uppercase font-bold text-indigo-500 block mb-1">Docs Enviados Resueltos</span>
              <p class="font-bold text-slate-900">${result.sent_count || 0} Documentos</p>
            </div>
          </div>
          ${responseUrl ? `
            <div class="mt-6">
              <a href="${responseUrl}" target="_blank" class="inline-flex items-center px-4 py-2.5 bg-indigo-600 text-white rounded-lg font-bold text-sm shadow-md hover:bg-indigo-700 transition-all active:scale-95">
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                Descargar Respuesta PDF Generada
              </a>
            </div>
          ` : ''}
        `;

        showStatus('success', 'Búsqueda RAG Completada', details);
      } catch (error) {
        showStatus('error', 'Error en Búsqueda RAG', error.message);
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Buscar y Generar RAG <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>';
      }
    });

    function showStatus(type, title, message) {
      statusAlert.classList.remove('hidden', 'bg-emerald-50', 'bg-rose-50', 'border-emerald-200', 'border-rose-200');
      statusAlert.classList.add(type === 'success' ? 'bg-emerald-50' : 'bg-rose-50');
      statusAlert.classList.add(type === 'success' ? 'border-emerald-200' : 'border-rose-200');
      
      const titleEl = document.getElementById('status-title');
      const messageEl = document.getElementById('status-message');
      const iconEl = document.getElementById('status-icon');
      
      titleEl.className = `text-base font-bold ${type === 'success' ? 'text-emerald-900' : 'text-rose-900'}`;
      messageEl.className = `mt-2 text-sm leading-relaxed ${type === 'success' ? 'text-emerald-800' : 'text-rose-800'}`;
      
      titleEl.textContent = title;
      messageEl.innerHTML = message;
      
      if (type === 'success') {
        iconEl.innerHTML = `<svg class="h-6 w-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path></svg>`;
      } else {
        iconEl.innerHTML = `<svg class="h-6 w-6 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"></path></svg>`;
      }
      
      statusAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, 0);

  return container;
}
