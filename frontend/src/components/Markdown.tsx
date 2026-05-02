import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';

const components: Components = {
  p: ({ children }) => (
    <p className="font-display text-[15px] leading-relaxed text-bone [&:not(:first-child)]:mt-2.5">
      {children}
    </p>
  ),
  h1: ({ children }) => (
    <h1 className="mt-3 mb-1.5 font-display text-[18px] leading-tight text-brass-bright [&:first-child]:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="mt-3 mb-1.5 font-display text-[16px] leading-tight text-brass-bright [&:first-child]:mt-0">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="mt-2.5 mb-1 font-display text-[14px] uppercase tracking-[0.18em] text-bone [&:first-child]:mt-0">
      {children}
    </h3>
  ),
  ul: ({ children }) => (
    <ul className="mt-2 ml-4 list-disc space-y-1 font-display text-[15px] leading-relaxed text-bone marker:text-brass-bright">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="mt-2 ml-4 list-decimal space-y-1 font-display text-[15px] leading-relaxed text-bone marker:text-brass-bright">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="pl-1">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-bone">{children}</strong>,
  em: ({ children }) => <em className="italic text-bone-dim">{children}</em>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-brass-bright underline decoration-brass-dim/60 underline-offset-2 hover:decoration-brass-bright"
    >
      {children}
    </a>
  ),
  code: ({ className, children }) => {
    const isBlock = className?.startsWith('language-');
    if (isBlock) {
      return (
        <code className="font-mono text-[12.5px] leading-relaxed text-bone">{children}</code>
      );
    }
    return (
      <code className="border border-rule bg-ink-2/60 px-1 py-0.5 font-mono text-[12.5px] text-brass-bright">
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="mt-2 overflow-x-auto border border-rule bg-ink-2/60 px-2.5 py-2 font-mono text-[12.5px] leading-relaxed text-bone">
      {children}
    </pre>
  ),
  blockquote: ({ children }) => (
    <blockquote className="mt-2 border-l-2 border-brass-dim/60 bg-ink-2/40 px-3 py-1.5 font-display text-[14px] italic text-bone-dim">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-3 border-t border-rule" />,
  table: ({ children }) => (
    <div className="mt-2 overflow-x-auto">
      <table className="w-full border border-rule font-mono text-[12px] text-bone">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-ink-2/60 text-[10px] uppercase tracking-[0.18em] text-bone-fade">
      {children}
    </thead>
  ),
  th: ({ children }) => (
    <th className="border-b border-rule px-2 py-1 text-left font-mono">{children}</th>
  ),
  td: ({ children }) => <td className="border-b border-rule/60 px-2 py-1">{children}</td>,
};

export function Markdown({ children }: { children: string }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{children}</ReactMarkdown>;
}
