import React from 'react';
import { X, Activity, Layers, Tag, Info } from 'lucide-react';

const DayDetailModal = ({ isOpen, onClose, data }) => {
    if (!isOpen || !data) return null;

    const getLevelColor = (level) => {
        switch (level) {
            case 'SAFE': return '#10b981';
            case 'WARNING': return '#f59e0b';
            case 'DANGER': return '#ef4444';
            case 'CRITICAL': return '#8b5cf6';
            default: return '#3b82f6';
        }
    };

    const levelColor = getLevelColor(data.level);

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-[60] p-6">
            <div className="glass-card p-0 w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
                {/* Header */}
                <div className="p-6 border-b border-white/5 flex justify-between items-center bg-white/5">
                    <div>
                        <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mb-1">Detailed Log</div>
                        <h3 className="text-2xl font-bold">
                            {new Date(data.date).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                        </h3>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-xl transition-all text-slate-400 hover:text-white">
                        <X size={24} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-8 overflow-y-auto flex flex-col gap-8">
                    {/* Summary Cards */}
                    <div className="grid grid-cols-3 gap-4">
                        <div className="glass-card p-4 bg-white/5">
                            <div className="flex items-center gap-2 text-slate-500 text-[10px] uppercase font-bold tracking-widest mb-2">
                                <Activity size={12} className="text-blue-400" /> Total Load
                            </div>
                            <div className="text-2xl font-bold" style={{ color: levelColor }}>{data.adjusted_load.toFixed(2)}</div>
                        </div>
                        <div className="glass-card p-4 bg-white/5">
                            <div className="flex items-center gap-2 text-slate-500 text-[10px] uppercase font-bold tracking-widest mb-2">
                                <Layers size={12} className="text-purple-400" /> Tasks
                            </div>
                            <div className="text-2xl font-bold text-white">{data.task_count}</div>
                        </div>
                        <div className="glass-card p-4 bg-white/5">
                            <div className="flex items-center gap-2 text-slate-500 text-[10px] uppercase font-bold tracking-widest mb-2">
                                <Tag size={12} className="text-emerald-400" /> Contexts
                            </div>
                            <div className="text-2xl font-bold text-white">{data.unique_contexts}</div>
                        </div>
                    </div>

                    {/* Breakdown Section */}
                    <div className="flex flex-col gap-4">
                        <h4 className="text-xs text-slate-500 uppercase font-bold tracking-widest flex items-center gap-2">
                            <Info size={14} /> Load Calculation Breakdown
                        </h4>
                        <div className="glass-card p-5 border-l-4" style={{ borderColor: levelColor }}>
                            <div className="flex flex-col gap-3 text-sm">
                                <div className="flex justify-between items-center text-slate-300">
                                    <span>Base Task Scores (Sum)</span>
                                    <span className="font-mono">{data.base_load?.toFixed(2) || "0.00"}</span>
                                </div>
                                <div className="flex justify-between items-center text-slate-400 text-xs italic">
                                    <span>+ Task Count Multiplier (α * N^β)</span>
                                    <span className="font-mono">{data.count_penalty?.toFixed(2) || "0.00"}</span>
                                </div>
                                <div className="flex justify-between items-center text-slate-400 text-xs italic">
                                    <span>+ Context Switch Cost (Cost * (C-1))</span>
                                    <span className="font-mono">{data.context_penalty?.toFixed(2) || "0.00"}</span>
                                </div>
                                <div className="h-px bg-white/5 my-1" />
                                <div className="flex justify-between items-center text-lg font-bold">
                                    <span className="text-white">Final Adjusted Load</span>
                                    <span style={{ color: levelColor }}>{data.adjusted_load.toFixed(2)}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Individual Tasks */}
                    <div className="flex flex-col gap-4">
                        <h4 className="text-xs text-slate-500 uppercase font-bold tracking-widest">Scheduled Tasks</h4>
                        <div className="flex flex-col gap-2">
                            {data.tasks.map((task, idx) => (
                                <div key={idx} className="glass-card p-4 flex justify-between items-center bg-white/5 hover:bg-white/10 transition-all border border-transparent hover:border-white/5">
                                    <div className="flex flex-col">
                                        <span className="font-bold text-slate-200">{task.task_name}</span>
                                        <span className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">{task.context}</span>
                                    </div>
                                    <div className="p-2 px-3 bg-white/5 rounded-lg font-mono text-sm text-blue-400">
                                        {task.load.toFixed(1)}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DayDetailModal;
