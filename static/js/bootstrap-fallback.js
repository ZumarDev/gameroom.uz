// Minimal Bootstrap JS fallback (Modal / Dropdown / Collapse / Tabs)
// Used when Bootstrap bundle can't be loaded (e.g., no internet access for CDN).
(function () {
  if (window.bootstrap && (bootstrap.Modal || bootstrap.Dropdown || bootstrap.Collapse || bootstrap.Tab)) return;

  window.bootstrap = window.bootstrap || {};

  const body = document.body;
  let activeBackdrop = null;

  function qs(sel, root = document) {
    return root.querySelector(sel);
  }

  function qsa(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
  }

  function getTarget(trigger) {
    const sel = trigger.getAttribute('data-bs-target') || trigger.getAttribute('href');
    if (!sel) return null;
    if (sel.startsWith('#')) return qs(sel);
    return null;
  }

  function ensureBackdrop() {
    if (activeBackdrop) return activeBackdrop;
    const bd = document.createElement('div');
    bd.className = 'modal-backdrop fade show';
    bd.addEventListener('click', function () {
      const modal = qs('.modal.show');
      if (modal) hideModal(modal);
    });
    document.body.appendChild(bd);
    activeBackdrop = bd;
    return bd;
  }

  function removeBackdrop() {
    if (!activeBackdrop) return;
    activeBackdrop.remove();
    activeBackdrop = null;
  }

  function showModal(modal) {
    if (!modal) return;
    // Move modal to body to avoid stacking-context issues.
    if (!modal._fallbackParent) {
      modal._fallbackParent = modal.parentElement;
      modal._fallbackNextSibling = modal.nextSibling;
      document.body.appendChild(modal);
    }
    ensureBackdrop();
    modal.style.display = 'block';
    modal.removeAttribute('aria-hidden');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('role', 'dialog');
    modal.classList.add('show');
    body.classList.add('modal-open');
  }

  function hideModal(modal) {
    if (!modal) return;
    modal.classList.remove('show');
    modal.setAttribute('aria-hidden', 'true');
    modal.removeAttribute('aria-modal');
    modal.style.display = 'none';
    body.classList.remove('modal-open');
    removeBackdrop();
    if (modal._fallbackParent) {
      const parent = modal._fallbackParent;
      const next = modal._fallbackNextSibling;
      if (next && next.parentElement === parent) {
        parent.insertBefore(modal, next);
      } else {
        parent.appendChild(modal);
      }
      delete modal._fallbackParent;
      delete modal._fallbackNextSibling;
    }
  }

  // Public API (Bootstrap-like)
  class Modal {
    constructor(el) {
      this._el = el;
    }
    show() { showModal(this._el); }
    hide() { hideModal(this._el); }
  }

  class Collapse {
    constructor(el) {
      this._el = el;
    }
    show() { this._el.classList.add('show'); }
    hide() { this._el.classList.remove('show'); }
    toggle() { this._el.classList.toggle('show'); }
  }

  class Dropdown {
    constructor(triggerEl) {
      this._trigger = triggerEl;
      this._menu = triggerEl && triggerEl.parentElement && qs('.dropdown-menu', triggerEl.parentElement);
    }
    show() { if (this._menu) this._menu.classList.add('show'); }
    hide() { if (this._menu) this._menu.classList.remove('show'); }
    toggle() { if (this._menu) this._menu.classList.toggle('show'); }
  }

  class Tab {
    constructor(triggerEl) {
      this._trigger = triggerEl;
    }
    show() {
      const trigger = this._trigger;
      const target = getTarget(trigger);
      if (!target) return;

      const tabList = trigger.closest('[role="tablist"]');
      if (tabList) {
        qsa('.nav-link.active', tabList).forEach((el) => el.classList.remove('active'));
      }
      trigger.classList.add('active');

      // panes
      const container = target.closest('.tab-content') || qs('.tab-content');
      if (container) {
        qsa('.tab-pane.show.active', container).forEach((pane) => pane.classList.remove('show', 'active'));
      }
      target.classList.add('show', 'active');
    }
  }

  window.bootstrap.Modal = window.bootstrap.Modal || Modal;
  window.bootstrap.Collapse = window.bootstrap.Collapse || Collapse;
  window.bootstrap.Dropdown = window.bootstrap.Dropdown || Dropdown;
  window.bootstrap.Tab = window.bootstrap.Tab || Tab;

  // Modals
  document.addEventListener('click', function (e) {
    const trigger = e.target.closest('[data-bs-toggle="modal"]');
    if (trigger) {
      e.preventDefault();
      const modal = getTarget(trigger);
      showModal(modal);
      return;
    }

    const dismiss = e.target.closest('[data-bs-dismiss="modal"]');
    if (dismiss) {
      e.preventDefault();
      const modal = e.target.closest('.modal');
      hideModal(modal);
      return;
    }

    // Click outside dialog closes (basic)
    const modalEl = e.target.classList && e.target.classList.contains('modal') ? e.target : null;
    if (modalEl && modalEl.classList.contains('show')) {
      hideModal(modalEl);
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    const modal = qs('.modal.show');
    if (modal) hideModal(modal);
  });

  // Collapse
  document.addEventListener('click', function (e) {
    const trigger = e.target.closest('[data-bs-toggle="collapse"]');
    if (!trigger) return;
    const target = getTarget(trigger);
    if (!target) return;
    e.preventDefault();
    const isShown = target.classList.contains('show');
    target.classList.toggle('show', !isShown);
    trigger.setAttribute('aria-expanded', String(!isShown));
  });

  // Dropdown
  function closeAllDropdowns(exceptMenu) {
    qsa('.dropdown-menu.show').forEach((menu) => {
      if (exceptMenu && menu === exceptMenu) return;
      menu.classList.remove('show');
    });
  }

  document.addEventListener('click', function (e) {
    const trigger = e.target.closest('[data-bs-toggle="dropdown"]');
    if (trigger) {
      e.preventDefault();
      const menu = trigger.parentElement && qs('.dropdown-menu', trigger.parentElement);
      if (!menu) return;
      const willShow = !menu.classList.contains('show');
      closeAllDropdowns(menu);
      menu.classList.toggle('show', willShow);
      return;
    }

    if (!e.target.closest('.dropdown-menu')) {
      closeAllDropdowns();
    }
  });

  // Tabs
  document.addEventListener('click', function (e) {
    const trigger = e.target.closest('[data-bs-toggle="tab"]');
    if (!trigger) return;
    e.preventDefault();
    new window.bootstrap.Tab(trigger).show();
  });
})();
