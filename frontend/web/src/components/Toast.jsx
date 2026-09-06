import { createContext, useCallback, useContext, useMemo, useState } from 'react';

/**
 * Minimal toast system.
 *
 * Exists because the console performs real, slow, failable work — model
 * inference, protocol calls, network lookups — and silent failure in front of
 * an audience is worse than an ugly error. Every mutating action reports what
 * happened.
 */

const ToastContext = createContext(() => {});

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (message, tone = 'info', ttl = 5200) => {
      const id = Math.random().toString(36).slice(2);
      setToasts((current) => [...current, { id, message, tone }]);
      if (ttl) setTimeout(() => dismiss(id), ttl);
      return id;
    },
    [dismiss],
  );

  const value = useMemo(() => push, [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((t) => (
          <button key={t.id} className={`toast toast-${t.tone}`} onClick={() => dismiss(t.id)}>
            <span className="toast-dot" />
            <span>{t.message}</span>
          </button>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
