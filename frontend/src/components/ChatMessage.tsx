import { User, Bot } from 'lucide-react';
import type { Message } from '../types';
import { Chart } from './Chart';
import { DataTable } from './DataTable';
import { SqlDisplay } from './SqlDisplay';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.type === 'user';

  return (
    <div className={`flex gap-4 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-blue-500' : 'bg-gray-700'
        }`}
      >
        {isUser ? (
          <User size={16} className="text-white" />
        ) : (
          <Bot size={16} className="text-white" />
        )}
      </div>

      <div className={`flex-1 max-w-3xl ${isUser ? 'text-right' : ''}`}>
        {isUser ? (
          <div className="inline-block bg-blue-500 text-white px-4 py-2 rounded-2xl rounded-tr-sm">
            {message.content}
          </div>
        ) : (
          <div className="space-y-4">
            {message.response ? (
              <>
                {/* Summary */}
                <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                  <p className="text-gray-800">{message.response.summary}</p>
                  {message.response.error && (
                    <p className="mt-2 text-red-600 text-sm">
                      Error: {message.response.error}
                    </p>
                  )}
                </div>

                {/* Chart */}
                {message.response.chart && message.response.data && (
                  <Chart
                    config={message.response.chart}
                    data={message.response.data}
                  />
                )}

                {/* Data Table */}
                {message.response.data && message.response.data.length > 0 && (
                  <DataTable data={message.response.data} />
                )}

                {/* SQL Query */}
                {message.response.sql && (
                  <SqlDisplay sql={message.response.sql} />
                )}
              </>
            ) : (
              <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                <p className="text-gray-800">{message.content}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
