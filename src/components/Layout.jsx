import React, { useContext } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { TransactionContext } from '../context/TransactionContext';
import { LayoutDashboard, PieChart, Wallet, LogOut, Sun, Moon, Brain, Sparkles, UserX, Users } from 'lucide-react';
import { motion } from 'framer-motion';

const Layout = ({ children }) => {
    const location = useLocation();
    const { logout, deleteAccount, user, theme, toggleTheme } = useContext(TransactionContext);

    const isActive = (path) => location.pathname === path;

    return (
        <div className="min-h-screen bg-[var(--bg-app)] selection:bg-indigo-100 selection:text-indigo-900">
            {/* Minimal Header */}
            <header className="sticky top-0 z-[100] bg-[var(--surface)] border-b border-[var(--border)] shadow-sm backdrop-blur-md bg-opacity-80">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-8">
                        <Link to="/" className="flex items-center gap-2 group">
                            <div className="bg-indigo-600 p-1.5 rounded-lg shadow-sm group-hover:bg-indigo-500 transition-colors">
                                <Wallet className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
                                Hisaab<span className="text-indigo-600">.AI</span>
                            </span>
                        </Link>

                        {/* Desktop Navigation */}
                        <nav className="hidden md:flex items-center gap-1">
                            {[
                                { path: '/', label: 'Overview', icon: LayoutDashboard },
                                { path: '/analysis', label: 'Treasury', icon: PieChart },
                                { path: '/lending', label: 'Ledger', icon: Wallet },
                                { path: '/bot-training', label: 'Bot Brain', icon: Brain },
                                { path: '/friends', label: 'Friends', icon: Users },
                            ].map((item) => (
                                <Link 
                                    key={item.path}
                                    to={item.path} 
                                    className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                                        isActive(item.path) 
                                        ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300' 
                                        : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800'
                                    }`}
                                >
                                    <item.icon size={16} strokeWidth={isActive(item.path) ? 2.5 : 2} />
                                    {item.label}
                                </Link>
                            ))}
                        </nav>
                    </div>

                    <div className="flex items-center gap-3">
                        <button
                            onClick={toggleTheme}
                            className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                            aria-label="Toggle Theme"
                        >
                            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
                        </button>
                        
                        <div className="h-4 w-px bg-slate-200 dark:bg-slate-700 mx-1"></div>

                        <div className="flex items-center gap-3 pr-1">
                            <div className="flex flex-col items-end items-center mr-1">
                                <div className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-900 dark:text-white font-black text-[10px] shadow-sm">
                                    {user?.username?.substring(0, 2).toUpperCase()}
                                </div>
                            </div>
                            <button
                                onClick={logout}
                                className="p-2 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all border border-transparent hover:border-red-100 dark:hover:border-red-900/40"
                                title="Exit Session"
                            >
                                <LogOut className="w-4 h-4" />
                            </button>
                            
                            <button
                                onClick={() => {
                                    if(window.confirm('Are you strictly sure you want to permanently delete your account and ALL associated financial data? This cannot be undone!')) {
                                        deleteAccount();
                                    }
                                }}
                                className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-red-600 transition-all"
                                title="Wipe Data & Delete Account"
                            >
                                <UserX className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content Area */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full min-h-[calc(100vh-4rem)] pb-24 md:pb-8">
                {children}
            </main>

            {/* Mobile Navigation Bar */}
            <nav className="fixed bottom-0 left-0 right-0 bg-[var(--surface)] border-t border-[var(--border)] md:hidden z-[100] pb-safe">
                <div className="flex justify-around items-center h-16">
                    {[
                        { path: '/', label: 'Home', icon: LayoutDashboard },
                        { path: '/analysis', label: 'Analysis', icon: PieChart },
                        { path: '/lending', label: 'Ledger', icon: Wallet },
                        { path: '/bot-training', label: 'Brain', icon: Brain },
                        { path: '/friends', label: 'Friends', icon: Users },
                    ].map((item) => (
                        <Link
                            key={item.path}
                            to={item.path}
                            className={`flex flex-col items-center justify-center w-full h-full transition-colors ${
                                isActive(item.path) ? 'text-indigo-600' : 'text-slate-400'
                            }`}
                        >
                            <item.icon className={`w-5 h-5 mb-1 ${isActive(item.path) ? 'stroke-[2.5px]' : ''}`} />
                            <span className="text-[10px] font-medium tracking-wide uppercase">{item.label}</span>
                        </Link>
                    ))}
                </div>
            </nav>
        </div>
    );
};

export default Layout;
