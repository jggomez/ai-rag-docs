import { uploadView } from './adapters/ui/uploadView.js';
import { retrieveView } from './adapters/ui/retrieveView.js';
import { agentChatView } from './adapters/ui/agentChatView.js';

// Simple SPA Router
const routes = {
  'upload': uploadView,
  'retrieve': retrieveView,
  'agent': agentChatView
};

function navigateTo(routeId) {
  const container = document.getElementById('app-container');
  
  // Update UI navigation state
  document.querySelectorAll('.nav-btn').forEach(btn => {
    if (btn.dataset.route === routeId) {
      btn.classList.add('nav-btn-active');
      btn.classList.remove('nav-btn-inactive');
      btn.querySelector('svg').classList.add('text-indigo-400');
      btn.querySelector('svg').classList.remove('text-slate-500');
    } else {
      btn.classList.remove('nav-btn-active');
      btn.classList.add('nav-btn-inactive');
      btn.querySelector('svg').classList.remove('text-indigo-400');
      btn.querySelector('svg').classList.add('text-slate-500');
    }
  });

  // Render view
  const viewFn = routes[routeId];
  if (viewFn) {
    container.innerHTML = '';
    const viewElement = viewFn();
    container.appendChild(viewElement);
  }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const route = e.currentTarget.dataset.route;
      navigateTo(route);
    });
  });

  // Default route
  navigateTo('upload');
});
