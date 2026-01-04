import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    CheckCircle2,
    Circle,
    XCircle,
    Calendar as CalendarIcon,
    Activity,
    Layers,
    Tag,
    ChevronLeft,
    ChevronRight,
    RefreshCw,
    Search
} from 'lucide-react';

const ExecutionManager = ({ token, apiKey }) => {
    const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
    const [dayData, setDayData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');

    const api = axios.create({
        baseURL: import.meta.env.VITE_API_BASE_URL || '/api/lbs',
        headers: {
            'Authorization': token ? `Bearer ${token}` : undefined,
            'X-API-Key': !token ? apiKey : undefined
        }
    });

    const fetchDayData = async (dateStr) => {
        setLoading(true);
        try {
            const resp = await api.get(`/calculate/${dateStr}`);
            setDayData(resp.data);
        } catch (err) {
            console.error("Error fetching execution data:", err);
            alert("Error fetching data: " + (err.response?.data?.detail || err.message));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (token || apiKey) fetchDayData(selectedDate);
    }, [selectedDate, token, apiKey]);

    const handleToggleStatus = async (taskId, newStatus) => {
        setLoading(true);
        try {
            await api.post(`/tasks/${taskId}/complete`, {
                target_date: selectedDate,
                status: newStatus
            });
            await fetchDayData(selectedDate);
        } catch (err) {
            alert("Error updating status: " + (err.response?.data?.detail || err.message));
        } finally {
            setLoading(false);
        }
    };

    const changeDate = (offset) => {
        const d = new Date(selectedDate);
        d.setDate(d.getDate() + offset);
        setSelectedDate(d.toISOString().split('T')[0]);
    };

    const getLevelColor = (level) => {
        switch (level) {
            case 'SAFE': return '#10b981';
            case 'WARNING': return '#f59e0b';
            case 'DANGER': return '#ef4444';
            case 'CRITICAL': return '#8b5cf6';
            default: return '#3b82f6';
        }
    };

    const filteredTasks = dayData?.tasks.filter(t =>
        t.task_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        t.context.toLowerCase().includes(searchQuery.toLowerCase())
    ) || [];

    const stats = dayData ? [
        { label: 'Total Load', value: dayData.adjusted_load.toFixed(2), icon: Activity, color: getLevelColor(dayData.level) },
        { label: 'Task Count', value: dayData.task_count, icon: Layers, color: '#a855f7' },
        { label: 'Contexts', value: dayData.unique_contexts, icon: Tag, color: '#10b981' },
    ] : [];

    return (
        <div className="flex flex-col gap-10">
            {/* Header & Date Selector */}
            <header className="flex justify-between items-end">
                <div>
                    <h2 className="text-3xl font-bold mb-1">Execution Log</h2>
                    <p className="text-slate-400">Manage daily task completion and execution status.</p>
                </div>

                <div className="flex items-center gap-4 bg-white/5 p-2 rounded-2xl border border-white/5 shadow-xl">
                    <button onClick={() => changeDate(-1)} className="p-3 hover:bg-white/5 rounded-xl text-slate-400 hover:text-white transition-all"><ChevronLeft size={20} /></button>
                    <div className="flex items-center gap-3 px-4 min-w-[200px] justify-center">
                        <CalendarIcon size={18} className="text-blue-400" />
                        <span className="font-bold text-lg">
                            {new Date(selectedDate).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                        </span>
                    </div>
                    <button onClick={() => changeDate(1)} className="p-3 hover:bg-white/5 rounded-xl text-slate-400 hover:text-white transition-all"><ChevronRight size={20} /></button>
                </div>
            </header>

            {/* Daily Stats KPI */}
            <div className="grid grid-cols-3 gap-6">
                {stats.map((s, i) => (
                    <div key={i} className="glass-card p-6 flex flex-col gap-2 relative overflow-hidden group">
                        <div className="flex items-center gap-3 text-slate-500 text-[10px] uppercase font-bold tracking-widest">
                            <s.icon size={14} style={{ color: s.color }} /> {s.label}
                        </div>
                        <div className="text-3xl font-bold" style={{ color: i === 0 ? s.color : 'white' }}>{s.value}</div>
                        <div className="absolute top-0 right-0 p-8 opacity-[0.03] group-hover:opacity-[0.07] transition-all">
                            <s.icon size={80} />
                        </div>
                    </div>
                ))}
            </div>

            {/* Task List Section */}
            <div className="flex flex-col gap-6">
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-4 flex-grow max-w-md">
                        <div className="relative w-full">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                            <input
                                className="w-full bg-white/5 border-white/5 hover:border-white/10 transition-all pl-12 h-12 rounded-2xl text-sm"
                                placeholder="Search today's tasks..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                            />
                        </div>
                        <button
                            onClick={() => fetchDayData(selectedDate)}
                            className={`p-3 glass-card text-slate-400 hover:text-white transition-all ${loading ? 'animate-spin' : ''}`}
                        >
                            <RefreshCw size={20} />
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 gap-3">
                    {loading && !dayData ? (
                        <div className="py-20 text-center text-slate-500 animate-pulse uppercase tracking-widest text-xs font-bold">Loading schedule...</div>
                    ) : filteredTasks.length === 0 ? (
                        <div className="py-20 text-center glass-card border-dashed border-white/5 text-slate-500">
                            {searchQuery ? "No matching tasks found." : "No tasks scheduled for this date."}
                        </div>
                    ) : (
                        filteredTasks.map((task, idx) => {
                            const isDone = task.status === 'done';
                            const isSkipped = task.status === 'skipped';
                            return (
                                <div key={idx} className={`glass-card p-5 flex justify-between items-center bg-white/5 transition-all border ${isDone ? 'border-emerald-500/20 bg-emerald-500/5' : isSkipped ? 'border-amber-500/20 bg-amber-500/5' : 'border-transparent hover:bg-white/10'}`}>
                                    <div className="flex items-center gap-6">
                                        <div className={`w-12 h-12 rounded-2xl flex items-center justify-center font-bold font-mono text-sm ${isDone ? 'bg-emerald-500/10 text-emerald-400' : isSkipped ? 'bg-amber-500/10 text-amber-400' : 'bg-blue-500/10 text-blue-400'}`}>
                                            {task.load.toFixed(1)}
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className={`text-lg font-bold ${isDone ? 'text-emerald-400/80 line-through' : 'text-slate-200'}`}>
                                                {task.task_name}
                                            </span>
                                            <div className="flex items-center gap-3">
                                                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-widest px-2 py-0.5 rounded bg-white/5 border border-white/5">
                                                    {task.context}
                                                </span>
                                                {task.status !== 'todo' && (
                                                    <span className={`text-[8px] px-2 py-0.5 rounded-full font-bold uppercase ${isDone ? 'bg-emerald-500/20 text-emerald-400' : isSkipped ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'}`}>
                                                        {task.status}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-3">
                                        <button
                                            onClick={() => handleToggleStatus(task.task_id, isDone ? 'todo' : 'done')}
                                            disabled={loading}
                                            className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${isDone ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/20' : 'bg-white/5 text-slate-500 hover:text-emerald-400 hover:bg-emerald-500/10'}`}
                                            title={isDone ? "Mark as Todo" : "Mark as Done"}
                                        >
                                            <CheckCircle2 size={22} />
                                        </button>
                                        <button
                                            onClick={() => handleToggleStatus(task.task_id, isSkipped ? 'todo' : 'skipped')}
                                            disabled={loading}
                                            className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${isSkipped ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/20' : 'bg-white/5 text-slate-500 hover:text-amber-400 hover:bg-amber-500/10'}`}
                                            title={isSkipped ? "Restore" : "Skip Task"}
                                        >
                                            <XCircle size={22} />
                                        </button>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
};

export default ExecutionManager;
