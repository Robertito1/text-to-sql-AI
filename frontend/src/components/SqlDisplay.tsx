import { useState } from 'react';
import { Copy, Check, Code } from 'lucide-react';

interface SqlDisplayProps {
  sql: string;
}

export function SqlDisplay({ sql }: SqlDisplayProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <Code size={14} />
          <span>SQL Query</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-gray-400 hover:text-white text-sm transition-colors"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="p-4 text-sm text-gray-100 overflow-x-auto">
        <code>{sql}</code>
      </pre>
    </div>
  );
}
