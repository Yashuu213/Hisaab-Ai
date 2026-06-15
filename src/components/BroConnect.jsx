import React, { useState, useContext, useEffect } from 'react';
import { TransactionContext } from '../context/TransactionContext';
import { Users, Send, MessageCircle, Bell, X, User as UserIcon, Zap, Ghost } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const BroConnect = () => {
    const { appUsers, nudges, markNudgeRead, sendMessage, getMessages, sendNudge, user } = useContext(TransactionContext);
    const [selectedFriend, setSelectedFriend] = useState(null);
    const [chatMessages, setChatMessages] = useState([]);
    const [newMessage, setNewMessage] = useState('');
    const [showNudges, setShowNudges] = useState(false);
    const [search, setSearch] = useState('');

    const fetchingRef = React.useRef(false);
    const scrollRef = React.useRef(null);
    const friendRef = React.useRef(null);

    // Update friend ref whenever selectedFriend changes
    useEffect(() => {
        friendRef.current = selectedFriend;
        if (selectedFriend) {
            setChatMessages([]);
            scrollToBottom();
        }
    }, [selectedFriend]);

    // Scroll to bottom helper
    const scrollToBottom = () => {
        setTimeout(() => {
            if (scrollRef.current) {
                scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
            }
        }, 100);
    };

    // Poll for new messages when chat is open
    useEffect(() => {
        let timeoutId;
        
        const poll = async () => {
            // Use ref to check if we should still be polling for THIS friend
            if (!friendRef.current || fetchingRef.current) return;
            
            fetchingRef.current = true;
            try {
                const msgs = await getMessages(friendRef.current.id);
                if (msgs && msgs.length > 0) {
                    setChatMessages(prev => {
                        const existingIds = new Set(prev.map(m => m.id));
                        const newMsgs = msgs.filter(m => !existingIds.has(m.id));
                        if (newMsgs.length > 0) scrollToBottom();
                        return [...prev, ...newMsgs];
                    });
                }
            } catch (err) {
                console.error("Chat fetch error", err);
            } finally {
                fetchingRef.current = false;
                if (friendRef.current) {
                    timeoutId = setTimeout(poll, 2500); // Slightly faster poll
                }
            }
        };

        if (selectedFriend) {
            poll();
        }

        return () => {
            if (timeoutId) clearTimeout(timeoutId);
            fetchingRef.current = false;
        };
    }, [selectedFriend]);

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!newMessage.trim() || !selectedFriend) return;

        const data = await sendMessage(selectedFriend.id, newMessage);
        if (data) {
            setChatMessages(prev => [...prev, {
                id: data.id,
                sender_id: 'me',
                content: newMessage,
                date: data.date
            }]);
            setNewMessage('');
            scrollToBottom();
        }
    };

    const filteredUsers = appUsers.filter(u => 
        u.username.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="space-y-6">
            {/* Header with Nudge Bell */}
            <div className="flex items-center justify-between bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-100 dark:border-slate-800 shadow-sm">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white">
                        <Users size={20} />
                    </div>
                    <div>
                        <h2 className="text-sm font-bold text-slate-800 dark:text-white">Bro-Connect</h2>
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Social Financial Network</p>
                    </div>
                </div>

                <div className="relative">
                    <button 
                        onClick={() => setShowNudges(!showNudges)}
                        className={`p-2.5 rounded-xl transition-all ${nudges.length > 0 ? 'bg-rose-50 text-rose-500 animate-pulse' : 'bg-slate-50 text-slate-400'}`}
                    >
                        <Bell size={20} />
                        {nudges.length > 0 && (
                            <span className="absolute -top-1 -right-1 w-5 h-5 bg-rose-600 text-white text-[10px] font-bold rounded-full flex items-center justify-center border-2 border-white dark:border-slate-900">
                                {nudges.length}
                            </span>
                        )}
                    </button>

                    <AnimatePresence>
                        {showNudges && (
                            <motion.div 
                                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                                animate={{ opacity: 1, y: 0, scale: 1 }}
                                exit={{ opacity: 0, y: 10, scale: 0.95 }}
                                className="absolute right-0 mt-3 w-72 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-2xl shadow-2xl z-50 overflow-hidden"
                            >
                                <div className="p-4 border-b border-slate-50 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/20">
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Incoming Nudges</p>
                                </div>
                                <div className="max-h-80 overflow-y-auto">
                                    {nudges.length > 0 ? nudges.map(nudge => (
                                        <div key={nudge.id} className="p-4 border-b border-slate-50 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group">
                                            <div className="flex gap-3">
                                                <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-indigo-600 text-xs font-bold">
                                                    {nudge.sender_name.charAt(0)}
                                                </div>
                                                <div className="flex-1">
                                                    <p className="text-xs font-bold text-slate-700 dark:text-slate-200">
                                                        <span className="text-indigo-600">{nudge.sender_name}</span> pushed you
                                                    </p>
                                                    {nudge.amount && <p className="text-[10px] font-black text-rose-500 mt-0.5">₹{nudge.amount.toLocaleString()}</p>}
                                                    {nudge.message && <p className="text-[10px] text-slate-500 mt-1 italic">"{nudge.message}"</p>}
                                                </div>
                                                <button 
                                                    onClick={() => markNudgeRead(nudge.id)}
                                                    className="p-1 text-slate-300 hover:text-indigo-600 transition-colors"
                                                >
                                                    <X size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    )) : (
                                        <div className="p-8 text-center text-slate-400">
                                            <Zap size={24} className="mx-auto mb-2 opacity-20" />
                                            <p className="text-[10px] font-bold uppercase">No active nudges</p>
                                        </div>
                                    )}
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>

            {/* Users List */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="col-span-full mb-2">
                    <div className="relative">
                        <Users className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
                        <input 
                            type="text" 
                            placeholder="Find friends by name or email..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full pl-12 pr-4 py-4 bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-2xl text-sm font-medium focus:ring-2 focus:ring-indigo-500/20 outline-none transition-all shadow-sm"
                        />
                    </div>
                </div>

                {filteredUsers.map(appUser => (
                    <motion.div 
                        key={appUser.id}
                        layout
                        className="pro-card p-5 group hover:border-indigo-500/30 transition-all cursor-pointer relative overflow-hidden"
                        onClick={() => {
                            setSelectedFriend(appUser);
                            setChatMessages([]);
                        }}
                    >
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-500 font-bold group-hover:bg-indigo-600 group-hover:text-white transition-all">
                                {appUser.username.charAt(0).toUpperCase()}
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-slate-800 dark:text-white">{appUser.username}</h3>
                                <p className="text-[10px] text-slate-400 font-medium truncate max-w-[150px]">{appUser.email}</p>
                            </div>
                        </div>
                        
                        <div className="mt-4 flex gap-2">
                            <button className="flex-1 py-2 bg-slate-50 dark:bg-slate-800 rounded-xl text-[9px] font-black uppercase tracking-widest text-slate-500 hover:bg-indigo-50 hover:text-indigo-600 transition-all flex items-center justify-center gap-1.5">
                                <MessageCircle size={12} /> Chat
                            </button>
                            <button 
                                onClick={(e) => {
                                    e.stopPropagation();
                                    sendNudge(appUser.id, 0, "Hey, let's settle up!");
                                }}
                                className="px-3 py-2 bg-indigo-600 text-white rounded-xl text-[9px] font-black uppercase tracking-widest hover:bg-indigo-500 transition-all flex items-center justify-center"
                            >
                                <Zap size={12} />
                            </button>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Chat Modal (Ghost Chat) */}
            <AnimatePresence>
                {selectedFriend && (
                    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
                        <motion.div 
                            initial={{ opacity: 0, scale: 0.9, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.9, y: 20 }}
                            className="w-full max-w-lg bg-white dark:bg-slate-900 rounded-[2.5rem] shadow-2xl overflow-hidden flex flex-col h-[600px]"
                        >
                            {/* Chat Header */}
                            <div className="p-6 bg-slate-900 text-white flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center text-white font-bold">
                                        {selectedFriend.username.charAt(0).toUpperCase()}
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-bold">{selectedFriend.username}</h3>
                                        <div className="flex items-center gap-1.5 mt-0.5">
                                            <Ghost size={10} className="text-indigo-400" />
                                            <span className="text-[9px] font-black uppercase tracking-widest text-indigo-400">Ephemeral Ghost Chat</span>
                                        </div>
                                    </div>
                                </div>
                                <button 
                                    onClick={() => setSelectedFriend(null)}
                                    className="p-2 hover:bg-white/10 rounded-xl transition-colors"
                                >
                                    <X size={20} />
                                </button>
                            </div>

                            {/* Chat Area */}
                            <div 
                                ref={scrollRef}
                                className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50 dark:bg-slate-950/50 custom-scrollbar"
                            >
                                <div className="text-center pb-4">
                                    <span className="px-3 py-1 rounded-full bg-slate-200 dark:bg-slate-800 text-[9px] font-bold text-slate-500 uppercase tracking-tighter">
                                        Messages are deleted after they are seen.
                                    </span>
                                </div>

                                {chatMessages.map((msg, i) => (
                                    <motion.div 
                                        initial={{ opacity: 0, x: msg.sender_id === 'me' ? 10 : -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        key={i} 
                                        className={`flex ${msg.sender_id === 'me' ? 'justify-end' : 'justify-start'}`}
                                    >
                                        <div className={`max-w-[80%] p-4 rounded-2xl text-sm font-medium shadow-sm ${
                                            msg.sender_id === 'me' 
                                            ? 'bg-indigo-600 text-white rounded-tr-none' 
                                            : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded-tl-none border border-slate-100 dark:border-slate-700'
                                        }`}>
                                            {msg.content}
                                            <p className={`text-[8px] mt-1 font-bold uppercase opacity-50 ${msg.sender_id === 'me' ? 'text-right' : 'text-left'}`}>
                                                {new Date(msg.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </p>
                                        </div>
                                    </motion.div>
                                ))}
                                
                                {chatMessages.length === 0 && (
                                    <div className="h-full flex flex-col items-center justify-center text-slate-300 opacity-50">
                                        <Ghost size={48} className="mb-4" />
                                        <p className="text-xs font-bold uppercase tracking-widest text-center">Start a ghost conversation...<br/><span className="text-[10px] normal-case font-medium text-slate-400 italic">No history will be saved.</span></p>
                                    </div>
                                )}
                            </div>

                            {/* Chat Input */}
                            <form onSubmit={handleSendMessage} className="p-6 bg-white dark:bg-slate-900 border-t border-slate-100 dark:border-slate-800">
                                <div className="flex items-center gap-3 bg-slate-100 dark:bg-slate-800 p-2 rounded-2xl">
                                    <input 
                                        type="text" 
                                        value={newMessage}
                                        onChange={(e) => setNewMessage(e.target.value)}
                                        placeholder="Type your secret message..."
                                        className="flex-1 bg-transparent border-none outline-none px-3 py-2 text-sm font-medium text-slate-700 dark:text-slate-200"
                                    />
                                    <button 
                                        type="submit"
                                        className="w-10 h-10 bg-indigo-600 text-white rounded-xl flex items-center justify-center hover:bg-indigo-500 transition-all shadow-lg shadow-indigo-500/20"
                                    >
                                        <Send size={18} />
                                    </button>
                                </div>
                            </form>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default BroConnect;
