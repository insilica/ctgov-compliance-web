(function () {
  'use strict';

  const config = window.QUERY_WORKSPACE_CONFIG || null;
  const root = document.querySelector('[data-query-workspace]');

  if (!config || !root) {
    return;
  }

  const form = root.querySelector('#query-workspace-form');
  const input = root.querySelector('#query-workspace-input');
  const sendButton = root.querySelector('#query-workspace-send');
  const resetButton = root.querySelector('#query-workspace-reset');
  const modeSelect = root.querySelector('#query-workspace-mode');
  const statusIndicator = root.querySelector('#query-workspace-mode-indicator');
  const log = root.querySelector('#query-workspace-log');
  const csrfInput = form.querySelector('input[name="csrf_token"]');
  const promptButtons = root.querySelectorAll('.query-workspace-prompt');

  const csrfToken = csrfInput ? csrfInput.value : '';
  let isSending = false;

  function escapeHtml(value) {
    const temp = document.createElement('div');
    temp.textContent = value;
    return temp.innerHTML;
  }

  function formatMessage(text) {
    if (!text) {
      return '';
    }
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  function appendMessage(role, content) {
    if (!log) {
      return;
    }
    const wrapper = document.createElement('div');
    wrapper.className = `query-message query-message--${role}`;
    const roleLabel = role === 'user' ? 'You' : 'ctgov_mcp';
    wrapper.innerHTML = `
      <div class="query-message__role">${roleLabel}</div>
      <div class="query-message__body">${formatMessage(content)}</div>
    `;
    log.appendChild(wrapper);
    log.scrollTop = log.scrollHeight;
  }

  function setStatusIndicator(useLLM) {
    if (!statusIndicator) {
      return;
    }
    statusIndicator.textContent = useLLM ? 'LLM parsing' : 'Pattern parsing';
  }

  async function postJson(url, body) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(body)
    });
    let data = null;
    try {
      data = await response.json();
    } catch (err) {
      data = null;
    }
    if (!response.ok) {
      const message = data && data.error ? data.error : `Request failed (${response.status})`;
      throw new Error(message);
    }
    return data;
  }

  function isLLMSelected() {
    return modeSelect && modeSelect.value === 'llm';
  }

  async function sendMessage(message) {
    if (!message || isSending) {
      return;
    }
    appendMessage('user', message);
    isSending = true;
    sendButton.setAttribute('disabled', 'true');
    sendButton.textContent = 'Sending...';
    try {
      const payload = await postJson(config.endpoints.message, {
        message,
        use_llm: isLLMSelected()
      });
      if (!payload.success) {
        throw new Error(payload.error || 'Query failed.');
      }
      appendMessage('assistant', payload.message || 'No response received.');
      setStatusIndicator(Boolean(payload.use_llm));
    } catch (error) {
      appendMessage('assistant', `Unable to process the request: ${error.message}`);
    } finally {
      isSending = false;
      sendButton.removeAttribute('disabled');
      sendButton.textContent = 'Send';
      input.value = '';
      input.focus();
    }
  }

  async function resetWorkspace(useLLMOverride) {
    const desiredMode = typeof useLLMOverride === 'boolean' ? useLLMOverride : isLLMSelected();
    if (resetButton) {
      resetButton.setAttribute('disabled', 'true');
      resetButton.textContent = 'Resetting...';
    }
    try {
      const payload = await postJson(config.endpoints.reset, {
        use_llm: desiredMode
      });
      setStatusIndicator(Boolean(payload.use_llm));
    } catch (error) {
      appendMessage('assistant', `Reset failed: ${error.message}`);
    } finally {
      if (resetButton) {
        resetButton.removeAttribute('disabled');
        resetButton.textContent = 'Reset conversation';
      }
      log.innerHTML = '';
      if (config.welcomeMessage) {
        appendMessage('assistant', config.welcomeMessage);
      }
    }
  }

  if (form) {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      sendMessage(input.value.trim());
    });
  }

  if (input) {
    input.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && event.ctrlKey) {
        event.preventDefault();
        sendMessage(input.value.trim());
      }
    });
  }

  if (resetButton) {
    resetButton.addEventListener('click', () => resetWorkspace());
  }

  if (modeSelect) {
    modeSelect.addEventListener('change', () => {
      const newModeIsLLM = isLLMSelected();
      resetWorkspace(newModeIsLLM);
    });
    modeSelect.value = config.defaultMode ? 'llm' : 'pattern';
    setStatusIndicator(config.defaultMode);
  }

  promptButtons.forEach((button) => {
    button.addEventListener('click', () => {
      input.value = button.dataset.prompt || '';
      input.focus();
    });
  });

  if (config.welcomeMessage) {
    appendMessage('assistant', config.welcomeMessage);
  }
  setStatusIndicator(Boolean(config.defaultMode));
})();
