import React, {useEffect, useRef} from 'react';
import {createPortal} from 'react-dom';
import {X} from 'lucide-react';

export default function StockDialog({children,onDismiss,label = 'Stock details'}) {
  const dialogRef = useRef(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    dialog.showModal();
    document.body.style.overflow = 'hidden';
    return () => {
      if (dialog.open) dialog.close();
      document.body.style.overflow = previousOverflow;
      if (previousFocus?.isConnected && !previousFocus.closest('[hidden]'))
        previousFocus.focus({preventScroll:true});
    };
  },[]);

  const content = <dialog ref={dialogRef} className="stock-backdrop" aria-label={label} aria-modal="true"
    onCancel={event => {event.preventDefault();onDismiss();}}
    onMouseDown={event => {if (event.target === event.currentTarget) onDismiss();}}>
    <section className="stock-drawer">
      <button type="button" className="drawer-close" aria-label="Close stock details" autoFocus onClick={onDismiss}><X size={18}/></button>
      {children}
    </section>
  </dialog>;

  return typeof document === 'undefined' ? content : createPortal(content,document.body);
}
