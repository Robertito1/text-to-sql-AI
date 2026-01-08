interface DataTableProps {
  data: Record<string, any>[];
}

export function DataTable({ data }: DataTableProps) {
  if (!data || data.length === 0) {
    return null;
  }

  const columns = Object.keys(data[0]);

  return (
    <div className="w-full overflow-x-auto bg-white rounded-lg shadow-sm border border-gray-100">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            {columns.map((col) => (
              <th
                key={col}
                className="px-4 py-3 text-left font-semibold text-gray-700 uppercase tracking-wider text-xs"
              >
                {col.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {data.slice(0, 100).map((row, rowIndex) => (
            <tr 
              key={rowIndex} 
              className="hover:bg-gray-50 transition-colors"
            >
              {columns.map((col) => (
                <td key={col} className="px-4 py-3 text-gray-600">
                  {formatValue(row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > 100 && (
        <div className="px-4 py-2 text-sm text-gray-500 bg-gray-50 border-t border-gray-200">
          Showing 100 of {data.length} rows
        </div>
      )}
    </div>
  );
}

function formatValue(value: any): string {
  if (value === null || value === undefined) {
    return '-';
  }
  if (typeof value === 'number') {
    if (Number.isInteger(value)) {
      return value.toLocaleString();
    }
    return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return String(value);
}
