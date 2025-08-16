import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface SortableQuestionProps {
  question: any;
  index: number;
  isCollapsed: boolean;
  onToggle: () => void;
  onEdit: (question: any) => void;
}

export const SortableQuestion: React.FC<SortableQuestionProps> = ({
  question,
  index,
  isCollapsed,
  onToggle,
  onEdit
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: question.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div 
      ref={setNodeRef} 
      style={style}
      className={`question-item ${isCollapsed ? 'collapsed' : 'expanded'} ${isDragging ? 'dragging' : ''}`}
    >
      <div className="question-header">
        <div 
          className="drag-handle"
          {...attributes}
          {...listeners}
          title="Drag to reorder"
        >
          ⋮⋮
        </div>
        <div 
          className="question-header-content" 
          onClick={onToggle}
        >
          <span className="toggle-icon">{isCollapsed ? '▶' : '▼'}</span>
          <span className="question-summary">
            {question.id}: {question.text.substring(0, 50)}{question.text.length > 50 ? '...' : ''}
          </span>
        </div>
        <button 
          className="btn btn-small btn-edit"
          onClick={(e) => {
            e.stopPropagation();
            onEdit(question);
          }}
          title="Edit this question"
        >
          Edit
        </button>
      </div>
      {!isCollapsed && (
        <div className="question-details">
          <p><strong>Text:</strong> {question.text}</p>
          <p><strong>Cluster:</strong> {question.cluster_name}</p>
          <p><strong>Type:</strong> {question.question_type}</p>
          <p><strong>Position:</strong> {question.position_in_cluster}</p>
          {question.hint && <p><strong>Hint:</strong> {question.hint}</p>}
          {question.info && <p><strong>Info:</strong> {question.info}</p>}
          {question.options && question.options.length > 0 && (
            <div>
              <strong>Options:</strong>
              <ul>
                {question.options.map((opt: any, idx: number) => (
                  <li key={idx}>{opt.code} → {opt.label}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};