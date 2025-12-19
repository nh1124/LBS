import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Plus, Edit2, Trash2, Calendar, CheckCircle2, XCircle,
    Menu, Filter, Search, Tag, Clock, ChevronDown
} from 'lucide-react';

const TaskCard = ({ task, onEdit, onDelete }) => {
    const getRuleLabel = (type) => {
        switch (type) {
            case 'WEEKLY': return 'Weekly';
            case 'ONCE': return 'One-time';
            case 'EVERY_N_DAYS': return `Every ${task.interval_days} days`;
            case 'MONTHLY_DAY': return `Day ${task.month_day} monthly`;
            default: return type;
        }
    };

    return (
        <div className="glass-card p-5 flex items-center gap-6 group hover:border-white/10 transition-all">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold ${task.active ? 'bg-blue-500/10 text-blue-400' : 'bg-slate-800 text-slate-500'}`}>
                {task.base_load_score.toFixed(1)}
            </div>

            <div className="flex-grow">
                <div className="flex items-center gap-3 mb-1">
                    <h4 className={`font-bold ${!task.active && 'text-slate-500 line-through'}`}>{task.task_name}</h4>
                    <span className="px-2 py-0.5 rounded-full bg-white/5 border border-white/5 text-[10px] text-slate-400 uppercase tracking-widest font-bold">{task.context}</span>
                </div>
                <div className="flex gap-4 text-xs text-slate-500">
                    <div className="flex items-center gap-1"><Clock size={12} /> {getRuleLabel(task.rule_type)}</div>
                    {task.due_date && <div className="flex items-center gap-1"><Calendar size={12} /> {task.due_date}</div>}
                </div>
            </div>

            <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-all">
                <button onClick={() => onEdit(task)} className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white"><Edit2 size={16} /></button>
                <button onClick={() => onDelete(task.task_id)} className="p-2 hover:bg-red-500/10 rounded-lg text-slate-400 hover:text-red-400"><Trash2 size={16} /></button>
            </div>
        </div>
    );
};

const TaskManager = ({ apiKey, userId }) => {
    const [tasks, setTasks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingTask, setEditingTask] = useState(null);

    // Form State
    const [formData, setFormData] = useState({
        task_name: '', context: 'work', base_load_score: 2.0, rule_type: 'WEEKLY',
        mon: true, tue: true, wed: true, thu: true, fri: true, sat: false, sun: false
    });

    const api = axios.create({
        baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8300/api/lbs',
        headers: { 'X-API-Key': apiKey, 'X-User-ID': userId }
    });

    const fetchTasks = async () => {
        try {
            const resp = await api.get('/tasks');
            setTasks(resp.data);
            setLoading(false);
        } catch (err) {
            console.error(err);
            setLoading(false);
        }
    };

    useEffect(() => { if (apiKey || userId) fetchTasks(); }, [apiKey, userId]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            if (editingTask) {
                await api.put(`/tasks/${editingTask.task_id}`, formData);
            } else {
                await api.post('/tasks', formData);
            }
            setIsModalOpen(false);
            setEditingTask(null);
            fetchTasks();
        } catch (err) {
            alert("Error saving task: " + err.message);
        }
    };

    const handleEdit = (task) => {
        setEditingTask(task);
        setFormData({ ...task });
        setIsModalOpen(true);
    };

    const handleDelete = async (id) => {
        if (window.confirm("Delete this task?")) {
            await api.delete(`/tasks/${id}`);
            fetchTasks();
        }
    };

    return (
        <div className="flex flex-col gap-8">
            <header className="flex justify-between items-center">
                <div>
                    <h2 className="text-3xl font-bold mb-1">Task Inventory</h2>
                    <p className="text-slate-400">Manage master tasks and scheduling rules.</p>
                </div>
                <button
                    onClick={() => { setEditingTask(null); setIsModalOpen(true); }}
                    className="primary flex items-center gap-2"
                >
                    <Plus size={20} /> Create Task
                </button>
            </header>

            <div className="flex gap-4 mb-4">
                <div className="flex-grow relative">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                    <input className="w-full pl-12 bg-white/5 border-white/5" placeholder="Search tasks or contexts..." />
                </div>
                <button className="p-2 px-4 glass-card flex items-center gap-2 text-sm text-slate-400">
                    <Filter size={16} /> Filters
                </button>
            </div>

            <div className="flex flex-col gap-3">
                {loading ? <div className="p-20 text-center text-slate-500">Loading tasks...</div> :
                    tasks.length === 0 ? <div className="p-20 text-center text-slate-500 glass-card">No tasks found. Create one to get started!</div> :
                        tasks.map(t => <TaskCard key={t.task_id} task={t} onEdit={handleEdit} onDelete={handleDelete} />)
                }
            </div>

            {/* Task Modal */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-6">
                    <form onSubmit={handleSubmit} className="glass-card p-10 w-full max-w-xl flex flex-col gap-6 overflow-y-auto max-h-[90vh]">
                        <h3 className="text-2xl font-bold">{editingTask ? 'Edit Task' : 'New LBS Task'}</h3>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="col-span-2">
                                <label className="block text-xs text-slate-500 uppercase font-bold tracking-widest mb-2">Task Name</label>
                                <input
                                    required className="w-full"
                                    value={formData.task_name}
                                    onChange={e => setFormData({ ...formData, task_name: e.target.value })}
                                />
                            </div>
                            <div className="">
                                <label className="block text-xs text-slate-500 uppercase font-bold tracking-widest mb-2">Context (Spoke)</label>
                                <input
                                    required className="w-full"
                                    value={formData.context}
                                    onChange={e => setFormData({ ...formData, context: e.target.value.toLowerCase() })}
                                />
                            </div>
                            <div className="">
                                <label className="block text-xs text-slate-500 uppercase font-bold tracking-widest mb-2">Base Load Score (0-10)</label>
                                <input
                                    type="number" step="0.5" min="0" max="10" required className="w-full"
                                    value={formData.base_load_score}
                                    onChange={e => setFormData({ ...formData, base_load_score: parseFloat(e.target.value) })}
                                />
                            </div>

                            <div className="col-span-2">
                                <label className="block text-xs text-slate-500 uppercase font-bold tracking-widest mb-2">Recurrence Rule</label>
                                <select
                                    className="w-full"
                                    value={formData.rule_type}
                                    onChange={e => setFormData({ ...formData, rule_type: e.target.value })}
                                >
                                    <option value="WEEKLY">Weekly (specific days)</option>
                                    <option value="ONCE">One-time</option>
                                    <option value="EVERY_N_DAYS">Interval (Every N days)</option>
                                    <option value="MONTHLY_DAY">Monthly (Specific day)</option>
                                </select>
                            </div>

                            {formData.rule_type === 'WEEKLY' && (
                                <div className="col-span-2 flex justify-between gap-1 mt-2">
                                    {['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'].map(day => (
                                        <button
                                            key={day} type="button"
                                            onClick={() => setFormData({ ...formData, [day]: !formData[day] })}
                                            className={`w-10 h-10 rounded-lg text-[10px] font-bold uppercase transition-all ${formData[day] ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/20' : 'bg-white/5 text-slate-500'}`}
                                        >
                                            {day.slice(0, 3)}
                                        </button>
                                    ))}
                                </div>
                            )}

                            {formData.rule_type === 'ONCE' && (
                                <div className="col-span-2">
                                    <label className="block text-xs text-slate-500 uppercase font-bold tracking-widest mb-2">Due Date</label>
                                    <input
                                        type="date" required className="w-full"
                                        value={formData.due_date || ''}
                                        onChange={e => setFormData({ ...formData, due_date: e.target.value })}
                                    />
                                </div>
                            )}
                        </div>

                        <div className="flex gap-4 pt-4 border-t border-white/5">
                            <button type="button" onClick={() => setIsModalOpen(false)} className="px-6 py-2 text-slate-400 hover:text-white">Cancel</button>
                            <button type="submit" className="primary flex-grow">Save Task Rule</button>
                        </div>
                    </form>
                </div>
            )}
        </div>
    );
};

export default TaskManager;
