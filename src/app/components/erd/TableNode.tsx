import React, { memo } from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { Key, Link2, Eye, Table2 } from "lucide-react";
import { TableNodeData } from "../../utils/erdTransform";

export const TableNode = memo(({ data, selected }: NodeProps<any>) => {
  const nodeData = data as TableNodeData;
  const { table, isLargeSchema, columnsToDisplay, inboundCount, outboundCount } = nodeData;
  const isView = table.kind === "view";

  return (
    <div
      tabIndex={0}
      role="button"
      aria-label={`Table node: ${table.name}`}
      className={`min-w-[240px] max-w-[320px] rounded-lg border bg-white dark:bg-slate-900 shadow-md transition-all duration-150 outline-none select-none text-xs ${
        selected
          ? "ring-2 ring-indigo-500 border-indigo-500 shadow-indigo-100 dark:shadow-indigo-950"
          : "border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
      }`}
    >
      {/* Handles for connections */}
      <Handle
        type="target"
        position={Position.Left}
        id="left"
        className="!w-2.5 !h-2.5 !-left-1.5 !bg-indigo-500 !border-2 !border-white dark:!border-slate-900"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="right"
        className="!w-2.5 !h-2.5 !-right-1.5 !bg-indigo-500 !border-2 !border-white dark:!border-slate-900"
      />
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        className="!w-2.5 !h-2.5 !-top-1.5 !bg-indigo-500 !border-2 !border-white dark:!border-slate-900 !opacity-0"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        className="!w-2.5 !h-2.5 !-bottom-1.5 !bg-indigo-500 !border-2 !border-white dark:!border-slate-900 !opacity-0"
      />

      {/* Header */}
      <div
        className={`px-3 py-2 flex items-center justify-between border-b rounded-t-lg ${
          isView
            ? "bg-purple-50/80 dark:bg-purple-950/40 border-purple-200 dark:border-purple-900"
            : "bg-slate-50 dark:bg-slate-800/60 border-slate-200 dark:border-slate-800"
        }`}
      >
        <div className="flex items-center gap-1.5 overflow-hidden">
          {isView ? (
            <Eye className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400 shrink-0" />
          ) : (
            <Table2 className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400 shrink-0" />
          )}
          <span
            className="font-semibold text-slate-900 dark:text-slate-100 truncate text-[13px]"
            title={table.name}
          >
            {table.name}
          </span>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {table.schema && table.schema !== "public" && (
            <span className="px-1.5 py-0.5 text-[10px] rounded font-medium bg-slate-200/80 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
              {table.schema}
            </span>
          )}
          <span
            className={`px-1.5 py-0.5 text-[10px] rounded font-medium ${
              isView
                ? "bg-purple-100 text-purple-700 dark:bg-purple-900/60 dark:text-purple-300"
                : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
            }`}
          >
            {table.kind}
          </span>
        </div>
      </div>

      {/* Body: Full column list vs Compact summary */}
      {isLargeSchema ? (
        <div className="px-3 py-2 text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between">
          <span>{table.columns.length} columns</span>
          <div className="flex items-center gap-1.5 text-[10px]">
            {inboundCount > 0 && <span title={`${inboundCount} incoming FKs`}>← {inboundCount}</span>}
            {outboundCount > 0 && <span title={`${outboundCount} outgoing FKs`}>→ {outboundCount}</span>}
          </div>
        </div>
      ) : (
        <div className="py-1 divide-y divide-slate-100 dark:divide-slate-800/60 max-h-[360px] overflow-y-auto">
          {columnsToDisplay.map((col) => (
            <div
              key={col.name}
              className="px-3 py-1.5 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
            >
              <div className="flex items-center gap-1.5 overflow-hidden">
                {col.is_pk && (
                  <Key
                    className="w-3 h-3 text-amber-500 shrink-0"
                    title="Primary Key"
                  />
                )}
                {col.is_fk && (
                  <Link2
                    className="w-3 h-3 text-indigo-500 shrink-0"
                    title="Foreign Key"
                  />
                )}
                <span
                  className={`truncate ${
                    col.is_pk
                      ? "font-semibold text-slate-900 dark:text-slate-100"
                      : "text-slate-700 dark:text-slate-300"
                  }`}
                  title={col.name}
                >
                  {col.name}
                </span>
              </div>
              <span className="font-mono text-[10px] text-slate-400 dark:text-slate-500 shrink-0 uppercase">
                {col.type}
              </span>
            </div>
          ))}

          {columnsToDisplay.length === 0 && (
            <div className="px-3 py-2 text-center text-slate-400 italic text-[11px]">
              No columns match filter
            </div>
          )}
        </div>
      )}
    </div>
  );
});

TableNode.displayName = "TableNode";
