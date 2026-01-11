import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon, Info } from 'lucide-react';
import DayDetailModal from './DayDetailModal';

const LBSCalendar = ({ token, apiKey }) => {
    const [currentDate, setCurrentDate] = useState(new Date());
    const [heatmapData, setHeatmapData] = useState({});
    const [loading, setLoading] = useState(false);
    const [selectedDayData, setSelectedDayData] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [includeCompleted, setIncludeCompleted] = useState(true);

    const api = axios.create({
        baseURL: import.meta.env.VITE_API_BASE_URL || '/api/lbs',
        headers: {
            'Authorization': token ? `Bearer ${token}` : undefined,
            'X-API-Key': !token ? apiKey : undefined
        }
    });

    const fetchMonthData = async () => {
        setLoading(true);
        try {
            const year = currentDate.getFullYear();
            const month = currentDate.getMonth();
            const start = new Date(year, month, 1).toISOString().split('T')[0];
            const end = new Date(year, month + 1, 0).toISOString().split('T')[0];

            const statusParams = `status=todo&status=skipped${includeCompleted ? '&status=done' : ''}`;
            const resp = await api.get(`/heatmap?start=${start}&end=${end}&${statusParams}`);
            const dataMap = {};
            resp.data.forEach(day => {
                dataMap[day.date] = day;
            });
            setHeatmapData(dataMap);
        } catch (err) {
            console.error("Error fetching calendar data:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (token || apiKey) fetchMonthData();
    }, [currentDate, token, apiKey, includeCompleted]);

    const daysInMonth = (y, m) => new Date(y, m + 1, 0).getDate();
    const firstDayOfMonth = (y, m) => new Date(y, m, 1).getDay();

    const handlePrevMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
    const handleNextMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));

    const handleDayClick = async (dateStr) => {
        try {
            const statusParams = `status=todo&status=skipped&status=done`;
            const resp = await api.get(`/calculate/${dateStr}?${statusParams}`);
            setSelectedDayData(resp.data);
            setIsModalOpen(true);
        } catch (err) {
            alert("Error fetching day details: " + err.message);
        }
    };

    const handleToggleTaskStatus = async (taskId, newStatus) => {
        if (!selectedDayData) return;
        setLoading(true);
        try {
            const dateStr = selectedDayData.date;
            await api.post(`/tasks/${taskId}/complete`, {
                target_date: dateStr,
                status: newStatus
            });

            // Refresh day details
            const statusParams = `status=todo&status=skipped&status=done`;
            const dayResp = await api.get(`/calculate/${dateStr}?${statusParams}`);
            setSelectedDayData(dayResp.data);

            // Refresh calendar heatmap
            fetchMonthData();
        } catch (err) {
            alert("Error updating task status: " + (err.response?.data?.detail || err.message));
        } finally {
            setLoading(false);
        }
    };

    const getLevelColor = (level) => {
        switch (level) {
            case 'SAFE': return '#10b981';
            case 'WARNING': return '#f59e0b';
            case 'DANGER': return '#ef4444';
            case 'CRITICAL': return '#8b5cf6';
            default: return 'transparent';
        }
    };

    const renderCalendar = () => {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth();
        const totalDays = daysInMonth(year, month);
        const startOffset = firstDayOfMonth(year, month);
        const days = [];

        // Header days
        ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].forEach(d => {
            days.push(<div key={`h-${d}`} className="text-center text-[10px] uppercase font-bold text-slate-500 pb-4">{d}</div>);
        });

        // Padding for start of month
        for (let i = 0; i < startOffset; i++) {
            days.push(<div key={`p-${i}`} className="h-24" />);
        }

        // Monthly days
        for (let d = 1; d <= totalDays; d++) {
            const dateObj = new Date(year, month, d);
            // Adjust for timezone offset to get YYYY-MM-DD
            const dateStr = new Date(dateObj.getTime() - (dateObj.getTimezoneOffset() * 60000)).toISOString().split('T')[0];
            const dayData = heatmapData[dateStr];
            const isToday = new Date().toISOString().split('T')[0] === dateStr;

            days.push(
                <div
                    key={dateStr}
                    onClick={() => handleDayClick(dateStr)}
                    className={`h-24 glass-card p-2 flex flex-col justify-between transition-all hover:scale-105 hover:z-10 cursor-pointer border ${isToday ? 'border-blue-500/50 outline outline-1 outline-blue-500/20' : 'border-transparent'}`}
                    style={{ background: dayData ? `${getLevelColor(dayData.level)}10` : 'rgba(255,255,255,0.02)' }}
                >
                    <div className="flex justify-between items-start">
                        <span className={`text-xs font-bold ${isToday ? 'text-blue-400' : 'text-slate-400'}`}>{d}</span>
                        {dayData && <div className="w-2 h-2 rounded-full" style={{ backgroundColor: getLevelColor(dayData.level) }} />}
                    </div>

                    {dayData ? (
                        <div className="flex flex-col items-end">
                            <span className="text-lg font-bold" style={{ color: getLevelColor(dayData.level) }}>{dayData.adjusted_load.toFixed(1)}</span>
                            <span className="text-[8px] text-slate-500 uppercase tracking-tighter">Tasks: {dayData.task_count}</span>
                        </div>
                    ) : (
                        <div className="flex flex-col items-end opacity-20">
                            <span className="text-lg font-bold">0.0</span>
                        </div>
                    )}
                </div>
            );
        }

        return days;
    };

    return (
        <div className="flex flex-col gap-8">
            <header className="flex justify-between items-center">
                <div>
                    <h2 className="text-3xl font-bold mb-1">LBS Calendar</h2>
                    <p className="text-slate-400">Monthly schedule and predictive load mapping.</p>
                </div>

                <div className="flex items-center gap-4 bg-white/5 p-2 rounded-xl border border-white/5">
                    <button
                        onClick={() => setIncludeCompleted(!includeCompleted)}
                        className={`px-4 py-2 rounded-lg text-xs font-bold uppercase transition-all ${includeCompleted ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'bg-white/5 text-slate-500 border border-transparent'}`}
                    >
                        {includeCompleted ? 'Showing Completed' : 'Hiding Completed'}
                    </button>
                    <div className="w-px h-6 bg-white/5" />
                    <div className="flex items-center gap-4">
                        <button onClick={handlePrevMonth} className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-all"><ChevronLeft size={20} /></button>
                        <div className="min-w-[140px] text-center font-bold text-lg">
                            {currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
                        </div>
                        <button onClick={handleNextMonth} className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-white transition-all"><ChevronRight size={20} /></button>
                    </div>
                </div>
            </header>

            <div className={`grid grid-cols-7 gap-3 ${loading ? 'opacity-50 grayscale' : ''}`}>
                {renderCalendar()}
            </div>

            {
                loading && (
                    <div className="fixed bottom-10 right-10 glass-card p-4 flex items-center gap-3 text-blue-400 animate-pulse border-blue-500/20 shadow-lg shadow-blue-500/5">
                        <CalendarIcon size={18} />
                        <span className="text-xs font-bold uppercase tracking-widest">Updating Calendar...</span>
                    </div>
                )
            }

            <DayDetailModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                data={selectedDayData}
                onToggleTaskStatus={handleToggleTaskStatus}
                isUpdating={loading}
            />
        </div >
    );
};

export default LBSCalendar;
