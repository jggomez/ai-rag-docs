import { executeUploadDocument } from '../../usecases/UploadDocument.js';
import { formatGcsUrl } from '../../infrastructure/api/ApiRepository.js';

export function uploadView() {
  const container = document.createElement('div');
  container.className = 'max-w-4xl mx-auto animate-in';
  
  container.innerHTML = `
    <div class="mb-10">
      <h2 class="text-3xl font-extrabold text-slate-900 tracking-tight">Upload Received Document</h2>
      <p class="text-slate-500 font-medium mt-2">Submit a new incoming communication to the high-performance processing pipeline.</p>
    </div>

    <div class="glass-panel rounded-2xl shadow-xl shadow-slate-200/50 border border-slate-200 overflow-hidden">
      <form id="upload-form" class="p-8 md:p-10 space-y-8">
        
        <!-- File Upload Area -->
        <div class="space-y-3">
          <label class="card-label">Document File (PDF)</label>
          <div class="relative group mt-1 flex justify-center px-6 py-10 border-2 border-slate-200 border-dashed rounded-xl hover:border-indigo-400 hover:bg-indigo-50/30 transition-all duration-300 bg-slate-50/50">
            <div class="space-y-2 text-center">
              <div class="w-16 h-16 bg-white rounded-2xl shadow-sm border border-slate-100 flex items-center justify-center mx-auto group-hover:scale-110 transition-transform duration-300">
                <svg class="h-8 w-8 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <div class="flex text-sm text-slate-600 justify-center pt-2">
                <label for="file-upload" class="relative cursor-pointer font-bold text-indigo-600 hover:text-indigo-500 focus-within:outline-none transition-colors">
                  <span>Click to upload</span>
                  <input id="file-upload" name="file-upload" type="file" class="sr-only" accept=".pdf">
                </label>
                <p class="pl-1">or drag and drop here</p>
              </div>
              <p class="text-xs font-semibold text-slate-400 uppercase tracking-tighter">PDF maximum 10MB</p>
              <div id="file-name-display" class="inline-flex items-center px-3 py-1 rounded-full bg-indigo-100 text-indigo-700 text-sm font-bold mt-4 hidden shadow-sm border border-indigo-200">
                <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20"><path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"></path></svg>
                <span id="file-name-text"></span>
              </div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
          <div class="space-y-1.5">
            <label class="card-label">ID Borrador</label>
            <input type="text" id="id_borrador" class="input-field" placeholder="e.g. 76857089" required>
          </div>
          <div class="space-y-1.5">
            <label class="card-label">Work Front</label>
            <input type="text" id="work_front" class="input-field" placeholder="e.g. Descarga intermedia" required>
          </div>
          <div class="space-y-1.5">
            <label class="card-label">Filename</label>
            <input type="text" id="filename" class="input-field" placeholder="e.g. CYS-CW276532-PHI-03362.pdf" required>
          </div>
          <div class="space-y-1.5">
            <label class="card-label">Document Type</label>
            <select id="document_type" class="input-field" required>
              <option value="received" selected>Received</option>
              <option value="sent">Sent</option>
            </select>
          </div>
          <div class="space-y-1.5 md:col-span-2">
            <label class="card-label">Document Date</label>
            <input type="date" id="doc_date" class="input-field">
          </div>
        </div>

        <div class="pt-6 flex items-center justify-end">
          <button type="submit" id="submit-btn" class="btn-primary w-full md:w-auto min-w-[180px]">
            <span>Process Document</span>
            <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 7l5 5m0 0l-5 5m5-5H6"></path></svg>
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
    const fileInput = document.getElementById('file-upload');
    const fileNameDisplay = document.getElementById('file-name-display');
    const fileNameText = document.getElementById('file-name-text');
    const form = document.getElementById('upload-form');
    const statusAlert = document.getElementById('status-alert');
    const submitBtn = document.getElementById('submit-btn');

    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        const selectedName = e.target.files[0].name;
        fileNameText.textContent = selectedName;
        fileNameDisplay.classList.remove('hidden');
        fileNameDisplay.classList.add('animate-in');
        const filenameField = document.getElementById('filename');
        if (filenameField) {
          filenameField.value = selectedName;
        }
      }
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const file = fileInput.files[0];
      if (!file) {
        showStatus('error', 'Selection Required', 'Please select a valid PDF communication to proceed.');
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = `<svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Analyzing...`;
      
      try {
        const metadata = {
          workFront: document.getElementById('work_front').value.trim(),
          documentDate: document.getElementById('doc_date').value.trim(),
          idBorrador: document.getElementById('id_borrador').value.trim(),
          documentType: document.getElementById('document_type').value,
        };

        const { ingestResult } = await executeUploadDocument(file, metadata);

        const details = `
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
            <div class="p-3 bg-white/50 rounded-lg border border-indigo-100">
              <span class="text-[10px] uppercase font-bold text-indigo-500 block mb-1">Document ID</span>
              <p class="font-bold text-slate-900">${ingestResult.document_id || 'N/A'}</p>
            </div>
            <div class="p-3 bg-white/50 rounded-lg border border-indigo-100">
              <span class="text-[10px] uppercase font-bold text-indigo-500 block mb-1">Status</span>
              <p class="font-bold text-slate-900">${ingestResult.status || 'N/A'}</p>
            </div>
            <div class="p-3 bg-white/50 rounded-lg border border-indigo-100 sm:col-span-2">
              <span class="text-[10px] uppercase font-bold text-indigo-500 block mb-1">Filename</span>
              <p class="font-bold text-slate-900">${ingestResult.filename || 'N/A'}</p>
            </div>
          </div>
        `;

        showStatus('success', 'Ingestion Pipeline Complete', details);
        form.reset();
        fileNameDisplay.classList.add('hidden');
      } catch (error) {
        showStatus('error', 'Pipeline Interrupted', error.message);
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Process Document <svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 7l5 5m0 0l-5 5m5-5H6"></path></svg>';
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
