import { useEffect, useRef } from 'react';

/**
 * Scroll-reveal wrapper.
 *
 * The important detail is what it does NOT do: content is never parked at
 * opacity:0 in CSS waiting for an observer. Anything already inside the first
 * viewport is left completely alone, and if JavaScript never runs, every
 * section renders normally. Only elements genuinely below the fold are hidden,
 * and only after JS has confirmed they're down there.
 *
 * That keeps the page whole for the first paint, for a link preview, and for
 * anyone with motion reduced or scripting off.
 */
export default function Reveal({ children, className = '', delay = 0, as: Tag = 'div' }) {
  const ref = useRef(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced || !('IntersectionObserver' in window)) return;

    // Already visible on load — leave it be, no animation, no flash.
    if (node.getBoundingClientRect().top <= window.innerHeight * 0.9) return;

    node.classList.add('pending');

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          node.classList.remove('pending');
          node.classList.add('revealed');
          io.unobserve(node);
        });
      },
      { threshold: 0.15, rootMargin: '0px 0px -8% 0px' },
    );

    io.observe(node);
    return () => io.disconnect();
  }, []);

  return (
    <Tag ref={ref} className={className} style={delay ? { animationDelay: `${delay}s` } : undefined}>
      {children}
    </Tag>
  );
}
