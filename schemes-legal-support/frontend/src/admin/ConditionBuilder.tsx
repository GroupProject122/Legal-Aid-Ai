import type { ConditionNode, LeafCondition, Operator, UserProfileField } from "../types";
import {
  coerceLeafValue,
  defaultLeaf,
  ENUM_OPTIONS,
  fieldKind,
  FIELD_LABELS,
  OPERATOR_LABELS,
  OPERATORS_BY_KIND,
  operatorNeedsArray,
  operatorNeedsNumber,
  operatorNeedsValue,
  PROFILE_FIELDS,
} from "./conditionMeta";

type NodeKind = "leaf" | "AND" | "OR" | "NOT";

function nodeKind(node: ConditionNode): NodeKind {
  if (!("op" in node)) return "leaf";
  return node.op;
}

function convert(node: ConditionNode, to: NodeKind): ConditionNode {
  const from = nodeKind(node);
  if (from === to) return node;

  if (to === "leaf") return defaultLeaf();

  if (to === "AND" || to === "OR") {
    if (from === "AND" || from === "OR") {
      return { op: to, children: (node as { children: ConditionNode[] }).children };
    }
    if (from === "NOT") {
      return { op: to, children: [(node as { child: ConditionNode }).child] };
    }
    return { op: to, children: [node] }; // was a leaf — keep it as the first child
  }

  // to NOT
  if (from === "AND" || from === "OR") {
    const children = (node as { children: ConditionNode[] }).children;
    return { op: "NOT", child: children[0] ?? defaultLeaf() };
  }
  return { op: "NOT", child: node };
}

// --- leaf editor -------------------------------------------------------

function LeafEditor({
  leaf,
  onChange,
}: {
  leaf: LeafCondition;
  onChange: (next: LeafCondition) => void;
}) {
  const kind = fieldKind(leaf.field);
  const operators = OPERATORS_BY_KIND[kind];
  const enumOptions = ENUM_OPTIONS[leaf.field];

  function setField(field: UserProfileField) {
    const nextKind = fieldKind(field);
    const operator = OPERATORS_BY_KIND[nextKind].includes(leaf.operator)
      ? leaf.operator
      : OPERATORS_BY_KIND[nextKind][0];
    onChange(coerceLeafValue({ field, operator, value: leaf.value }));
  }

  function setOperator(operator: Operator) {
    onChange(coerceLeafValue({ ...leaf, operator }));
  }

  const arrayValue = Array.isArray(leaf.value) ? (leaf.value as string[]) : [];

  return (
    <div className="leaf">
      <select
        aria-label="Field"
        value={leaf.field}
        onChange={(e) => setField(e.target.value as UserProfileField)}
      >
        {PROFILE_FIELDS.map((f) => (
          <option key={f} value={f}>
            {FIELD_LABELS[f]}
          </option>
        ))}
      </select>

      <select
        aria-label="Operator"
        value={leaf.operator}
        onChange={(e) => setOperator(e.target.value as Operator)}
      >
        {operators.map((op) => (
          <option key={op} value={op}>
            {OPERATOR_LABELS[op]}
          </option>
        ))}
      </select>

      {!operatorNeedsValue(leaf.operator) ? (
        <span className="leaf-novalue">(no value)</span>
      ) : operatorNeedsNumber(leaf.operator) ? (
        <input
          aria-label="Value"
          type="number"
          value={typeof leaf.value === "number" ? leaf.value : ""}
          onChange={(e) =>
            onChange({ ...leaf, value: e.target.value === "" ? 0 : Number(e.target.value) })
          }
        />
      ) : operatorNeedsArray(leaf.operator) ? (
        enumOptions ? (
          <div className="leaf-checks">
            {enumOptions.map((opt) => {
              const checked = arrayValue.includes(opt.value);
              return (
                <label key={opt.value} className="check">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(e) =>
                      onChange({
                        ...leaf,
                        value: e.target.checked
                          ? [...arrayValue, opt.value]
                          : arrayValue.filter((v) => v !== opt.value),
                      })
                    }
                  />
                  {opt.label}
                </label>
              );
            })}
          </div>
        ) : (
          <input
            aria-label="Value"
            type="text"
            placeholder="comma,separated,values"
            value={arrayValue.join(",")}
            onChange={(e) =>
              onChange({
                ...leaf,
                value: e.target.value
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean),
              })
            }
          />
        )
      ) : kind === "boolean" ? (
        <select
          aria-label="Value"
          value={
            leaf.value === true ? "true" : leaf.value === false ? "false" : ""
          }
          onChange={(e) =>
            onChange({
              ...leaf,
              value: e.target.value === "" ? undefined : e.target.value === "true",
            })
          }
        >
          <option value="">— choose —</option>
          <option value="true">Yes (true)</option>
          <option value="false">No (false)</option>
        </select>
      ) : enumOptions ? (
        <select
          aria-label="Value"
          value={typeof leaf.value === "string" ? leaf.value : ""}
          onChange={(e) => onChange({ ...leaf, value: e.target.value })}
        >
          <option value="">— choose —</option>
          {enumOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          aria-label="Value"
          type="text"
          value={typeof leaf.value === "string" ? leaf.value : ""}
          onChange={(e) => onChange({ ...leaf, value: e.target.value })}
        />
      )}
    </div>
  );
}

// --- recursive builder ------------------------------------------------

interface ConditionBuilderProps {
  node: ConditionNode;
  onChange: (next: ConditionNode) => void;
  onRemove?: () => void;
}

export function ConditionBuilder({
  node,
  onChange,
  onRemove,
}: ConditionBuilderProps) {
  const kind = nodeKind(node);

  return (
    <div className={`cond cond-${kind === "leaf" ? "leaf" : "group"}`}>
      <div className="cond-bar">
        <select
          aria-label="Condition type"
          value={kind}
          onChange={(e) => onChange(convert(node, e.target.value as NodeKind))}
        >
          <option value="leaf">Leaf condition</option>
          <option value="AND">ALL of (AND)</option>
          <option value="OR">ANY of (OR)</option>
          <option value="NOT">NOT</option>
        </select>
        {onRemove ? (
          <button type="button" className="cond-remove" onClick={onRemove}>
            Remove
          </button>
        ) : null}
      </div>

      {kind === "leaf" ? (
        <LeafEditor leaf={node as LeafCondition} onChange={onChange} />
      ) : kind === "NOT" ? (
        <div className="cond-children">
          <ConditionBuilder
            node={(node as { child: ConditionNode }).child}
            onChange={(child) => onChange({ op: "NOT", child })}
          />
        </div>
      ) : (
        <GroupChildren
          op={kind as "AND" | "OR"}
          items={(node as { children: ConditionNode[] }).children}
          onChange={onChange}
        />
      )}
    </div>
  );
}

function GroupChildren({
  op,
  items,
  onChange,
}: {
  op: "AND" | "OR";
  items: ConditionNode[];
  onChange: (next: ConditionNode) => void;
}) {
  const replaceAt = (index: number, child: ConditionNode) =>
    onChange({ op, children: items.map((c, i) => (i === index ? child : c)) });
  const removeAt = (index: number) =>
    onChange({ op, children: items.filter((_, i) => i !== index) });
  const add = (child: ConditionNode) =>
    onChange({ op, children: [...items, child] });

  return (
    <div className="cond-children">
      {items.length === 0 ? (
        <p className="cond-empty">
          Empty {op} group — add at least one condition (the backend rejects
          empty groups).
        </p>
      ) : null}
      {items.map((child, index) => (
        <ConditionBuilder
          key={index}
          node={child}
          onChange={(next) => replaceAt(index, next)}
          onRemove={() => removeAt(index)}
        />
      ))}
      <div className="cond-add">
        <button type="button" onClick={() => add(defaultLeaf())}>
          + Condition
        </button>
        <button
          type="button"
          onClick={() => add({ op: "AND", children: [defaultLeaf()] })}
        >
          + Group
        </button>
      </div>
    </div>
  );
}
